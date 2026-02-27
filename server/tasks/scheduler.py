import asyncio
import logging
from tasks.subscription_tasks import check_expired_subscriptions
from tasks.license_tasks import check_expiring_licenses

logger = logging.getLogger(__name__)

async def start_background_tasks():
    """Start all backend maintenance tasks."""
    logger.info("[Tasks] Starting background maintenance tasks...")
    
    # Run tasks in the background
    asyncio.create_task(check_expired_subscriptions())
    asyncio.create_task(check_expiring_licenses())
    
    logger.info("[Tasks] All background tasks initialized")
