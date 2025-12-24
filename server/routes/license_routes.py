"""
License routes for CodeVault API.
Extracted from main.py for modularity.
"""

import json
import time
import secrets
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from starlette.concurrency import run_in_threadpool

from models import LicenseValidationRequest, LicenseValidationResponse, LicenseCreateRequest
from utils import (
    get_current_user, utc_now, generate_license_key,
    create_validation_response, get_user_tier_limits
)
from database import get_db, release_db
from email_service import notify_license_created

router = APIRouter(prefix="/api/v1", tags=["Licenses"])


# Import trigger_webhook from webhook_routes
def _get_trigger_webhook():
    """Lazy import to avoid circular dependency."""
    from routes.webhook_routes import trigger_webhook
    return trigger_webhook


# GeoIP functions (import from geoip module when created, for now inline)
def get_geo_from_ip(ip_address: str) -> dict:
    """Get geolocation data from IP address."""
    result = {"city": None, "country": None, "latitude": None, "longitude": None}
    
    if ip_address in ("127.0.0.1", "::1", "localhost", "unknown"):
        return result
    
    try:
        import ipaddress
        ip = ipaddress.ip_address(ip_address)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            return result
    except ValueError:
        return result
    
    # Try GeoIP lookup
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
    except Exception:
        pass
    
    return result


