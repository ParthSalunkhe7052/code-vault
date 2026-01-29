import logging
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from database import get_db, release_db
from utils import get_current_user
from services.dodo_service import dodo_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Sellers"])

class SellerOnboardRequest(BaseModel):
    payout_details: Dict[str, Any] # e.g. {"upi_id": "user@upi"} or {"bank_account": "..."}

class ProjectMonetizationRequest(BaseModel):
    is_public_store: bool
    price_cents: int
    short_description: str
    long_description: Optional[str] = None
    category: Optional[str] = "automation"

@router.post("/sellers/onboard")
async def onboard_seller(
    data: SellerOnboardRequest,
    user: dict = Depends(get_current_user)
):
    """Register the current user as a seller with payout details."""
    conn = await get_db()
    try:
        # Check if already a seller
        existing = await conn.fetchrow(
            "SELECT user_id FROM sellers WHERE user_id = $1", 
            user["id"]
        )
        
        payout_json = json.dumps(data.payout_details)
        
        if existing:
            # Update existing
            await conn.execute(
                """
                UPDATE sellers 
                SET payout_details = $1, updated_at = NOW() 
                WHERE user_id = $2
                """,
                payout_json, user["id"]
            )
        else:
            # Create new
            await conn.execute(
                """
                INSERT INTO sellers (user_id, payout_details, created_at)
                VALUES ($1, $2, NOW())
                """,
                user["id"], payout_json
            )
            
        return {"status": "success", "message": "Seller profile updated"}
    finally:
        await release_db(conn)

@router.get("/sellers/me")
async def get_seller_profile(user: dict = Depends(get_current_user)):
    """Get current user's seller status."""
    conn = await get_db()
    try:
        seller = await conn.fetchrow(
            "SELECT * FROM sellers WHERE user_id = $1", 
            user["id"]
        )
        
        if not seller:
            return {"is_seller": False}
            
        return {
            "is_seller": True,
            "balance_cents": seller["balance_cents"],
            "total_earnings_cents": seller["total_earnings_cents"],
            "is_verified": seller["is_verified"],
            "payout_details": json.loads(seller["payout_details"]) if seller["payout_details"] else {}
        }
    finally:
        await release_db(conn)

@router.put("/projects/{project_id}/monetization")
async def update_monetization(
    project_id: str,
    data: ProjectMonetizationRequest,
    user: dict = Depends(get_current_user)
):
    """Enable monetization for a project and sync with Dodo."""
    conn = await get_db()
    try:
        # Verify ownership
        project = await conn.fetchrow(
            "SELECT id, name, dodo_product_id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, user["id"]
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Verify user is a seller
        is_seller = await conn.fetchval(
            "SELECT 1 FROM sellers WHERE user_id = $1", 
            user["id"]
        )
        
        if not is_seller:
            raise HTTPException(status_code=403, detail="You must onboard as a seller first")

        dodo_product_id = project["dodo_product_id"]

        # Sync with Dodo if publishing
        if data.is_public_store:
            if not dodo_product_id:
                # Create new product
                dodo_product_id = await dodo_service.create_product(
                    name=project["name"],
                    description=data.short_description,
                    price_cents=data.price_cents
                )
            else:
                # Update existing
                await dodo_service.update_product(
                    product_id=dodo_product_id,
                    name=project["name"],
                    description=data.short_description,
                    price_cents=data.price_cents
                )
        
        # Update DB
        await conn.execute(
            """
            UPDATE projects 
            SET is_public_store = $1,
                price_cents = $2,
                short_description = $3,
                long_description = $4,
                category = $5,
                dodo_product_id = $6,
                updated_at = NOW()
            WHERE id = $7
            """,
            data.is_public_store,
            data.price_cents,
            data.short_description,
            data.long_description,
            data.category,
            dodo_product_id,
            project_id
        )
        
        return {
            "status": "success", 
            "dodo_product_id": dodo_product_id,
            "message": "Monetization settings updated"
        }
    finally:
        await release_db(conn)
