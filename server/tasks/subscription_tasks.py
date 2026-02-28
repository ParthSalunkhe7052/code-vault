import asyncio
import logging
from database import get_db, release_db

logger = logging.getLogger(__name__)

async def check_expired_subscriptions():
    """Background task to check for expired subscriptions and notify users."""
    while True:
        try:
            # Check every hour
            await asyncio.sleep(3600)
            logger.info("[Tasks] Checking for expired subscriptions...")
            
            conn = await get_db()
            try:
                # Find subscriptions that expired in the last hour
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, plan_id, expires_at 
                    FROM subscriptions 
                    WHERE status = 'active' AND expires_at < NOW()
                    """
                )
                
                for row in rows:
                    logger.info(f"[Tasks] Subscription {row['id']} for user {row['user_id']} has expired")
                    # Update status and notify (pseudo-code/logic from main.py)
                    await conn.execute(
                        "UPDATE subscriptions SET status = 'expired' WHERE id = $1",
                        row['id']
                    )
                    # Notify user via email (if service configured)
                    # await notify_subscription_expired(row['user_id'])
                    
            finally:
                await release_db(conn)
                
        except Exception as e:
            logger.error(f"[Tasks] Error in check_expired_subscriptions: {e}")
            await asyncio.sleep(60) # Wait a bit before retrying on error
