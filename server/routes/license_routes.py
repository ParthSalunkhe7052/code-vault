"""
License routes for CodeVault API.
Extracted from main.py for modularity.
"""

import json
import time
import secrets
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from starlette.concurrency import run_in_threadpool

from models import (
    LicenseValidationRequest,
    LicenseValidationResponse,
    LicenseCreateRequest,
    LicenseVariableCreateRequest,
    LicenseVariableUpdateRequest,
)
from utils import (
    get_current_user,
    utc_now,
    generate_license_key,
    create_validation_response,
    get_user_tier_limits,
)
from database import get_db, release_db
from email_service import notify_license_created
from middleware.rate_limiter import license_validate_rate_limit

router = APIRouter(prefix="/api/v1", tags=["Licenses"])


# GeoIP functions (import from geoip module when created, for now inline)
_geoip_warned = False  # Module-level flag to avoid log spam


def get_geo_from_ip(ip_address: str) -> dict:
    """Get geolocation data from IP address.

    For localhost/private IPs, returns a "Dev Location" (New York) so the
    Mission Control map works during local development.
    """
    global _geoip_warned

    # Default result
    result = {"city": None, "country": None, "latitude": None, "longitude": None}

    # For localhost/dev, return a sample location so the map works
    if ip_address in ("127.0.0.1", "::1", "localhost", "unknown"):
        return {
            "city": "New York",
            "country": "US",
            "latitude": 40.7128,
            "longitude": -74.0060,
        }

    try:
        import ipaddress

        ip = ipaddress.ip_address(ip_address)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            # Return dev location for private IPs too
            return {
                "city": "Local Network",
                "country": "XX",
                "latitude": 40.7128,
                "longitude": -74.0060,
            }
    except ValueError:
        return result

    # Try GeoIP lookup
    reader = None
    try:
        import geoip2.database
        import geoip2.errors
        from pathlib import Path

        geoip_path = Path(__file__).parent.parent / "data" / "GeoLite2-City.mmdb"
        if geoip_path.exists():
            reader = geoip2.database.Reader(str(geoip_path))
            response = reader.city(ip_address)
            result["city"] = response.city.name
            result["country"] = response.country.iso_code
            result["latitude"] = response.location.latitude
            result["longitude"] = response.location.longitude
        else:
            if not _geoip_warned:
                logging.warning(
                    f"[GeoIP] Database not found at {geoip_path}. "
                    "Map data will be unavailable. Download GeoLite2-City.mmdb from MaxMind."
                )
                _geoip_warned = True
    except geoip2.errors.AddressNotFoundError:
        # IP not in database, this is normal for some IPs
        pass
    except Exception as e:
        logging.warning(f"[GeoIP] Lookup failed for {ip_address}: {e}")
    finally:
        if reader:
            reader.close()

    return result


async def _push_validation_log_to_redis(log_data: dict):
    """Push validation log to Redis queue for asynchronous processing by log worker."""
    from config import REDIS_URL
    import redis.asyncio as redis
    
    if not REDIS_URL:
        logging.warning("[Redis] REDIS_URL not set, log will be dropped")
        return

    try:
        r = redis.from_url(REDIS_URL)
        await r.lpush("license_logs_queue", json.dumps(log_data))
        await r.close()
    except Exception as e:
        logging.error(f"[Redis] Failed to push log: {e}")


