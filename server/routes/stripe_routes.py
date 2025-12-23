"""
Stripe payment integration routes for CodeVault.
Handles subscriptions, checkout sessions, and webhooks.

FIXED ISSUES (Dec 16, 2025):
- C1: Authentication now uses proper JWT/API key validation
- C2: Added license purchase webhook handler
- C3: All Stripe API calls wrapped in exception handling
- C4: Customer ID persisted to prevent race conditions
"""

import uuid
import secrets
import logging
import stripe
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from config import (
    STRIPE_SECRET_KEY, 
    STRIPE_WEBHOOK_SECRET,
    STRIPE_PRICE_PRO,
    STRIPE_PRICE_ENTERPRISE,
    TIER_LIMITS,
    JWT_SECRET,
    JWT_ALGORITHM
)
from database import get_db, release_db

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Create router
router = APIRouter(prefix="/api/v1", tags=["stripe"])

# Security
security = HTTPBearer(auto_error=False)


# =============================================================================
# Pydantic Models
# =============================================================================

from pydantic import BaseModel, EmailStr

class CreateCheckoutSessionRequest(BaseModel):
    price_id: str
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
# Authentication (FIX C1: Proper auth instead of request.state)
# =============================================================================

def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.exceptions.PyJWTError:
        return None


async def get_current_user_for_stripe(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Verify JWT or API key and return user. Used for Stripe routes."""
    conn = await get_db()
    try:
        # Try JWT token first
        if credentials:
            payload = verify_jwt_token(credentials.credentials)
            if payload:
                user = await conn.fetchrow(
                    "SELECT id, email, name, plan, role, api_key FROM users WHERE id = $1",
                    payload["sub"]
                )
                if user:
                    return dict(user)
        
        # Try API key
        if x_api_key:
            user = await conn.fetchrow(
                "SELECT id, email, name, plan, role, api_key FROM users WHERE api_key = $1",
                x_api_key
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
        segment = ''.join(secrets.choice(chars) for _ in range(4))
        parts.append(segment)
    return '-'.join(parts)


async def get_user_subscription(user_id: str, conn) -> dict:
    """Get user's current subscription or return free tier defaults."""
    row = await conn.fetchrow("""
        SELECT * FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1
    """, user_id)
    
    if not row:
        return {
            "plan_tier": "free",
            "status": "active",
            "current_period_end": None,
            "cancel_at_period_end": False,
            "stripe_customer_id": None,
            "stripe_subscription_id": None
        }
    
    return dict(row)


async def create_or_get_stripe_customer(user_id: str, email: str, conn) -> str:
    """
    Create a Stripe customer or return existing customer ID.
    FIX C3: Added exception handling
    FIX C4: Persists customer ID immediately to prevent race conditions
    """
    # Check if user already has a Stripe customer ID
    sub = await get_user_subscription(user_id, conn)
    if sub.get("stripe_customer_id"):
        return sub["stripe_customer_id"]
    
    try:
        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=email,
            metadata={"user_id": user_id}
        )
        
        # FIX C4: Persist customer ID immediately to prevent duplicate customers
        existing = await conn.fetchrow(
            "SELECT id FROM subscriptions WHERE user_id = $1", user_id
        )
        
        if existing:
            await conn.execute("""
                UPDATE subscriptions SET stripe_customer_id = $1, updated_at = NOW() 
                WHERE user_id = $2
            """, customer.id, user_id)
        else:
            # Create a subscription record with customer ID (free tier)
            await conn.execute("""
                INSERT INTO subscriptions (id, user_id, stripe_customer_id, plan_tier, status)
                VALUES ($1, $2, $3, 'free', 'active')
            """, str(uuid.uuid4()), user_id, customer.id)
        
        logger.info(f"[Stripe] Created customer {customer.id} for user {user_id}")
        return customer.id
        
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Failed to create customer: {str(e)}")
        # Security: Don't expose Stripe error details to client
        raise HTTPException(status_code=502, detail="Payment provider error. Please try again later.")


def get_tier_from_price_id(price_id: str) -> str:
    """Map Stripe price ID to tier name."""
    if price_id == STRIPE_PRICE_PRO:
        return "pro"
    elif price_id == STRIPE_PRICE_ENTERPRISE:
        return "enterprise"
    return "free"


async def sync_user_tier(user_id: str, tier: str, conn):
    """Sync tier from subscriptions to users table."""
    try:
        await conn.execute(
            "UPDATE users SET plan = $1 WHERE id = $2",
            tier, user_id
        )
        logger.info(f"[Tier Sync] Updated user {user_id} plan to {tier}")
    except Exception as e:
        logger.error(f"[Tier Sync] Failed to sync user {user_id} to {tier}: {e}")


