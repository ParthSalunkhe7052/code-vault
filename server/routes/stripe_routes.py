"""
Stripe billing routes for CodeVault API.
Supports checkout sessions and webhooks for usage-based pricing (MON5).
"""

import logging
import stripe
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from config import STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET
from utils import get_current_user, utc_now
from database import get_db, release_db

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])
stripe.api_key = STRIPE_API_KEY

logger = logging.getLogger("stripe")

@router.post("/create-checkout-session")
async def create_checkout_session(price_id: str, user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session for subscription."""
    try:
        session = stripe.checkout.Session.create(
            customer_email=user["email"],
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url="https://codevault.app/dashboard?billing_success=true",
            cancel_url="https://codevault.app/dashboard?billing_cancel=true",
            metadata={"user_id": user["id"]}
        )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Handle Stripe webhooks for subscription state changes."""
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    conn = await get_db()
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session.get('metadata', {}).get('user_id')
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')
            
            if user_id:
                # Update user with stripe customer ID
                await conn.execute(
                    "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
                    customer_id, user_id
                )
                
                # Fetch subscription details from Stripe
                sub = stripe.Subscription.retrieve(subscription_id)
                plan_tier = sub.get('metadata', {}).get('plan_tier', 'pro')
                
                # Insert/Update subscription record
                from secrets import token_hex
                await conn.execute(
                    """INSERT INTO subscriptions (id, user_id, plan_tier, status, stripe_subscription_id, stripe_status)
                       VALUES ($1, $2, $3, 'active', $4, $5)
                       ON CONFLICT (user_id) DO UPDATE SET 
                       plan_tier = EXCLUDED.plan_tier, status = 'active', stripe_status = EXCLUDED.stripe_status""",
                    token_hex(16), user_id, plan_tier, subscription_id, sub.status
                )
                logger.info(f"✅ Subscription activated for user {user_id}")

        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            await conn.execute(
                "UPDATE subscriptions SET status = 'canceled', stripe_status = 'canceled' WHERE stripe_subscription_id = $1",
                subscription.id
            )
            logger.info(f"🛑 Subscription canceled: {subscription.id}")

        return {"status": "success"}
    finally:
        await release_db(conn)