@router.post("/license/validate", response_model=LicenseValidationResponse)
async def validate_license(
    request: Request,
    data: LicenseValidationRequest,
    _rate_limit: None = Depends(license_validate_rate_limit),
):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    if abs(int(time.time()) - data.timestamp) > 300:
        return create_validation_response(
            "invalid", "Request timestamp expired", data.nonce
        )

    conn = await get_db()
    try:
        # Use transaction with row-level locking to prevent race conditions
        async with conn.transaction():
            # Lock the license row and JOIN with projects to get signing_secret
            license_row = await conn.fetchrow(
                """SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features, p.signing_secret 
                   FROM licenses l 
                   JOIN projects p ON l.project_id = p.id
                   WHERE l.license_key = $1 FOR UPDATE""",
                data.license_key,
            )
            response_time = int((time.time() - start_time) * 1000)

            result_status = "valid"
            message = "License valid"
            
            # Use project secret or fallback to global if none (for legacy)
            from config import SECRET_KEY
            signing_secret = license_row["signing_secret"] if license_row and license_row["signing_secret"] else SECRET_KEY

            if not license_row:
                result_status = "invalid"
                message = "License not found"
            elif license_row["status"] == "revoked":
                result_status = "revoked"
                message = "License has been revoked"
            elif license_row["expires_at"] and license_row["expires_at"] < utc_now():
                result_status = "expired"
                message = "License has expired"
            
            # Prepare log data for Redis
            log_data = {
                "license_id": license_row["id"] if license_row else None,
                "license_key": data.license_key,
                "hwid": data.hwid,
                "ip_address": client_ip,
                "result": result_status,
                "response_time_ms": response_time,
                "machine_name": data.machine_name,
                "created_at": utc_now().isoformat()
            }

            if result_status != "valid":
                # Push log to Redis and return early
                asyncio.create_task(_push_validation_log_to_redis(log_data))
                return create_validation_response(result_status, message, data.nonce)

            # Check HWID binding
            license_id = license_row["id"]
            existing_binding = await conn.fetchrow(
                "SELECT id, is_active FROM hardware_bindings WHERE license_id = $1 AND hwid = $2",
                license_id,
                data.hwid,
            )

            if existing_binding:
                # If machine was deactivated, check if we can reactivate it (limit check)
                if not existing_binding["is_active"]:
                    machine_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
                        license_id,
                    )
                    if machine_count >= license_row["max_machines"]:
                        log_data["result"] = "hwid_mismatch"
                        asyncio.create_task(_push_validation_log_to_redis(log_data))
                        return create_validation_response(
                            "hwid_mismatch",
                            f"Maximum machines ({license_row['max_machines']}) reached",
                            data.nonce,
                        )

                # Update existing binding (reactivate if needed, always update IP)
                await conn.execute(
                    """UPDATE hardware_bindings 
                       SET last_seen_at = NOW(), machine_name = $1, ip_address = $2, is_active = TRUE 
                       WHERE id = $3""",
                    data.machine_name,
                    client_ip,
                    existing_binding["id"],
                )
            else:
                machine_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
                    license_id,
                )
                if machine_count >= license_row["max_machines"]:
                    log_data["result"] = "hwid_mismatch"
                    asyncio.create_task(_push_validation_log_to_redis(log_data))
                    return create_validation_response(
                        "hwid_mismatch",
                        f"Maximum machines ({license_row['max_machines']}) reached",
                        data.nonce,
                    )

                await conn.execute(
                    """
                    INSERT INTO hardware_bindings (id, license_id, hwid, machine_name, ip_address, is_active)
                    VALUES ($1, $2, $3, $4, $5, TRUE)
                """,
                    secrets.token_hex(16),
                    license_id,
                    data.hwid,
                    data.machine_name,
                    client_ip,
                )

            await conn.execute(
                "UPDATE licenses SET last_validated_at = NOW() WHERE id = $1",
                license_id,
            )

            # Final success log push
            asyncio.create_task(_push_validation_log_to_redis(log_data))

            # Fetch variables
            var_rows = await conn.fetchrow(
                """SELECT json_object_agg(key, value) as vars 
                   FROM license_variables 
                   WHERE license_id = $1 AND is_secret = FALSE""",
                license_id,
            )
            variables = var_rows["vars"] if var_rows and var_rows["vars"] else {}

        return create_validation_response(
            "valid",
            "License valid",
            data.nonce,
            expires_at=int(license_row["expires_at"].timestamp()) if license_row["expires_at"] else None,
            features=json.loads(license_row["features"]) if isinstance(license_row["features"], str) else (license_row["features"] or []),
            variables=variables,
            secret=signing_secret,
        )
    finally:
        await release_db(conn)


