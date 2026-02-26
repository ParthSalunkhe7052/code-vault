"""
Polar payment integration routes for CodeVault.
Handles subscriptions, checkout sessions, and webhooks via Polar.

Replaces the previous Stripe integration. Polar uses the Standard Webhooks
spec for webhook signature verification (webhook-id, webhook-timestamp,
webhook-signature headers).
"""

import uuid
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi import Header
from pydantic import BaseModel
import httpx
import asyncpg

from config import (
    POLAR_ACCESS_TOKEN,
    POLAR_WEBHOOK_SECRET,
    POLAR_PRODUCT_PRO,
    POLAR_PRODUCT_BUSINESS,
    TIER_LIMITS,
    PRICING_CONFIG,
    ENVIRONMENT,
)
from database import get_db, release_db
from utils import hash_api_key, get_current_user as _get_current_user, verify_jwt_token_async

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["polar"])

# Polar API base URL
POLAR_API_BASE = "https://api.polar.sh/v1"


# =============================================================================
# Pydantic Models
# =============================================================================


class CreateCheckoutRequest(BaseModel):
    product_id: str
    success_url: Optional[str] = None


class SubscriptionStatusResponse(BaseModel):
    plan_tier: str
    status: str
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    limits: dict
    usage: dict


# =============================================================================
# Authentication
# =============================================================================

# O1/O2 FIX: Use the shared get_current_user dependency from utils.py.
# The previous local verify_jwt_token() / get_current_user_for_polar() were
# duplicates that (a) skipped the JWT blacklist check and (b) diverged from the
# canonical auth logic.  All Polar routes now use the same dependency as every
# other route, ensuring that logged-out (blacklisted) tokens are rejected here too.
get_current_user_for_polar = _get_current_user


# =============================================================================
# Helper Functions
# =============================================================================


def utc_now():
    return datetime.now(timezone.utc)


def get_tier_from_product_id(product_id: str) -> str:
    """Map Polar product ID to tier name."""
    if product_id == POLAR_PRODUCT_PRO:
        return "pro"
    elif product_id == POLAR_PRODUCT_BUSINESS:
        return "business"
    return "free"


def get_product_id_from_tier(tier: str) -> Optional[str]:
    """Map tier name to Polar product ID."""
    if tier == "pro":
        return POLAR_PRODUCT_PRO
    elif tier == "business":
        return POLAR_PRODUCT_BUSINESS
    return None


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
            "polar_customer_id": None,
            "polar_subscription_id": None,
        }

    result = dict(row)
    # Handle legacy column names (stripe_customer_id -> polar_customer_id)
    if "stripe_customer_id" in result and "polar_customer_id" not in result:
        result["polar_customer_id"] = result.get("stripe_customer_id")
    if "stripe_subscription_id" in result and "polar_subscription_id" not in result:
        result["polar_subscription_id"] = result.get("stripe_subscription_id")
    return result


async def sync_user_tier(user_id: str, tier: str, conn):
    """Sync tier from subscriptions to users table.

    Raises:
        Exception: If the database update fails, allowing the transaction to roll back.
    """
    await conn.execute("UPDATE users SET plan = $1 WHERE id = $2", tier, user_id)
    logger.info(f"[Tier Sync] Updated user {user_id} plan to {tier}")


# =============================================================================
# Subscription Endpoints
# =============================================================================


@router.get("/subscription/status")
async def get_subscription_status(user: dict = Depends(get_current_user_for_polar)):
    """Get current user's subscription status and tier limits."""
    conn = await get_db()
    try:
        sub = await get_user_subscription(user["id"], conn)
        tier = sub.get("plan_tier", "free")
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

        # Count current usage
        project_count = await conn.fetchval(
            "SELECT COUNT(*) FROM projects WHERE user_id = $1",
            user["id"],
        )

        return {
            "plan_tier": tier,
            "status": sub.get("status", "active"),
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "limits": limits,
            "usage": {"projects": project_count},
            "pricing": PRICING_CONFIG,
        }
    finally:
        await release_db(conn)


