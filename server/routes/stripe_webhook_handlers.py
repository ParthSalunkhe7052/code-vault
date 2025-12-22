"""
Stripe webhook handlers for CodeVault.
Handles subscription and license purchase events from Stripe.
"""

import logging
import secrets
from datetime import datetime, timezone

from config import PRICING_CONFIG

logger = logging.getLogger(__name__)


def utc_now():
    return datetime.now(timezone.utc)


def generate_license_key(prefix: str = "LIC") -> str:
    """Generate a unique license key."""
    import secrets
    key_parts = [secrets.token_hex(4).upper() for _ in range(4)]
    return f"{prefix}-{'-'.join(key_parts)}"


def get_tier_from_price_id(price_id: str) -> str:
    """Map Stripe price ID to tier name."""
    for tier_name, tier_config in PRICING_CONFIG.items():
        if tier_config.get("stripe_price_id") == price_id:
            return tier_name
    return "free"


async def sync_user_tier(user_id: str, tier: str, conn):
    """Sync tier from subscriptions to users table."""
    await conn.execute("""
        UPDATE users SET plan = $1, updated_at = NOW() WHERE id = $2
    """, tier, user_id)
    logger.info(f"[Tier Sync] User {user_id} tier synced to: {tier}")


async def handle_subscription_checkout_completed(session, conn):
    """Handle successful subscription checkout - create or update subscription."""
    customer_id = session.customer if hasattr(session, 'customer') else session.get('customer')
    subscription_id = session.subscription if hasattr(session, 'subscription') else session.get('subscription')
    
    if not subscription_id:
        logger.warning("[Stripe Webhook] checkout.session.completed without subscription_id, skipping")
        return
    
    user = await conn.fetchrow("SELECT id FROM users WHERE stripe_customer_id = $1", customer_id)
    
    if not user:
        logger.warning(f"[Stripe Webhook] No user found for customer {customer_id}")
        return
    
    user_id = user['id']
    
    import stripe
    sub = stripe.Subscription.retrieve(subscription_id)
    
    price_id = None
    if hasattr(sub, 'items') and sub.items.data:
        price_id = sub.items.data[0].price.id
    
    tier = get_tier_from_price_id(price_id) if price_id else "starter"
    
    existing = await conn.fetchrow(
        "SELECT id FROM subscriptions WHERE stripe_subscription_id = $1", subscription_id
    )
    
    current_period_end = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)
    
    if existing:
        await conn.execute("""
            UPDATE subscriptions SET
                plan_tier = $1,
                status = $2,
                current_period_end = $3,
                updated_at = NOW()
            WHERE stripe_subscription_id = $4
        """, tier, sub.status, current_period_end, subscription_id)
        logger.info(f"[Stripe Webhook] Updated subscription {subscription_id} to tier: {tier}")
    else:
        sub_id = secrets.token_hex(16)
        await conn.execute("""
            INSERT INTO subscriptions (
                id, user_id, stripe_subscription_id, stripe_customer_id,
                plan_tier, status, current_period_start, current_period_end
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, sub_id, user_id, subscription_id, customer_id, tier, sub.status,
            datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc),
            current_period_end)
        logger.info(f"[Stripe Webhook] Created subscription {subscription_id} for user {user_id}, tier: {tier}")
    
    await sync_user_tier(user_id, tier, conn)


async def handle_license_purchase_completed(session, conn):
    """
    Handle completed license purchase - create license for buyer.
    This handles one-time payment checkouts for end-user license purchases.
    """
    metadata = session.metadata if hasattr(session, 'metadata') else session.get('metadata', {})
    
    project_id = metadata.get('project_id')
    buyer_email = metadata.get('buyer_email')
    buyer_name = metadata.get('buyer_name', '')
    purchase_id = metadata.get('purchase_id')
    
    if not project_id or not buyer_email:
        logger.warning("[Stripe Webhook] License purchase missing required metadata")
        return
    
    project = await conn.fetchrow("SELECT id, name, user_id FROM projects WHERE id = $1", project_id)
    if not project:
        logger.warning(f"[Stripe Webhook] Project not found: {project_id}")
        return
    
    existing_license = await conn.fetchrow("""
        SELECT id FROM licenses WHERE project_id = $1 AND client_email = $2
    """, project_id, buyer_email)
    
    if existing_license:
        logger.info(f"[Stripe Webhook] License already exists for {buyer_email} on project {project_id}")
        return
    
    license_id = secrets.token_hex(16)
    license_key = generate_license_key(prefix="LIC")
    
    await conn.execute("""
        INSERT INTO licenses (
            id, project_id, license_key, status, max_machines, 
            client_name, client_email, notes
        ) VALUES ($1, $2, $3, 'active', 1, $4, $5, $6)
    """, license_id, project_id, license_key, buyer_name or buyer_email,
        buyer_email, f"Purchased via Stripe on {utc_now().isoformat()}")
    
    if purchase_id:
        await conn.execute("""
            UPDATE license_purchases SET
                license_id = $1,
                status = 'completed',
                completed_at = NOW()
            WHERE id = $2
        """, license_id, purchase_id)
    
    logger.info(f"[Stripe Webhook] Created license {license_key} for {buyer_email} on project {project['name']}")
    
    try:
        from email_service import notify_license_created
        await notify_license_created(
            buyer_name or buyer_email,
            buyer_email,
            license_key,
            project['name'],
            None,  # No expiration
            1,     # max_machines
            []     # features
        )
    except Exception as e:
        logger.error(f"[Stripe Webhook] Failed to send license email: {e}")


async def handle_subscription_updated(subscription, conn):
    """Handle subscription updates (plan changes, cancellation scheduled)."""
    subscription_id = subscription.id if hasattr(subscription, 'id') else subscription.get('id')
    status = subscription.status if hasattr(subscription, 'status') else subscription.get('status')
    cancel_at_period_end = subscription.cancel_at_period_end if hasattr(subscription, 'cancel_at_period_end') else subscription.get('cancel_at_period_end')
    
    price_id = None
    items = subscription.items if hasattr(subscription, 'items') else subscription.get('items', {})
    if hasattr(items, 'data') and items.data:
        price_id = items.data[0].price.id
    elif isinstance(items, dict) and items.get('data'):
        price_id = items['data'][0]['price']['id']
    
    tier = get_tier_from_price_id(price_id) if price_id else None
    
    current_period_end = subscription.current_period_end if hasattr(subscription, 'current_period_end') else subscription.get('current_period_end')
    if current_period_end:
        current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
    
    result = await conn.fetchrow("SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", subscription_id)
    
    if result:
        update_query = """
            UPDATE subscriptions SET
                status = $1,
                cancel_at_period_end = $2,
                current_period_end = COALESCE($3, current_period_end),
                plan_tier = COALESCE($4, plan_tier),
                updated_at = NOW()
            WHERE stripe_subscription_id = $5
        """
        await conn.execute(update_query, status, cancel_at_period_end, current_period_end, tier, subscription_id)
        
        if tier:
            await sync_user_tier(result['user_id'], tier, conn)
        
        logger.info(f"[Stripe Webhook] Updated subscription {subscription_id}: status={status}, tier={tier}")


async def handle_subscription_deleted(subscription, conn):
    """Handle subscription cancellation - downgrade to free tier."""
    subscription_id = subscription.id if hasattr(subscription, 'id') else subscription.get('id')
    
    result = await conn.fetchrow("SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", subscription_id)
    
    if result:
        await conn.execute("""
            UPDATE subscriptions SET
                status = 'canceled',
                plan_tier = 'free',
                updated_at = NOW()
            WHERE stripe_subscription_id = $1
        """, subscription_id)
        
        await sync_user_tier(result['user_id'], "free", conn)
        
        logger.info(f"[Stripe Webhook] Subscription {subscription_id} canceled, user downgraded to free")


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
