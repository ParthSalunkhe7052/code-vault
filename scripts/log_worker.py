"""
CodeVault Log Worker
Asynchronously flushes validation logs from Redis to PostgreSQL in batches.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import List

import asyncpg
import redis.asyncio as redis
from dotenv import load_dotenv

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("log_worker")

async def flush_batch(conn: asyncpg.Connection, batch: List[dict]):
    """Insert a batch of logs into PostgreSQL."""
    if not batch:
        return

    try:
        # Prepare data for executemany
        # columns: license_id, license_key, hwid, ip_address, result, response_time_ms, machine_name, created_at
        data = [
            (
                b.get("license_id"),
                b.get("license_key"),
                b.get("hwid"),
                b.get("ip_address"),
                b.get("result"),
                b.get("response_time_ms"),
                b.get("created_at")
            )
            for b in batch
        ]

        await conn.executemany(
            """
            INSERT INTO validation_logs (license_id, license_key, hwid, ip_address, result, response_time_ms, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            data
        )
        logger.info(f"✅ Flushed {len(batch)} logs to Postgres")
    except Exception as e:
        logger.error(f"❌ Failed to flush batch: {e}")

async def run_worker():
    # Try to load from server/.env if not in root
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'server', '.env'))
    load_dotenv() # Fallback to root
    redis_url = os.getenv("REDIS_URL")
    # If REDIS_URL not set, try to construct it from UPSTASH variables
    if not redis_url:
        rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
        rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        if rest_url and rest_token:
            endpoint = rest_url.replace("https://", "").replace("http://", "")
            redis_url = f"rediss://default:{rest_token}@{endpoint}:6379"
    
    database_url = os.getenv("DATABASE_URL")

    if not redis_url or not database_url:
        logger.error("❌ REDIS_URL or DATABASE_URL not set")
        return

    logger.info("🚀 Starting Log Worker...")
    
    r = redis.from_url(redis_url)
    conn = await asyncpg.connect(database_url)
    
    batch = []
    last_flush = time.time()
    
    try:
        while True:
            # Block for up to 5 seconds waiting for a log
            result = await r.brpop("license_logs_queue", timeout=5)
            
            if result:
                _, log_json = result
                batch.append(json.loads(log_json))
            
            # Flush if batch is full (100) or 10 seconds passed
            if len(batch) >= 100 or (time.time() - last_flush > 10 and batch):
                await flush_batch(conn, batch)
                batch = []
                last_flush = time.time()
                
    except asyncio.CancelledError:
        logger.info("🛑 Worker shutting down...")
        if batch:
            await flush_batch(conn, batch)
    except Exception as e:
        logger.error(f"💥 Worker crashed: {e}")
    finally:
        await r.close()
        await conn.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