# =============================================================================
# Subscription Endpoints (FIX C1: Using Depends for auth)
# =============================================================================

@router.get("/subscription/status")
async def get_subscription_status(user: dict = Depends(get_current_user_for_stripe)):
    """Get current user's subscription status and tier limits."""
    conn = await get_db()
    try:
        sub = await get_user_subscription(user["id"], conn)
        tier = sub.get("plan_tier", "free")
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        
        # Count current usage
        project_count = await conn.fetchval("""
            SELECT COUNT(*) FROM projects WHERE user_id = $1
        """, user["id"])
        
        return {
            "plan_tier": tier,
            "status": sub.get("status", "active"),
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "limits": limits,
            "usage": {
                "projects": project_count
            }
        }
    finally:
        await release_db(conn)


@router.post("/stripe/create-checkout-session")
async def create_checkout_session(
    data: CreateCheckoutSessionRequest, 
    request: Request,
    user: dict = Depends(get_current_user_for_stripe)
):
    """Create a Stripe Checkout session for subscription."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    # Validate price ID
    if data.price_id not in [STRIPE_PRICE_PRO, STRIPE_PRICE_ENTERPRISE]:
        raise HTTPException(status_code=400, detail="Invalid price ID")
    
    conn = await get_db()
    try:
        # Get or create Stripe customer (FIX C3: exception handling inside function)
        customer_id = await create_or_get_stripe_customer(user["id"], user["email"], conn)
        
        # Default URLs
        base_url = str(request.base_url).rstrip("/")
        success_url = data.success_url or f"{base_url}/billing?success=true"
        cancel_url = data.cancel_url or f"{base_url}/pricing?canceled=true"
        
        try:
            # Create checkout session (FIX C3: wrapped in try-except)
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": data.price_id,
                    "quantity": 1
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user["id"]
                },
                allow_promotion_codes=True,
                billing_address_collection="auto",
                payment_method_collection="always"
            )
            
            return {"checkout_url": session.url, "session_id": session.id}
            
        except stripe.error.StripeError as e:
            logger.error(f"[Stripe] Checkout session error: {str(e)}")
            # Security: Don't expose Stripe error details to client
            raise HTTPException(status_code=502, detail="Could not create checkout session. Please try again later.")
    finally:
        await release_db(conn)


@router.post("/stripe/create-customer-portal")
async def create_customer_portal(
    data: CreatePortalSessionRequest, 
    request: Request,
    user: dict = Depends(get_current_user_for_stripe)
):
    """Create a Stripe Customer Portal session for managing subscription."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    conn = await get_db()
    try:
        sub = await get_user_subscription(user["id"], conn)
        
        if not sub.get("stripe_customer_id"):
            raise HTTPException(status_code=400, detail="No active subscription found")
        
        # Default return URL
        base_url = str(request.base_url).rstrip("/")
        return_url = data.return_url or f"{base_url}/billing"
        
        try:
            # Create portal session (FIX C3: wrapped in try-except)
            session = stripe.billing_portal.Session.create(
                customer=sub["stripe_customer_id"],
                return_url=return_url
            )
            
            return {"portal_url": session.url}
            
        except stripe.error.StripeError as e:
            logger.error(f"[Stripe] Portal session error: {str(e)}")
            # Security: Don't expose Stripe error details to client
            raise HTTPException(status_code=502, detail="Could not open billing portal. Please try again later.")
    finally:
        await release_db(conn)


# =============================================================================
# Webhook Endpoint
# =============================================================================

