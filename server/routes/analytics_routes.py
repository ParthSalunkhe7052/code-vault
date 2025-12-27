"""
Analytics routes for CodeVault API.
Extracted from main.py for modularity.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends

from utils import get_current_user, utc_now
from database import get_db, release_db
from middleware.tier_enforcement import requires_feature

router = APIRouter(prefix="/api/v1", tags=["Analytics"])


@router.get("/stats/dashboard")
@requires_feature("analytics")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    import asyncio

    conn = await get_db()
    try:
        # Pre-calculate timestamps once
        now = utc_now()
        yesterday = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)
        seven_days_from_now = now + timedelta(days=7)
        user_id = user["id"]

        # Define all queries as coroutines to run in parallel
        async def get_projects():
            return await conn.fetchval(
                "SELECT COUNT(*) FROM projects WHERE user_id = $1", user_id
            )

        async def get_license_stats():
            return await conn.fetchrow(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN l.status = 'active' THEN 1 ELSE 0 END) as active,
                       SUM(CASE WHEN l.status = 'revoked' THEN 1 ELSE 0 END) as revoked
                FROM licenses l JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1
            """,
                user_id,
            )

        async def get_val_24h():
            return await conn.fetchrow(
                """
                SELECT COUNT(*) as total, SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as successful
                FROM validation_logs vl JOIN licenses l ON vl.license_id = l.id
                JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1 AND vl.created_at > $2
            """,
                user_id,
                yesterday,
            )

        async def get_recent_activity():
            return await conn.fetch(
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

        async def get_expiring_soon():
            return await conn.fetch(
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

        async def get_active_machines():
            return await conn.fetch(
                """
                SELECT DISTINCT ON (hb.hwid)
                    hb.hwid, hb.machine_name, hb.last_seen_at,
                    l.license_key, l.client_name,
                    (SELECT vl.ip_address FROM validation_logs vl 
                     WHERE vl.license_id = l.id ORDER BY vl.created_at DESC LIMIT 1) as ip_address
                FROM hardware_bindings hb
                JOIN licenses l ON hb.license_id = l.id 
                JOIN projects p ON l.project_id = p.id
                WHERE p.user_id = $1 AND hb.is_active = TRUE
                ORDER BY hb.hwid, hb.last_seen_at DESC
                LIMIT 10
            """,
                user_id,
            )

        async def get_history():
            return await conn.fetch(
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

        # Run all queries in parallel
        (
            total_projects,
            license_stats,
            val_24h,
            recent_activity_rows,
            expiring_soon_rows,
            active_machines_rows,
            history_rows,
        ) = await asyncio.gather(
            get_projects(),
            get_license_stats(),
            get_val_24h(),
            get_recent_activity(),
            get_expiring_soon(),
            get_active_machines(),
            get_history(),
        )

        # Format results
        recent_activity = [
            {
                "license_key": row["license_key"],
                "result": row["result"],
                "client_name": row["client_name"],
                "ip_address": row["ip_address"],
                "created_at": row["created_at"].isoformat()
                if row["created_at"]
                else None,
            }
            for row in recent_activity_rows
        ]

        expiring_soon = [
            {
                "id": str(row["id"]),
                "license_key": row["license_key"],
                "client_name": row["client_name"],
                "expires_at": row["expires_at"].isoformat()
                if row["expires_at"]
                else None,
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
    finally:
        await release_db(conn)


@router.get("/analytics/map-data")
async def get_map_data(user: dict = Depends(get_current_user)):
    """
    Get geolocation data for the Mission Control Live Map.
    Returns the latest validation location for each unique HWID
    for the user's projects in the last 24 hours.
    """
    conn = await get_db()
    try:
        yesterday = utc_now() - timedelta(days=1)

        rows = await conn.fetch(
            """
            WITH latest_validations AS (
                SELECT DISTINCT ON (vl.hwid)
                    vl.hwid, vl.city, vl.country, vl.latitude, vl.longitude, vl.created_at
                FROM validation_logs vl
                JOIN licenses l ON vl.license_id = l.id
                JOIN projects p ON l.project_id = p.id
                WHERE p.user_id = $1 
                  AND vl.created_at > $2
                  AND vl.latitude IS NOT NULL 
                  AND vl.longitude IS NOT NULL
                ORDER BY vl.hwid, vl.created_at DESC
            )
            SELECT 
                latitude as lat, 
                longitude as lng, 
                city, 
                country,
                COUNT(*) as count
            FROM latest_validations
            GROUP BY latitude, longitude, city, country
            ORDER BY count DESC
            LIMIT 100
        """,
            user["id"],
            yesterday,
        )

        return [
            {
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "city": row["city"] or "Unknown",
                "country": row["country"] or "??",
                "count": row["count"],
            }
            for row in rows
        ]
    finally:
        await release_db(conn)