@router.post("/license/validate", response_model=LicenseValidationResponse)
async def validate_license(request: Request, data: LicenseValidationRequest):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    geo = await run_in_threadpool(get_geo_from_ip, client_ip)
    
    if abs(int(time.time()) - data.timestamp) > 300:
        return create_validation_response("invalid", "Request timestamp expired", data.nonce)
    
    conn = await get_db()
    try:
        license_row = await conn.fetchrow(
            "SELECT id, license_key, status, expires_at, max_machines, features FROM licenses WHERE license_key = $1",
            data.license_key
        )
        response_time = int((time.time() - start_time) * 1000)
        
        if not license_row:
            await conn.execute("""
                INSERT INTO validation_logs (license_key, hwid, ip_address, result, response_time_ms, city, country, latitude, longitude)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, data.license_key, data.hwid, client_ip, "invalid", response_time,
                geo["city"], geo["country"], geo["latitude"], geo["longitude"])
            return create_validation_response("invalid", "License not found", data.nonce)
        
        license_id = license_row['id']
        status = license_row['status']
        expires_at = license_row['expires_at']
        max_machines = license_row['max_machines']
        features = license_row['features'] if license_row['features'] else []
        
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except Exception:
                features = []
        if not isinstance(features, list):
            features = []
        
        if status == 'revoked':
            await conn.execute("""
                INSERT INTO validation_logs (license_id, license_key, hwid, ip_address, result, response_time_ms, city, country, latitude, longitude)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, license_id, data.license_key, data.hwid, client_ip, "revoked", response_time,
                geo["city"], geo["country"], geo["latitude"], geo["longitude"])
            return create_validation_response("revoked", "License has been revoked", data.nonce)
        
        if expires_at and expires_at < utc_now():
            await conn.execute("""
                INSERT INTO validation_logs (license_id, license_key, hwid, ip_address, result, response_time_ms, city, country, latitude, longitude)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, license_id, data.license_key, data.hwid, client_ip, "expired", response_time,
                geo["city"], geo["country"], geo["latitude"], geo["longitude"])
            return create_validation_response("expired", "License has expired", data.nonce)
        
        # Check HWID binding
        existing_binding = await conn.fetchrow(
            "SELECT id, is_active FROM hardware_bindings WHERE license_id = $1 AND hwid = $2",
            license_id, data.hwid
        )
        
        if existing_binding:
            await conn.execute(
                "UPDATE hardware_bindings SET last_seen_at = NOW(), machine_name = $1 WHERE id = $2",
                data.machine_name, existing_binding['id']
            )
        else:
            machine_count = await conn.fetchval(
                "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
                license_id
            )
            if machine_count >= max_machines:
                await conn.execute("""
                    INSERT INTO validation_logs (license_id, license_key, hwid, ip_address, result, response_time_ms, city, country, latitude, longitude)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, license_id, data.license_key, data.hwid, client_ip, "hwid_mismatch", response_time,
                    geo["city"], geo["country"], geo["latitude"], geo["longitude"])
                return create_validation_response("hwid_mismatch", f"Maximum machines ({max_machines}) reached", data.nonce)
            
            await conn.execute("""
                INSERT INTO hardware_bindings (id, license_id, hwid, machine_name, ip_address)
                VALUES ($1, $2, $3, $4, $5)
            """, secrets.token_hex(16), license_id, data.hwid, data.machine_name, client_ip)
        
        await conn.execute("UPDATE licenses SET last_validated_at = NOW() WHERE id = $1", license_id)
        await conn.execute("""
            INSERT INTO validation_logs (license_id, license_key, hwid, ip_address, result, response_time_ms, city, country, latitude, longitude)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, license_id, data.license_key, data.hwid, client_ip, "valid", response_time,
            geo["city"], geo["country"], geo["latitude"], geo["longitude"])
        
        return create_validation_response(
            "valid", "License valid", data.nonce,
            expires_at=int(expires_at.timestamp()) if expires_at else None,
            features=features if isinstance(features, list) else []
        )
    finally:
        await release_db(conn)


@router.get("/licenses")
async def list_licenses(user: dict = Depends(get_current_user), project_id: Optional[str] = None):
    conn = await get_db()
    try:
        query = """
            SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features,
                   l.client_name, l.client_email, l.created_at, l.project_id, p.name as project_name,
                   (SELECT COUNT(*) FROM hardware_bindings hb WHERE hb.license_id = l.id AND hb.is_active = TRUE) as active_machines
            FROM licenses l JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1
        """
        params = [user['id']]
        if project_id:
            query += " AND l.project_id = $2"
            params.append(project_id)
        query += " ORDER BY l.created_at DESC"
        
        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            features = r['features'] or []
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except Exception:
                    features = []
            if not isinstance(features, list):
                features = []
            
            result.append({
                "id": r['id'], 
                "license_key": r['license_key'], 
                "status": r['status'],
                "project_id": r['project_id'],
                "project_name": r['project_name'],
                "expires_at": r['expires_at'].isoformat() if r['expires_at'] else None,
                "max_machines": r['max_machines'], 
                "features": features,
                "client_name": r['client_name'], 
                "client_email": r['client_email'],
                "created_at": r['created_at'].isoformat(), 
                "active_machines": r['active_machines']
            })
        return result
    finally:
        await release_db(conn)


@router.post("/licenses")
async def create_license(data: LicenseCreateRequest, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow("SELECT id, name FROM projects WHERE id = $1 AND user_id = $2", data.project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        limits = await get_user_tier_limits(user['id'], conn)
        max_licenses = limits.get('max_licenses_per_project', 5)
        
        if max_licenses != -1:
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM licenses WHERE project_id = $1", data.project_id
            )
            if current_count >= max_licenses:
                raise HTTPException(
                    status_code=403, 
                    detail=f"License limit reached ({max_licenses}/project). Upgrade your plan for more."
                )
        
        license_id = secrets.token_hex(16)
        license_key = generate_license_key()
        
        await conn.execute("""
            INSERT INTO licenses (id, project_id, license_key, expires_at, max_machines, features, client_name, client_email, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, license_id, data.project_id, license_key, data.expires_at, data.max_machines,
            json.dumps(data.features), data.client_name, data.client_email, data.notes)
        
        if data.client_email:
            await notify_license_created(data.client_name, data.client_email, license_key,
                                        project['name'], data.expires_at, data.max_machines, data.features)
        
        trigger_webhook = _get_trigger_webhook()
        asyncio.create_task(trigger_webhook(user['id'], "license.created", {
            "license_id": license_id,
            "license_key": license_key,
            "project_id": data.project_id,
            "project_name": project['name'],
            "client_name": data.client_name,
            "client_email": data.client_email,
            "expires_at": data.expires_at.isoformat() if data.expires_at else None,
            "max_machines": data.max_machines,
            "features": data.features
        }))
        
        return {"id": license_id, "license_key": license_key, "status": "active",
                "expires_at": data.expires_at.isoformat() if data.expires_at else None,
                "max_machines": data.max_machines, "features": data.features,
                "client_name": data.client_name, "client_email": data.client_email,
                "created_at": utc_now().isoformat(), "active_machines": 0}
    finally:
        await release_db(conn)


@router.post("/licenses/{license_id}/revoke")
async def revoke_license(license_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        license_data = await conn.fetchrow("""
            SELECT l.id, l.license_key, l.client_name, l.client_email, p.id as project_id, p.name as project_name
            FROM licenses l JOIN projects p ON l.project_id = p.id
            WHERE l.id = $1 AND p.user_id = $2
        """, license_id, user['id'])
        
        if not license_data:
            raise HTTPException(status_code=404, detail="License not found")
        
        result = await conn.execute("""
            UPDATE licenses SET status = 'revoked', updated_at = NOW()
            WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)
        """, license_id, user['id'])
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="License not found")
        
        trigger_webhook = _get_trigger_webhook()
        asyncio.create_task(trigger_webhook(user['id'], "license.revoked", {
            "license_id": license_data['id'],
            "license_key": license_data['license_key'],
            "project_id": license_data['project_id'],
            "project_name": license_data['project_name'],
            "client_name": license_data['client_name'],
            "client_email": license_data['client_email']
        }))
        
        return {"status": "revoked"}
    finally:
        await release_db(conn)


@router.delete("/licenses/{license_id}")
async def delete_license(license_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        result = await conn.execute("""
            DELETE FROM licenses WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)
        """, license_id, user['id'])
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="License not found")
        return {"status": "deleted"}
    finally:
        await release_db(conn)


@router.get("/licenses/{license_id}/bindings")
async def get_license_bindings(license_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        license_check = await conn.fetchrow("""
            SELECT l.id FROM licenses l JOIN projects p ON l.project_id = p.id WHERE l.id = $1 AND p.user_id = $2
        """, license_id, user['id'])
        if not license_check:
            raise HTTPException(status_code=404, detail="License not found")
        
        rows = await conn.fetch("""
            SELECT id, hwid, machine_name, ip_address, first_seen_at, last_seen_at, is_active
            FROM hardware_bindings WHERE license_id = $1 ORDER BY last_seen_at DESC
        """, license_id)
        return [{"id": r['id'], "hwid": r['hwid'], "machine_name": r['machine_name'],
                "ip_address": r['ip_address'], "first_seen_at": r['first_seen_at'].isoformat(),
                "last_seen_at": r['last_seen_at'].isoformat(), "is_active": r['is_active']} for r in rows]
    finally:
        await release_db(conn)


@router.delete("/licenses/{license_id}/bindings/{binding_id}")
async def delete_binding(license_id: str, binding_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM hardware_bindings WHERE id = $1 AND license_id = $2", binding_id, license_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)


# =============================================================================
# HWID Reset Endpoints
# =============================================================================

@router.post("/licenses/{license_id}/reset-hwid")
async def reset_hwid(license_id: str, user: dict = Depends(get_current_user), reason: Optional[str] = None):
    """Reset all hardware bindings for a license."""
    conn = await get_db()
    try:
        # Verify ownership
        license_data = await conn.fetchrow("""
            SELECT l.id, l.license_key, l.client_name, l.client_email, p.id as project_id, p.name as project_name
            FROM licenses l JOIN projects p ON l.project_id = p.id
            WHERE l.id = $1 AND p.user_id = $2
        """, license_id, user['id'])
        
        if not license_data:
            raise HTTPException(status_code=404, detail="License not found")
        
        # Count bindings being removed
        binding_count = await conn.fetchval(
            "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
            license_id
        )
        
        # Delete all bindings
        await conn.execute("DELETE FROM hardware_bindings WHERE license_id = $1", license_id)
        
        # Log the reset
        reset_id = secrets.token_hex(16)
        await conn.execute("""
            INSERT INTO hwid_reset_logs (id, license_id, reset_by_user_id, bindings_removed, reason)
            VALUES ($1, $2, $3, $4, $5)
        """, reset_id, license_id, user['id'], binding_count, reason)
        
        # Trigger webhook
        trigger_webhook = _get_trigger_webhook()
        asyncio.create_task(trigger_webhook(user['id'], "hwid.reset", {
            "license_id": license_data['id'],
            "license_key": license_data['license_key'],
            "project_id": license_data['project_id'],
            "project_name": license_data['project_name'],
            "client_name": license_data['client_name'],
            "client_email": license_data['client_email'],
            "bindings_removed": binding_count,
            "reason": reason
        }))
        
        return {
            "status": "reset",
            "bindings_removed": binding_count,
            "message": f"Successfully removed {binding_count} hardware binding(s)"
        }
    finally:
        await release_db(conn)


@router.get("/licenses/{license_id}/reset-history")
async def get_reset_history(license_id: str, user: dict = Depends(get_current_user)):
    """Get HWID reset history for a license."""
    conn = await get_db()
    try:
        # Verify ownership
        license_check = await conn.fetchrow("""
            SELECT l.id FROM licenses l JOIN projects p ON l.project_id = p.id 
            WHERE l.id = $1 AND p.user_id = $2
        """, license_id, user['id'])
        
        if not license_check:
            raise HTTPException(status_code=404, detail="License not found")
        
        rows = await conn.fetch("""
            SELECT id, bindings_removed, reason, created_at
            FROM hwid_reset_logs
            WHERE license_id = $1
            ORDER BY created_at DESC
            LIMIT 50
        """, license_id)
        
        return [
            {
                "id": r['id'],
                "bindings_removed": r['bindings_removed'],
                "reason": r['reason'],
                "reset_at": r['created_at'].isoformat()
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
        license_data = await conn.fetchrow("""
            SELECT l.id, l.max_machines, l.status
            FROM licenses l JOIN projects p ON l.project_id = p.id 
            WHERE l.id = $1 AND p.user_id = $2
        """, license_id, user['id'])
        
        if not license_data:
            raise HTTPException(status_code=404, detail="License not found")
        
        # Get active bindings count
        active_bindings = await conn.fetchval(
            "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
            license_id
        )
        
        # Get last reset time
        last_reset = await conn.fetchrow(
            "SELECT created_at FROM hwid_reset_logs WHERE license_id = $1 ORDER BY created_at DESC LIMIT 1",
            license_id
        )
        
        # Get total reset count
        reset_count = await conn.fetchval(
            "SELECT COUNT(*) FROM hwid_reset_logs WHERE license_id = $1",
            license_id
        )
        
        return {
            "license_id": license_id,
            "active_bindings": active_bindings,
            "max_machines": license_data['max_machines'],
            "can_reset": active_bindings > 0 and license_data['status'] == 'active',
            "last_reset_at": last_reset['created_at'].isoformat() if last_reset else None,
            "total_resets": reset_count
        }
    finally:
        await release_db(conn)
