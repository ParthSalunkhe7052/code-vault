"""
Dodo Payments Webhook Handler - Marketplace Payment Fulfillment
Phase 2: Buyer Storefront Implementation

Handles payment.succeeded webhooks from Dodo to:
1. Auto-generate license for buyer
2. Record sale in database
3. Credit seller balance (minus 10% platform fee)
4. Send purchase confirmation email
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel

from database import get_db, release_db
from services.dodo_service import dodo_service
from services.storage_service import storage_service
from config import DODO_WEBHOOK_SECRET
from utils import generate_license_key
from email_service import email_service, EmailMessage, _get_base_template

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

# Platform fee percentage (10%)
PLATFORM_FEE_PERCENT = 10


# =============================================================================
# Pydantic Models
# =============================================================================


class DodoWebhookPayload(BaseModel):
    """Dodo webhook event payload"""

    event_type: str
    payment_id: Optional[str] = None
    product_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None
    customer: Optional[dict] = None


# =============================================================================
# Email Template for Purchase Receipt
# =============================================================================


def create_purchase_receipt_email(
    buyer_email: str,
    product_name: str,
    license_key: str,
    amount_cents: int,
    currency: str,
    seller_name: str,
    download_url: Optional[str] = None,
) -> EmailMessage:
    """Create purchase receipt email with license key and download link."""
    amount_formatted = f"${amount_cents / 100:.2f} {currency.upper()}"
    
    download_section = ""
    if download_url:
        download_section = f"""
        <div style="margin: 24px 0; text-align: center;">
            <a href="{download_url}" style="background-color: #06b6d4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Download {product_name}</a>
            <p style="font-size: 12px; color: #64748b; margin-top: 8px;">Link expires in 24 hours.</p>
        </div>
        """

    content = f"""
    <div class="content">
        <p>Hello,</p>
        
        <div class="alert alert-success">
            <strong>🎉 Purchase Successful!</strong><br>
            Thank you for your purchase on CodeVault Marketplace.
        </div>
        
        <p>Here are your purchase details:</p>
        
        <div class="details">
            <div class="details-row">
                <span class="details-label">Product</span>
                <span class="details-value">{product_name}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Seller</span>
                <span class="details-value">{seller_name}</span>
            </div>
            <div class="details-row">
                <span class="details-label">Amount Paid</span>
                <span class="details-value">{amount_formatted}</span>
            </div>
            <div class="details-row">
                <span class="details-label">License Key</span>
                <span class="details-value" style="font-family: monospace; font-size: 16px; color: #6366f1;">{license_key}</span>
            </div>
        </div>
        
        {download_section}
        
        <p><strong>Important:</strong> Please save your license key securely. You will need it to activate the software.</p>
        
        <p>If you have any questions about your purchase, please contact the seller or our support team.</p>
        
        <p>Best regards,<br>The CodeVault Marketplace Team</p>
    </div>
    """

    return EmailMessage(
        to=buyer_email,
        subject=f"🎉 Purchase Confirmed - {product_name}",
        html_body=_get_base_template(content, "Purchase Receipt"),
        text_body=f"Thank you for your purchase of {product_name}! Your license key: {license_key}. Amount paid: {amount_formatted}. Download here: {download_url or 'N/A'}",
    )


# =============================================================================
# Webhook Handler
# =============================================================================


@router.post("/dodo")
async def handle_dodo_webhook(
    request: Request,
    dodo_signature: Optional[str] = Header(None, alias="dodo-signature"),
):
    """
    Handle Dodo payment webhooks for marketplace purchases.

    Flow:
    1. Verify webhook signature
    2. Extract payment metadata (project_id, seller_id, buyer_email)
    3. Generate license key for buyer
    4. Calculate platform fee (10%) and seller earnings
    5. Update seller balance
    6. Record sale in database
    7. Send purchase confirmation email
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature (if secret is configured)
    if DODO_WEBHOOK_SECRET:
        if not dodo_signature:
            logger.warning("Missing dodo-signature header")
            raise HTTPException(status_code=401, detail="Missing signature")

        is_valid = await dodo_service.verify_webhook_signature(
            body, dodo_signature, DODO_WEBHOOK_SECRET
        )

        if not is_valid:
            logger.warning("Invalid Dodo webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse webhook payload
    try:
        import json

        payload = json.loads(body)
        logger.info(f"Dodo webhook received: {payload.get('event_type', 'unknown')}")
    except json.JSONDecodeError:
        logger.error("Failed to parse webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Handle different event types
    event_type = payload.get("event_type") or payload.get("type") or ""

    # Process payment.succeeded events
    if event_type in [
        "payment.succeeded",
        "payment_intent.succeeded",
        "payment.completed",
    ]:
        await process_successful_payment(payload)
    else:
        logger.info(f"Ignoring webhook event type: {event_type}")

    return {"status": "ok"}


async def process_successful_payment(payload: dict):
    """
    Process a successful payment and fulfill the order.
    """
    conn = await get_db()
    try:
        # Extract payment details
        payment_id = payload.get("payment_id") or payload.get("id") or ""
        amount = payload.get("amount") or 0
        currency = payload.get("currency") or "USD"

        # Handle amount - could be dollars or cents depending on Dodo response
        # If amount is a float like 10.00, convert to cents
        if isinstance(amount, float) and amount < 1000:
            amount_cents = int(amount * 100)
        else:
            amount_cents = int(amount)

        # Extract metadata
        metadata = payload.get("metadata") or {}
        project_id = metadata.get("project_id")
        seller_id = metadata.get("seller_id")

        # Get buyer email from metadata or customer object
        buyer_email = metadata.get("buyer_email") or ""
        if not buyer_email:
            customer = payload.get("customer") or {}
            buyer_email = customer.get("email") or ""

        if not project_id or not seller_id:
            logger.error(
                f"Missing metadata in payment {payment_id}: project_id={project_id}, seller_id={seller_id}"
            )
            return

        # Check if this payment was already processed (idempotency)
        existing_sale = await conn.fetchrow(
            "SELECT id FROM sales WHERE dodo_payment_id = $1", payment_id
        )
        if existing_sale:
            logger.info(f"Payment {payment_id} already processed, skipping")
            return

        # Get project details including the linked build artifact
        project = await conn.fetchrow(
            """
            SELECT id, name, user_id, price_cents, currency, current_build_id
            FROM projects
            WHERE id = $1
            """,
            project_id,
        )

        if not project:
            logger.error(f"Project not found: {project_id}")
            return

        # Get seller details
        seller = await conn.fetchrow(
            "SELECT id, name, email FROM users WHERE id = $1", seller_id
        )

        if not seller:
            logger.error(f"Seller not found: {seller_id}")
            return

        # Calculate fees
        platform_fee_cents = int(amount_cents * PLATFORM_FEE_PERCENT / 100)
        seller_earnings_cents = amount_cents - platform_fee_cents
        
        # Get Download Link (if a build is linked)
        download_url = None
        current_build_id = project["current_build_id"]
        
        if current_build_id:
            # Look up the build artifact
            artifact = await conn.fetchrow(
                """
                SELECT download_key, download_filename 
                FROM cloud_builds 
                WHERE id = $1 AND status = 'success'
                """,
                current_build_id
            )
            
            if artifact and artifact["download_key"]:
                # Generate presigned URL (valid for 24 hours)
                download_url = await storage_service.generate_presigned_url(
                    artifact["download_key"], 
                    expiration=86400
                )
            else:
                logger.warning(f"No successful artifact found for build {current_build_id}")
        else:
            logger.warning(f"Project {project_id} has no linked build artifact for sale")

        # Generate license key for buyer
        license_key = generate_license_key(prefix="MKT")
        license_id = secrets.token_hex(16)
        sale_id = secrets.token_hex(16)

        # Create license for buyer
        await conn.execute(
            """
            INSERT INTO licenses (
                id, project_id, license_key, client_name, client_email,
                max_machines, features, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """,
            license_id,
            project_id,
            license_key,
            buyer_email.split("@")[0] if buyer_email else "Marketplace Buyer",
            buyer_email,
            1,  # Default max machines
            ["standard"],  # Default features
            "active",
        )

        # Record the sale
        await conn.execute(
            """
            INSERT INTO sales (
                id, project_id, seller_id, buyer_email, license_id,
                amount_cents, platform_fee_cents, seller_earnings_cents,
                dodo_payment_id, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
            """,
            sale_id,
            project_id,
            seller_id,
            buyer_email,
            license_id,
            amount_cents,
            platform_fee_cents,
            seller_earnings_cents,
            payment_id,
            "completed",
        )

        # Update seller balance and total earnings
        await conn.execute(
            """
            UPDATE sellers
            SET balance_cents = balance_cents + $1,
                total_earnings_cents = total_earnings_cents + $1,
                updated_at = NOW()
            WHERE user_id = $2
            """,
            seller_earnings_cents,
            seller_id,
        )

        logger.info(
            f"Sale recorded: sale_id={sale_id}, project={project['name']}, "
            f"buyer={buyer_email}, amount=${amount_cents / 100:.2f}, "
            f"seller_earnings=${seller_earnings_cents / 100:.2f}"
        )

        # Send purchase confirmation email to buyer
        if buyer_email:
            try:
                email_message = create_purchase_receipt_email(
                    buyer_email=buyer_email,
                    product_name=project["name"],
                    license_key=license_key,
                    amount_cents=amount_cents,
                    currency=currency,
                    seller_name=seller["name"],
                    download_url=download_url
                )
                await email_service.send_async(email_message)
                logger.info(f"Purchase receipt sent to {buyer_email}")
            except Exception as e:
                logger.error(f"Failed to send purchase email: {e}")

    except Exception as e:
        logger.error(f"Error processing payment: {e}", exc_info=True)
        raise

    finally:
        await release_db(conn)


# =============================================================================
# Test Endpoint (Development Only)
# =============================================================================


@router.post("/dodo/test")
async def test_dodo_webhook():
    """
    Test endpoint to simulate a Dodo payment webhook.
    Only for development/testing purposes.
    """
    from config import DODO_ENVIRONMENT

    if DODO_ENVIRONMENT == "live_mode":
        raise HTTPException(
            status_code=403, detail="Test endpoint disabled in production"
        )

    # Simulate webhook payload
    test_payload = {
        "event_type": "payment.succeeded",
        "payment_id": f"test_{secrets.token_hex(8)}",
        "amount": 10.00,
        "currency": "USD",
        "metadata": {
            "project_id": "test_project_id",
            "seller_id": "test_seller_id",
            "buyer_email": "test@example.com",
        },
    }

    return {
        "message": "Test webhook payload generated",
        "payload": test_payload,
        "note": "POST this payload to /api/v1/webhooks/dodo to test",
    }