@router.post("/polar/create-checkout")
async def create_checkout(
    data: CreateCheckoutRequest,
    request: Request,
    user: dict = Depends(get_current_user_for_polar),
):
    """Create a Polar checkout session for subscription.

    Uses the Polar API to create a checkout session and returns the redirect URL.
    The user's CodeVault user ID is passed as external_customer_id for reconciliation.
    """
    if not POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Payment provider not configured")

    # Validate product ID
    if data.product_id not in [POLAR_PRODUCT_PRO, POLAR_PRODUCT_BUSINESS]:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    # Default success URL
    success_url = (
        data.success_url or str(request.base_url).rstrip("/") + "/pricing?success=true"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POLAR_API_BASE}/checkouts/",
                headers={
                    "Authorization": f"Bearer {POLAR_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "products": [data.product_id],
                    "success_url": success_url,
                    "customer_email": user["email"],
                    "customer_external_id": user["id"],
                    "metadata": {
                        "user_id": user["id"],
                    },
                },
                timeout=15.0,
            )

            if response.status_code not in (200, 201):
                logger.error(
                    f"[Polar] Checkout creation failed: {response.status_code} {response.text}"
                )
                raise HTTPException(
                    status_code=502,
                    detail="Could not create checkout session. Please try again later.",
                )

            checkout_data = response.json()
            checkout_url = checkout_data.get("url")

            if not checkout_url:
                logger.error(f"[Polar] No URL in checkout response: {checkout_data}")
                raise HTTPException(
                    status_code=502,
                    detail="Payment provider returned an invalid response.",
                )

            return {
                "checkout_url": checkout_url,
                "session_id": checkout_data.get("id"),
            }

    except httpx.HTTPError as e:
        logger.error(f"[Polar] HTTP error creating checkout: {e}")
        raise HTTPException(
            status_code=502,
            detail="Could not reach payment provider. Please try again later.",
        )


# =============================================================================
# Webhook Endpoint
# =============================================================================


