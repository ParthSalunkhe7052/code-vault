"""
CodeVault Cloud Build - Queue System

Background task queue for managing build jobs.
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from database import get_db, release_db
from middleware.rate_limiter import get_redis_client

logger = logging.getLogger(__name__)

# In-memory queue processing task (runs in background)
_queue_processor_started = False


async def add_to_queue(
    build_id: str, config: dict, user_id: str, priority: int, project_id: str
):
    """Add a build to the Redis queue."""
    redis_client = await get_redis_client()
    if not redis_client:
        # No Redis - trigger immediately (handled by caller)
        return None

    queue_name = "cloud_build_queue"
    queue_item = {
        "build_id": build_id,
        "config": config,
        "user_id": user_id,
        "project_id": project_id,
        "priority": priority,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    }

    # Add to sorted set with priority (lower score = higher priority)
    await redis_client.zadd(queue_name, {json.dumps(queue_item): priority})

    # Start queue processor if not already started
    global _queue_processor_started
    if not _queue_processor_started:
        _queue_processor_started = True
        asyncio.create_task(process_build_queue())

    # Get queue position
    position = await redis_client.zrank(queue_name, json.dumps(queue_item))

    return {
        "status": "queued",
        "position": position if position is not None else 0,
        "message": "Build queued for processing",
    }


async def process_build_queue():
    """Background task that processes builds from the queue."""
    try:
        redis_client = await get_redis_client()
        if not redis_client:
            logger.warning("[Queue] Redis not available, queue processing disabled")
            return

        queue_name = "cloud_build_queue"
        logger.info("[Queue] Build queue processor started")

        while True:
            try:
                # Get highest priority item (lowest score)
                items = await redis_client.zrange(queue_name, 0, 0, withscores=True)

                if items:
                    queue_item_json, priority = items[0]
                    queue_item = json.loads(queue_item_json)

                    build_id = queue_item["build_id"]
                    config = queue_item["config"]
                    project_id = queue_item["project_id"]

                    # Check if build is still pending
                    conn = await get_db()
                    try:
                        build = await conn.fetchrow(
                            "SELECT status FROM cloud_builds WHERE id = $1", build_id
                        )

                        if build and build["status"] == "pending":
                            # Import here to avoid circular dependency
                            from .cloud_build_routes import (
                                validate_safe_path,
                                trigger_cloud_build,
                            )
                            from .cloud_build_routes import UPLOAD_DIR

                            # Get source directory
                            safe_project_dir = validate_safe_path(
                                UPLOAD_DIR, project_id
                            )
                            source_dir = safe_project_dir / "source"

                            if not source_dir.exists():
                                projects_base = UPLOAD_DIR / "projects"
                                safe_alt = validate_safe_path(projects_base, project_id)
                                if (safe_alt / "source").exists():
                                    source_dir = safe_alt / "source"

                            if source_dir.exists() and list(source_dir.iterdir()):
                                # Trigger the build
                                logger.info(
                                    f"[Queue] Processing build {build_id} (priority: {priority})"
                                )
                                await trigger_cloud_build(build_id, config, source_dir)
                            else:
                                logger.error(
                                    f"[Queue] Build {build_id} source not found"
                                )
                                await conn.execute(
                                    "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
                                    "Source files not found",
                                    build_id,
                                )
                        else:
                            logger.info(
                                f"[Queue] Build {build_id} already processed or cancelled"
                            )
                    finally:
                        await release_db(conn)

                    # Remove from queue
                    await redis_client.zrem(queue_name, queue_item_json)
                else:
                    # Queue empty - wait a bit
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"[Queue] Error processing queue: {e}")
                await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"[Queue] Fatal error in queue processor: {e}")
        raise


async def get_queue_position(build_id: str) -> Optional[int]:
    """Get the position of a build in the queue."""
    redis_client = await get_redis_client()
    if not redis_client:
        return None

    queue_name = "cloud_build_queue"

    # Find item with matching build_id
    all_items = await redis_client.zrange(queue_name, 0, -1, withscores=True)
    for item_json, _ in all_items:
        item = json.loads(item_json)
        if item["build_id"] == build_id:
            # Get rank (0-based, so add 1 for human-readable)
            rank = await redis_client.zrank(queue_name, item_json)
            return rank + 1 if rank is not None else None

    return None


async def trigger_build_directly(build_id: str, config: dict, project_id: str):
    """Fallback: trigger build directly without queue."""
    try:
        # Import here to avoid circular dependency
        from .cloud_build_routes import validate_safe_path, trigger_cloud_build
        from .cloud_build_routes import UPLOAD_DIR

        safe_project_dir = validate_safe_path(UPLOAD_DIR, project_id)
        source_dir = safe_project_dir / "source"

        if not source_dir.exists():
            projects_base = UPLOAD_DIR / "projects"
            safe_alt = validate_safe_path(projects_base, project_id)
            if (safe_alt / "source").exists():
                source_dir = safe_alt / "source"

        await trigger_cloud_build(build_id, config, source_dir)
        return {"status": "running", "message": "Build started immediately"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_queue_status(build_id: str, user_id: str) -> Dict[str, Any]:
    """Get queue position for a specific build."""
    conn = await get_db()
    try:
        from fastapi import HTTPException

        build = await conn.fetchrow(
            "SELECT id, status FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id,
            user_id,
        )
        if not build:
            raise HTTPException(404, "Build not found")

        if build["status"] != "pending":
            return {
                "position": None,
                "status": build["status"],
                "message": "Not in queue",
            }

        position = await get_queue_position(build_id)
        return {
            "position": position,
            "status": "queued",
            "message": f"Your build is #{position} in queue"
            if position
            else "In queue",
        }
    finally:
        await release_db(conn)


async def get_queue_info() -> Dict[str, Any]:
    """Get overall queue information."""
    redis_client = await get_redis_client()
    if not redis_client:
        return {"enabled": False, "message": "Queue not available"}

    queue_name = "cloud_build_queue"
    queue_length = await redis_client.zcard(queue_name)

    # Get top 5 items
    items = await redis_client.zrange(queue_name, 0, 4, withscores=True)
    queue_preview = []

    for item_json, priority in items:
        item = json.loads(item_json)
        queue_preview.append(
            {
                "build_id": item["build_id"],
                "priority": priority,
                "user_id": item["user_id"],
            }
        )

    return {"enabled": True, "length": queue_length, "preview": queue_preview}
