"""
Dodo Payments integration routes for CodeVault.
Handles subscriptions, checkout sessions, and webhooks.

Replaces Stripe integration with Dodo Payments.
"""

import uuid
import secrets
import logging
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from config import (
    DODO_API_KEY,
    DODO_WEBHOOK_SECRET,
    DODO_ENVIRONMENT,
    DODO_PRODUCT_PRO,
    DODO_PRODUCT_ENTERPRISE,
    TIER_LIMITS,
    JWT_SECRET,
    JWT_ALGORITHM,
    ENVIRONMENT,
)
from database import get_db, release_db

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["dodo", "payments"])

# Security
security = HTTPBearer(auto_error=False)


# =============================================================================
# Pydantic Models
# =============================================================================

from pydantic import BaseModel, EmailStr


class CreateCheckoutSessionRequest(BaseModel):
    product_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CreatePortalSessionRequest(BaseModel):
    return_url: Optional[str] = None


class SubscriptionStatus(BaseModel):
    plan_tier: str
    status: str
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    limits: dict


class PublicPurchaseRequest(BaseModel):
    store_slug: str
    buyer_email: EmailStr
    buyer_name: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


# =============================================================================
# Authentication
# =============================================================================


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.exceptions.PyJWTError:
        return None


async def get_current_user_for_dodo(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None),
) -> dict:
    """Verify JWT or API key and return user. Used for Dodo routes."""
    conn = await get_db()
    try:
        # Try JWT token first
        if credentials:
            payload = verify_jwt_token(credentials.credentials)
            if payload:
                user = await conn.fetchrow(
                    "SELECT id, email, name, plan, role, api_key FROM users WHERE id = $1",
                    payload["sub"],
                )
                if user:
                    return dict(user)

        # Try API key
        if x_api_key:
            user = await conn.fetchrow(
                "SELECT id, email, name, plan, role, api_key FROM users WHERE api_key = $1",
                x_api_key,
            )
            if user:
                return dict(user)

        raise HTTPException(status_code=401, detail="Authentication required")
    finally:
        await release_db(conn)


# =============================================================================
# Helper Functions
# =============================================================================


def utc_now():
    return datetime.now(timezone.utc)


def generate_license_key(prefix: str = "LIC") -> str:
    """Generate a unique license key."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    parts = [prefix]
    for _ in range(4):
        segment = "".join(secrets.choice(chars) for _ in range(4))
        parts.append(segment)
    return "-".join(parts)


async def get_user_subscription(user_id: str, conn) -> dict:
    """Get user's current subscription or return free tier defaults."""
    row = await conn.fetchrow(
        """
        SELECT * FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1
    """,
        user_id,
    )

    if not row:
        return {
            "plan_tier": "free",
            "status": "active",
            "current_period_end": None,
            "cancel_at_period_end": False,
            "dodo_customer_id": None,
            "dodo_subscription_id": None,
        }

    return dict(row)


def get_tier_from_product_id(product_id: str) -> str:
    """Map Dodo product ID to tier name."""
    if product_id == DODO_PRODUCT_PRO:
        return "pro"
    elif product_id == DODO_PRODUCT_ENTERPRISE:
        return "enterprise"
    return "free"


async def sync_user_tier(user_id: str, tier: str, conn):
    """Sync tier from subscriptions to users table."""
    try:
        await conn.execute("UPDATE users SET plan = $1 WHERE id = $2", tier, user_id)
        logger.info(f"[Tier Sync] Updated user {user_id} plan to {tier}")
    except Exception as e:
        logger.error(f"[Tier Sync] Failed to sync user {user_id} to {tier}: {e}")


def get_dodo_client():
    """Get initialized Dodo Payments client."""
    from dodopayments import DodoPayments

    if not DODO_API_KEY:
        raise HTTPException(status_code=500, detail="Dodo Payments not configured")

    return DodoPayments(
        bearer_token=DODO_API_KEY,
        environment=DODO_ENVIRONMENT,
    )


# =============================================================================
# Subscription Endpoints
# =============================================================================