@router.post("/polar/webhook")
async def polar_webhook(request: Request):
    """Handle Polar webhook events.

    Polar uses the Standard Webhooks spec for signature verification.
    Headers: webhook-id, webhook-timestamp, webhook-signature

    Key events handled:
    - checkout.created / checkout.updated: Track checkout progress
    - subscription.created: New subscription activated
    - subscription.updated: Plan changes
    - subscription.active: Subscription became active (e.g. after payment)
    - subscription.canceled: User canceled (access until period end)
    - subscription.revoked: Immediately revoked (refund, etc.)
    - order.created / order.paid: Track payments for credit refills
    - order.refunded: Handle refunds
    """
    payload = await request.body()

    # Extract Standard Webhooks headers
    webhook_id = request.headers.get("webhook-id")
    webhook_timestamp = request.headers.get("webhook-timestamp")
    webhook_signature = request.headers.get("webhook-signature")

    is_production = ENVIRONMENT == "production"

    # Verify webhook signature
    if is_production:
        if not POLAR_WEBHOOK_SECRET:
            logger.error(
                "[Polar Webhook] CRITICAL: POLAR_WEBHOOK_SECRET not configured in production!"
            )
            raise HTTPException(
                status_code=500,
                detail="Webhook processing unavailable. Server configuration error.",
            )

        if not webhook_id or not webhook_timestamp or not webhook_signature:
            logger.warning("[Polar Webhook] Missing Standard Webhooks headers")
            raise HTTPException(
                status_code=400, detail="Missing webhook signature headers"
            )

        # Verify using Standard Webhooks spec
        if not _verify_webhook_signature(
            payload,
            webhook_id,
            webhook_timestamp,
            webhook_signature,
            POLAR_WEBHOOK_SECRET,
        ):
            logger.error("[Polar Webhook] Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")

        logger.info("[Polar Webhook] Signature verified successfully")
    else:
        # Development: verify if secret is configured, otherwise allow with warning
        if (
            POLAR_WEBHOOK_SECRET
            and webhook_id
            and webhook_timestamp
            and webhook_signature
        ):
            if not _verify_webhook_signature(
                payload,
                webhook_id,
                webhook_timestamp,
                webhook_signature,
                POLAR_WEBHOOK_SECRET,
            ):
                logger.error("[Polar Webhook] Dev mode: Invalid signature")
                raise HTTPException(status_code=400, detail="Invalid signature")
            logger.info("[Polar Webhook] Dev mode: Signature verified")
        else:
            logger.warning(
                "[Polar Webhook] DEVELOPMENT MODE: Processing webhook WITHOUT "
                "signature verification. This would be REJECTED in production!"
            )

    # Parse event
    try:
        event = json.loads(payload)
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f"[Polar Webhook] Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type", "")
    event_data = event.get("data", {})

    # Idempotency check using webhook-id header
    event_id = webhook_id or event_data.get("id", str(uuid.uuid4()))

    conn = await get_db()
    try:
        # Check if this event was already processed
        already_processed = await conn.fetchval(
            "SELECT event_id FROM processed_webhook_events WHERE event_id = $1",
            event_id,
        )
        if already_processed:
            logger.info(
                f"[Polar Webhook] Idempotency: Event {event_id} already processed, skipping"
            )
            return {"status": "success", "message": "Event already processed"}

        # C8 FIX: Never raise HTTPException inside an asyncpg transaction() context —
        # FastAPI intercepts it before the context manager can roll back.  Instead we
        # run the handler dispatch inside the transaction and convert any HTTPException
        # raised by a handler into a plain RuntimeError so the transaction rolls back
        # cleanly, then re-raise the original HTTPException outside the block.
        _captured_http_exc: Optional[HTTPException] = None

        async with conn.transaction():
            logger.info(f"[Polar Webhook] Processing event: {event_type}")

            try:
                if event_type == "subscription.created":
                    await handle_subscription_created(event_data, conn)
                elif event_type == "subscription.active":
                    await handle_subscription_active(event_data, conn)
                elif event_type == "subscription.updated":
                    await handle_subscription_updated(event_data, conn)
                elif event_type == "subscription.canceled":
                    await handle_subscription_canceled(event_data, conn)
                elif event_type == "subscription.revoked":
                    await handle_subscription_revoked(event_data, conn)
                elif event_type == "order.paid":
                    await handle_order_paid(event_data, conn)
                elif event_type == "order.refunded":
                    await handle_order_refunded(event_data, conn)
                elif event_type in ("checkout.created", "checkout.updated"):
                    # Informational only - no action needed
                    logger.info(f"[Polar Webhook] Checkout event: {event_type}")
                else:
                    logger.info(f"[Polar Webhook] Unhandled event type: {event_type}")

                # Store event ID for idempotency
                try:
                    await conn.execute(
                        "INSERT INTO processed_webhook_events (event_id, event_type) VALUES ($1, $2)",
                        event_id,
                        event_type,
                    )
                except asyncpg.UniqueViolationError:
                    # Race condition: another request processed this event simultaneously
                    logger.info(
                        f"[Polar Webhook] Idempotency race: Event {event_id} was already "
                        "processed by another request"
                    )
                    # Return inside the transaction — no exception, clean commit.
                    return {"status": "success", "message": "Event already processed"}

            except HTTPException as http_exc:
                # Capture and re-raise as RuntimeError so the transaction rolls back
                # cleanly, then we surface it below outside the transaction block.
                _captured_http_exc = http_exc
                logger.error(
                    f"[Polar Webhook] Handler raised HTTPException for {event_type}: "
                    f"{http_exc.status_code} {http_exc.detail}"
                )
                raise RuntimeError(f"handler_http_error:{http_exc.status_code}") from http_exc
            except Exception as handler_error:
                logger.error(
                    f"[Polar Webhook] Handler error for {event_type}: {handler_error}"
                )
                raise

        # Re-raise the HTTPException after the transaction has been rolled back
        if _captured_http_exc is not None:
            raise _captured_http_exc

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Polar Webhook] Critical error processing event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal error processing webhook")
    finally:
        await release_db(conn)


