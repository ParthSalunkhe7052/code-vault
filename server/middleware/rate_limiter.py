"""
Rate limiting middleware using Upstash Redis.

Provides configurable rate limiting for API endpoints to prevent:
- Brute force attacks on login/register
- API abuse on license validation
- DoS attacks on public endpoints
"""

import logging
import hashlib
from typing import Optional, Callable
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlparse

from fastapi import HTTPException, Request
import redis.asyncio as redis


logger = logging.getLogger(__name__)

# Redis connection pool (initialized in startup)
_redis_client: Optional[redis.Redis] = None


async def init_rate_limiter(redis_url: str) -> None:
    """Initialize the Redis client for rate limiting.

    Args:
        redis_url: Redis connection URL (e.g., redis://... or rediss://...)
    """
    global _redis_client

    if not redis_url:
        logger.warning("[RateLimiter] No Redis URL configured - rate limiting disabled")
        return

    try:
        # Check if this is Upstash URL and handle connection issues using hostname parsing
        parsed = urlparse(redis_url)
        if parsed.hostname and parsed.hostname.endswith(".upstash.io"):
            logger.info("[RateLimiter] Upstash Redis detected - testing connection...")

        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        # Test connection
        await _redis_client.ping()
        logger.info("[RateLimiter] Connected to Redis successfully")
    except Exception as e:
        # Handle common Upstash connection issues gracefully
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "Name or service not known" in error_msg:
            logger.warning("[RateLimiter] Cannot reach Upstash Redis (DNS/network issue)")
            logger.info("[RateLimiter] Rate limiting will be disabled - this is OK for local development")
        elif "Connection refused" in error_msg:
            logger.warning("[RateLimiter] Redis connection refused - ensure Redis server is running")
            logger.info("[RateLimiter] Rate limiting disabled")
        else:
            logger.warning(f"[RateLimiter] Failed to connect to Redis: {e}")
            logger.info("[RateLimiter] Rate limiting disabled")

        _redis_client = None


async def close_rate_limiter() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("[RateLimiter] Redis connection closed")


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (set by reverse proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def _hash_identifier(identifier: str) -> str:
    """Hash an identifier for privacy (don't store raw IPs/emails in Redis)."""
    return hashlib.sha256(identifier.encode()).hexdigest()[:16]


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=429,
            detail=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )
        self.retry_after = retry_after


async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int, int]:
    """Check if a rate limit has been exceeded.

    Uses sliding window counter algorithm.

    Args:
        key: Unique key for this rate limit (e.g., "login:user@example.com")
        max_requests: Maximum allowed requests in the window
        window_seconds: Time window in seconds

    Returns:
        Tuple of (allowed: bool, remaining: int, retry_after: int)
    """
    if not _redis_client:
        # Rate limiting disabled - allow all requests
        return (True, max_requests, 0)

    try:
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - window_seconds

        # Redis key for this rate limit
        redis_key = f"ratelimit:{key}"

        # Use pipeline for atomic operations
        pipe = _redis_client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count current requests in window
        pipe.zcard(redis_key)

        # Add current request
        pipe.zadd(redis_key, {str(now): now})

        # Set expiry on the key
        pipe.expire(redis_key, window_seconds + 1)

        results = await pipe.execute()
        current_count = results[1]  # zcard result

        if current_count >= max_requests:
            # Get the oldest entry to calculate retry time
            oldest = await _redis_client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                retry_after = int(oldest_time + window_seconds - now) + 1
            else:
                retry_after = window_seconds

            return (False, 0, max(retry_after, 1))

        remaining = max_requests - current_count - 1
        return (True, max(remaining, 0), 0)

    except Exception as e:
        logger.error(f"[RateLimiter] Redis error: {e}")
        # On error, allow the request (fail open)
        return (True, max_requests, 0)


def rate_limit(
    max_requests: int = 10,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
    prefix: str = "",
):
    """Decorator to apply rate limiting to an endpoint.

    Args:
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
        key_func: Optional function to extract a custom key from request
        prefix: Prefix for the rate limit key

    Example:
        @router.post("/login")
        @rate_limit(max_requests=5, window_seconds=60, prefix="login")
        async def login(request: Request, data: LoginRequest):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the Request object in args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                # No request object found, skip rate limiting
                return await func(*args, **kwargs)

            # Generate rate limit key
            if key_func:
                identifier = key_func(request)
            else:
                identifier = _get_client_ip(request)

            key = f"{prefix}:{_hash_identifier(identifier)}" if prefix else _hash_identifier(identifier)

            # Check rate limit
            allowed, remaining, retry_after = await check_rate_limit(
                key, max_requests, window_seconds
            )

            if not allowed:
                logger.warning(
                    f"[RateLimiter] Rate limit exceeded for {prefix}: "
                    f"IP={_get_client_ip(request)[:16]}..."
                )
                raise RateLimitExceeded(retry_after)

            # Add rate limit headers to response
            response = await func(*args, **kwargs)

            # If response is a dict (common in FastAPI), wrap it
            if isinstance(response, dict):
                return response

            return response

        return wrapper
    return decorator


class RateLimitDependency:
    """FastAPI Dependency for rate limiting.

    Usage:
        @router.post("/login")
        async def login(
            request: Request,
            data: LoginRequest,
            _rate_limit: None = Depends(RateLimitDependency(5, 60, "login"))
        ):
            ...
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        prefix: str = "",
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix
        self.key_func = key_func

    async def __call__(self, request: Request) -> None:
        # Generate rate limit key
        if self.key_func:
            identifier = self.key_func(request)
        else:
            identifier = _get_client_ip(request)

        key = f"{self.prefix}:{_hash_identifier(identifier)}" if self.prefix else _hash_identifier(identifier)

        # Check rate limit
        allowed, remaining, retry_after = await check_rate_limit(
            key, self.max_requests, self.window_seconds
        )

        if not allowed:
            logger.warning(
                f"[RateLimiter] Rate limit exceeded for {self.prefix}: "
                f"IP={_get_client_ip(request)[:16]}..."
            )
            raise RateLimitExceeded(retry_after)


# Pre-configured rate limiters for common use cases
login_rate_limit = RateLimitDependency(
    max_requests=5,
    window_seconds=60,
    prefix="auth:login"
)

register_rate_limit = RateLimitDependency(
    max_requests=3,
    window_seconds=300,  # 5 minutes
    prefix="auth:register"
)

license_validate_rate_limit = RateLimitDependency(
    max_requests=30,
    window_seconds=60,
    prefix="license:validate"
)

api_key_regen_rate_limit = RateLimitDependency(
    max_requests=3,
    window_seconds=3600,  # 1 hour
    prefix="auth:apikey"
)

password_reset_rate_limit = RateLimitDependency(
    max_requests=3,
    window_seconds=300,  # 5 minutes
    prefix="auth:reset"
)


# Redis client getter for external use (e.g., build queue)
async def get_redis_client() -> Optional[redis.Redis]:
    """Get the Redis client instance for use in other modules."""
    return _redis_client
