"""
Database connection pool and initialization for PostgreSQL.
"""

import os
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
from fastapi import HTTPException

from config import DATABASE_URL, ENVIRONMENT

logger = logging.getLogger(__name__)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

# Connection retry configuration
MAX_CONNECTION_RETRIES = 5
CONNECTION_RETRY_DELAY = 2  # seconds


async def get_db():
    """Get database connection from pool with health check."""
    global db_pool
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        conn = await db_pool.acquire()
        # Quick health check
        await conn.fetchval("SELECT 1")
        return conn
    except asyncpg.exceptions.PostgresError as e:
        logger.error(f"[Database] Failed to acquire healthy connection: {e}")
        raise HTTPException(status_code=503, detail="Database temporarily unavailable")


async def release_db(conn):
    """Release connection back to pool."""
    if db_pool and conn:
        try:
            await db_pool.release(conn)
        except Exception as e:
            logger.warning(f"[Database] Error releasing connection: {e}")


async def init_database_with_retry():
    """Initialize database with retry logic for resilience."""
    global db_pool

    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")

    # Configure connection pool
    pool_min = int(os.getenv("DB_POOL_MIN_SIZE", "3"))
    pool_max = int(os.getenv("DB_POOL_MAX_SIZE", "20"))

    # Heroku Postgres requires SSL
    ssl_mode = os.getenv("DB_SSL", "")
    pool_kwargs = {}
    if ssl_mode == "require" or "sslmode=require" in DATABASE_URL:
        import ssl as ssl_module

        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_module.CERT_NONE
        pool_kwargs["ssl"] = ssl_ctx

    # Retry loop for initial connection
    last_exception = None
    for attempt in range(1, MAX_CONNECTION_RETRIES + 1):
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=pool_min,
                max_size=pool_max,
                timeout=30,
                command_timeout=60,
                **pool_kwargs,
            )

            # Test the connection
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            logger.info(
                f"[Database] Pool initialized successfully on attempt {attempt} "
                f"(min_size={pool_min}, max_size={pool_max})"
            )
            return

        except Exception as e:
            last_exception = e
            logger.warning(
                f"[Database] Connection attempt {attempt}/{MAX_CONNECTION_RETRIES} failed: {e}"
            )
            if attempt < MAX_CONNECTION_RETRIES:
                delay = CONNECTION_RETRY_DELAY * attempt  # Exponential backoff
                logger.info(f"[Database] Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    # All retries failed
    logger.error(
        f"[Database] Failed to initialize after {MAX_CONNECTION_RETRIES} attempts"
    )
    raise last_exception


async def init_database():
    """Initialize PostgreSQL database connection pool (legacy wrapper)."""
    await init_database_with_retry()


async def check_database_health() -> dict:
    """Check database health and return status."""
    global db_pool

    if db_pool is None:
        return {"status": "error", "message": "Database pool not initialized"}

    try:
        async with db_pool.acquire() as conn:
            start_time = asyncio.get_event_loop().time()
            await conn.fetchval("SELECT 1")
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            # Get pool stats
            size = db_pool.get_size()
            free = db_pool.get_idle_size()

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "pool_size": size,
                "pool_free": free,
                "pool_used": size - free,
            }
    except Exception as e:
        logger.error(f"[Database] Health check failed: {e}")
        return {"status": "error", "message": str(e)}


async def close_database():
    """Close database pool gracefully."""
    global db_pool
    if db_pool:
        logger.info("[Database] Closing connection pool...")
        await db_pool.close()
        db_pool = None
        logger.info("[Database] Connection pool closed")


async def close_database():
    """Close database pool."""
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for database initialization."""
    await init_database()
    yield
    await close_database()