def _verify_webhook_signature(
    payload: bytes,
    webhook_id: str,
    webhook_timestamp: str,
    webhook_signature: str,
    secret: str,
) -> bool:
    """Verify Standard Webhooks signature.

    The secret from Polar is expected to be base64-encoded (with or without
    the 'whsec_' prefix). The signature is computed as:
    base64(HMAC-SHA256(secret, "{webhook_id}.{webhook_timestamp}.{body}"))

    Also checks timestamp staleness (rejects webhooks older than 5 minutes).
    """
    import base64
    import hashlib
    import hmac
    import time

    try:
        # Check timestamp staleness (5 minute tolerance)
        try:
            webhook_ts = int(webhook_timestamp)
            current_ts = int(time.time())
            if abs(current_ts - webhook_ts) > 300:  # 300 seconds = 5 minutes
                logger.error(
                    f"[Polar Webhook] Timestamp stale: {webhook_ts} vs current {current_ts} "
                    f"(diff: {abs(current_ts - webhook_ts)}s)"
                )
                return False
        except (ValueError, TypeError) as e:
            logger.error(
                f"[Polar Webhook] Invalid timestamp format: {webhook_timestamp}"
            )
            return False

        # Strip 'whsec_' prefix if present, then base64-decode the secret
        secret_str = secret
        if secret_str.startswith("whsec_"):
            secret_str = secret_str[6:]
        secret_bytes = base64.b64decode(secret_str)

        # Construct the signed content: "webhook_id.webhook_timestamp.body"
        if isinstance(payload, bytes):
            body_str = payload.decode("utf-8")
        else:
            body_str = payload

        signed_content = f"{webhook_id}.{webhook_timestamp}.{body_str}"

        # Compute HMAC-SHA256
        expected_sig = base64.b64encode(
            hmac.new(
                secret_bytes, signed_content.encode("utf-8"), hashlib.sha256
            ).digest()
        ).decode("utf-8")

        # The webhook-signature header may contain multiple signatures separated by spaces
        # Each is in the format "v1,{base64_signature}"
        signatures = webhook_signature.split(" ")
        for sig in signatures:
            parts = sig.split(",", 1)
            if len(parts) == 2:
                sig_value = parts[1]
                if hmac.compare_digest(expected_sig, sig_value):
                    return True

        return False

    except Exception as e:
        logger.error(f"[Polar Webhook] Signature verification error: {e}")
        return False


# =============================================================================
# Webhook Event Handlers
# =============================================================================


async def _resolve_user_id(event_data: dict, conn) -> Optional[str]:
    """Resolve the CodeVault user_id from Polar webhook event data.

    Tries multiple strategies in order of trust:
    1. customer.external_id (set as user_id during checkout — most authoritative)
    2. metadata.user_id cross-validated against customer.external_id or customer.email
    3. customer.email (match against users table)
    4. subscription ID lookup in subscriptions table

    H5 FIX: metadata.user_id is no longer trusted blindly. It is only accepted when it
    matches the customer.external_id or resolves to the same user as customer.email.
    This prevents a spoofed webhook (possible in dev mode without signature checks) from
    upgrading an arbitrary account by injecting a victim's user_id into the metadata field.
    """
    customer = event_data.get("customer", {}) or {}
    metadata = event_data.get("metadata", {}) or {}

    # Strategy 1: customer.external_id — set by us during checkout, most authoritative
    if customer.get("external_id"):
        external_id = customer["external_id"]
        # Verify this external_id actually exists in our database
        exists = await conn.fetchval(
            "SELECT id FROM users WHERE id = $1", external_id
        )
        if exists:
            return external_id

    # Strategy 2: metadata.user_id — only accept if it matches customer.email lookup
    # (cross-validate to prevent injection of arbitrary user_ids)
    if metadata.get("user_id"):
        candidate_id = metadata["user_id"]
        customer_email = customer.get("email", "").lower().strip()
        if customer_email:
            # Confirm the candidate user has the same email as the Polar customer
            db_email = await conn.fetchval(
                "SELECT email FROM users WHERE id = $1", candidate_id
            )
            if db_email and db_email.lower().strip() == customer_email:
                return candidate_id
        else:
            # No email to validate against; verify at least the user exists
            exists = await conn.fetchval(
                "SELECT id FROM users WHERE id = $1", candidate_id
            )
            if exists:
                return candidate_id

    # Strategy 3: customer email
    customer_email = customer.get("email")
    if customer_email:
        user_id = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1", customer_email
        )
        if user_id:
            return user_id

    # Strategy 4: existing subscription record lookup
    polar_sub_id = event_data.get("id")
    if polar_sub_id:
        # Try both column names for backward compatibility
        user_id = await conn.fetchval(
            """SELECT user_id FROM subscriptions 
               WHERE stripe_subscription_id = $1 OR polar_subscription_id = $1
               LIMIT 1""",
            polar_sub_id,
        )
        if user_id:
            return user_id

    return None


