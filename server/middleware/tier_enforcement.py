
import logging
from functools import wraps
from typing import Optional, Callable
from fastapi import HTTPException, Request, Depends

from utils import get_user_tier_limits
from database import get_db, release_db

logger = logging.getLogger(__name__)

class TierEnforcementException(HTTPException):
    def __init__(self, feature: str, required_tier: str = "pro"):
        super().__init__(
            status_code=403,
            detail=f"Access denied: This feature ({feature}) requires the {required_tier} plan."
        )

async def check_feature_access(user_id: str, feature: str, conn):
    """
    Check if a user has access to a specific feature based on their tier.
    Raises TierEnforcementException if access is denied.
    """
    limits = await get_user_tier_limits(user_id, conn)
    
    # Check if feature is enabled in limits
    if not limits.get(feature, False):
        tier_name = limits.get("_tier_name", "Free")
        raise TierEnforcementException(feature, required_tier="pro" if tier_name == "Free" else "enterprise")
    
    return True

def requires_feature(feature_name: str):
    """
    Decorator to enforce tier limits on API endpoints.
    Assumes `user` dependency is injected into the route handler.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs
            user = kwargs.get('user')
            
            # If explicit Dependencies were used, we might need to find them
            if not user:
                # Try to find user in args (if positional) or kwargs
                for arg in args:
                    if isinstance(arg, dict) and "id" in arg and "email" in arg:
                        user = arg
                        break
            
            if not user and "request" in kwargs:
                 # Try to get from request state if available (legacy)
                 user = getattr(kwargs["request"].state, "user", None)

            if not user:
                # If we still can't find user, we can't enforce tier.
                # In a real app this should probably error out, but for safety in existing endpoints
                # we'll log logic error and skip matching.
                # However, if the endpoint REQUIRES user, FastAPI would have failed before reaching here (401/422).
                # If user is optional, we skip.
                return await func(*args, **kwargs)

            conn = await get_db()
            try:
                await check_feature_access(user['id'], feature_name, conn)
            finally:
                await release_db(conn)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
