"""
Whop Integration Routes
Handles incoming webhooks from Whop.com to generate licenses.
"""

import hmac
import hashlib
import json
import logging
import secrets
import asyncio
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, BackgroundTasks

from database import get_db, release_db
from utils import generate_license_key, utc_now
from email_service import notify_license_created
from config import ENVIRONMENT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/whop", tags=["Whop"])

async def verify_whop_signature(request: Request, secret: str) -> bool:
    """Verify Whop webhook signature."""
    if not secret:
        return True # Dev mode or unconfigured
        
    signature = request.headers.get("X-Whop-Signature")
    if not signature:
        return False
        
    body = await request.body()
    
    # Whop uses HMAC SHA256
    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(computed, signature)

@router.post("/webhook")
async def whop_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Whop webhooks.
    Event: payment.succeeded
    """
    payload_body = await request.body()
    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Get event type
    event_type = payload.get("action") # Whop uses 'action' field (e.g., 'payment.succeeded')
    # Note: Whop documentation varies, sometimes it's 'type'. We handle common structures.
    if not event_type:
        # Try finding it in 'type'
        event_type = payload.get("type")
    
    if event_type != "payment.succeeded":
        return {"status": "ignored", "reason": f"Event {event_type} not handled"}

    # Extract Data
    data = payload.get("data", {})
    payment_id = data.get("id")
    product_id = data.get("product_id") or data.get("line_items", [{}])[0].get("product_id")
    buyer_email = data.get("email") or data.get("user", {}).get("email")
    buyer_name = data.get("user", {}).get("username") or "Whop Customer"
    
    if not product_id:
        logger.warning(f"[Whop] No product_id in payload: {payment_id}")
        return {"status": "error", "message": "No product_id found"}

    conn = await get_db()
    try:
        # Link Whop Product ID to CodeVault Project
        project = await conn.fetchrow("""
            SELECT id, user_id, name, settings 
            FROM projects 
            WHERE settings->>'whop_product_id' = $1
        """, product_id)

        if not project:
            logger.warning(f"[Whop] No project found for Whop Product ID: {product_id}")
            return {"status": "skipped", "message": "Project not linked"}

        user_id = project["user_id"]

        # Verify Signature
        integration = await conn.fetchrow("""
            SELECT whop_api_key FROM whop_integrations WHERE user_id = $1
        """, user_id)
        
        whop_secret = integration["whop_api_key"] if integration else None
        
        if whop_secret and not await verify_whop_signature(request, whop_secret):
            logger.warning(f"[Whop] Invalid signature for project {project['id']}")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Idempotency check
        existing = await conn.fetchrow("SELECT id FROM whop_purchases WHERE whop_payment_id = $1", payment_id)
        if existing:
            return {"status": "success", "message": "Already processed"}

        # Generate License
        license_id = secrets.token_hex(16)
        license_key = generate_license_key()
        max_machines = 1 
        expires_at = None 

        await conn.execute("""
            INSERT INTO licenses (
                id, project_id, license_key, status, max_machines, client_name, client_email, created_at, notes
            ) VALUES ($1, $2, $3, 'active', $4, $5, $6, NOW(), 'Generated via Whop')
        """, license_id, project["id"], license_key, max_machines, buyer_name, buyer_email)

        # Log Purchase
        purchase_id = secrets.token_hex(16)
        amount_cents = data.get("final_amount", 0)
        
        await conn.execute("""
            INSERT INTO whop_purchases (
                id, user_id, whop_payment_id, license_id, buyer_email, amount_cents, status
            ) VALUES ($1, $2, $3, $4, $5, $6, 'completed')
        """, purchase_id, user_id, payment_id, license_id, buyer_email, amount_cents)

        # Email User
        try:
            background_tasks.add_task(
                notify_license_created,
                client_name=buyer_name,
                client_email=buyer_email,
                license_key=license_key,
                project_name=project["name"],
                expires_at=None,
                max_machines=max_machines,
                features=[]
            )
        except Exception as e:
            logger.error(f"[Whop] Failed to queue email: {e}")

        logger.info(f"[Whop] Generated license {license_key} for payment {payment_id}")
        return {"status": "success", "license_key": license_key}

    finally:
        await release_db(conn)
