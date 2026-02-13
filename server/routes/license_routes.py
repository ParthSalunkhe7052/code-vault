"""
License routes for CodeVault API.
Extracted from main.py for modularity.
"""

import json
import time
import secrets
import asyncio
import logging
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends, Request

from models import (
    LicenseValidationRequest,
    LicenseValidationResponse,
    LicenseCreateRequest,
    LicenseReleaseRequest,
    LicenseVariableCreateRequest,
    LicenseVariableUpdateRequest,
)
from utils import (
    get_current_user,
    utc_now,
    generate_license_key,
    create_validation_response,
    get_user_tier_limits,
    check_and_store_jti,
    create_lease_token,
    LEASE_DURATION_SECONDS,
    compute_signature,
    compute_ed25519_signature,
)
from database import get_db, release_db
from config import SECRET_KEY
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
                """SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features, 
                          l.license_mode, l.max_concurrent,
                          p.id as project_id, p.signing_secret, p.signing_private_key, p.user_id 
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

            # Extract signing info safely (handles migration gaps and mocks)
            signing_secret = SECRET_KEY
            signing_private_key = None
            project_id = None
            user_id = None

            if license_row:
                try:
                    signing_secret = license_row["signing_secret"] or SECRET_KEY
                    signing_private_key = license_row["signing_private_key"]
                    project_id = license_row["project_id"]
                    user_id = license_row["user_id"]
                except (KeyError, TypeError):
                    # Fallback for old schema or incomplete mocks
                    if not project_id and "project_id" in license_row:
                        project_id = license_row["project_id"]
                    if not user_id and "user_id" in license_row:
                        user_id = license_row["user_id"]

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
            geo = get_geo_from_ip(client_ip)
            log_data = {
                "license_id": license_row["id"] if license_row else None,
                "project_id": license_row["project_id"] if license_row else None,
                "license_key": data.license_key,
                "hwid": data.hwid,
                "ip_address": client_ip,
                "country": geo.get("country"),
                "city": geo.get("city"),
                "latitude": geo.get("latitude"),
                "longitude": geo.get("longitude"),
                "result": result_status,
                "response_time_ms": response_time,
                "machine_name": data.machine_name,
                "created_at": utc_now().isoformat(),
            }

            if result_status != "valid":
                # Push log to Redis
                asyncio.create_task(_push_validation_log_to_redis(log_data))

                # Trigger tamper alert webhook for Pro+ users
                if license_row and user_id:
                    from routes.webhook_routes import trigger_webhook

                    asyncio.create_task(
                        trigger_webhook(
                            user_id,
                            "tamper.alert",
                            {
                                "alert_type": result_status,
                                "license_key": data.license_key,
                                "reason": message,
                                "hwid": data.hwid,
                                "ip_address": client_ip,
                                "machine_name": data.machine_name,
                                "country": geo.get("country"),
                                "city": geo.get("city"),
                                "timestamp": utc_now().isoformat(),
                            },
                        )
                    )

                return create_validation_response(result_status, message, data.nonce)

            # SEC2: Binary integrity check — if client sends binary_hash,
            # verify it matches a registered hash for this project
            if data.binary_hash and license_row:
                project_id = await conn.fetchval(
                    "SELECT project_id FROM licenses WHERE id = $1", license_row["id"]
                )
                hash_match = await conn.fetchval(
                    "SELECT 1 FROM binary_hashes WHERE project_id = $1 AND binary_hash = $2",
                    project_id,
                    data.binary_hash,
                )
                if not hash_match:
                    log_data["result"] = "tampered"
                    asyncio.create_task(_push_validation_log_to_redis(log_data))

                    # Trigger tamper alert for binary integrity failure
                    from routes.webhook_routes import trigger_webhook

                    asyncio.create_task(
                        trigger_webhook(
                            license_row["user_id"],
                            "tamper.alert",
                            {
                                "alert_type": "binary_integrity_failed",
                                "license_key": data.license_key,
                                "reason": "Binary hash does not match registered hash",
                                "hwid": data.hwid,
                                "ip_address": client_ip,
                                "machine_name": data.machine_name,
                                "country": geo.get("country"),
                                "city": geo.get("city"),
                                "timestamp": utc_now().isoformat(),
                            },
                        )
                    )

                    return create_validation_response(
                        "tampered",
                        "Binary integrity check failed. This executable may have been modified.",
                        data.nonce,
                    )

            # Check HWID binding
            license_id = license_row["id"]

            # SEC3: HWID heuristics
            from utils import analyze_hwid

            flag_reason = analyze_hwid(data.hwid)
            if flag_reason:
                from routes.webhook_routes import trigger_webhook

                asyncio.create_task(
                    trigger_webhook(
                        license_row["user_id"],
                        "hwid.suspicious",
                        {
                            "license_key": data.license_key,
                            "hwid": data.hwid,
                            "reason": flag_reason,
                            "ip_address": client_ip,
                            "machine_name": data.machine_name,
                        },
                    )
                )

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

                        # Trigger tamper alert for max machines reached
                        from routes.webhook_routes import trigger_webhook

                        asyncio.create_task(
                            trigger_webhook(
                                license_row["user_id"],
                                "tamper.alert",
                                {
                                    "alert_type": "max_machines_exceeded",
                                    "license_key": data.license_key,
                                    "reason": f"Attempted activation on new machine but max limit ({license_row['max_machines']}) reached",
                                    "hwid": data.hwid,
                                    "ip_address": client_ip,
                                    "machine_name": data.machine_name,
                                    "country": geo.get("country"),
                                    "city": geo.get("city"),
                                    "timestamp": utc_now().isoformat(),
                                    "current_machines": machine_count,
                                    "max_machines": license_row["max_machines"],
                                },
                            )
                        )

                        return create_validation_response(
                            "hwid_mismatch",
                            f"Maximum machines ({license_row['max_machines']}) reached",
                            data.nonce,
                        )

                # Update existing binding (reactivate if needed, always update IP)
                await conn.execute(
                    """UPDATE hardware_bindings 
                       SET last_seen_at = NOW(), machine_name = $1, ip_address = $2, is_active = TRUE,
                           is_flagged = $4, flagged_reason = $5, flagged_at = CASE WHEN $4 = TRUE THEN NOW() ELSE flagged_at END
                       WHERE id = $3""",
                    data.machine_name,
                    client_ip,
                    existing_binding["id"],
                    flag_reason is not None,
                    flag_reason,
                )
            else:
                machine_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
                    license_id,
                )
                if machine_count >= license_row["max_machines"]:
                    log_data["result"] = "hwid_mismatch"
                    asyncio.create_task(_push_validation_log_to_redis(log_data))

                    # Trigger tamper alert for max machines reached
                    from routes.webhook_routes import trigger_webhook

                    asyncio.create_task(
                        trigger_webhook(
                            license_row["user_id"],
                            "tamper.alert",
                            {
                                "alert_type": "max_machines_exceeded",
                                "license_key": data.license_key,
                                "reason": f"New machine activation blocked - max limit ({license_row['max_machines']}) reached",
                                "hwid": data.hwid,
                                "ip_address": client_ip,
                                "machine_name": data.machine_name,
                                "country": geo.get("country"),
                                "city": geo.get("city"),
                                "timestamp": utc_now().isoformat(),
                                "current_machines": machine_count,
                                "max_machines": license_row["max_machines"],
                            },
                        )
                    )

                    return create_validation_response(
                        "hwid_mismatch",
                        f"Maximum machines ({license_row['max_machines']}) reached",
                        data.nonce,
                    )

                await conn.execute(
                    """
                    INSERT INTO hardware_bindings (id, license_id, hwid, machine_name, ip_address, is_active, 
                                                 is_flagged, flagged_reason, flagged_at)
                    VALUES ($1, $2, $3, $4, $5, TRUE, $6, $7, CASE WHEN $6 = TRUE THEN NOW() ELSE NULL END)
                """,
                    secrets.token_hex(16),
                    license_id,
                    data.hwid,
                    data.machine_name,
                    client_ip,
                    flag_reason is not None,
                    flag_reason,
                )

            await conn.execute(
                "UPDATE licenses SET last_validated_at = NOW() WHERE id = $1",
                license_id,
            )

            # Final success log push
            asyncio.create_task(_push_validation_log_to_redis(log_data))

            # MON2: Floating licenses
            session_token = None
            if license_row.get("license_mode") == "floating":
                # Check for existing active session for this HWID
                active_session = await conn.fetchrow(
                    """SELECT session_token FROM license_sessions 
                       WHERE license_id = $1 AND hwid = $2 AND is_active = TRUE AND expires_at > NOW()""",
                    license_id,
                    data.hwid,
                )

                if active_session:
                    session_token = active_session["session_token"]
                    # Update TTL (6 mins - interval 5m + 1m grace)
                    await conn.execute(
                        """UPDATE license_sessions 
                           SET expires_at = NOW() + INTERVAL '360 seconds', last_active_at = NOW() 
                           WHERE license_id = $1 AND hwid = $2 AND is_active = TRUE""",
                        license_id,
                        data.hwid,
                    )
                else:
                    # Count active sessions
                    active_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM license_sessions WHERE license_id = $1 AND is_active = TRUE AND expires_at > NOW()",
                        license_id,
                    )

                    if active_count >= (license_row["max_concurrent"] or 1):
                        log_data["result"] = "concurrent_limit"
                        asyncio.create_task(_push_validation_log_to_redis(log_data))
                        return create_validation_response(
                            "concurrent_limit",
                            f"Maximum concurrent sessions ({license_row['max_concurrent']}) reached. Close other instances or upgrade.",
                            data.nonce,
                        )

                    # Create new session
                    session_token = secrets.token_hex(32)
                    await conn.execute(
                        """INSERT INTO license_sessions (id, license_id, hwid, session_token, ip_address, expires_at)
                           VALUES ($1, $2, $3, $4, $5, NOW() + INTERVAL '360 seconds')""",
                        secrets.token_hex(16),
                        license_id,
                        data.hwid,
                        session_token,
                        client_ip,
                    )

            # Fetch variables
            var_rows = await conn.fetchrow(
                """SELECT json_object_agg(key, value) as vars 
                   FROM license_variables 
                   WHERE license_id = $1 AND is_secret = FALSE""",
                license_id,
            )
            variables = var_rows["vars"] if var_rows and var_rows["vars"] else {}
            if session_token:
                variables["_cv_session_token"] = session_token

        # Protocol v2: Check for replay attack before generating response
        # Generate a temporary jti to check - actual jti is created in create_validation_response
        temp_jti = secrets.token_hex(16)
        is_valid, replay_error = await check_and_store_jti(temp_jti, data.license_key)
        if not is_valid:
            return create_validation_response(
                "invalid",
                replay_error,
                data.nonce,
                secret=signing_secret,
                private_key_pem=signing_private_key,
                license_key=data.license_key,
            )

        # Phase 4: Generate server-signed lease token for offline validation
        lease_token = None
        if license_row["expires_at"]:
            lease_expires = int(time.time()) + LEASE_DURATION_SECONDS
            # Use the earlier of license expiry or lease duration
            lease_expires = min(
                lease_expires, int(license_row["expires_at"].timestamp())
            )
            lease_token = create_lease_token(
                license_key=data.license_key,
                hwid=data.hwid,
                expires_at=lease_expires,
                private_key_pem=signing_private_key,
                secret=signing_secret,
            )

        response = create_validation_response(
            "valid",
            "License valid",
            data.nonce,
            expires_at=int(license_row["expires_at"].timestamp())
            if license_row["expires_at"]
            else None,
            features=json.loads(license_row["features"])
            if isinstance(license_row["features"], str)
            else (license_row["features"] or []),
            variables=variables,
            secret=signing_secret,
            private_key_pem=signing_private_key,
            license_key=data.license_key,
        )
        # Attach lease token to response
        response.lease_token = lease_token
        return response
    finally:
        await release_db(conn)


@router.post("/license/heartbeat")
async def license_heartbeat(
    request: Request,
    data: LicenseValidationRequest,
):
    """Update heartbeat for an active license session (SEC4).

    Updates both hardware_bindings and license_sessions (if floating license).
    """
    conn = await get_db()
    try:
        # Check if the binding exists and is active
        binding = await conn.fetchrow(
            """SELECT hb.id, hb.is_active, p.heartbeat_interval_seconds 
               FROM hardware_bindings hb
               JOIN licenses l ON hb.license_id = l.id
               JOIN projects p ON l.project_id = p.id
               WHERE l.license_key = $1 AND hb.hwid = $2""",
            data.license_key,
            data.hwid,
        )

        if not binding:
            raise HTTPException(status_code=404, detail="License session not found")

        if not binding["is_active"]:
            raise HTTPException(status_code=403, detail="Session inactive")

        # Update heartbeat in hardware_bindings
        await conn.execute(
            """UPDATE hardware_bindings 
               SET last_heartbeat_at = NOW(), 
                   heartbeat_count = heartbeat_count + 1
               WHERE id = $1""",
            binding["id"],
        )

        # Phase 3: Update license_sessions TTL if session_token provided (floating license)
        if data.session_token:
            await conn.execute(
                """UPDATE license_sessions 
                   SET expires_at = NOW() + INTERVAL '360 seconds',
                       last_active_at = NOW()
                   WHERE license_id = (SELECT id FROM licenses WHERE license_key = $1)
                   AND hwid = $2 AND session_token = $3 AND is_active = TRUE""",
                data.license_key,
                data.hwid,
                data.session_token,
            )

        return {
            "status": "alive",
            "server_time": int(time.time()),
            "next_heartbeat": binding["heartbeat_interval_seconds"],
        }
    finally:
        await release_db(conn)


@router.post("/license/release")
async def release_license(
    data: LicenseReleaseRequest,
):
    """Release a floating license session (MON2)."""
    conn = await get_db()
    try:
        # Find session and release it
        result = await conn.execute(
            """UPDATE license_sessions 
               SET is_active = FALSE, released_at = NOW()
               WHERE license_id = (SELECT id FROM licenses WHERE license_key = $1)
               AND hwid = $2 AND session_token = $3 AND is_active = TRUE""",
            data.license_key,
            data.hwid,
            data.session_token,
        )

        if result == "UPDATE 0":
            return {
                "status": "error",
                "message": "Session not found or already released",
            }

        return {"status": "released"}
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
            INSERT INTO licenses (id, project_id, license_key, expires_at, max_machines, features, client_name, client_email, notes, license_type, license_mode, max_concurrent)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
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
            data.license_type,
            data.license_mode,
            data.max_concurrent,
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


@router.post("/licenses/{license_id}/convert")
async def convert_license(
    license_id: str,
    new_type: str = "perpetual",
    user: dict = Depends(get_current_user),
):
    """Convert a trial license to perpetual or subscription (MON1)."""
    conn = await get_db()
    try:
        # Verify ownership and current type
        license_data = await conn.fetchrow(
            """SELECT l.id, l.license_type
               FROM licenses l JOIN projects p ON l.project_id = p.id
               WHERE l.id = $1 AND p.user_id = $2""",
            license_id,
            user["id"],
        )

        if not license_data:
            raise HTTPException(status_code=404, detail="License not found")

        if license_data["license_type"] != "trial":
            raise HTTPException(
                status_code=400, detail="Only trial licenses can be converted"
            )

        await conn.execute(
            """UPDATE licenses 
               SET license_type = $1, 
                   converted_from_trial = TRUE,
                   converted_at = NOW(),
                   updated_at = NOW()
               WHERE id = $2""",
            new_type,
            license_id,
        )

        return {"status": "converted", "new_type": new_type}
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
            raise HTTPException(
                status_code=404, detail="License not found or access denied"
            )

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


# =============================================================================
# Phase 8: Auto-Update Manifest & Kill-Switch
# =============================================================================


@router.get("/projects/{project_id}/update-manifest")
async def get_update_manifest(project_id: str):
    """Public endpoint to get auto-update manifest for a project.

    Returns a signed manifest that clients can use to check for updates.
    This allows software vendors to push updates to their customers.
    """
    import hashlib
    import base64

    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, name, signing_private_key, signing_secret FROM projects WHERE id = $1",
            project_id,
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get latest build info
        latest_build = await conn.fetchrow(
            """SELECT id, created_at, build_type FROM cloud_builds 
               WHERE project_id = $1 AND status = 'completed' 
               ORDER BY created_at DESC LIMIT 1""",
            project_id,
        )

        manifest = {
            "project_id": project_id,
            "project_name": project["name"],
            "latest_version": latest_build["id"][:8] if latest_build else "0.0.0",
            "latest_build_date": latest_build["created_at"].isoformat()
            if latest_build
            else None,
            "min_required_version": "1.0.0",
            "update_url": f"/api/v1/projects/{project_id}/download",
        }

        # Sign the manifest
        signing_private_key = project.get("signing_private_key")
        signing_secret = project.get("signing_secret")

        if signing_private_key:
            from utils import compute_ed25519_signature

            signature = compute_ed25519_signature(manifest, signing_private_key)
        else:
            from utils import compute_signature

            active_secret = signing_secret or SECRET_KEY
            signature = compute_signature(manifest, active_secret)

        manifest["signature"] = signature
        manifest["signed_at"] = int(time.time())

        return manifest
    finally:
        await release_db(conn)


class KillSwitchPolicy(BaseModel):
    enabled: bool = False
    reason: Optional[str] = None
    killed_versions: List[str] = []
    redirect_url: Optional[str] = None


@router.get("/projects/{project_id}/kill-switch")
async def get_kill_switch(project_id: str):
    """Public endpoint to check kill-switch policy for a project.

    Returns whether the application should be terminated and optional redirect.
    Used for emergency shutdown of compromised or pirated software.
    """
    import hashlib

    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, signing_private_key, signing_secret FROM projects WHERE id = $1",
            project_id,
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check for active kill-switch (stored as project metadata or separate table)
        kill_switch = await conn.fetchrow(
            """SELECT enabled, reason, killed_versions, redirect_url 
               FROM kill_switches 
               WHERE project_id = $1 AND enabled = TRUE""",
            project_id,
        )

        if not kill_switch:
            return {
                "enabled": False,
                "project_id": project_id,
            }

        # Sign the kill-switch response
        response_data = {
            "enabled": kill_switch["enabled"],
            "reason": kill_switch["reason"],
            "killed_versions": kill_switch["killed_versions"] or [],
            "redirect_url": kill_switch["redirect_url"],
        }

        signing_private_key = project.get("signing_private_key")

        if signing_private_key:
            from utils import compute_ed25519_signature

            signature = compute_ed25519_signature(response_data, signing_private_key)
        else:
            from utils import compute_signature

            signing_secret = project.get("signing_secret") or SECRET_KEY
            signature = compute_signature(response_data, signing_secret)

        return {
            **response_data,
            "signature": signature,
            "project_id": project_id,
        }
    finally:
        await release_db(conn)


@router.post("/projects/{project_id}/kill-switch")
async def set_kill_switch(
    project_id: str,
    policy: KillSwitchPolicy,
    user: dict = Depends(get_current_user),
):
    """Set kill-switch policy for a project (owner only)."""
    conn = await get_db()
    try:
        # Verify ownership
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Upsert kill-switch
        await conn.execute(
            """INSERT INTO kill_switches (id, project_id, enabled, reason, killed_versions, redirect_url, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, NOW())
               ON CONFLICT (project_id) DO UPDATE SET
               enabled = $3, reason = $4, killed_versions = $5, redirect_url = $6
            """,
            secrets.token_hex(16),
            project_id,
            policy.enabled,
            policy.reason,
            json.dumps(policy.killed_versions),
            policy.redirect_url,
        )

        return {
            "status": "success",
            "message": f"Kill-switch {'enabled' if policy.enabled else 'disabled'}",
            "policy": {
                "enabled": policy.enabled,
                "reason": policy.reason,
            },
        }
    finally:
        await release_db(conn)
