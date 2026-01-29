import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db, release_db
from utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payouts", tags=["Payouts"])

# Minimum payout threshold (.00)
MIN_PAYOUT_CENTS = 5000 

class PayoutStats(BaseModel):
    balance_cents: int
    total_earnings_cents: int
    pending_payouts_cents: int
    last_payout_at: Optional[datetime]

class PayoutRequestResponse(BaseModel):
    payout_id: str
    amount_cents: int
    status: str
    message: str

@router.get("/stats", response_model=PayoutStats)
async def get_payout_stats(user: dict = Depends(get_current_user)):
    """Get seller's current financial stats."""
    conn = await get_db()
    try:
        # Get seller balance
        seller = await conn.fetchrow(
            "SELECT balance_cents, total_earnings_cents FROM sellers WHERE user_id = ",
            user["id"]
        )
        
        if not seller:
            return PayoutStats(
                balance_cents=0,
                total_earnings_cents=0,
                pending_payouts_cents=0,
                last_payout_at=None
            )

        # Get pending payouts sum
        pending = await conn.fetchval(
            """
            SELECT COALESCE(SUM(amount_cents), 0) 
            FROM payouts 
            WHERE seller_id =  AND status = 'pending'
            """,
            user["id"]
        )

        # Get last payout date
        last_payout = await conn.fetchval(
            """
            SELECT created_at 
            FROM payouts 
            WHERE seller_id =  AND status = 'paid' 
            ORDER BY created_at DESC LIMIT 1
            """,
            user["id"]
        )

        return PayoutStats(
            balance_cents=seller["balance_cents"],
            total_earnings_cents=seller["total_earnings_cents"],
            pending_payouts_cents=pending,
            last_payout_at=last_payout
        )
    finally:
        await release_db(conn)

@router.post("/request", response_model=PayoutRequestResponse)
async def request_payout(user: dict = Depends(get_current_user)):
    """Request a payout of the entire available balance."""
    conn = await get_db()
    try:
        async with conn.transaction():
            # Lock seller row to prevent race conditions
            seller = await conn.fetchrow(
                "SELECT balance_cents FROM sellers WHERE user_id =  FOR UPDATE",
                user["id"]
            )
            
            if not seller:
                raise HTTPException(status_code=403, detail="Not a seller")
                
            balance = seller["balance_cents"]
            
            if balance < MIN_PAYOUT_CENTS:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Minimum payout is . Current balance: "
                )

            # Deduct from balance immediately
            await conn.execute(
                "UPDATE sellers SET balance_cents = 0, updated_at = NOW() WHERE user_id = ",
                user["id"]
            )

            # Create payout record
            payout_id = await conn.fetchval(
                """
                INSERT INTO payouts (id, seller_id, amount_cents, status, created_at)
                VALUES (gen_random_uuid()::text, , , 'pending', NOW())
                RETURNING id
                """,
                user["id"], balance
            )
            
            logger.info(f"Payout requested: {payout_id} for user {user['id']} amount ")

            return PayoutRequestResponse(
                payout_id=payout_id,
                amount_cents=balance,
                status="pending",
                message="Payout request submitted successfully"
            )

    finally:
        await release_db(conn)
