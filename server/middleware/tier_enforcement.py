"""
Tier enforcement middleware for CodeVault API.
Checks usage limits and subscription status (MON5).
"""

from fastapi import Request, HTTPException, Depends
from utils import get_current_user, get_user_tier_limits
from database import get_db, release_db

async def check_limit(metric: str, user: dict = Depends(get_current_user)):
    """Dependency to check if a user has exceeded a specific tier limit."""
    conn = await get_db()
    try:
        limits = await get_user_tier_limits(user["id"], conn)
        limit = limits.get(metric)
        
        if limit is None:
            return True # No limit defined
            
        if limit == -1:
            return True # Unlimited
            
        # Special case for license count
        if metric == "max_licenses_per_project":
            return True

        # Check usage counters for metered metrics
        current = await conn.fetchval(
            "SELECT current_value FROM usage_counters WHERE user_id = $1 AND metric_name = $2",
            user["id"], metric
        )
        
        if current and current >= limit:
            raise HTTPException(
                status_code=403, 
                detail=f"Limit reached for {metric.replace('_', ' ')}. Please upgrade your plan."
            )
            
        return True
    finally:
        await release_db(conn)

def requires_feature(feature_name: str):
    """Factory for feature requirement dependency (SEC4/MON5)."""
    async def _requires_feature(user: dict = Depends(get_current_user)):
        conn = await get_db()
        try:
            limits = await get_user_tier_limits(user["id"], conn)
            if not limits.get(feature_name, False):
                raise HTTPException(
                    status_code=403, 
                    detail=f"The '{feature_name}' feature is not available on your current plan. Please upgrade."
                )
            return True
        finally:
            await release_db(conn)
    return _requires_feature

async def increment_usage(user_id: str, metric: str):
    """Utility to increment a usage counter."""
    conn = await get_db()
    try:
        await conn.execute(
            """INSERT INTO usage_counters (user_id, metric_name, current_value)
               VALUES ($1, $2, 1)
               ON CONFLICT (user_id, metric_name) DO UPDATE SET 
               current_value = usage_counters.current_value + 1""",
            user_id, metric
        )
    finally:
        await release_db(conn)
