"""
Analytics routes for CodeVault API.
Extracted from main.py for modularity.
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from utils import get_current_user, utc_now, get_user_tier
from database import get_db, release_db

router = APIRouter(prefix="/api/v1", tags=["Analytics"])


@router.get("/stats/dashboard")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    # Pre-calculate timestamps once
    now = utc_now()
    yesterday = now - timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)
    seven_days_from_now = now + timedelta(days=7)
    user_id = user["id"]

    # Use a single connection for all queries to avoid pool exhaustion
    conn = await get_db()
    try:
        # 1. Projects Count
        total_projects = await conn.fetchval(
            "SELECT COUNT(*) FROM projects WHERE user_id = $1", user_id
        )

        # 2. License Stats
        license_stats = await conn.fetchrow(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN l.status = 'active' THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN l.status = 'revoked' THEN 1 ELSE 0 END) as revoked
            FROM licenses l JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1
        """,
            user_id,
        )

        # 3. Validations (Last 24h)
        val_24h = await conn.fetchrow(
            """
            SELECT COUNT(*) as total, SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as successful
            FROM validation_logs vl JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1 AND vl.created_at > $2
        """,
            user_id,
            yesterday,
        )

        # 4. Recent Activity
        recent_activity_rows = await conn.fetch(
            """
            SELECT vl.result, vl.ip_address, vl.created_at, 
                   l.license_key, l.client_name
            FROM validation_logs vl 
            JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id 
            WHERE p.user_id = $1
            ORDER BY vl.created_at DESC 
            LIMIT 10
        """,
            user_id,
        )

        # 5. Expiring Soon
        expiring_soon_rows = await conn.fetch(
            """
            SELECT l.id, l.license_key, l.client_name, l.expires_at, p.name as project_name
            FROM licenses l
            JOIN projects p ON l.project_id = p.id 
            WHERE p.user_id = $1 
              AND l.status = 'active'
              AND l.expires_at IS NOT NULL
              AND l.expires_at < $2
              AND l.expires_at > $3
            ORDER BY l.expires_at ASC
            LIMIT 5
        """,
            user_id,
            seven_days_from_now,
            now,
        )

        # 6. Active Machines
        active_machines_rows = await conn.fetch(
            """
            SELECT DISTINCT ON (hb.hwid)
                hb.hwid, hb.machine_name, hb.last_seen_at, hb.ip_address,
                l.license_key, l.client_name
            FROM hardware_bindings hb
            JOIN licenses l ON hb.license_id = l.id 
            JOIN projects p ON l.project_id = p.id
            WHERE p.user_id = $1 AND hb.is_active = TRUE
            ORDER BY hb.hwid, hb.last_seen_at DESC
            LIMIT 10
        """,
            user_id,
        )

        # 7. Validation History
        history_rows = await conn.fetch(
            """
            SELECT DATE(vl.created_at) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as successful,
                   SUM(CASE WHEN vl.result != 'valid' THEN 1 ELSE 0 END) as failed
            FROM validation_logs vl 
            JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id 
            WHERE p.user_id = $1 AND vl.created_at > $2
            GROUP BY DATE(vl.created_at)
            ORDER BY date ASC
        """,
            user_id,
            seven_days_ago,
        )

    finally:
        await release_db(conn)

    # Format results
    recent_activity = [
        {
            "license_key": row["license_key"],
            "result": row["result"],
            "client_name": row["client_name"],
            "ip_address": row["ip_address"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in recent_activity_rows
    ]

    expiring_soon = [
        {
            "id": str(row["id"]),
            "license_key": row["license_key"],
            "client_name": row["client_name"],
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
            "project_name": row["project_name"],
        }
        for row in expiring_soon_rows
    ]

    active_machines = [
        {
            "hwid": row["hwid"],
            "machine_name": row["machine_name"],
            "license_key": row["license_key"],
            "client_name": row["client_name"],
            "ip_address": row["ip_address"],
            "last_seen": row["last_seen_at"].isoformat()
            if row["last_seen_at"]
            else None,
        }
        for row in active_machines_rows
    ]

    validation_history = [
        {
            "date": row["date"].isoformat() if row["date"] else None,
            "total": row["total"] or 0,
            "successful": row["successful"] or 0,
            "failed": row["failed"] or 0,
        }
        for row in history_rows
    ]

    return {
        "projects": total_projects or 0,
        "licenses": {
            "total": license_stats["total"] or 0,
            "active": license_stats["active"] or 0,
            "revoked": license_stats["revoked"] or 0,
        },
        "validations": {
            "last_24h": {
                "total": val_24h["total"] or 0,
                "successful": val_24h["successful"] or 0,
            },
            "history": validation_history,
        },
        "active_machines": active_machines,
        "recent_activity": recent_activity,
        "expiring_soon": expiring_soon,
    }


@router.get("/analytics/licenses")
async def get_license_analytics(
    user: dict = Depends(get_current_user),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
):
    """
    Get detailed license analytics.

    Includes validation trends, geography distribution, and usage patterns.
    Advanced analytics available for Pro+ tiers.
    """
    conn = await get_db()
    try:
        # Check user tier
        tier = await get_user_tier(user["id"], conn)
        is_pro_tier = tier in ["pro", "business", "enterprise"]

        now = utc_now()
        start_date = now - timedelta(days=days)
        user_id = user["id"]

        # Base WHERE clause
        where_clause = "p.user_id = $1 AND vl.created_at > $2"
        params = [user_id, start_date]

        if project_id:
            where_clause += " AND p.id = $" + str(len(params) + 1)
            params.append(project_id)

        # 1. Validation trends (basic for all, extended for Pro+)
        validation_trends = await conn.fetch(
            f"""
            SELECT 
                DATE(vl.created_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN vl.result = 'invalid' THEN 1 ELSE 0 END) as invalid,
                SUM(CASE WHEN vl.result = 'expired' THEN 1 ELSE 0 END) as expired,
                SUM(CASE WHEN vl.result = 'revoked' THEN 1 ELSE 0 END) as revoked,
                SUM(CASE WHEN vl.result = 'tampered' THEN 1 ELSE 0 END) as tampered
            FROM validation_logs vl
            JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id
            WHERE {where_clause}
            GROUP BY DATE(vl.created_at)
            ORDER BY date DESC
            """,
            *params,
        )

        # 2. Country distribution (Pro+ only)
        country_distribution = []
        if is_pro_tier:
            country_rows = await conn.fetch(
                f"""
                SELECT 
                    COALESCE(vl.country, 'Unknown') as country,
                    COUNT(*) as count,
                    SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as valid_count
                FROM validation_logs vl
                JOIN licenses l ON vl.license_id = l.id
                JOIN projects p ON l.project_id = p.id
                WHERE {where_clause}
                GROUP BY vl.country
                ORDER BY count DESC
                LIMIT 20
                """,
                *params,
            )
            country_distribution = [
                {
                    "country": row["country"],
                    "count": row["count"],
                    "valid_count": row["valid_count"],
                }
                for row in country_rows
            ]

        # 3. Top licenses by usage
        top_licenses = await conn.fetch(
            f"""
            SELECT 
                l.license_key,
                l.client_name,
                p.name as project_name,
                COUNT(*) as validation_count,
                SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as valid_count,
                MAX(vl.created_at) as last_validated
            FROM validation_logs vl
            JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id
            WHERE {where_clause}
            GROUP BY l.id, l.license_key, l.client_name, p.name
            ORDER BY validation_count DESC
            LIMIT 10
            """,
            *params,
        )

        # 4. Summary stats
        summary = await conn.fetchrow(
            f"""
            SELECT 
                COUNT(DISTINCT l.id) as total_licenses,
                COUNT(*) as total_validations,
                SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as successful_validations,
                COUNT(DISTINCT vl.hwid) as unique_machines,
                COUNT(DISTINCT vl.ip_address) as unique_ips
            FROM validation_logs vl
            JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id
            WHERE {where_clause}
            """,
            *params,
        )

    finally:
        await release_db(conn)

    return {
        "summary": {
            "total_licenses": summary["total_licenses"] or 0,
            "total_validations": summary["total_validations"] or 0,
            "successful_validations": summary["successful_validations"] or 0,
            "unique_machines": summary["unique_machines"] or 0,
            "unique_ips": summary["unique_ips"] or 0,
            "success_rate": round(
                (summary["successful_validations"] or 0)
                / max(summary["total_validations"] or 1, 1)
                * 100,
                2,
            ),
        },
        "trends": [
            {
                "date": row["date"].isoformat() if row["date"] else None,
                "total": row["total"],
                "valid": row["valid"],
                "invalid": row["invalid"],
                "expired": row["expired"],
                "revoked": row["revoked"],
                "tampered": row["tampered"],
            }
            for row in validation_trends
        ],
        "geography": country_distribution
        if is_pro_tier
        else {"message": "Upgrade to Pro for advanced geography analytics"},
        "top_licenses": [
            {
                "license_key": row["license_key"],
                "client_name": row["client_name"],
                "project_name": row["project_name"],
                "validation_count": row["validation_count"],
                "valid_count": row["valid_count"],
                "last_validated": row["last_validated"].isoformat()
                if row["last_validated"]
                else None,
            }
            for row in top_licenses
        ],
        "tier": tier,
        "advanced_available": is_pro_tier,
    }


@router.get("/analytics/licenses/export")
async def export_license_analytics(
    user: dict = Depends(get_current_user),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    format: str = Query("json", pattern="^(json|csv)$", description="Export format"),
):
    """Export license analytics as JSON or CSV.

    Returns detailed validation history per license for the specified time period.
    """
    import json
    from datetime import datetime

    conn = await get_db()
    try:
        since = utc_now() - timedelta(days=days)
        user_id = user["id"]

        # Build query with optional project filter
        where_clause = "p.user_id = $1 AND vl.created_at > $2"
        params = [user_id, since]

        if project_id:
            where_clause += " AND p.id = $3"
            params.append(project_id)

        # Fetch detailed license analytics
        rows = await conn.fetch(
            f"""
            SELECT 
                l.id as license_id,
                l.license_key,
                l.client_name,
                l.client_email,
                l.status as license_status,
                p.id as project_id,
                p.name as project_name,
                vl.result,
                vl.hwid,
                vl.machine_name,
                vl.ip_address,
                vl.country,
                vl.city,
                vl.created_at as validated_at
            FROM validation_logs vl
            JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id
            WHERE {where_clause}
            ORDER BY vl.created_at DESC
            LIMIT 10000
            """,
            *params,
        )

        data = [
            {
                "license_id": row["license_id"],
                "license_key": row["license_key"],
                "client_name": row["client_name"],
                "client_email": row["client_email"],
                "license_status": row["license_status"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "validation_result": row["result"],
                "hwid": row["hwid"],
                "machine_name": row["machine_name"],
                "ip_address": row["ip_address"],
                "country": row["country"],
                "city": row["city"],
                "validated_at": row["validated_at"].isoformat()
                if row["validated_at"]
                else None,
            }
            for row in rows
        ]

        if format == "csv":
            import io
            import csv

            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            from fastapi.responses import Response

            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=license_analytics_{datetime.now().strftime('%Y%m%d')}.csv"
                },
            )

        return {
            "exported_at": datetime.now().isoformat(),
            "days": days,
            "total_records": len(data),
            "records": data,
        }
    finally:
        await release_db(conn)


@router.get("/analytics/licenses/summary")
async def get_license_usage_summary(
    user: dict = Depends(get_current_user),
):
    """Get a quick summary of license usage across all projects."""
    conn = await get_db()
    try:
        user_id = user["id"]

        # Get per-project license counts
        project_stats = await conn.fetch(
            """
            SELECT 
                p.id as project_id,
                p.name as project_name,
                COUNT(l.id) as total_licenses,
                SUM(CASE WHEN l.status = 'active' THEN 1 ELSE 0 END) as active_licenses,
                SUM(CASE WHEN l.status = 'revoked' THEN 1 ELSE 0 END) as revoked_licenses,
                SUM(CASE WHEN l.status = 'expired' THEN 1 ELSE 0 END) as expired_licenses,
                (SELECT COUNT(*) FROM hardware_bindings hb 
                 JOIN licenses l2 ON hb.license_id = l2.id 
                 WHERE l2.project_id = p.id AND hb.is_active = TRUE) as active_bindings
            FROM projects p
            LEFT JOIN licenses l ON l.project_id = p.id
            WHERE p.user_id = $1
            GROUP BY p.id, p.name
            ORDER BY total_licenses DESC
            """,
            user_id,
        )

        # Get user's total license usage
        user_data = await conn.fetchrow(
            """
            SELECT 
                total_licenses_used,
                legacy_tier_model,
                plan
            FROM users WHERE id = $1
            """,
            user_id,
        )

        from config import TIER_LIMITS

        tier = user_data["plan"] or "free"
        tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        max_total = tier_limits.get("max_licenses_total", -1)

        return {
            "tier": tier,
            "licenses_used": user_data["total_licenses_used"] or 0,
            "licenses_limit": max_total,
            "legacy_tier_model": user_data["legacy_tier_model"] or False,
            "projects": [
                {
                    "project_id": row["project_id"],
                    "project_name": row["project_name"],
                    "total_licenses": row["total_licenses"] or 0,
                    "active_licenses": row["active_licenses"] or 0,
                    "revoked_licenses": row["revoked_licenses"] or 0,
                    "expired_licenses": row["expired_licenses"] or 0,
                    "active_bindings": row["active_bindings"] or 0,
                }
                for row in project_stats
            ],
        }
    finally:
        await release_db(conn)
