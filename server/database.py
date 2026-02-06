"""
Database connection pool and initialization for PostgreSQL.
"""

import os
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
from fastapi import HTTPException

from config import DATABASE_URL

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


async def get_db():
    """Get database connection from pool."""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return await db_pool.acquire()


async def release_db(conn):
    """Release connection back to pool."""
    if db_pool and conn:
        await db_pool.release(conn)


async def init_database():
    """Initialize PostgreSQL database connection pool."""
    global db_pool

    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")

    # Configure connection pool
    # Pool sizes configurable via env vars for different deployment targets
    # Heroku basic Postgres allows 20 connections; Neon free tier allows 100
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

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=pool_min,
        max_size=pool_max,
        timeout=30,
        command_timeout=60,
        **pool_kwargs,
    )
    print(f"[Database] Pool initialized (min_size={pool_min}, max_size={pool_max})")


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
