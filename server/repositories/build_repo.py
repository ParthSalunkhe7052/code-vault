"""
Build Repository - Data access layer for cloud build operations.
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from asyncpg import Connection

class BuildRepository:
    """Handles all database operations for cloud builds, artifacts, and credits."""

    @staticmethod
    async def get_build_by_id(conn: Connection, build_id: str) -> Optional[Dict[str, Any]]:
        """Get a cloud build record."""
        return await conn.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1",
            build_id
        )

    @staticmethod
    async def list_user_builds(conn: Connection, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List builds for a user."""
        return await conn.fetch(
            "SELECT * FROM cloud_builds WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
            user_id,
            limit
        )

    @staticmethod
    async def create_build(conn: Connection, data: Dict[str, Any]) -> None:
        """Create a new cloud build record."""
        await conn.execute(
            """
            INSERT INTO cloud_builds (id, user_id, project_id, license_id, status, target_platforms, build_type)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            data['id'],
            data['user_id'],
            data['project_id'],
            data.get('license_id'),
            data['status'],
            data['target_platforms'],
            data.get('build_type', 'standard')
        )

    @staticmethod
    async def update_build_status(conn: Connection, build_id: str, status: str, error: Optional[str] = None) -> None:
        """Update the overall status of a build."""
        await conn.execute(
            """
            UPDATE cloud_builds SET status = $1, error_message = $2, updated_at = NOW()
            WHERE id = $3
            """,
            status,
            error,
            build_id
        )

    @staticmethod
    async def deduct_credits(conn: Connection, user_id: str, amount: int) -> bool:
        """Deduct build credits from a user. Returns True if successful."""
        result = await conn.execute(
            "UPDATE users SET build_credits = build_credits - $1 WHERE id = $2 AND build_credits >= $1",
            amount,
            user_id
        )
        return result != "UPDATE 0"

    @staticmethod
    async def refund_credits(conn: Connection, user_id: str, amount: int) -> None:
        """Refund build credits to a user."""
        await conn.execute(
            "UPDATE users SET build_credits = build_credits + $1 WHERE id = $2",
            amount,
            user_id
        )

    @staticmethod
    async def create_artifact(conn: Connection, data: Dict[str, Any]) -> None:
        """Create an artifact record for a specific platform."""
        await conn.execute(
            """
            INSERT INTO cloud_build_artifacts (id, build_id, platform, status)
            VALUES ($1, $2, $3, $4)
            """,
            data['id'],
            data['build_id'],
            data['platform'],
            data.get('status', 'pending')
        )

    @staticmethod
    async def update_artifact(conn: Connection, build_id: str, platform: str, data: Dict[str, Any]) -> None:
        """Update an artifact's status and download info."""
        await conn.execute(
            """
            UPDATE cloud_build_artifacts
            SET status = $1, download_key = $2, download_filename = $3, 
                error_message = $4, completed_at = NOW()
            WHERE build_id = $5 AND platform = $6
            """,
            data['status'],
            data.get('download_key'),
            data.get('filename'),
            data.get('error'),
            build_id,
            platform
        )

    @staticmethod
    async def check_webhook_idempotency(conn: Connection, event_id: str) -> bool:
        """Check if a webhook event has already been processed."""
        existing = await conn.fetchval(
            "SELECT event_id FROM processed_webhook_events WHERE event_id = $1",
            event_id
        )
        return bool(existing)

    @staticmethod
    async def record_webhook_event(conn: Connection, event_id: str, event_type: str) -> None:
        """Record a webhook event for idempotency."""
        await conn.execute(
            """INSERT INTO processed_webhook_events (event_id, event_type, processed_at)
               VALUES ($1, $2, NOW())
               ON CONFLICT (event_id) DO NOTHING""",
            event_id,
            event_type
        )