@router.get("/licenses")
async def list_licenses(
    user: dict = Depends(get_current_user), project_id: Optional[str] = None
):
    conn = await get_db()
    try:
        query = """
            SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features,
                   l.client_name, l.client_email, l.created_at, l.project_id, p.name as project_name,
                   (SELECT COUNT(*) FROM hardware_bindings hb WHERE hb.license_id = l.id AND hb.is_active = TRUE) as active_machines
            FROM licenses l JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1
        """
        params = [user["id"]]
        if project_id:
            query += " AND l.project_id = $2"
            params.append(project_id)
        query += " ORDER BY l.created_at DESC"

        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            features = r["features"] or []
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except Exception:
                    features = []
            if not isinstance(features, list):
                features = []

            result.append(
                {
                    "id": r["id"],
                    "license_key": r["license_key"],
                    "status": r["status"],
                    "project_id": r["project_id"],
                    "project_name": r["project_name"],
                    "expires_at": r["expires_at"].isoformat()
                    if r["expires_at"]
                    else None,
                    "max_machines": r["max_machines"],
                    "features": features,
                    "client_name": r["client_name"],
                    "client_email": r["client_email"],
                    "created_at": r["created_at"].isoformat(),
                    "active_machines": r["active_machines"],
                }
            )
        return result
    finally:
        await release_db(conn)


@router.post("/licenses")
async def create_license(
    data: LicenseCreateRequest, user: dict = Depends(get_current_user)
):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, name FROM projects WHERE id = $1 AND user_id = $2",
            data.project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        limits = await get_user_tier_limits(user["id"], conn)
        max_licenses = limits.get("max_licenses_per_project", 5)

        if max_licenses != -1:
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM licenses WHERE project_id = $1", data.project_id
            )
            if current_count >= max_licenses:
                raise HTTPException(
                    status_code=403,
                    detail=f"License limit reached ({max_licenses}/project). Upgrade your plan for more.",
                )

        license_id = secrets.token_hex(16)
        license_key = generate_license_key()

        await conn.execute(
            """
            INSERT INTO licenses (id, project_id, license_key, expires_at, max_machines, features, client_name, client_email, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
            license_id,
            data.project_id,
            license_key,
            data.expires_at,
            data.max_machines,
            json.dumps(data.features),
            data.client_name,
            data.client_email,
            data.notes,
        )

        if data.client_email:
            await notify_license_created(
                data.client_name,
                data.client_email,
                license_key,
                project["name"],
                data.expires_at,
                data.max_machines,
                data.features,
            )

        from routes.webhook_routes import trigger_webhook
        asyncio.create_task(
            trigger_webhook(
                user["id"],
                "license.created",
                {
                    "license_id": license_id,
                    "license_key": license_key,
                    "project_id": data.project_id,
                    "project_name": project["name"],
                    "client_name": data.client_name,
                    "client_email": data.client_email,
                    "expires_at": data.expires_at.isoformat()
                    if data.expires_at
                    else None,
                    "max_machines": data.max_machines,
                    "features": data.features,
                },
            )
        )

        return {
            "id": license_id,
            "license_key": license_key,
            "status": "active",
            "expires_at": data.expires_at.isoformat() if data.expires_at else None,
            "max_machines": data.max_machines,
            "features": data.features,
            "client_name": data.client_name,
            "client_email": data.client_email,
            "created_at": utc_now().isoformat(),
            "active_machines": 0,
        }
    finally:
        await release_db(conn)


@router.post("/licenses/{license_id}/revoke")
async def revoke_license(license_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        license_data = await conn.fetchrow(
            """
            SELECT l.id, l.license_key, l.client_name, l.client_email, p.id as project_id, p.name as project_name
            FROM licenses l JOIN projects p ON l.project_id = p.id
            WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )

        if not license_data:
            raise HTTPException(status_code=404, detail="License not found")

        result = await conn.execute(
            """
            UPDATE licenses SET status = 'revoked', updated_at = NOW()
            WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)
        """,
            license_id,
            user["id"],
        )

        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="License not found")

        from routes.webhook_routes import trigger_webhook
        asyncio.create_task(
            trigger_webhook(
                user["id"],
                "license.revoked",
                {
                    "license_id": license_data["id"],
                    "license_key": license_data["license_key"],
                    "project_id": license_data["project_id"],
                    "project_name": license_data["project_name"],
                    "client_name": license_data["client_name"],
                    "client_email": license_data["client_email"],
                },
            )
        )

        return {"status": "revoked"}
    finally:
        await release_db(conn)