@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """Handle Stripe webhook events."""
    # Allow webhook without secret in test mode for local development
    payload = await request.body()
    
    # Verify payload and signature
    event = None
    try:
        # If no secret is set, we can't verify signature (dev mode)
        if not STRIPE_WEBHOOK_SECRET:
            import json
            event_data = json.loads(payload)
            event = stripe.Event.construct_from(event_data, stripe.api_key)
            logger.warning("[Stripe Webhook] processing without signature verification (dev mode)")
        else:
            # Production: Strict signature verification
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
    except ValueError as e:
        logger.error(f"[Stripe Webhook] Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"[Stripe Webhook] Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
         logger.error(f"[Stripe Webhook] Error constructing event: {e}")
         raise HTTPException(status_code=400, detail="Webhook error")

    conn = await get_db()
    try:
        async with conn.transaction():
            logger.info(f"[Stripe Webhook] Processing event: {event.type}")
            
            # Handle checkout completion - route to appropriate handler
            if event.type == "checkout.session.completed":
                session = event.data.object
                if getattr(session, 'mode', None) == "subscription":
                    await handle_subscription_checkout_completed(session, conn)
                elif getattr(session, 'mode', None) == "payment":
                    await handle_license_purchase_completed(session, conn)
                else:
                    # Default to subscription if mode not specified
                    await handle_subscription_checkout_completed(session, conn)
            
            elif event.type == "customer.subscription.updated":
                await handle_subscription_updated(event.data.object, conn)
            
            elif event.type == "customer.subscription.deleted":
                await handle_subscription_deleted(event.data.object, conn)
            
            elif event.type == "invoice.payment_succeeded":
                await handle_invoice_paid(event.data.object, conn)
            
            elif event.type == "invoice.payment_failed":
                await handle_invoice_failed(event.data.object, conn)
            
            return {"status": "success"}
    except Exception as e:
        # Security: Log full error server-side, return generic message to client
        logger.error(f"[Stripe Webhook] Error processing event: {e}")
        # Return success to prevent Stripe from retrying endlessly (we logged the error)
        # In a real production system, you might want to return 500 for retryable errors
        return {"status": "error", "message": "An internal error occurred processing this webhook"}
    finally:
        await release_db(conn)


async def handle_subscription_checkout_completed(session, conn):
    """Handle successful subscription checkout - create or update subscription."""
    user_id = session.metadata.get("user_id") if hasattr(session, 'metadata') else None
    if not user_id:
        logger.warning("[Stripe Webhook] No user_id in checkout session metadata")
        return
    
    # Get subscription details from Stripe
    subscription_id = getattr(session, 'subscription', None)
    customer_id = getattr(session, 'customer', None)
    
    if subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            price_id = stripe_sub["items"]["data"][0]["price"]["id"]
            tier = get_tier_from_price_id(price_id)
            
            # Check if subscription record exists
            existing = await conn.fetchrow("""
                SELECT id, stripe_subscription_id FROM subscriptions WHERE user_id = $1
            """, user_id)
            
            # Idempotency check: if already processed this subscription ID, just ensure updated
            if existing and existing['stripe_subscription_id'] == subscription_id:
                 logger.info(f"[Stripe Webhook] Idempotency: Subscription {subscription_id} already linked to user {user_id}")

            
            if existing:
                # Update existing subscription
                await conn.execute("""
                    UPDATE subscriptions SET
                        stripe_customer_id = $2,
                        stripe_subscription_id = $3,
                        plan_tier = $4,
                        status = $5,
                        current_period_start = to_timestamp($6),
                        current_period_end = to_timestamp($7),
                        cancel_at_period_end = $8,
                        updated_at = NOW()
                    WHERE user_id = $1
                """, user_id, customer_id, subscription_id, tier,
                    stripe_sub["status"],
                    stripe_sub["current_period_start"],
                    stripe_sub["current_period_end"],
                    stripe_sub.get("cancel_at_period_end", False))
            else:
                # Create new subscription record
                await conn.execute("""
                    INSERT INTO subscriptions (
                        id, user_id, stripe_customer_id, stripe_subscription_id,
                        plan_tier, status, current_period_start, current_period_end,
                        cancel_at_period_end
                    ) VALUES ($1, $2, $3, $4, $5, $6, to_timestamp($7), to_timestamp($8), $9)
                """, str(uuid.uuid4()), user_id, customer_id, subscription_id, tier,
                    stripe_sub["status"],
                    stripe_sub["current_period_start"],
                    stripe_sub["current_period_end"],
                    stripe_sub.get("cancel_at_period_end", False))
            
            
            # Critical Fix: Sync user tier to users table
            await sync_user_tier(user_id, tier, conn)
            
            logger.info(f"[Stripe Webhook] Subscription created/updated for user {user_id}: {tier}")
            
        except stripe.error.StripeError as e:
            logger.error(f"[Stripe Webhook] Error retrieving subscription: {e}")


async def handle_license_purchase_completed(session, conn):
    """
    FIX C2: Handle completed license purchase - create license for buyer.
    This handles one-time payment checkouts for end-user license purchases.
    """
    purchase_id = session.metadata.get("purchase_id") if hasattr(session, 'metadata') else None
    if not purchase_id:
        logger.warning("[Stripe Webhook] No purchase_id in checkout session metadata")
        return
    
    # Get purchase record
    purchase = await conn.fetchrow("""
        SELECT * FROM license_purchases WHERE id = $1
    """, purchase_id)
    
    if not purchase:
        logger.warning(f"[Stripe Webhook] Purchase not found: {purchase_id}")
        return
    
    if purchase["status"] == "completed":
        logger.info(f"[Stripe Webhook] Purchase already completed: {purchase_id}")
        return
    
    # Generate license key
    license_key = generate_license_key()
    license_id = str(uuid.uuid4())
    
    # Create license
    await conn.execute("""
        INSERT INTO licenses (
            id, project_id, license_key, status, max_machines,
            client_name, client_email, created_at
        ) VALUES ($1, $2, $3, 'active', 1, $4, $5, NOW())
    """, license_id, purchase["project_id"], license_key,
        purchase["buyer_name"], purchase["buyer_email"])
    
    # Update purchase record
    payment_intent = getattr(session, 'payment_intent', None)
    await conn.execute("""
        UPDATE license_purchases SET
            license_id = $2,
            stripe_payment_intent_id = $3,
            status = 'completed'
        WHERE id = $1
    """, purchase_id, license_id, payment_intent)
    
    logger.info(f"[Stripe Webhook] License created for purchase {purchase_id}: {license_key}")
    
    # Send email to buyer with license key
    try:
        from email_service import notify_license_created
        project = await conn.fetchrow("SELECT name FROM projects WHERE id = $1", purchase["project_id"])
        await notify_license_created(
            client_name=purchase["buyer_name"] or "Customer",
            client_email=purchase["buyer_email"],
            license_key=license_key,
            project_name=project["name"] if project else "Your Software",
            expires_at=None,  # Purchased licenses don't expire by default
            max_machines=1,
            features=[]
        )
        logger.info(f"[Stripe Webhook] Sent license email to {purchase['buyer_email']}")
    except Exception as e:
        logger.error(f"[Stripe Webhook] Failed to send license email: {e}")


async def handle_subscription_updated(subscription, conn):
    """Handle subscription updates (plan changes, cancellation scheduled)."""
    subscription_id = subscription.id if hasattr(subscription, 'id') else subscription.get('id')
    
    try:
        items = subscription.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id", "")
        else:
            price_id = ""
        tier = get_tier_from_price_id(price_id)
        
        await conn.execute("""
            UPDATE subscriptions SET
                plan_tier = $2,
                status = $3,
                current_period_start = to_timestamp($4),
                current_period_end = to_timestamp($5),
                cancel_at_period_end = $6,
                updated_at = NOW()
            WHERE stripe_subscription_id = $1
        """, subscription_id, tier, subscription.get("status"),
            subscription.get("current_period_start"),
            subscription.get("current_period_end"),
            subscription.get("cancel_at_period_end", False))
        
        
        # Get user_id to sync tier
        user_id = await conn.fetchval(
            "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", subscription_id
        )
        if user_id:
            await sync_user_tier(user_id, tier, conn)
        
        logger.info(f"[Stripe Webhook] Subscription updated: {subscription_id} -> {tier}")
    except Exception as e:
        logger.error(f"[Stripe Webhook] Error updating subscription: {e}")


async def handle_subscription_deleted(subscription, conn):
    """Handle subscription cancellation - downgrade to free tier."""
    subscription_id = subscription.id if hasattr(subscription, 'id') else subscription.get('id')
    
    await conn.execute("""
        UPDATE subscriptions SET
            plan_tier = 'free',
            status = 'canceled',
            cancel_at_period_end = FALSE,
            updated_at = NOW()
        WHERE stripe_subscription_id = $1
    """, subscription_id)
    
    
    # Get user_id to sync tier
    user_id = await conn.fetchval(
        "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", subscription_id
    )
    if user_id:
        await sync_user_tier(user_id, 'free', conn)
    
    logger.info(f"[Stripe Webhook] Subscription canceled: {subscription_id}")


async def handle_invoice_paid(invoice, conn):
    """Handle successful invoice payment."""
    subscription_id = invoice.subscription if hasattr(invoice, 'subscription') else invoice.get('subscription')
    if subscription_id:
        await conn.execute("""
            UPDATE subscriptions SET
                status = 'active',
                updated_at = NOW()
            WHERE stripe_subscription_id = $1
        """, subscription_id)
        logger.info(f"[Stripe Webhook] Invoice paid for subscription: {subscription_id}")


async def handle_invoice_failed(invoice, conn):
    """Handle failed invoice payment."""
    subscription_id = invoice.subscription if hasattr(invoice, 'subscription') else invoice.get('subscription')
    if subscription_id:
        await conn.execute("""
            UPDATE subscriptions SET
                status = 'past_due',
                updated_at = NOW()
            WHERE stripe_subscription_id = $1
        """, subscription_id)
        logger.info(f"[Stripe Webhook] Invoice failed for subscription: {subscription_id}")


# =============================================================================
# Public Store Endpoints (for end-user license purchases - NO AUTH REQUIRED)
# =============================================================================

@router.get("/public/store/{store_slug}")
async def get_public_store(store_slug: str):
    """Get public project info for store page (no auth required)."""
    conn = await get_db()
    try:
        project = await conn.fetchrow("""
            SELECT p.id, p.name, p.description, p.price_cents, p.currency, p.store_slug,
                   u.name as developer_name
            FROM projects p
            JOIN users u ON p.user_id = u.id
            WHERE p.store_slug = $1 AND p.is_public = TRUE AND p.price_cents > 0
        """, store_slug)
        
        if not project:
            raise HTTPException(status_code=404, detail="Store not found")
        
        return {
            "id": project["id"],
            "name": project["name"],
            "description": project["description"],
            "price": project["price_cents"] / 100,  # Convert cents to dollars
            "currency": project["currency"],
            "developer": project["developer_name"]
        }
    finally:
        await release_db(conn)


@router.post("/public/purchase")
async def create_license_purchase(data: PublicPurchaseRequest, request: Request):
    """Create a Stripe Checkout session for license purchase (no auth required)."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    conn = await get_db()
    try:
        # Get project info
        project = await conn.fetchrow("""
            SELECT id, name, price_cents, currency, user_id
            FROM projects
            WHERE store_slug = $1 AND is_public = TRUE AND price_cents > 0
        """, data.store_slug)
        
        if not project:
            raise HTTPException(status_code=404, detail="Store not found")
        
        # Check if developer can sell licenses (has pro or enterprise)
        dev_sub = await get_user_subscription(project["user_id"], conn)
        if dev_sub["plan_tier"] == "free":
            raise HTTPException(status_code=403, detail="Developer needs Pro plan to sell licenses")
        
        # Default URLs
        base_url = str(request.base_url).rstrip("/")
        success_url = data.success_url or f"{base_url}/license/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = data.cancel_url or f"{base_url}/store/{data.store_slug}?canceled=true"
        
        # Create purchase record
        purchase_id = str(uuid.uuid4())
        
        try:
            # Create Stripe checkout session for one-time payment (FIX C3: wrapped in try-except)
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": project["currency"],
                        "unit_amount": project["price_cents"],
                        "product_data": {
                            "name": f"{project['name']} - License",
                            "description": f"License key for {project['name']}"
                        }
                    },
                    "quantity": 1
                }],
                mode="payment",
                customer_email=data.buyer_email,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "purchase_id": purchase_id,
                    "project_id": project["id"],
                    "buyer_email": data.buyer_email,
                    "buyer_name": data.buyer_name or ""
                }
            )
            
            # Save purchase record
            await conn.execute("""
                INSERT INTO license_purchases (
                    id, project_id, stripe_checkout_session_id, buyer_email, buyer_name,
                    amount_cents, currency, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
            """, purchase_id, project["id"], session.id, data.buyer_email,
                data.buyer_name, project["price_cents"], project["currency"])
            
            return {"checkout_url": session.url, "session_id": session.id}
            
        except stripe.error.StripeError as e:
            logger.error(f"[Stripe] License purchase checkout error: {str(e)}")
            # Security: Don't expose Stripe error details to client
            raise HTTPException(status_code=502, detail="Could not create checkout session. Please try again later.")
    finally:
        await release_db(conn)


@router.get("/public/license/{license_key}")
async def get_license_portal(license_key: str):
    """Get license info for the license portal (no auth required)."""
    conn = await get_db()
    try:
        license_row = await conn.fetchrow("""
            SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features,
                   l.client_name, l.client_email, l.created_at,
                   p.name as project_name, p.description as project_description
            FROM licenses l
            JOIN projects p ON l.project_id = p.id
            WHERE l.license_key = $1
        """, license_key)
        
        if not license_row:
            raise HTTPException(status_code=404, detail="License not found")
        
        # Count active machines
        machine_count = await conn.fetchval("""
            SELECT COUNT(*) FROM hardware_bindings
            WHERE license_id = $1 AND is_active = TRUE
        """, license_row["id"])
        
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
                "description": license_row["project_description"]
            }
        }
    finally:
        await release_db(conn)


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.post("/subscription/force-sync")
async def force_sync_subscription_tiers(user: dict = Depends(get_current_user_for_stripe)):
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
            "updated_count": int(count) if count.isdigit() else 0
        }
    finally:
        await release_db(conn)
