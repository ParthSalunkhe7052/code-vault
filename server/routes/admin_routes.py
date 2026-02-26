"""
Admin routes for CodeVault API.
Extracted from main.py for modularity.
"""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from utils import get_current_admin_user
from database import get_db, release_db, db_pool

logger = logging.getLogger(__name__)

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


# ============== NEW ADMIN ENDPOINTS ==============


@router.get("/revenue")
async def get_revenue_analytics(user: dict = Depends(get_current_admin_user)):
    """Get revenue analytics - MRR, subscription breakdown, growth data."""
    conn = await get_db()
    try:
        # Active subscriptions by tier (excluding free)
        tier_breakdown = await conn.fetch("""
            SELECT plan_tier, COUNT(*) as count
            FROM subscriptions
            WHERE status = 'active' AND plan_tier != 'free'
            GROUP BY plan_tier
        """)

        # Calculate MRR (pro=$15, business=$39)
        mrr_result = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(CASE WHEN plan_tier = 'pro' THEN 15 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN plan_tier = 'business' THEN 39 ELSE 0 END), 0) as mrr,
                COUNT(*) FILTER (WHERE plan_tier = 'pro') as pro_count,
                COUNT(*) FILTER (WHERE plan_tier = 'business') as business_count
            FROM subscriptions
            WHERE status = 'active'
        """)

        # Subscription changes over time (last 30 days)
        subscription_history = await conn.fetch("""
            SELECT DATE(created_at) as date, plan_tier, COUNT(*) as count
            FROM subscriptions
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(created_at), plan_tier
            ORDER BY date
        """)

        # Total users by plan
        users_by_plan = await conn.fetch("""
            SELECT plan, COUNT(*) as count
            FROM users
            GROUP BY plan
        """)

        return {
            "mrr": mrr_result["mrr"] if mrr_result else 0,
            "pro_subscribers": mrr_result["pro_count"] if mrr_result else 0,
            "business_subscribers": mrr_result["business_count"]
            if mrr_result
            else 0,
            "tier_breakdown": [dict(r) for r in tier_breakdown],
            "subscription_history": [
                {
                    "date": r["date"].isoformat(),
                    "tier": r["plan_tier"],
                    "count": r["count"],
                }
                for r in subscription_history
            ],
            "users_by_plan": [dict(r) for r in users_by_plan],
        }
    finally:
        await release_db(conn)


@router.get("/system-health")
async def get_system_health(user: dict = Depends(get_current_admin_user)):
    """Get system health metrics - DB pool, webhook stats, recent errors."""
    conn = await get_db()
    try:
        # Database connection pool stats
        db_stats = {
            "min_size": db_pool.get_min_size() if db_pool else 0,
            "max_size": db_pool.get_max_size() if db_pool else 0,
            "size": db_pool.get_size() if db_pool else 0,
            "free_size": db_pool.get_idle_size() if db_pool else 0,
        }

        # Recent compile errors
        recent_errors = await conn.fetch("""
            SELECT id, error_message, created_at
            FROM compile_jobs
            WHERE status = 'failed' AND error_message IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """)

        # Webhook health (success rate last 24h)
        webhook_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE success = true) as successful
            FROM webhook_deliveries
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)

        # API performance (validation response times - approximate from logs)
        validation_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_validations
            FROM validation_logs
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """)

        return {
            "database": db_stats,
            "recent_errors": [
                {
                    "id": r["id"],
                    "message": r["error_message"][:200] if r["error_message"] else None,
                    "timestamp": r["created_at"].isoformat()
                    if r["created_at"]
                    else None,
                }
                for r in recent_errors
            ],
            "webhooks": {
                "total_24h": webhook_stats["total"] if webhook_stats else 0,
                "success_rate": (
                    round(webhook_stats["successful"] / webhook_stats["total"] * 100, 1)
                    if webhook_stats and webhook_stats["total"] > 0
                    else 100
                ),
            },
            "api_performance": {
                "validations_last_hour": validation_stats["total_validations"]
                if validation_stats
                else 0,
            },
        }
    finally:
        await release_db(conn)


# Pydantic models for user management
class UpdateUserPlanRequest(BaseModel):
    plan: str  # 'free', 'pro', 'business'


class UpdateUserRoleRequest(BaseModel):
    role: str  # 'user', 'admin'