@router.delete("/licenses/{license_id}")
async def delete_license(license_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        result = await conn.execute(
            """
            DELETE FROM licenses WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)
        """,
            license_id,
            user["id"],
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="License not found")
        return {"status": "deleted"}
    finally:
        await release_db(conn)


@router.get("/licenses/{license_id}/bindings")
async def get_license_bindings(license_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        license_check = await conn.fetchrow(
            """
            SELECT l.id FROM licenses l JOIN projects p ON l.project_id = p.id WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )
        if not license_check:
            raise HTTPException(status_code=404, detail="License not found")

        rows = await conn.fetch(
            """
            SELECT id, hwid, machine_name, ip_address, first_seen_at, last_seen_at, is_active
            FROM hardware_bindings WHERE license_id = $1 ORDER BY last_seen_at DESC
        """,
            license_id,
        )
        return [
            {
                "id": r["id"],
                "hwid": r["hwid"],
                "machine_name": r["machine_name"],
                "ip_address": r["ip_address"],
                "first_seen_at": r["first_seen_at"].isoformat(),
                "last_seen_at": r["last_seen_at"].isoformat(),
                "is_active": r["is_active"],
            }
            for r in rows
        ]
    finally:
        await release_db(conn)


@router.delete("/licenses/{license_id}/bindings/{binding_id}")
async def delete_binding(
    license_id: str, binding_id: str, user: dict = Depends(get_current_user)
):
    conn = await get_db()
    try:
        # SECURITY FIX: Verify ownership before deletion
        license_check = await conn.fetchrow(
            """
            SELECT l.id FROM licenses l 
            JOIN projects p ON l.project_id = p.id 
            WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )
        if not license_check:
            raise HTTPException(status_code=404, detail="License not found or access denied")

        await conn.execute(
            "DELETE FROM hardware_bindings WHERE id = $1 AND license_id = $2",
            binding_id,
            license_id,
        )
        return {"status": "deleted"}
    finally:
        await release_db(conn)


# =============================================================================
# HWID Reset Endpoints
# =============================================================================


@router.post("/licenses/{license_id}/reset-hwid")
async def reset_hwid(
    license_id: str,
    user: dict = Depends(get_current_user),
    reason: Optional[str] = None,
):
    """Reset all hardware bindings for a license."""
    conn = await get_db()
    try:
        # Verify ownership
        license_data = await conn.fetchrow(
            """
            SELECT l.id, l.license_key, l.client_name, l.client_email, p.id as project_id, p.name as project_name
            FROM licenses l JOIN projects p ON l.project_id = p.id
            WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )

        if not license_data:
            raise HTTPException(status_code=404, detail="License not found")

        # Count bindings being removed
        binding_count = await conn.fetchval(
            "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
            license_id,
        )

        # Delete all bindings
        await conn.execute(
            "DELETE FROM hardware_bindings WHERE license_id = $1", license_id
        )

        # Log the reset
        reset_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO hwid_reset_logs (id, license_id, reset_by_user_id, bindings_removed, reason)
            VALUES ($1, $2, $3, $4, $5)
        """,
            reset_id,
            license_id,
            user["id"],
            binding_count,
            reason,
        )

        # Trigger webhook
        from routes.webhook_routes import trigger_webhook
        asyncio.create_task(
            trigger_webhook(
                user["id"],
                "hwid.reset",
                {
                    "license_id": license_data["id"],
                    "license_key": license_data["license_key"],
                    "project_id": license_data["project_id"],
                    "project_name": license_data["project_name"],
                    "client_name": license_data["client_name"],
                    "client_email": license_data["client_email"],
                    "bindings_removed": binding_count,
                    "reason": reason,
                },
            )
        )

        return {
            "status": "reset",
            "bindings_removed": binding_count,
            "message": f"Successfully removed {binding_count} hardware binding(s)",
        }
    finally:
        await release_db(conn)


@router.get("/licenses/{license_id}/reset-history")
async def get_reset_history(license_id: str, user: dict = Depends(get_current_user)):
    """Get HWID reset history for a license."""
    conn = await get_db()
    try:
        # Verify ownership
        license_check = await conn.fetchrow(
            """
            SELECT l.id FROM licenses l JOIN projects p ON l.project_id = p.id 
            WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )

        if not license_check:
            raise HTTPException(status_code=404, detail="License not found")

        rows = await conn.fetch(
            """
            SELECT id, bindings_removed, reason, created_at
            FROM hwid_reset_logs
            WHERE license_id = $1
            ORDER BY created_at DESC
            LIMIT 50
        """,
            license_id,
        )

        return [
            {
                "id": r["id"],
                "bindings_removed": r["bindings_removed"],
                "reason": r["reason"],
                "reset_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    finally:
        await release_db(conn)


@router.get("/licenses/{license_id}/reset-status")
async def get_reset_status(license_id: str, user: dict = Depends(get_current_user)):
    """Get current reset status for a license (binding count, can reset, etc.)."""
    conn = await get_db()
    try:
        # Verify ownership and get license info
        license_data = await conn.fetchrow(
            """
            SELECT l.id, l.max_machines, l.status
            FROM licenses l JOIN projects p ON l.project_id = p.id 
            WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )

        if not license_data:
            raise HTTPException(status_code=404, detail="License not found")

        # Get active bindings count
        active_bindings = await conn.fetchval(
            "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
            license_id,
        )

        # Get last reset time
        last_reset = await conn.fetchrow(
            "SELECT created_at FROM hwid_reset_logs WHERE license_id = $1 ORDER BY created_at DESC LIMIT 1",
            license_id,
        )

        # Get total reset count
        reset_count = await conn.fetchval(
            "SELECT COUNT(*) FROM hwid_reset_logs WHERE license_id = $1", license_id
        )

        return {
            "license_id": license_id,
            "active_bindings": active_bindings,
            "max_machines": license_data["max_machines"],
            "can_reset": active_bindings > 0 and license_data["status"] == "active",
            "last_reset_at": last_reset["created_at"].isoformat()
            if last_reset
            else None,
            "total_resets": reset_count,
        }
    finally:
        await release_db(conn)


# =============================================================================
# License Variables CRUD Endpoints
# =============================================================================


@router.get("/licenses/{license_id}/variables")
async def get_license_variables(
    license_id: str, user: dict = Depends(get_current_user)
):
    """Get all variables for a license (owner only)."""
    conn = await get_db()
    try:
        # Verify ownership
        license_check = await conn.fetchrow(
            """
            SELECT l.id FROM licenses l 
            JOIN projects p ON l.project_id = p.id 
            WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )

        if not license_check:
            raise HTTPException(status_code=404, detail="License not found")

        # Get all variables (including secrets for owner)
        rows = await conn.fetch(
            """
            SELECT id, key, value, is_secret, created_at, updated_at
            FROM license_variables
            WHERE license_id = $1
            ORDER BY key ASC
        """,
            license_id,
        )

        return [
            {
                "id": r["id"],
                "key": r["key"],
                "value": r["value"],
                "is_secret": r["is_secret"],
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in rows
        ]
    finally:
        await release_db(conn)


@router.post("/licenses/{license_id}/variables")
async def create_license_variable(
    license_id: str,
    data: LicenseVariableCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new variable for a license."""
    conn = await get_db()
    try:
        # Verify ownership
        license_check = await conn.fetchrow(
            """
            SELECT l.id FROM licenses l 
            JOIN projects p ON l.project_id = p.id 
            WHERE l.id = $1 AND p.user_id = $2
        """,
            license_id,
            user["id"],
        )

        if not license_check:
            raise HTTPException(status_code=404, detail="License not found")

        # Check if variable key already exists
        existing = await conn.fetchrow(
            """
            SELECT id FROM license_variables 
            WHERE license_id = $1 AND key = $2
        """,
            license_id,
            data.key,
        )

        if existing:
            raise HTTPException(
                status_code=400, detail=f"Variable '{data.key}' already exists"
            )

        # Create variable
        variable_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO license_variables (id, license_id, key, value, is_secret)
            VALUES ($1, $2, $3, $4, $5)
        """,
            variable_id,
            license_id,
            data.key,
            data.value,
            data.is_secret,
        )

        # Get created variable
        variable = await conn.fetchrow(
            """
            SELECT id, key, value, is_secret, created_at, updated_at
            FROM license_variables
            WHERE id = $1
        """,
            variable_id,
        )

        return {
            "id": variable["id"],
            "key": variable["key"],
            "value": variable["value"],
            "is_secret": variable["is_secret"],
            "created_at": variable["created_at"].isoformat(),
            "updated_at": variable["updated_at"].isoformat(),
        }
    finally:
        await release_db(conn)


@router.put("/licenses/{license_id}/variables/{variable_id}")
async def update_license_variable(
    license_id: str,
    variable_id: str,
    data: LicenseVariableUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Update a license variable."""
    conn = await get_db()
    try:
        # Verify ownership and variable exists
        variable_check = await conn.fetchrow(
            """
            SELECT lv.id FROM license_variables lv
            JOIN licenses l ON lv.license_id = l.id
            JOIN projects p ON l.project_id = p.id
            WHERE lv.id = $1 AND lv.license_id = $2 AND p.user_id = $3
        """,
            variable_id,
            license_id,
            user["id"],
        )

        if not variable_check:
            raise HTTPException(status_code=404, detail="Variable not found")

        # Update variable
        if data.is_secret is not None:
            await conn.execute(
                """
                UPDATE license_variables 
                SET value = $1, is_secret = $2, updated_at = NOW()
                WHERE id = $3
            """,
                data.value,
                data.is_secret,
                variable_id,
            )
        else:
            await conn.execute(
                """
                UPDATE license_variables 
                SET value = $1, updated_at = NOW()
                WHERE id = $2
            """,
                data.value,
                variable_id,
            )

        # Get updated variable
        variable = await conn.fetchrow(
            """
            SELECT id, key, value, is_secret, created_at, updated_at
            FROM license_variables
            WHERE id = $1
        """,
            variable_id,
        )

        return {
            "id": variable["id"],
            "key": variable["key"],
            "value": variable["value"],
            "is_secret": variable["is_secret"],
            "created_at": variable["created_at"].isoformat(),
            "updated_at": variable["updated_at"].isoformat(),
        }
    finally:
        await release_db(conn)


@router.delete("/licenses/{license_id}/variables/{variable_id}")
async def delete_license_variable(
    license_id: str, variable_id: str, user: dict = Depends(get_current_user)
):
    """Delete a license variable."""
    conn = await get_db()
    try:
        # Verify ownership and variable exists
        variable_check = await conn.fetchrow(
            """
            SELECT lv.id, lv.key FROM license_variables lv
            JOIN licenses l ON lv.license_id = l.id
            JOIN projects p ON l.project_id = p.id
            WHERE lv.id = $1 AND lv.license_id = $2 AND p.user_id = $3
        """,
            variable_id,
            license_id,
            user["id"],
        )

        if not variable_check:
            raise HTTPException(status_code=404, detail="Variable not found")

        # Delete variable
        await conn.execute("DELETE FROM license_variables WHERE id = $1", variable_id)

        return {
            "status": "deleted",
            "key": variable_check["key"],
            "message": f"Variable '{variable_check['key']}' deleted successfully",
        }
    finally:
        await release_db(conn)