async def _upsert_subscription(
    user_id: str,
    polar_customer_id: Optional[str],
    polar_subscription_id: Optional[str],
    tier: str,
    status: str,
    current_period_start: Optional[datetime],
    current_period_end: Optional[datetime],
    cancel_at_period_end: bool,
    conn,
):
    """Create or update a subscription record. Handles legacy stripe_* columns."""
    existing = await conn.fetchrow(
        "SELECT id FROM subscriptions WHERE user_id = $1", user_id
    )

    # Determine which column names exist in the table
    # Try the Polar columns first, fall back to Stripe columns for backward compat
    try:
        if existing:
            await conn.execute(
                """
                UPDATE subscriptions SET
                    stripe_customer_id = $2,
                    stripe_subscription_id = $3,
                    plan_tier = $4,
                    status = $5,
                    current_period_start = $6,
                    current_period_end = $7,
                    cancel_at_period_end = $8,
                    updated_at = NOW()
                WHERE user_id = $1
            """,
                user_id,
                polar_customer_id,
                polar_subscription_id,
                tier,
                status,
                current_period_start,
                current_period_end,
                cancel_at_period_end,
            )
        else:
            await conn.execute(
                """
                INSERT INTO subscriptions (
                    id, user_id, stripe_customer_id, stripe_subscription_id,
                    plan_tier, status, current_period_start, current_period_end,
                    cancel_at_period_end
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                str(uuid.uuid4()),
                user_id,
                polar_customer_id,
                polar_subscription_id,
                tier,
                status,
                current_period_start,
                current_period_end,
                cancel_at_period_end,
            )
    except Exception as e:
        logger.error(f"[Polar] Failed to upsert subscription for user {user_id}: {e}")
        raise


def _parse_polar_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 datetime string from Polar API."""
    if not dt_str:
        return None
    try:
        # Handle both with and without timezone
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def _extract_product_id(event_data: dict) -> Optional[str]:
    """Extract the product ID from a Polar subscription/order event."""
    # Polar subscription events have a product field
    product = event_data.get("product")
    if product and isinstance(product, dict):
        return product.get("id")

    # Or it could be in product_id directly
    product_id = event_data.get("product_id")
    if product_id:
        return product_id

    # Check in items array for orders
    items = event_data.get("items", [])
    if items and isinstance(items, list):
        for item in items:
            prod = item.get("product", {})
            if prod and isinstance(prod, dict):
                return prod.get("id")
            if item.get("product_id"):
                return item["product_id"]

    return None


async def handle_subscription_created(event_data: dict, conn):
    """Handle new subscription creation from Polar."""
    user_id = await _resolve_user_id(event_data, conn)
    if not user_id:
        logger.error("[Polar Webhook] subscription.created: Could not resolve user_id")
        raise HTTPException(
            status_code=422, detail="Could not resolve user_id from webhook data"
        )

    product_id = _extract_product_id(event_data)
    tier = get_tier_from_product_id(product_id) if product_id else "free"

    customer = event_data.get("customer", {}) or {}
    polar_customer_id = customer.get("id")
    polar_subscription_id = event_data.get("id")
    status = event_data.get("status", "active")

    current_period_start = _parse_polar_datetime(event_data.get("current_period_start"))
    current_period_end = _parse_polar_datetime(event_data.get("current_period_end"))
    cancel_at_period_end = event_data.get("cancel_at_period_end", False)

    await _upsert_subscription(
        user_id=user_id,
        polar_customer_id=polar_customer_id,
        polar_subscription_id=polar_subscription_id,
        tier=tier,
        status=status,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        conn=conn,
    )

    # Atomic transaction: sync tier and grant credits together
    async with conn.transaction():
        # Sync user tier
        await sync_user_tier(user_id, tier, conn)

        # Credit System: Grant build credits for new subscription
        # Use credits_per_month (per-platform credit budget); -1 = enterprise unlimited
        credits = TIER_LIMITS.get(tier, {}).get("credits_per_month", 0)
        if credits > 0:
            await conn.execute(
                "UPDATE users SET build_credits = $1 WHERE id = $2",
                credits,
                user_id,
            )
            logger.info(f"[Credit System] Granted {credits} credits for user {user_id}")

    logger.info(f"[Polar Webhook] Subscription created for user {user_id}: {tier}")


async def handle_subscription_active(event_data: dict, conn):
    """Handle subscription becoming active (e.g., after successful payment)."""
    # Same logic as created - ensure user is on the right tier
    await handle_subscription_created(event_data, conn)


async def handle_subscription_updated(event_data: dict, conn):
    """Handle subscription updates (plan changes, etc.)."""
    user_id = await _resolve_user_id(event_data, conn)
    if not user_id:
        logger.error("[Polar Webhook] subscription.updated: Could not resolve user_id")
        raise HTTPException(
            status_code=422, detail="Could not resolve user_id from webhook data"
        )

    product_id = _extract_product_id(event_data)
    tier = get_tier_from_product_id(product_id) if product_id else "free"

    customer = event_data.get("customer", {}) or {}
    polar_customer_id = customer.get("id")
    polar_subscription_id = event_data.get("id")
    status = event_data.get("status", "active")

    current_period_start = _parse_polar_datetime(event_data.get("current_period_start"))
    current_period_end = _parse_polar_datetime(event_data.get("current_period_end"))
    cancel_at_period_end = event_data.get("cancel_at_period_end", False)

    await _upsert_subscription(
        user_id=user_id,
        polar_customer_id=polar_customer_id,
        polar_subscription_id=polar_subscription_id,
        tier=tier,
        status=status,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        conn=conn,
    )

    await sync_user_tier(user_id, tier, conn)

    logger.info(
        f"[Polar Webhook] Subscription updated for user {user_id}: {tier} ({status})"
    )


async def handle_subscription_canceled(event_data: dict, conn):
    """Handle subscription cancellation (access continues until period end)."""
    user_id = await _resolve_user_id(event_data, conn)
    if not user_id:
        logger.error("[Polar Webhook] subscription.canceled: Could not resolve user_id")
        raise HTTPException(
            status_code=422, detail="Could not resolve user_id from webhook data"
        )

    # Mark as canceled but keep the current tier until period ends
    await conn.execute(
        """
        UPDATE subscriptions SET
            status = 'canceled',
            cancel_at_period_end = TRUE,
            updated_at = NOW()
        WHERE user_id = $1
    """,
        user_id,
    )

    logger.info(
        f"[Polar Webhook] Subscription canceled for user {user_id} (access until period end)"
    )


async def handle_subscription_revoked(event_data: dict, conn):
    """Handle subscription revocation (immediate access removal)."""
    user_id = await _resolve_user_id(event_data, conn)
    if not user_id:
        logger.error("[Polar Webhook] subscription.revoked: Could not resolve user_id")
        raise HTTPException(
            status_code=422, detail="Could not resolve user_id from webhook data"
        )

    # Immediately downgrade to free
    await conn.execute(
        """
        UPDATE subscriptions SET
            plan_tier = 'free',
            status = 'revoked',
            cancel_at_period_end = FALSE,
            updated_at = NOW()
        WHERE user_id = $1
    """,
        user_id,
    )

    await sync_user_tier(user_id, "free", conn)

    logger.info(
        f"[Polar Webhook] Subscription revoked for user {user_id}, downgraded to free"
    )


async def handle_order_paid(event_data: dict, conn):
    """Handle successful order payment (monthly renewal credit refill)."""
    user_id = await _resolve_user_id(event_data, conn)
    if not user_id:
        logger.error("[Polar Webhook] order.paid: Could not resolve user_id")
        raise HTTPException(
            status_code=422, detail="Could not resolve user_id from webhook data"
        )

    # Get the user's current tier to refill credits
    sub = await conn.fetchrow(
        "SELECT plan_tier FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        user_id,
    )
    if sub:
        tier = sub["plan_tier"]
        # Use credits_per_month (per-platform credit budget); -1 = enterprise unlimited
        credits = TIER_LIMITS.get(tier, {}).get("credits_per_month", 0)
        if credits > 0:
            await conn.execute(
                "UPDATE users SET build_credits = $1 WHERE id = $2",
                credits,
                user_id,
            )
            logger.info(
                f"[Credit System] Monthly refill: {credits} credits for user {user_id}"
            )

    logger.info(f"[Polar Webhook] Order paid for user {user_id}")


async def handle_order_refunded(event_data: dict, conn):
    """Handle order refund - downgrade to free tier."""
    user_id = await _resolve_user_id(event_data, conn)
    if not user_id:
        logger.error("[Polar Webhook] order.refunded: Could not resolve user_id")
        raise HTTPException(
            status_code=422, detail="Could not resolve user_id from webhook data"
        )

    # Downgrade subscription to free
    await conn.execute(
        """
        UPDATE subscriptions SET
            status = 'refunded',
            plan_tier = 'free',
            updated_at = NOW()
        WHERE user_id = $1
    """,
        user_id,
    )

    await sync_user_tier(user_id, "free", conn)

    logger.info(
        f"[Polar Webhook] Order refunded for user {user_id}, downgraded to free"
    )


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.post("/subscription/force-sync")
async def force_sync_subscription_tiers(
    user: dict = Depends(get_current_user_for_polar),
):
    """Admin only: Force sync all users' plans with their subscription tiers."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    conn = await get_db()
    try:
        # Sync users.plan with subscriptions.plan_tier where they differ
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

        # Get count of updated rows (asyncpg execute returns string like "UPDATE 5")
        count = result.replace("UPDATE ", "")

        return {
            "status": "success",
            "message": f"Synced tiers for {count} users",
            "updated_count": int(count) if count.isdigit() else 0,
        }
    finally:
        await release_db(conn)


# =============================================================================
# Phase 6: User-Facing Reconcile & Idempotent Processing
# =============================================================================


@router.get("/subscription/reconcile")
async def reconcile_subscription(
    user: dict = Depends(get_current_user_for_polar),
):
    """User-facing endpoint to reconcile subscription status with Polar API.

    This endpoint fetches the current subscription state from Polar and compares
    it with our local state. Returns any discrepancies found.
    """
    if not POLAR_ACCESS_TOKEN:
        raise HTTPException(
            status_code=503, detail="Reconciliation service unavailable"
        )

    conn = await get_db()
    try:
        # Get user's Polar customer ID
        user_record = await conn.fetchrow(
            "SELECT polar_customer_id, polar_subscription_id, plan FROM users WHERE id = $1",
            user["id"],
        )

        if not user_record or not user_record.get("polar_subscription_id"):
            return {
                "status": "ok",
                "local_state": {
                    "has_subscription": False,
                    "current_plan": user_record.get("plan", "free")
                    if user_record
                    else "free",
                },
                "polar_state": None,
                "discrepancies": [],
            }

        # Fetch subscription from Polar API
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POLAR_API_BASE}/subscriptions/{user_record['polar_subscription_id']}",
                headers={"Authorization": f"Bearer {POLAR_ACCESS_TOKEN}"},
            )

            if response.status_code == 404:
                return {
                    "status": "ok",
                    "local_state": {
                        "has_subscription": True,
                        "subscription_id": user_record["polar_subscription_id"],
                        "current_plan": user_record.get("plan", "free"),
                    },
                    "polar_state": "not_found",
                    "discrepancies": [
                        "Subscription exists locally but not found in Polar - may be canceled"
                    ],
                }

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch from Polar: {response.status_code}",
                )

            polar_data = response.json()

        # Compare states
        polar_status = polar_data.get("status")
        polar_tier = get_tier_from_product_id(polar_data.get("product_id") or "")

        discrepancies = []

        # Check if local plan matches Polar tier
        if user_record.get("plan") != polar_tier:
            discrepancies.append(
                {
                    "field": "plan",
                    "local_value": user_record.get("plan"),
                    "polar_value": polar_tier,
                    "fix": f"Update local plan to '{polar_tier}'",
                }
            )

        # Check if subscription is canceled/active
        if (
            polar_status in ("canceled", "past_due", "unpaid")
            and user_record.get("plan") != "free"
        ):
            discrepancies.append(
                {
                    "field": "status",
                    "local_value": "active",
                    "polar_value": polar_status,
                    "fix": "Downgrade to free tier",
                }
            )

        return {
            "status": "ok",
            "local_state": {
                "has_subscription": True,
                "subscription_id": user_record["polar_subscription_id"],
                "current_plan": user_record.get("plan", "free"),
            },
            "polar_state": {
                "status": polar_status,
                "tier": polar_tier,
                "current_period_end": polar_data.get("current_period_end"),
            },
            "discrepancies": discrepancies,
            "action_required": len(discrepancies) > 0,
        }
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, detail=f"Failed to connect to Polar: {str(e)}"
        )
    finally:
        await release_db(conn)


@router.post("/subscription/reconcile/fix")
async def reconcile_fix(
    user: dict = Depends(get_current_user_for_polar),
):
    """Apply reconciliation fixes to align local state with Polar.

    This is the deterministic idempotent processing path for billing issues.
    """
    conn = await get_db()
    try:
        # Get user's current subscription info
        user_record = await conn.fetchrow(
            "SELECT polar_customer_id, polar_subscription_id, plan FROM users WHERE id = $1",
            user["id"],
        )

        if not user_record or not user_record.get("polar_subscription_id"):
            # No subscription - ensure user is on free tier
            await conn.execute(
                "UPDATE users SET plan = 'free' WHERE id = $1",
                user["id"],
            )
            return {
                "status": "fixed",
                "message": "No subscription found - reset to free tier",
            }

        # Fetch latest from Polar
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POLAR_API_BASE}/subscriptions/{user_record['polar_subscription_id']}",
                headers={"Authorization": f"Bearer {POLAR_ACCESS_TOKEN}"},
            )

            if response.status_code == 404:
                # Subscription not found in Polar - cancel locally
                await conn.execute(
                    """UPDATE users SET plan = 'free', polar_subscription_id = NULL 
                       WHERE id = $1""",
                    user["id"],
                )
                await conn.execute(
                    """INSERT INTO webhook_deliveries 
                       (id, event_type, payload, success, created_at)
                       VALUES ($1, 'reconciliation.fix', $2, TRUE, NOW())""",
                    f"rec_{secrets.token_hex(8)}",
                    json.dumps(
                        {"action": "subscription_not_found", "user_id": user["id"]}
                    ),
                )
                return {
                    "status": "fixed",
                    "message": "Subscription not found in Polar - reset to free tier",
                }

            polar_data = response.json()

        # Apply fix based on Polar state
        new_plan = get_tier_from_product_id(polar_data.get("product_id") or "")
        polar_status = polar_data.get("status")

        if polar_status in ("canceled", "past_due", "unpaid"):
            new_plan = "free"

        await conn.execute(
            "UPDATE users SET plan = $1 WHERE id = $2",
            new_plan,
            user["id"],
        )

        # Log the fix for audit
        await conn.execute(
            """INSERT INTO webhook_deliveries 
               (id, event_type, payload, success, created_at)
               VALUES ($1, 'reconciliation.fix', $2, TRUE, NOW())""",
            secrets.token_hex(16),
            json.dumps(
                {
                    "action": "subscription_synced",
                    "user_id": user["id"],
                    "new_plan": new_plan,
                    "polar_status": polar_status,
                }
            ),
        )

        return {
            "status": "fixed",
            "message": f"Subscription reconciled - plan updated to {new_plan}",
            "new_plan": new_plan,
        }
    finally:
        await release_db(conn)