@router.get("/subscription/status")
async def get_subscription_status(user: dict = Depends(get_current_user_for_dodo)):
    """Get current user's subscription status and tier limits."""
    conn = await get_db()
    try:
        sub = await get_user_subscription(user["id"], conn)
        tier = sub.get("plan_tier", "free")
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

        # Count current usage
        project_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM projects WHERE user_id = $1
        """,
            user["id"],
        )

        return {
            "plan_tier": tier,
            "status": sub.get("status", "active"),
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "limits": limits,
            "usage": {"projects": project_count},
        }
    finally:
        await release_db(conn)


@router.post("/dodo/create-checkout-session")
async def create_checkout_session(
    data: CreateCheckoutSessionRequest,
    request: Request,
    user: dict = Depends(get_current_user_for_dodo),
):
    """Create a Dodo Payments Checkout session for subscription."""
    if not DODO_API_KEY:
        raise HTTPException(status_code=500, detail="Dodo Payments not configured")

    # Validate product ID
    if data.product_id not in [DODO_PRODUCT_PRO, DODO_PRODUCT_ENTERPRISE]:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    # Default URLs
    base_url = str(request.base_url).rstrip("/")
    success_url = data.success_url or f"{base_url}/billing?success=true"
    cancel_url = data.cancel_url or f"{base_url}/pricing?canceled=true"

    try:
        client = get_dodo_client()

        # Create checkout session with Dodo Payments
        session = client.checkout_sessions.create(
            product_cart=[{"product_id": data.product_id, "quantity": 1}],
            customer={
                "email": user["email"],
                "name": user.get("name", user["email"]),
            },
            return_url=success_url,
            metadata={
                "user_id": user["id"],
                "product_id": data.product_id,
            },
        )

        logger.info(f"[Dodo] Created checkout session for user {user['id']}")

        return {
            "checkout_url": session.checkout_url,
            "session_id": session.session_id,
        }

    except Exception as e:
        logger.error(f"[Dodo] Checkout session error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="Could not create checkout session. Please try again later.",
        )


# =============================================================================
# Webhook Endpoint
# =============================================================================


@router.post("/dodo/webhook")
async def dodo_webhook(
    request: Request,
    webhook_id: str = Header(None, alias="webhook-id"),
    webhook_signature: str = Header(None, alias="webhook-signature"),
    webhook_timestamp: str = Header(None, alias="webhook-timestamp"),
):
    """Handle Dodo Payments webhook events.

    SECURITY: Webhook signature verification is REQUIRED in production.
    Uses standardwebhooks library for verification.
    """
    payload = await request.body()
    payload_text = payload.decode("utf-8")

    # SECURITY: Verify webhook signature
    is_production = ENVIRONMENT == "production"

    if is_production and not DODO_WEBHOOK_SECRET:
        logger.error(
            "[Dodo Webhook] CRITICAL: DODO_WEBHOOK_SECRET not configured in production!"
        )
        raise HTTPException(
            status_code=500,
            detail="Webhook processing unavailable. Server configuration error.",
        )

    # Verify signature using standardwebhooks
    if DODO_WEBHOOK_SECRET:
        try:
            from standardwebhooks.webhooks import Webhook

            wh = Webhook(DODO_WEBHOOK_SECRET)
            headers = {
                "webhook-id": webhook_id or "",
                "webhook-signature": webhook_signature or "",
                "webhook-timestamp": webhook_timestamp or "",
            }

            if not wh.verify(payload_text, headers):
                logger.warning("[Dodo Webhook] Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

            logger.info("[Dodo Webhook] Signature verified successfully")
        except ImportError:
            logger.warning(
                "[Dodo Webhook] standardwebhooks not installed, skipping verification"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Dodo Webhook] Signature verification error: {e}")
            if is_production:
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif is_production:
        raise HTTPException(status_code=401, detail="Missing webhook secret")
    else:
        logger.warning(
            "[Dodo Webhook] DEVELOPMENT MODE: Processing webhook WITHOUT signature verification!"
        )

    # Parse payload
    try:
        event_data = json.loads(payload_text)
    except json.JSONDecodeError as e:
        logger.error(f"[Dodo Webhook] Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event_data.get("type", "")
    data = event_data.get("data", {})

    conn = await get_db()
    try:
        # Idempotency check
        if webhook_id:
            already_processed = await conn.fetchval(
                "SELECT event_id FROM processed_webhook_events WHERE event_id = $1",
                webhook_id,
            )
            if already_processed:
                logger.info(
                    f"[Dodo Webhook] Event {webhook_id} already processed, skipping"
                )
                return {"status": "success", "message": "Event already processed"}

        async with conn.transaction():
            logger.info(f"[Dodo Webhook] Processing event: {event_type}")

            try:
                # Handle different event types
                if event_type == "subscription.active":
                    await handle_subscription_active(data, conn)
                elif event_type == "subscription.cancelled":
                    await handle_subscription_cancelled(data, conn)
                elif event_type == "subscription.renewed":
                    await handle_subscription_renewed(data, conn)
                elif event_type == "subscription.on_hold":
                    await handle_subscription_on_hold(data, conn)
                elif event_type == "subscription.plan_changed":
                    await handle_subscription_plan_changed(data, conn)
                elif event_type == "payment.succeeded":
                    await handle_payment_succeeded(data, conn)
                elif event_type == "payment.failed":
                    await handle_payment_failed(data, conn)
                elif event_type == "refund.succeeded":
                    await handle_refund_succeeded(data, conn)
                else:
                    logger.info(f"[Dodo Webhook] Unhandled event type: {event_type}")

                # Store event ID for idempotency
                if webhook_id:
                    await conn.execute(
                        "INSERT INTO processed_webhook_events (event_id, event_type) VALUES ($1, $2)",
                        webhook_id,
                        event_type,
                    )

                return {"status": "success"}

            except Exception as handler_error:
                logger.error(
                    f"[Dodo Webhook] Handler error for {event_type}: {handler_error}"
                )
                raise handler_error

    except Exception as e:
        logger.error(
            f"[Dodo Webhook] Critical error processing event {webhook_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal error processing webhook",
        )
    finally:
        await release_db(conn)


# =============================================================================
# Webhook Handlers
# =============================================================================


async def handle_subscription_active(data: dict, conn):
    """Handle subscription.active event - activate or create subscription."""
    subscription_id = data.get("subscription_id") or data.get("id")
    customer_id = data.get("customer", {}).get("customer_id") or data.get("customer_id")
    customer_email = data.get("customer", {}).get("email")
    product_id = data.get("product_id")
    metadata = data.get("metadata", {})

    user_id = metadata.get("user_id")

    # If no user_id in metadata, try to find by customer email
    if not user_id and customer_email:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", customer_email
        )
        if user:
            user_id = user["id"]

    if not user_id:
        logger.warning(
            f"[Dodo Webhook] No user found for subscription {subscription_id}"
        )
        return

    tier = get_tier_from_product_id(product_id) if product_id else "pro"

    # Check if subscription record exists
    existing = await conn.fetchrow(
        "SELECT id FROM subscriptions WHERE user_id = $1", user_id
    )

    if existing:
        await conn.execute(
            """
            UPDATE subscriptions SET
                dodo_customer_id = $2,
                dodo_subscription_id = $3,
                plan_tier = $4,
                status = 'active',
                updated_at = NOW()
            WHERE user_id = $1
        """,
            user_id,
            customer_id,
            subscription_id,
            tier,
        )
    else:
        await conn.execute(
            """
            INSERT INTO subscriptions (
                id, user_id, dodo_customer_id, dodo_subscription_id,
                plan_tier, status
            ) VALUES ($1, $2, $3, $4, $5, 'active')
        """,
            str(uuid.uuid4()),
            user_id,
            customer_id,
            subscription_id,
            tier,
        )

    # Sync user tier
    await sync_user_tier(user_id, tier, conn)

    # Refill credits
    credits = TIER_LIMITS.get(tier, {}).get("cloud_builds_per_month", 0)
    if credits > 0:
        await conn.execute(
            "UPDATE users SET build_credits = $1 WHERE id = $2", credits, user_id
        )
        logger.info(f"[Dodo Webhook] Refilled {credits} credits for user {user_id}")

    logger.info(f"[Dodo Webhook] Subscription activated for user {user_id}: {tier}")


async def handle_subscription_cancelled(data: dict, conn):
    """Handle subscription.cancelled event - downgrade to free tier."""
    subscription_id = data.get("subscription_id") or data.get("id")

    result = await conn.fetchrow(
        "SELECT user_id FROM subscriptions WHERE dodo_subscription_id = $1",
        subscription_id,
    )

    if result:
        await conn.execute(
            """
            UPDATE subscriptions SET
                status = 'canceled',
                plan_tier = 'free',
                updated_at = NOW()
            WHERE dodo_subscription_id = $1
        """,
            subscription_id,
        )
        await sync_user_tier(result["user_id"], "free", conn)
        logger.info(f"[Dodo Webhook] Subscription canceled: {subscription_id}")


async def handle_subscription_renewed(data: dict, conn):
    """Handle subscription.renewed event - keep active and refill credits."""
    subscription_id = data.get("subscription_id") or data.get("id")

    result = await conn.fetchrow(
        "SELECT user_id, plan_tier FROM subscriptions WHERE dodo_subscription_id = $1",
        subscription_id,
    )

    if result:
        await conn.execute(
            """
            UPDATE subscriptions SET
                status = 'active',
                updated_at = NOW()
            WHERE dodo_subscription_id = $1
        """,
            subscription_id,
        )

        # Refill credits on renewal
        tier = result["plan_tier"]
        credits = TIER_LIMITS.get(tier, {}).get("cloud_builds_per_month", 0)
        if credits > 0:
            await conn.execute(
                "UPDATE users SET build_credits = $1 WHERE id = $2",
                credits,
                result["user_id"],
            )
            logger.info(
                f"[Dodo Webhook] Monthly refill: {credits} credits for user {result['user_id']}"
            )

        logger.info(f"[Dodo Webhook] Subscription renewed: {subscription_id}")


async def handle_subscription_on_hold(data: dict, conn):
    """Handle subscription.on_hold event - mark as past_due."""
    subscription_id = data.get("subscription_id") or data.get("id")

    await conn.execute(
        """
        UPDATE subscriptions SET
            status = 'past_due',
            updated_at = NOW()
        WHERE dodo_subscription_id = $1
    """,
        subscription_id,
    )
    logger.info(f"[Dodo Webhook] Subscription on hold: {subscription_id}")


async def handle_subscription_plan_changed(data: dict, conn):
    """Handle subscription.plan_changed event - update tier."""
    subscription_id = data.get("subscription_id") or data.get("id")
    new_product_id = data.get("new_product_id") or data.get("product_id")

    tier = get_tier_from_product_id(new_product_id) if new_product_id else None

    if tier:
        result = await conn.fetchrow(
            "SELECT user_id FROM subscriptions WHERE dodo_subscription_id = $1",
            subscription_id,
        )

        if result:
            await conn.execute(
                """
                UPDATE subscriptions SET
                    plan_tier = $2,
                    updated_at = NOW()
                WHERE dodo_subscription_id = $1
            """,
                subscription_id,
                tier,
            )
            await sync_user_tier(result["user_id"], tier, conn)
            logger.info(
                f"[Dodo Webhook] Subscription plan changed to {tier}: {subscription_id}"
            )


async def handle_payment_succeeded(data: dict, conn):
    """Handle payment.succeeded event."""
    subscription_id = data.get("subscription_id")

    if subscription_id:
        await conn.execute(
            """
            UPDATE subscriptions SET
                status = 'active',
                updated_at = NOW()
            WHERE dodo_subscription_id = $1
        """,
            subscription_id,
        )
        logger.info(
            f"[Dodo Webhook] Payment succeeded for subscription: {subscription_id}"
        )


async def handle_payment_failed(data: dict, conn):
    """Handle payment.failed event."""
    subscription_id = data.get("subscription_id")

    if subscription_id:
        await conn.execute(
            """
            UPDATE subscriptions SET
                status = 'past_due',
                updated_at = NOW()
            WHERE dodo_subscription_id = $1
        """,
            subscription_id,
        )
        logger.info(
            f"[Dodo Webhook] Payment failed for subscription: {subscription_id}"
        )


async def handle_refund_succeeded(data: dict, conn):
    """Handle refund.succeeded event - downgrade user."""
    subscription_id = data.get("subscription_id")

    if subscription_id:
        result = await conn.fetchrow(
            "SELECT user_id FROM subscriptions WHERE dodo_subscription_id = $1",
            subscription_id,
        )

        if result:
            await conn.execute(
                """
                UPDATE subscriptions SET
                    status = 'refunded',
                    plan_tier = 'free',
                    updated_at = NOW()
                WHERE dodo_subscription_id = $1
            """,
                subscription_id,
            )
            await sync_user_tier(result["user_id"], "free", conn)
            logger.info(
                f"[Dodo Webhook] Refund processed, downgraded user: {result['user_id']}"
            )


# =============================================================================
# Public Store Endpoints (for end-user license purchases - NO AUTH REQUIRED)
# =============================================================================


@router.get("/public/store/{store_slug}")
async def get_public_store(store_slug: str):
    """Get public project info for store page (no auth required)."""
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            """
            SELECT p.id, p.name, p.description, p.price_cents, p.currency, p.store_slug,
                   u.name as developer_name
            FROM projects p
            JOIN users u ON p.user_id = u.id
            WHERE p.store_slug = $1 AND p.is_public = TRUE AND p.price_cents > 0
        """,
            store_slug,
        )

        if not project:
            raise HTTPException(status_code=404, detail="Store not found")

        return {
            "id": project["id"],
            "name": project["name"],
            "description": project["description"],
            "price": project["price_cents"] / 100,
            "currency": project["currency"],
            "developer": project["developer_name"],
        }
    finally:
        await release_db(conn)


@router.post("/public/purchase")
async def create_license_purchase(data: PublicPurchaseRequest, request: Request):
    """Create a Dodo Payments Checkout session for license purchase (no auth required)."""
    if not DODO_API_KEY:
        raise HTTPException(status_code=500, detail="Dodo Payments not configured")

    conn = await get_db()
    try:
        # Get project info
        project = await conn.fetchrow(
            """
            SELECT id, name, price_cents, currency, user_id
            FROM projects
            WHERE store_slug = $1 AND is_public = TRUE AND price_cents > 0
        """,
            data.store_slug,
        )

        if not project:
            raise HTTPException(status_code=404, detail="Store not found")

        # Check if developer can sell licenses (has pro or enterprise)
        dev_sub = await get_user_subscription(project["user_id"], conn)
        if dev_sub["plan_tier"] == "free":
            raise HTTPException(
                status_code=403, detail="Developer needs Pro plan to sell licenses"
            )

        # Default URLs
        base_url = str(request.base_url).rstrip("/")
        success_url = (
            data.success_url
            or f"{base_url}/license/success?session_id={{CHECKOUT_SESSION_ID}}"
        )
        cancel_url = (
            data.cancel_url or f"{base_url}/store/{data.store_slug}?canceled=true"
        )

        # Create purchase record
        purchase_id = str(uuid.uuid4())

        try:
            client = get_dodo_client()

            # For one-time payments, we need to create a checkout with the price
            # Dodo handles this differently - we pass the price directly
            session = client.checkout_sessions.create(
                product_cart=[
                    {
                        "product_id": f"license_{project['id']}",  # Dynamic product
                        "quantity": 1,
                    }
                ],
                customer={
                    "email": data.buyer_email,
                    "name": data.buyer_name or data.buyer_email,
                },
                return_url=success_url,
                metadata={
                    "purchase_id": purchase_id,
                    "project_id": project["id"],
                    "buyer_email": data.buyer_email,
                    "buyer_name": data.buyer_name or "",
                    "type": "license_purchase",
                },
            )

            # Save purchase record
            await conn.execute(
                """
                INSERT INTO license_purchases (
                    id, project_id, dodo_checkout_session_id, buyer_email, buyer_name,
                    amount_cents, currency, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
            """,
                purchase_id,
                project["id"],
                session.session_id,
                data.buyer_email,
                data.buyer_name,
                project["price_cents"],
                project["currency"],
            )

            return {
                "checkout_url": session.checkout_url,
                "session_id": session.session_id,
            }

        except Exception as e:
            logger.error(f"[Dodo] License purchase checkout error: {str(e)}")
            raise HTTPException(
                status_code=502,
                detail="Could not create checkout session. Please try again later.",
            )
    finally:
        await release_db(conn)


@router.get("/public/license/{license_key}")
async def get_license_portal(license_key: str):
    """Get license info for the license portal (no auth required)."""
    conn = await get_db()
    try:
        license_row = await conn.fetchrow(
            """
            SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features,
                   l.client_name, l.client_email, l.created_at,
                   p.name as project_name, p.description as project_description
            FROM licenses l
            JOIN projects p ON l.project_id = p.id
            WHERE l.license_key = $1
        """,
            license_key,
        )

        if not license_row:
            raise HTTPException(status_code=404, detail="License not found")

        # Count active machines
        machine_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM hardware_bindings
            WHERE license_id = $1 AND is_active = TRUE
        """,
            license_row["id"],
        )

        return {
            "license_key": license_row["license_key"],
            "status": license_row["status"],
            "expires_at": license_row["expires_at"],
            "max_machines": license_row["max_machines"],
            "active_machines": machine_count,
            "features": license_row["features"],
            "client_name": license_row["client_name"],
            "created_at": license_row["created_at"],
            "project": {
                "name": license_row["project_name"],
                "description": license_row["project_description"],
            },
        }
    finally:
        await release_db(conn)


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.post("/subscription/force-sync")
async def force_sync_subscription_tiers(
    user: dict = Depends(get_current_user_for_dodo),
):
    """Admin only: Force sync all users' plans with their subscription tiers."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    conn = await get_db()
    try:
        result = await conn.execute("""
            UPDATE users u
            SET plan = sub_query.plan_tier
            FROM (
                SELECT DISTINCT ON (user_id) user_id, plan_tier
                FROM subscriptions
                ORDER BY user_id, created_at DESC
            ) AS sub_query
            WHERE u.id = sub_query.user_id AND u.plan != sub_query.plan_tier
        """)

        count = result.replace("UPDATE ", "")

        return {
            "status": "success",
            "message": f"Synced tiers for {count} users",
            "updated_count": int(count) if count.isdigit() else 0,
        }
    finally:
        await release_db(conn)
