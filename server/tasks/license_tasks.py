import asyncio
import logging
from database import get_db, release_db

logger = logging.getLogger(__name__)

async def check_expiring_licenses():
    """Background task to check for licenses expiring soon."""
    while True:
        try:
            # Check every 12 hours
            await asyncio.sleep(12 * 3600)
            logger.info("[Tasks] Checking for expiring licenses...")
            
            conn = await get_db()
            try:
                # Find licenses expiring in the next 3 days
                rows = await conn.fetch(
                    """
                    SELECT l.id, l.license_key, l.expires_at, p.user_id, p.name as project_name
                    FROM licenses l 
                    JOIN projects p ON l.project_id = p.id
                    WHERE l.status = 'active' 
                    AND l.expires_at BETWEEN NOW() AND NOW() + INTERVAL '3 days'
                    """
                )
                
                for row in rows:
                    logger.info(f"[Tasks] License {row['license_key']} for project {row['project_name']} is expiring soon")
                    # Logic for notifications would go here
                    
            finally:
                await release_db(conn)
                
        except Exception as e:
            logger.error(f"[Tasks] Error in check_expiring_licenses: {e}")
            await asyncio.sleep(60)