@router.put("/users/{user_id}/plan")
async def update_user_plan(
    user_id: str,
    data: UpdateUserPlanRequest,
    admin: dict = Depends(get_current_admin_user),
):
    """Admin: Change a user's subscription tier."""
    if data.plan not in ["free", "pro", "business"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan tier. Must be 'free', 'pro', or 'business'",
        )

    conn = await get_db()
    try:
        async with conn.transaction():
            # Verify user exists
            user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Update users table
            await conn.execute(
                "UPDATE users SET plan = $1, updated_at = NOW() WHERE id = $2",
                data.plan,
                user_id,
            )

            # Update or create subscription
            existing = await conn.fetchrow(
                "SELECT id FROM subscriptions WHERE user_id = $1", user_id
            )
            if existing:
                await conn.execute(
                    """
                    UPDATE subscriptions SET plan_tier = $1, status = 'active',
                    sync_source = 'admin_override', updated_at = NOW()
                    WHERE user_id = $2
                    """,
                    data.plan,
                    user_id,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO subscriptions (id, user_id, plan_tier, status, sync_source)
                    VALUES ($1, $2, $3, 'active', 'admin_override')
                    """,
                    str(uuid.uuid4()),
                    user_id,
                    data.plan,
                )

        return {"message": f"User plan updated to {data.plan}"}
    finally:
        await release_db(conn)


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    data: UpdateUserRoleRequest,
    admin: dict = Depends(get_current_admin_user),
):
    """Admin: Change a user's role."""
    if data.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=400, detail="Invalid role. Must be 'user' or 'admin'"
        )

    conn = await get_db()
    try:
        # Verify user exists
        user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await conn.execute(
            "UPDATE users SET role = $1, updated_at = NOW() WHERE id = $2",
            data.role,
            user_id,
        )

        logger.info(
            f"[Admin] Role changed to '{data.role}' for user ID: {user_id[:8]}... "
            f"(by admin: {admin['id'][:8]}...)"
        )

        return {"message": f"User role updated to {data.role}"}
    finally:
        await release_db(conn)


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    admin: dict = Depends(get_current_admin_user),
):
    """Admin: Ban a user - revoke all licenses, disable account."""
    conn = await get_db()
    try:
        async with conn.transaction():
            # Verify user exists with role
            user = await conn.fetchrow(
                "SELECT id, email, role FROM users WHERE id = $1", user_id
            )
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Security checks
            if user_id == admin["id"]:
                raise HTTPException(status_code=400, detail="Cannot ban yourself")
            if user.get("role") == "admin":
                raise HTTPException(status_code=400, detail="Cannot ban another admin")

            # Revoke all user's licenses
            await conn.execute(
                """
                UPDATE licenses l SET status = 'revoked'
                FROM projects p
                WHERE l.project_id = p.id AND p.user_id = $1
                """,
                user_id,
            )

            # Set plan to free and role to banned
            await conn.execute(
                """
                UPDATE users SET plan = 'free', role = 'banned', updated_at = NOW()
                WHERE id = $1
                """,
                user_id,
            )

            # Update subscription to inactive
            await conn.execute(
                """
                UPDATE subscriptions SET status = 'canceled', plan_tier = 'free',
                sync_source = 'admin_ban', updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id,
            )

        return {"message": "User has been banned", "user_id": user_id}
    finally:
        await release_db(conn)


@router.post("/migrate-signing")
async def migrate_signing_to_ed25519(
    admin: dict = Depends(get_current_admin_user),
):
    """Admin: Migrate all legacy HMAC projects to Ed25519 asymmetric signing.

    Generates Ed25519 key pairs for projects that don't have them yet.
    Existing compiled binaries using HMAC will continue to work during
    a 90-day grace period — the server still accepts HMAC validation
    but logs deprecation warnings.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PrivateFormat,
        PublicFormat,
        NoEncryption,
    )

    conn = await get_db()
    try:
        # Find projects without Ed25519 keys
        projects = await conn.fetch(
            "SELECT id, name FROM projects WHERE signing_private_key IS NULL"
        )

        if not projects:
            return {
                "message": "All projects already have Ed25519 keys",
                "migrated": 0,
            }

        migrated = 0
        for project in projects:
            private_key = Ed25519PrivateKey.generate()
            private_pem = private_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.PKCS8,
                encryption_algorithm=NoEncryption(),
            ).decode("utf-8")
            public_pem = private_key.public_key().public_bytes(
                encoding=Encoding.PEM,
                format=PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            await conn.execute(
                """
                UPDATE projects
                SET signing_private_key = $1,
                    signing_public_key = $2,
                    signing_algorithm = 'ed25519'
                WHERE id = $3
                """,
                private_pem,
                public_pem,
                project["id"],
            )
            migrated += 1
            logger.info(
                f"[Ed25519] Migrated project: {project['name']} ({project['id'][:8]}...)"
            )

        return {
            "message": f"Migrated {migrated} project(s) to Ed25519 signing",
            "migrated": migrated,
        }
    finally:
        await release_db(conn)
