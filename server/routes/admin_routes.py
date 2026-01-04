"""
Admin routes for CodeVault API.
Extracted from main.py for modularity.
"""

from fastapi import APIRouter, Depends

from utils import get_current_admin_user
from database import get_db, release_db

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/stats")
async def get_admin_stats(user: dict = Depends(get_current_admin_user)):
    """Get system-wide statistics (admin only)."""
    conn = await get_db()
    try:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_projects = await conn.fetchval("SELECT COUNT(*) FROM projects")
        total_licenses = await conn.fetchval("SELECT COUNT(*) FROM licenses")
        active_licenses = await conn.fetchval(
            "SELECT COUNT(*) FROM licenses WHERE status = 'active'"
        )

        validations_today = await conn.fetchval("""
            SELECT COUNT(*) FROM validation_logs 
            WHERE created_at >= CURRENT_DATE
        """)

        validations_week = await conn.fetchval("""
            SELECT COUNT(*) FROM validation_logs 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        """)

        total_compiles = await conn.fetchval("SELECT COUNT(*) FROM compile_jobs")
        successful_compiles = await conn.fetchval(
            "SELECT COUNT(*) FROM compile_jobs WHERE status = 'completed'"
        )

        return {
            "total_users": total_users or 0,
            "total_projects": total_projects or 0,
            "total_licenses": total_licenses or 0,
            "active_licenses": active_licenses or 0,
            "validations_today": validations_today or 0,
            "validations_week": validations_week or 0,
            "total_compiles": total_compiles or 0,
            "successful_compiles": successful_compiles or 0,
        }
    finally:
        await release_db(conn)


@router.get("/users")
async def list_all_users(user: dict = Depends(get_current_admin_user)):
    """List all users in the system with their project/license counts (admin only)."""
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT 
                u.id, u.email, u.name, u.plan, u.role, u.created_at,
                (SELECT COUNT(*) FROM projects p WHERE p.user_id = u.id) as project_count,
                (SELECT COUNT(*) FROM licenses l 
                 JOIN projects p ON l.project_id = p.id 
                 WHERE p.user_id = u.id) as license_count
            FROM users u
            ORDER BY u.created_at DESC
        """)

        return [
            {
                "id": r["id"],
                "email": r["email"],
                "name": r["name"],
                "plan": r["plan"],
                "role": r["role"] or "user",
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "project_count": r["project_count"] or 0,
                "license_count": r["license_count"] or 0,
            }
            for r in rows
        ]
    finally:
        await release_db(conn)


@router.get("/analytics")
async def get_admin_analytics(
    days: int = 30, user: dict = Depends(get_current_admin_user)
):
    """Get analytics data for charts (admin only)."""
    conn = await get_db()
    try:
        validation_stats = await conn.fetch(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM validation_logs
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            GROUP BY DATE(created_at)
            ORDER BY date
        """,
            days,
        )

        user_stats = await conn.fetch(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            GROUP BY DATE(created_at)
            ORDER BY date
        """,
            days,
        )

        compile_stats = await conn.fetch(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM compile_jobs
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            GROUP BY DATE(created_at)
            ORDER BY date
        """,
            days,
        )

        recent_webhooks = await conn.fetch("""
            SELECT wd.id, wd.event_type, wd.success, wd.created_at, w.name as webhook_name
            FROM webhook_deliveries wd
            JOIN webhooks w ON wd.webhook_id = w.id
            ORDER BY wd.created_at DESC
            LIMIT 20
        """)

        return {
            "validations": [
                {"date": r["date"].isoformat(), "count": r["count"]}
                for r in validation_stats
            ],
            "new_users": [
                {"date": r["date"].isoformat(), "count": r["count"]} for r in user_stats
            ],
            "compiles": [
                {"date": r["date"].isoformat(), "count": r["count"]}
                for r in compile_stats
            ],
            "recent_webhooks": [
                {
                    "id": r["id"],
                    "event_type": r["event_type"],
                    "success": r["success"],
                    "webhook_name": r["webhook_name"],
                    "created_at": r["created_at"].isoformat()
                    if r["created_at"]
                    else None,
                }
                for r in recent_webhooks
            ],
        }
    finally:
        await release_db(conn)
