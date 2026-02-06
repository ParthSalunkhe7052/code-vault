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
    # Increased max_size for better concurrency under Enterprise load
    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=50,
        timeout=30,
        command_timeout=60
    )
    print(f"[Database] Pool initialized (min_size=5, max_size=50)")


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