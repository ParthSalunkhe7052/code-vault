"""
License Server API - Production Version (PostgreSQL + R2)
FastAPI-based license validation and management server.

NOTE: This file has been refactored. Core functionality is now in:
- config.py - Configuration settings
- database.py - Database connection pool
- models.py - Pydantic models
- utils.py - Utility functions
"""

import os
import sys
import time
import secrets
import hashlib
import hmac
import json
import zipfile
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Header, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
import bcrypt
import jwt
import httpx
import asyncpg

# Import from refactored modules
from config import (
    DATABASE_URL, SECRET_KEY, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS,
    CORS_ORIGINS, CORS_ALLOW_ALL, ENVIRONMENT, ADMIN_EMAIL, CLI_VERSION, 
    CLI_DOWNLOAD_URLS, WEBHOOK_EVENTS, LICENSE_SERVER_URL, TIER_LIMITS,
    PRICING_CONFIG
)
from middleware.tier_enforcement import requires_feature
from startup_checks import run_startup_checks
from database import get_db, release_db, init_database, close_database, lifespan, db_pool
from contextlib import asynccontextmanager
from models import (
    LoginRequest, RegisterRequest, TokenResponse, ResetPasswordRequest,
    LicenseValidationRequest, LicenseValidationResponse, LicenseCreateRequest,
    ProjectCreateRequest, ProjectConfigRequest,
    CompileJobRequest, CompileJobResponse,
    WebhookCreateRequest, WebhookUpdateRequest, HWIDResetRequest
)
from utils import (
    utc_now, generate_nonce, generate_license_key, generate_api_key,
    compute_signature, create_jwt_token, verify_jwt_token,
    hash_password, verify_password, security,
    get_current_user, get_current_admin_user, create_validation_response,
    get_user_tier_limits
)

# Import storage and email services
from storage_service import storage_service, upload_project_file, upload_build_artifact, get_download_url, LOCAL_UPLOAD_DIR
from email_service import email_service, notify_license_created, notify_license_revoked
from compilers.nodejs_compiler import NodeJSCompiler

# GeoIP for Mission Control Map
try:
    import geoip2.database
    import geoip2.errors
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False
    print("[Warning] geoip2 not installed. Mission Control Map geolocation disabled.")

# GeoIP Reader singleton
_geoip_reader = None
GEOIP_DB_PATH = Path(__file__).parent / "data" / "GeoLite2-City.mmdb"

def get_geoip_reader():
    """Get or create GeoIP reader singleton. Returns None if DB not available."""
    global _geoip_reader
    if not GEOIP_AVAILABLE:
        return None
    if _geoip_reader is None and GEOIP_DB_PATH.exists():
        try:
            _geoip_reader = geoip2.database.Reader(str(GEOIP_DB_PATH))
            print(f"[GeoIP] Loaded database from {GEOIP_DB_PATH}")
        except Exception as e:
            print(f"[GeoIP] Failed to load database: {e}")
            return None
    return _geoip_reader

def get_geo_from_ip(ip_address: str) -> dict:
    """
    Get geolocation data from IP address.
    Returns dict with city, country, latitude, longitude (all may be None).
    """
    result = {"city": None, "country": None, "latitude": None, "longitude": None}
    
    # Skip local IPs
    if ip_address in ("127.0.0.1", "::1", "localhost", "unknown"):
        return result
    
    # Skip private IPs
    try:
        import ipaddress
        ip = ipaddress.ip_address(ip_address)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            return result
    except ValueError:
        return result
    
    reader = get_geoip_reader()
    if reader is None:
        return result
    
    try:
        response = reader.city(ip_address)
        result["city"] = response.city.name
        result["country"] = response.country.iso_code
        result["latitude"] = response.location.latitude
        result["longitude"] = response.location.longitude
    except geoip2.errors.AddressNotFoundError:
        pass  # IP not in database
    except Exception as e:
        print(f"[GeoIP] Error looking up {ip_address}: {e}")
    
    return result

# Local upload directory (fallback)
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)



# Initialize FastAPI
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Run environment checks
    try:
        run_startup_checks()
    except Exception as e:
        # In production, specific errors in run_startup_checks will raise and stop the server
        # In dev, we just log warnings
        if ENVIRONMENT == 'production':
            raise e
            
    # Chain to database lifespan
    async with lifespan(app):
        # Start background tasks
        import asyncio
        # cleanup_compile_cache is defined later in this file but will be available at runtime
        asyncio.create_task(cleanup_compile_cache())
        
        yield

app = FastAPI(
    title="CodeVault API",
    description="API for CodeVault License Management SaaS",
    version="1.0.0",
    lifespan=app_lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ALLOW_ALL else CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Stripe routes
from routes.stripe_routes import router as stripe_router
app.include_router(stripe_router)


# =============================================================================
# Health Check Endpoint (for Desktop App)
# =============================================================================

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for Tauri desktop app.
    Returns backend status and available compilers.
    """
    import shutil
    
    # Check if Node.js compiler is available
    nodejs_available = False
    try:
        pkg_path = shutil.which('pkg')
        nodejs_available = pkg_path is not None
    except Exception:
        pass
    
    # Check if Python/Nuitka is available
    nuitka_available = False
    try:
        nuitka_path = shutil.which('nuitka') or shutil.which('python')
        nuitka_available = nuitka_path is not None
    except Exception:
        pass
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "compilers": {
            "nodejs": nodejs_available,
            "python": nuitka_available
        }
    }


# =============================================================================
# Configuration Endpoints
# =============================================================================

@app.get("/api/v1/config/pricing")

async def get_pricing_config():
    """Get pricing configuration for the frontend."""
    return PRICING_CONFIG


# NOTE: Pydantic models are imported from models.py above. 
# Keeping this comment for reference on what's available:
# - LoginRequest, RegisterRequest, TokenResponse
# - LicenseValidationRequest, LicenseValidationResponse, LicenseCreateRequest  
# - ProjectCreateRequest, ProjectConfigRequest
# - CompileJobRequest, CompileJobResponse
# - WebhookCreateRequest, WebhookUpdateRequest, HWIDResetRequest



# NOTE: Utility functions are imported from utils.py above.
# Available: utc_now, generate_nonce, generate_license_key, generate_api_key,
#            compute_signature, create_jwt_token, verify_jwt_token, hash_password,
#            verify_password, security, get_current_user, get_current_admin_user,
#            create_validation_response, get_user_tier_limits


async def trigger_webhook(user_id: str, event: str, payload: dict):
    """
    Send webhook notifications for an event.
    Fetches all active webhooks for the user subscribed to this event,
    sends HTTP POST requests, and logs delivery results.
    """
    conn = await get_db()
    try:
        # Get all active webhooks for this user subscribed to this event
        rows = await conn.fetch("""
            SELECT id, url, secret, events FROM webhooks 
            WHERE user_id = $1 AND is_active = TRUE
        """, user_id)
        
        for webhook in rows:
            # Check if webhook is subscribed to this event
            events = webhook['events']
            if isinstance(events, str):
                try:
                    events = json.loads(events)
                except:
                    events = []
            
            if event not in events:
                continue
            
            webhook_id = webhook['id']
            url = webhook['url']
            secret = webhook['secret']
            
            # Prepare payload
            webhook_payload = {
                "event": event,
                "timestamp": utc_now().isoformat(),
                "data": payload
            }
            
            # Calculate signature if secret is set
            headers = {"Content-Type": "application/json"}
            if secret:
                payload_str = json.dumps(webhook_payload, sort_keys=True)
                signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
                headers["X-Webhook-Signature"] = signature
            
            # Send HTTP request
            start_time = time.time()
            delivery_id = secrets.token_hex(16)
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(url, json=webhook_payload, headers=headers)
                    delivery_time_ms = int((time.time() - start_time) * 1000)
                    
                    # Log delivery
                    success = 200 <= response.status_code < 300
                    await conn.execute("""
                        INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """, delivery_id, webhook_id, event, json.dumps(webhook_payload), response.status_code, 
                        response.text[:1000] if response.text else None, delivery_time_ms, success)
                    
                    # Update webhook stats
                    if success:
                        await conn.execute("""
                            UPDATE webhooks SET last_triggered_at = NOW(), failure_count = 0 WHERE id = $1
                        """, webhook_id)
                    else:
                        await conn.execute("""
                            UPDATE webhooks SET last_triggered_at = NOW(), failure_count = failure_count + 1 WHERE id = $1
                        """, webhook_id)
                        
            except Exception as e:
                delivery_time_ms = int((time.time() - start_time) * 1000)
                # Log failed delivery
                await conn.execute("""
                    INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """, delivery_id, webhook_id, event, json.dumps(webhook_payload), 0, str(e)[:1000], delivery_time_ms, False)
                
                await conn.execute("""
                    UPDATE webhooks SET failure_count = failure_count + 1 WHERE id = $1
                """, webhook_id)
                print(f"[Webhook] Failed to deliver {event} to {url}: {e}")
                
    except Exception as e:
        print(f"[Webhook] Error triggering webhooks for {event}: {e}")
    finally:
        await release_db(conn)


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post("/api/v1/auth/register")
async def register(data: RegisterRequest):
    conn = await get_db()
    try:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
        user_id = secrets.token_hex(16)
        api_key = generate_api_key()
        
        await conn.execute("""
            INSERT INTO users (id, email, password_hash, name, api_key) VALUES ($1, $2, $3, $4, $5)
        """, user_id, data.email, password_hash, data.name, api_key)
        
        token = create_jwt_token(user_id, data.email)
        return {"access_token": token, "token_type": "bearer",
                "user": {"id": user_id, "email": data.email, "name": data.name, "plan": "free", "api_key": api_key}}
    finally:
        await release_db(conn)

@app.post("/api/v1/auth/login")
async def login(data: LoginRequest):
    conn = await get_db()
    try:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash, name, plan, role, api_key FROM users WHERE email = $1",
            data.email
        )
        
        if not user:
            print(f"[Login] User not found: {data.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Check password
        try:
            password_match = bcrypt.checkpw(data.password.encode(), user["password_hash"].encode())
            if not password_match:
                print(f"[Login] Password mismatch for user: {data.email}")
                raise HTTPException(status_code=401, detail="Invalid email or password")
        except Exception as e:
            print(f"[Login] Password verification error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        print(f"[Login] Successful login: {data.email} (role: {user.get('role', 'user')})")
        token = create_jwt_token(user["id"], user["email"])
        return {"access_token": token, "token_type": "bearer",
                "user": {"id": user["id"], "email": user["email"], "name": user["name"], 
                        "plan": user["plan"], "role": user.get("role", "user"), "api_key": user["api_key"]}}
    finally:
        await release_db(conn)

@app.get("/api/v1/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"], "name": user.get("name"),
            "plan": user.get("plan", "free"), "role": user.get("role", "user"), 
            "api_key": user.get("api_key"), "created_at": utc_now().isoformat()}

@app.post("/api/v1/auth/regenerate-api-key")
async def regenerate_api_key(user: dict = Depends(get_current_user)):
    new_api_key = generate_api_key()
    conn = await get_db()
    try:
        await conn.execute("UPDATE users SET api_key = $1, updated_at = NOW() WHERE id = $2",
                          new_api_key, user["id"])
        return {"api_key": new_api_key}
    finally:
        await release_db(conn)

@app.post("/api/v1/auth/reset-password")
async def reset_password(data: ResetPasswordRequest, user: dict = Depends(get_current_user)):
    """Reset password for logged-in user"""
    password_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    conn = await get_db()
    try:
        await conn.execute("UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
                          password_hash, user["id"])
        return {"message": "Password reset successfully"}
    finally:
        await release_db(conn)

@app.post("/api/v1/auth/admin-reset-password")
async def admin_reset_password(
    email: str, 
    new_password: str,
    admin_user: dict = Depends(get_current_admin_user)  # SECURITY: Require admin auth
):
    """Admin endpoint to reset any user's password (admin auth required)"""
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    conn = await get_db()
    try:
        user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await conn.execute("UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
                          password_hash, user["id"])
        print(f"[Admin] Password reset for user: {email} (by admin: {admin_user['email']})")
        return {"message": f"Password reset successfully for {email}"}
    finally:
        await release_db(conn)


# =============================================================================
# Webhook Endpoints
# =============================================================================

WEBHOOK_EVENTS = [
    "license.created",
    "license.validated", 
    "license.revoked",
    "license.expired",
    "hwid.bound",
    "hwid.reset",
    "compilation.started",
    "compilation.completed",
    "compilation.failed"
]

class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=500)
    events: Optional[List[str]] = None
    secret: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

@app.get("/api/v1/webhooks")
async def list_webhooks(user: dict = Depends(get_current_user)):
    """List all webhooks for the current user."""
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT id, name, url, events, is_active, last_triggered_at, failure_count, created_at
            FROM webhooks WHERE user_id = $1 ORDER BY created_at DESC
        """, user['id'])
        
        result = []
        for w in rows:
            events = w['events']
            if isinstance(events, str):
                try:
                    events = json.loads(events)
                except:
                    events = []
            result.append({
                "id": w['id'],
                "name": w['name'],
                "url": w['url'],
                "events": events,
                "is_active": bool(w['is_active']),
                "last_triggered_at": w['last_triggered_at'].isoformat() if w['last_triggered_at'] else None,
                "failure_count": w['failure_count'] or 0,
                "created_at": w['created_at'].isoformat() if w['created_at'] else None
            })
        return result
    finally:
        await release_db(conn)

@app.post("/api/v1/webhooks")
@requires_feature('webhooks')
async def create_webhook(data: WebhookCreateRequest, user: dict = Depends(get_current_user)):
    """Create a new webhook."""
    invalid_events = [e for e in data.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid_events}")
    
    if not data.url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Webhook URL must start with http:// or https://")
    
    conn = await get_db()
    try:
        webhook_id = secrets.token_hex(16)
        events_json = json.dumps(data.events)
        
        await conn.execute("""
            INSERT INTO webhooks (id, user_id, name, url, secret, events, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, webhook_id, user['id'], data.name, data.url, data.secret, events_json)
        
        return {
            "id": webhook_id,
            "name": data.name,
            "url": data.url,
            "events": data.events,
            "is_active": True,
            "last_triggered_at": None,
            "failure_count": 0,
            "created_at": utc_now().isoformat()
        }
    finally:
        await release_db(conn)

@app.get("/api/v1/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Get a specific webhook."""
    conn = await get_db()
    try:
        row = await conn.fetchrow("""
            SELECT id, name, url, events, secret, is_active, last_triggered_at, failure_count, created_at
            FROM webhooks WHERE id = $1 AND user_id = $2
        """, webhook_id, user['id'])
        
        if not row:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        events = row['events']
        if isinstance(events, str):
            try:
                events = json.loads(events)
            except:
                events = []
        
        return {
            "id": row['id'],
            "name": row['name'],
            "url": row['url'],
            "events": events,
            "secret": row['secret'],
            "is_active": bool(row['is_active']),
            "last_triggered_at": row['last_triggered_at'].isoformat() if row['last_triggered_at'] else None,
            "failure_count": row['failure_count'] or 0,
            "created_at": row['created_at'].isoformat() if row['created_at'] else None
        }
    finally:
        await release_db(conn)

@app.put("/api/v1/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, data: WebhookUpdateRequest, user: dict = Depends(get_current_user)):
    """Update a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow("SELECT id FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        updates = []
        params = []
        param_count = 1
        
        if data.name is not None:
            updates.append(f"name = ${param_count}")
            params.append(data.name)
            param_count += 1
        if data.url is not None:
            if not data.url.startswith(('http://', 'https://')):
                raise HTTPException(status_code=400, detail="Webhook URL must start with http:// or https://")
            updates.append(f"url = ${param_count}")
            params.append(data.url)
            param_count += 1
        if data.events is not None:
            invalid_events = [e for e in data.events if e not in WEBHOOK_EVENTS]
            if invalid_events:
                raise HTTPException(status_code=400, detail=f"Invalid events: {invalid_events}")
            updates.append(f"events = ${param_count}")
            params.append(json.dumps(data.events))
            param_count += 1
        if data.secret is not None:
            updates.append(f"secret = ${param_count}")
            params.append(data.secret)
            param_count += 1
        if data.is_active is not None:
            updates.append(f"is_active = ${param_count}")
            params.append(data.is_active)
            param_count += 1
        
        if updates:
            updates.append(f"updated_at = NOW()")
            params.append(webhook_id)
            await conn.execute(f"UPDATE webhooks SET {', '.join(updates)} WHERE id = ${param_count}", *params)
        
        return await get_webhook(webhook_id, user)
    finally:
        await release_db(conn)

@app.delete("/api/v1/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Delete a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow("SELECT id FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        await conn.execute("DELETE FROM webhooks WHERE id = $1", webhook_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)

@app.get("/api/v1/webhooks/{webhook_id}/deliveries")
async def get_webhook_deliveries(webhook_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Get delivery history for a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow("SELECT id FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        rows = await conn.fetch("""
            SELECT id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at
            FROM webhook_deliveries WHERE webhook_id = $1
            ORDER BY created_at DESC LIMIT $2
        """, webhook_id, limit)
        
        return [{
            "id": row['id'],
            "event_type": row['event_type'],
            "payload": json.loads(row['payload']) if row['payload'] else None,
            "response_status": row['response_status'],
            "response_body": row['response_body'],
            "delivery_time_ms": row['delivery_time_ms'],
            "success": row['success'],
            "created_at": row['created_at'].isoformat() if row['created_at'] else None
        } for row in rows]
    finally:
        await release_db(conn)

@app.post("/api/v1/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Test a webhook by sending a test payload."""
    conn = await get_db()
    try:
        webhook = await conn.fetchrow("SELECT id, url, secret FROM webhooks WHERE id = $1 AND user_id = $2", webhook_id, user['id'])
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        url = webhook['url']
        secret = webhook['secret']
        
        # Prepare test payload
        test_payload = {
            "event": "test",
            "timestamp": utc_now().isoformat(),
            "data": {
                "message": "This is a test webhook from CodeVault",
                "webhook_id": webhook_id
            }
        }
        
        # Calculate signature if secret is set
        headers = {"Content-Type": "application/json"}
        if secret:
            payload_str = json.dumps(test_payload, sort_keys=True)
            signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = signature
        
        # Send actual HTTP request
        start_time = time.time()
        delivery_id = secrets.token_hex(16)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=test_payload, headers=headers)
                delivery_time_ms = int((time.time() - start_time) * 1000)
                success = 200 <= response.status_code < 300
                
                # Log delivery
                await conn.execute("""
                    INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """, delivery_id, webhook_id, "test", json.dumps(test_payload), response.status_code, 
                    response.text[:1000] if response.text else None, delivery_time_ms, success)
                
                await conn.execute("UPDATE webhooks SET last_triggered_at = NOW(), failure_count = 0 WHERE id = $1", webhook_id)
                
                if success:
                    return {"status": "success", "message": f"Test webhook sent successfully! Response: {response.status_code}", "delivery_time_ms": delivery_time_ms}
                else:
                    return {"status": "error", "message": f"Webhook returned non-2xx status: {response.status_code}", "delivery_time_ms": delivery_time_ms}
                    
        except Exception as e:
            delivery_time_ms = int((time.time() - start_time) * 1000)
            await conn.execute("""
                INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """, delivery_id, webhook_id, "test", json.dumps(test_payload), 0, str(e)[:1000], delivery_time_ms, False)
            
            await conn.execute("UPDATE webhooks SET failure_count = failure_count + 1 WHERE id = $1", webhook_id)
            raise HTTPException(status_code=500, detail=f"Failed to send webhook: {str(e)}")
    finally:
        await release_db(conn)

@app.get("/api/v1/webhooks/events/list")
async def get_webhook_events():
    """Get list of available webhook events with descriptions."""
    descriptions = {
        "license.created": "Triggered when a new license is created",
        "license.validated": "Triggered when a license is successfully validated",
        "license.revoked": "Triggered when a license is revoked",
        "license.expired": "Triggered when a license expires during validation",
        "hwid.bound": "Triggered when a new hardware ID is bound to a license",
        "hwid.reset": "Triggered when hardware bindings are reset for a license",
        "compilation.started": "Triggered when a compilation job starts",
        "compilation.completed": "Triggered when a compilation job completes successfully",
        "compilation.failed": "Triggered when a compilation job fails"
    }
    return {
        "events": WEBHOOK_EVENTS,
        "descriptions": descriptions
    }


# =============================================================================
# License Validation Endpoint
# =============================================================================

from starlette.concurrency import run_in_threadpool

# ... existing code ...

@app.post("/api/v1/license/validate", response_model=LicenseValidationResponse)
async def validate_license(request: Request, data: LicenseValidationRequest):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    # Get geolocation for Mission Control Map (run in threadpool to avoid blocking async loop)
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
        
        # Ensure features is an array
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except:
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


# =============================================================================
# License Management Endpoints
# =============================================================================

@app.get("/api/v1/licenses")
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
            # Ensure features is an array
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
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

@app.post("/api/v1/licenses")
async def create_license(data: LicenseCreateRequest, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow("SELECT id, name FROM projects WHERE id = $1 AND user_id = $2", data.project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check tier limits before creating license
        limits = await get_user_tier_limits(user['id'], conn)
        max_licenses = limits.get('max_licenses_per_project', 5)
        
        if max_licenses != -1:  # -1 means unlimited (enterprise)
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
        
        # Send email notification
        if data.client_email:
            await notify_license_created(data.client_name, data.client_email, license_key,
                                        project['name'], data.expires_at, data.max_machines, data.features)
        
        # Trigger webhook
        import asyncio
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

@app.post("/api/v1/licenses/{license_id}/revoke")
async def revoke_license(license_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        # Fetch license details before revoking
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
        
        # Trigger webhook
        import asyncio
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

@app.delete("/api/v1/licenses/{license_id}")
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

@app.get("/api/v1/licenses/{license_id}/bindings")
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

@app.delete("/api/v1/licenses/{license_id}/bindings/{binding_id}")
async def delete_binding(license_id: str, binding_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM hardware_bindings WHERE id = $1 AND license_id = $2", binding_id, license_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)


# =============================================================================
# Project Endpoints
# =============================================================================

@app.get("/api/v1/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT p.id, p.name, p.description, p.created_at, p.language,
                   (SELECT COUNT(*) FROM licenses l WHERE l.project_id = p.id) as license_count
            FROM projects p WHERE p.user_id = $1 ORDER BY p.created_at DESC
        """, user['id'])
        return [{"id": r['id'], "name": r['name'], "description": r['description'],
                "language": r.get('language', 'python'),
                "created_at": r['created_at'].isoformat(), "license_count": r['license_count'],
                "local_path": str(LOCAL_UPLOAD_DIR / r['id'])} for r in rows]
    finally:
        await release_db(conn)

@app.post("/api/v1/projects")
async def create_project(data: ProjectCreateRequest, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        # Check tier limits before creating project
        limits = await get_user_tier_limits(user['id'], conn)
        max_projects = limits.get('max_projects', 1)
        
        if max_projects != -1:  # -1 means unlimited (enterprise)
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM projects WHERE user_id = $1", user['id']
            )
            if current_count >= max_projects:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Project limit reached ({max_projects}). Upgrade your plan for more projects."
                )
        
        project_id = secrets.token_hex(16)
        await conn.execute("""
            INSERT INTO projects (id, user_id, name, description, language, compiler_options) 
            VALUES ($1, $2, $3, $4, $5, $6)
        """, project_id, user['id'], data.name, data.description, data.language, json.dumps(data.compiler_options))
        return {"id": project_id, "name": data.name, "description": data.description,
                "language": data.language, "compiler_options": data.compiler_options,
                "created_at": utc_now().isoformat(), "license_count": 0,
                "local_path": str(LOCAL_UPLOAD_DIR / project_id)}
    finally:
        await release_db(conn)

@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow("SELECT id FROM projects WHERE id = $1 AND user_id = $2", project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        await storage_service.delete_project_files(project_id)
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)

@app.get("/api/v1/projects/{project_id}/download-source")
async def download_project_source(project_id: str, user: dict = Depends(get_current_user)):
    """Download all project files as a ZIP for local compilation."""
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, name FROM projects WHERE id = $1 AND user_id = $2", 
            project_id, user['id']
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all files for this project
        files = await conn.fetch("""
            SELECT id, file_path, original_filename, is_cloud
            FROM project_files WHERE project_id = $1
        """, project_id)
        
        if not files:
            raise HTTPException(status_code=404, detail="No files found for this project")
        
        # Create temporary ZIP file
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / f"{project['name'].replace(' ', '_')}_source.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                file_path = file['file_path']
                original_name = file['original_filename']
                is_cloud = file['is_cloud']
                
                try:
                    if is_cloud:
                        # Download from cloud storage
                        content = await storage_service.download_file(file_path)
                        if content:
                            zf.writestr(original_name, content)
                    else:
                        # Read from local storage
                        local_path = LOCAL_UPLOAD_DIR / file_path.lstrip('/')
                        if local_path.exists():
                            zf.write(local_path, original_name)
                except Exception as e:
                    print(f"[Download] Error adding file {original_name}: {e}")
                    continue
        
        # Return the ZIP file
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{project['name'].replace(' ', '_')}_source.zip",
            background=None  # Don't use background for cleanup
        )
    finally:
        await release_db(conn)

@app.get("/api/v1/projects/{project_id}/config")
async def get_project_config(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow("SELECT id, settings, compiler_options, language FROM projects WHERE id = $1 AND user_id = $2", project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        settings = project['settings'] or {}
        # Parse settings if it's a string
        if isinstance(settings, str):
            settings = json.loads(settings) if settings else {}
            
        # Parse compiler_options if needed
        compiler_opts = project.get('compiler_options') or {}
        if isinstance(compiler_opts, str):
            compiler_opts = json.loads(compiler_opts)
            
        language = project.get('language', 'python')

        files = await conn.fetch("""
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
        """, project_id)
        
        return {"entry_file": settings.get('entry_file'), "output_name": settings.get('output_name'),
                "include_modules": settings.get('include_modules', []), "exclude_modules": settings.get('exclude_modules', []),
                "nuitka_options": settings.get('nuitka_options', {}),
                "compiler_options": compiler_opts,
                "language": language,
                "files": [{"id": f['id'], "filename": f['filename'], "original_filename": f['original_filename'],
                          "file_size": f['file_size'], "file_hash": f['file_hash'],
                          "created_at": f['created_at'].isoformat()} for f in files]}
    finally:
        await release_db(conn)

@app.put("/api/v1/projects/{project_id}/config")
async def update_project_config(project_id: str, data: ProjectConfigRequest, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow("SELECT id, settings FROM projects WHERE id = $1 AND user_id = $2", project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Merge with existing settings to preserve file_tree etc
        current_settings = json.loads(project['settings']) if isinstance(project['settings'], str) else (project['settings'] or {})
        
        current_settings.update({
            "entry_file": data.entry_file,
            "output_name": data.output_name,
            "include_modules": data.include_modules, 
            "exclude_modules": data.exclude_modules,
            "nuitka_options": data.nuitka_options
        })
        
        await conn.execute("""
            UPDATE projects 
            SET settings = $1, compiler_options = $2, updated_at = NOW() 
            WHERE id = $3
        """, json.dumps(current_settings), json.dumps(data.compiler_options), project_id)
        
        return await get_project_config(project_id, user)
    finally:
        await release_db(conn)

@app.post("/api/v1/projects/{project_id}/upload")
async def upload_files(project_id: str, files: List[UploadFile] = File(...), user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow("SELECT id FROM projects WHERE id = $1 AND user_id = $2", project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        uploaded = []
        for upload_file in files:
            content = await upload_file.read()
            
            # Validate file size
            from storage_service import validate_file_size, MAX_FILE_SIZE
            is_valid, error_msg = validate_file_size(len(content), is_zip=False)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"File '{upload_file.filename}': {error_msg}")
            
            stored = await upload_project_file(project_id, upload_file.filename, content)
            
            file_id = secrets.token_hex(16)
            await conn.execute("""
                INSERT INTO project_files (id, project_id, filename, original_filename, file_path, file_hash, file_size, is_cloud)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, file_id, project_id, Path(stored.key).name, upload_file.filename, stored.key, stored.hash, stored.size, not stored.is_local)
            
            uploaded.append({"id": file_id, "filename": Path(stored.key).name, "original_filename": upload_file.filename,
                           "file_size": stored.size, "file_hash": stored.hash, "created_at": utc_now().isoformat()})
        return uploaded
    finally:
        await release_db(conn)

@app.get("/api/v1/projects/{project_id}/files")
async def list_files(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow("SELECT id FROM projects WHERE id = $1 AND user_id = $2", project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        files = await conn.fetch("""
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
        """, project_id)
        return [{"id": f['id'], "filename": f['filename'], "original_filename": f['original_filename'],
                "file_size": f['file_size'], "file_hash": f['file_hash'],
                "created_at": f['created_at'].isoformat()} for f in files]
    finally:
        await release_db(conn)

@app.delete("/api/v1/projects/{project_id}/files/{file_id}")
async def delete_file(project_id: str, file_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        file_row = await conn.fetchrow("""
            SELECT pf.id, pf.file_path, pf.is_cloud FROM project_files pf
            JOIN projects p ON pf.project_id = p.id
            WHERE pf.id = $1 AND p.user_id = $2
        """, file_id, user['id'])
        if not file_row:
            raise HTTPException(status_code=404, detail="File not found")
        
        await storage_service.delete_file(file_row['file_path'], not file_row['is_cloud'])
        await conn.execute("DELETE FROM project_files WHERE id = $1", file_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)


def detect_entry_point_smart(base_path: Path, files: list) -> dict:
    """
    Smart entry point detection with confidence scoring.
    Scores files based on:
    - Has `if __name__ == "__main__":` block (+100)
    - Common entry names like main.py, app.py, run.py (+50)
    - Root level file (+25)
    
    Returns: {
        'entry_point': 'main.py',
        'confidence': 'high' | 'medium' | 'low',
        'candidates': [{'file': 'main.py', 'score': 175, 'reason': '...'}, ...]
    }
    """
    candidates = []
    common_names = ['main.py', 'app.py', 'run.py', 'cli.py', '__main__.py', 'start.py']
    
    for file_path in files:
        full_path = base_path / file_path
        if not full_path.exists():
            continue
            
        score = 0
        reasons = []
        
        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check for __main__ block
            if 'if __name__' in content and '__main__' in content:
                score += 100
                reasons.append("has __main__ block")
            
            # Check for common entry point names
            filename = Path(file_path).name
            if filename in common_names:
                score += 50
                reasons.append(f"common entry name '{filename}'")
            
            # Check if root level (not in subfolder)
            if '/' not in file_path and '\\' not in file_path:
                score += 25
                reasons.append("root level file")
            
            # Bonus for imports that suggest it's a main file
            if 'import argparse' in content or 'from argparse' in content:
                score += 10
                reasons.append("uses argparse")
            
        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            continue
        
        if score > 0 or not candidates:  # Always add at least one candidate
            candidates.append({
                'file': file_path,
                'score': score,
                'reason': ', '.join(reasons) if reasons else 'default'
            })
    
    # Sort by score descending
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Determine confidence
    if not candidates:
        return {
            'entry_point': None,
            'confidence': 'low',
            'candidates': []
        }
    
    best = candidates[0]
    
    if best['score'] >= 125:
        confidence = 'high'
    elif best['score'] >= 50:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    return {
        'entry_point': best['file'],
        'confidence': confidence,
        'candidates': candidates[:5]  # Top 5 candidates
    }


def scan_project_structure(base_path: Path) -> dict:
    """
    Scan uploaded project and return file tree with dependencies.
    Returns: {
        'files': ['main.py', 'backend/models.py', ...],
        'folders': ['backend', 'backend/api', ...],
        'entry_point': 'main.py',
        'entry_point_confidence': 'high' | 'medium' | 'low',
        'entry_point_candidates': [...],
        'total_files': 10,
        'dependencies': {
            'python': ['requests', 'fastapi'],
            'has_requirements': True
        }
    }
    """
    files = []
    folders = set()
    dependencies = {
        'python': [],
        'has_requirements': False
    }
    
    # Find all Python files
    for py_file in base_path.rglob("*.py"):
        relative_path = py_file.relative_to(base_path)
        files.append(str(relative_path).replace("\\", "/"))
        
        # Track folders
        for parent in relative_path.parents:
            if str(parent) != '.':
                folders.add(str(parent).replace("\\", "/"))
    
    # Smart entry point detection
    entry_detection = detect_entry_point_smart(base_path, files)
    
    # Check for requirements.txt
    req_file = base_path / "requirements.txt"
    if req_file.exists():
        dependencies['has_requirements'] = True
        try:
            dependencies['python'] = [
                line.strip() 
                for line in req_file.read_text(encoding='utf-8').splitlines()
                if line.strip() and not line.strip().startswith('#')
            ]
        except Exception as e:
            print(f"Warning: Could not parse requirements.txt: {e}")
    
    return {
        "files": sorted(files),
        "folders": sorted(list(folders)),
        "entry_point": entry_detection['entry_point'],
        "entry_point_confidence": entry_detection['confidence'],
        "entry_point_candidates": entry_detection['candidates'],
        "total_files": len(files),
        "dependencies": dependencies
    }


def detect_nodejs_entry_point(base_path: Path, files: list) -> dict:
    """
    Smart entry point detection for Node.js projects.
    Scores files based on:
    - package.json "main" field (+200)
    - Common entry names like index.js, main.js, app.js (+100)
    - Root level file (+25)
    """
    candidates = []
    common_names = ['index.js', 'main.js', 'app.js', 'server.js', 'start.js', 'cli.js']
    
    # Check package.json for main field first
    pkg_json = base_path / "package.json"
    if pkg_json.exists():
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding='utf-8'))
            main_entry = pkg_data.get('main')
            if main_entry and main_entry in files:
                candidates.append({
                    'file': main_entry,
                    'score': 200,
                    'reason': 'package.json main field'
                })
        except:
            pass
    
    for file_path in files:
        if file_path in [c['file'] for c in candidates]:
            continue  # Skip if already added from package.json
            
        score = 0
        reasons = []
        
        filename = Path(file_path).name
        
        # Check for common entry point names
        if filename in common_names:
            score += 100
            reasons.append(f"common entry name '{filename}'")
        
        # Check if root level (not in subfolder)
        if '/' not in file_path and '\\' not in file_path:
            score += 25
            reasons.append("root level file")
        
        if score > 0:
            candidates.append({
                'file': file_path,
                'score': score,
                'reason': ', '.join(reasons) if reasons else 'default'
            })
    
    # Sort by score descending
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    if not candidates:
        return {
            'entry_point': None,
            'confidence': 'low',
            'candidates': []
        }
    
    best = candidates[0]
    
    if best['score'] >= 150:
        confidence = 'high'
    elif best['score'] >= 50:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    return {
        'entry_point': best['file'],
        'confidence': confidence,
        'candidates': candidates[:5]
    }


def scan_nodejs_project_structure(base_path: Path) -> dict:
    """
    Scan uploaded Node.js project and return file tree with dependencies.
    """
    files = []
    folders = set()
    dependencies = {
        'nodejs': [],
        'has_package_json': False
    }
    
    # Find all JS/TS files (excluding node_modules)
    js_extensions = ["*.js", "*.mjs", "*.cjs", "*.ts", "*.tsx", "*.jsx"]
    for ext in js_extensions:
        for js_file in base_path.rglob(ext):
            # Skip node_modules
            if "node_modules" in str(js_file):
                continue
            relative_path = js_file.relative_to(base_path)
            files.append(str(relative_path).replace("\\", "/"))
            
            # Track folders
            for parent in relative_path.parents:
                if str(parent) != '.':
                    folders.add(str(parent).replace("\\", "/"))
    
    # Smart entry point detection for Node.js
    entry_detection = detect_nodejs_entry_point(base_path, files)
    
    # Check for package.json
    pkg_json = base_path / "package.json"
    if pkg_json.exists():
        dependencies['has_package_json'] = True
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding='utf-8'))
            deps = list(pkg_data.get('dependencies', {}).keys())
            dev_deps = list(pkg_data.get('devDependencies', {}).keys())
            dependencies['nodejs'] = deps + dev_deps
        except Exception as e:
            print(f"Warning: Could not parse package.json: {e}")
    
    return {
        "files": sorted(files),
        "folders": sorted(list(folders)),
        "entry_point": entry_detection['entry_point'],
        "entry_point_confidence": entry_detection['confidence'],
        "entry_point_candidates": entry_detection['candidates'],
        "total_files": len(files),
        "dependencies": dependencies
    }


@app.post("/api/v1/projects/{project_id}/upload-zip")
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Upload an entire project as a ZIP file.
    Extracts and preserves folder structure.
    """
    conn = await get_db()
    try:
        # Verify project ownership and get language
        project = await conn.fetchrow("SELECT id, name, language FROM projects WHERE id = $1 AND user_id = $2", 
                                      project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Validate it's a ZIP file
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="File must be a .zip file")
        
        # Create temporary directory for extraction
        project_dir = UPLOAD_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded ZIP
        zip_path = project_dir / "project.zip"
        content = await file.read()
        
        # Validate ZIP file size
        from storage_service import validate_file_size, MAX_ZIP_SIZE
        is_valid, error_msg = validate_file_size(len(content), is_zip=True)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        with open(zip_path, "wb") as f:
            f.write(content)
        
        # Extract ZIP preserving structure
        source_dir = project_dir / "source"
        if source_dir.exists():
            shutil.rmtree(source_dir)
        source_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(source_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        
        # Get project language and scan with appropriate function
        language = project.get('language', 'python') if hasattr(project, 'get') else (project['language'] if 'language' in project else 'python')
        
        if language == 'nodejs':
            file_tree = scan_nodejs_project_structure(source_dir)
        else:
            file_tree = scan_project_structure(source_dir)
        
        if file_tree['total_files'] == 0:
            lang_name = "JavaScript/TypeScript" if language == 'nodejs' else "Python"
            raise HTTPException(status_code=400, detail=f"No {lang_name} files found in ZIP")
        
        # Update project in database with file_tree
        settings = await conn.fetchval("SELECT settings FROM projects WHERE id = $1", project_id)
        if settings is None:
            settings = {}
        else:
            settings = json.loads(settings) if isinstance(settings, str) else settings
        
        settings['file_tree'] = file_tree
        settings['is_multi_folder'] = True
        settings['zip_uploaded_at'] = utc_now().isoformat()
        
        await conn.execute(
            "UPDATE projects SET settings = $1, updated_at = NOW() WHERE id = $2",
            json.dumps(settings), project_id
        )
        
        # Clean up ZIP file but keep extracted source
        zip_path.unlink()
        
        return {
            "success": True,
            "file_count": file_tree['total_files'],
            "structure": file_tree,
            "message": f"Successfully uploaded {file_tree['total_files']} files"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading ZIP: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process ZIP: {str(e)}")
    finally:
        await release_db(conn)


# =============================================================================
# Compilation Endpoints
# =============================================================================

# In-memory job tracking for live updates
compile_jobs_cache = {}

async def cleanup_compile_cache():
    """Background task to remove completed jobs from cache after 1 hour."""
    import asyncio
    while True:
        await asyncio.sleep(3600)  # Run every hour
        now = time.time()
        to_remove = []
        for job_id, data in list(compile_jobs_cache.items()):
            if data.get('status') in ['completed', 'failed']:
                completed_time = data.get('completed_time', 0)
                if completed_time and completed_time < now - 3600:
                    to_remove.append(job_id)
        for job_id in to_remove:
            del compile_jobs_cache[job_id]
        if to_remove:
            print(f"[Cache Cleanup] Removed {len(to_remove)} old compile jobs from memory")

# Cache cleanup is now handled in app_lifespan


@app.post("/api/v1/compile/start", response_model=CompileJobResponse)
@requires_feature('cloud_compilation')
async def start_compilation(data: CompileJobRequest, project_id: str, user: dict = Depends(get_current_user)):
    """Start a compilation job for a project."""
    conn = await get_db()
    try:
        print(f"[DEBUG] Compile request - project_id: {project_id}, data: {data}")
        
        project = await conn.fetchrow("SELECT id, settings, language FROM projects WHERE id = $1 AND user_id = $2", project_id, user['id'])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check Tier Access for Node.js
        if project.get('language') == 'nodejs':
            await check_feature_access(user['id'], 'node_support', conn)
        
        # Parse settings
        settings = json.loads(project['settings']) if isinstance(project['settings'], str) else (project['settings'] or {})
        
        # Check if project has files (either individual files or ZIP file tree)
        file_count = await conn.fetchval("SELECT COUNT(*) FROM project_files WHERE project_id = $1", project_id)
        has_file_tree = settings.get('file_tree') is not None
        
        print(f"[DEBUG] file_count: {file_count}, has_file_tree: {has_file_tree}")
        
        if file_count == 0 and not has_file_tree:
            raise HTTPException(status_code=400, detail="No files uploaded to project")
        
        # Create compile job
        job_id = secrets.token_hex(16)
        created_at = utc_now()
        
        await conn.execute("""
            INSERT INTO compile_jobs (id, project_id, status, progress, created_at) 
            VALUES ($1, $2, $3, $4, $5)
        """, job_id, project_id, 'pending', 0, created_at)
        
        # Store job in cache for status updates
        compile_jobs_cache[job_id] = {
            'status': 'pending',
            'progress': 0,
            'logs': ['Compilation job created...'],
            'project_id': project_id,
            'entry_file': data.entry_file,
            'output_name': data.output_name,
            'options': data.options
        }
        
        # Start background compilation task
        import asyncio
        asyncio.create_task(run_compilation_job(job_id, project_id, data))
        
        return CompileJobResponse(
            id=job_id,
            project_id=project_id,
            status='pending',
            progress=0,
            output_filename=None,
            error_message=None,
            logs=['Compilation job created...'],
            started_at=None,
            completed_at=None,
            created_at=created_at.isoformat()
        )
    finally:
        await release_db(conn)


async def run_compilation_job(job_id: str, project_id: str, data: CompileJobRequest):
    """Background task to run actual compilation with Nuitka."""
    import asyncio
    
    try:
        # Update status to running
        compile_jobs_cache[job_id]['status'] = 'running'
        compile_jobs_cache[job_id]['logs'].append('Starting compilation...')
        started_at = utc_now()
        
        conn = await get_db()
        try:
            await conn.execute("UPDATE compile_jobs SET status = $1, started_at = $2 WHERE id = $3", 
                             'running', started_at, job_id)
            
            # Get project settings
            project = await conn.fetchrow("SELECT settings, language FROM projects WHERE id = $1", project_id)
            settings = json.loads(project['settings']) if isinstance(project['settings'], str) else project['settings']
            language = project.get('language', 'python')
        finally:
            await release_db(conn)
        
        # Determine if multi-folder project
        file_tree = settings.get('file_tree')
        is_multi_folder = settings.get('is_multi_folder', False)
        
        if language == 'nodejs':
            await compile_nodejs_project(job_id, project_id, data, compile_jobs_cache)
        elif is_multi_folder and file_tree:
            # Compile multi-folder project
            await compile_multi_folder_project(job_id, project_id, file_tree, data, compile_jobs_cache)
        else:
            # Compile single file project (existing flow)
            await compile_single_file_project(job_id, project_id, data, compile_jobs_cache)
        
        # Mark as completed
        completed_at = utc_now()
        output_filename = f"{data.output_name or 'output'}.exe"
        
        compile_jobs_cache[job_id]['status'] = 'completed'
        compile_jobs_cache[job_id]['output_filename'] = output_filename
        compile_jobs_cache[job_id]['completed_time'] = time.time()  # For cache eviction
        compile_jobs_cache[job_id]['logs'].append('✅ Compilation completed successfully!')
        
        conn = await get_db()
        try:
            await conn.execute("""
                UPDATE compile_jobs SET status = $1, progress = $2, output_filename = $3, 
                completed_at = $4, logs = $5 WHERE id = $6
            """, 'completed', 100, output_filename, completed_at, 
               json.dumps(compile_jobs_cache[job_id]['logs']), job_id)
        finally:
            await release_db(conn)
        
    except Exception as e:
        compile_jobs_cache[job_id]['status'] = 'failed'
        compile_jobs_cache[job_id]['error_message'] = str(e)
        compile_jobs_cache[job_id]['completed_time'] = time.time()  # For cache eviction
        compile_jobs_cache[job_id]['logs'].append(f'❌ Compilation failed: {str(e)}')
        
        conn = await get_db()
        try:
            await conn.execute("UPDATE compile_jobs SET status = $1, error_message = $2, logs = $3 WHERE id = $4",
                             'failed', str(e), json.dumps(compile_jobs_cache[job_id]['logs']), job_id)
        finally:
            await release_db(conn)


async def compile_multi_folder_project(job_id: str, project_id: str, file_tree: dict, data: CompileJobRequest, job_cache: dict):
    """
    Compile a multi-folder project with dependencies.
    Uses the virtual environment at the project root.
    """
    import asyncio
    
    print(f"[DEBUG] Starting multi-folder compilation for project {project_id}")
    job_cache[job_id]['logs'].append('📦 Multi-folder project detected')
    job_cache[job_id]['logs'].append(f"   Files: {file_tree['total_files']}")
    job_cache[job_id]['logs'].append(f"   Entry: {file_tree['entry_point']}")
    
    # Get source directory
    project_dir = UPLOAD_DIR / project_id / "source"
    print(f"[DEBUG] Project directory: {project_dir}")
    print(f"[DEBUG] Directory exists: {project_dir.exists()}")
    
    if not project_dir.exists():
        raise Exception(f"Project source directory not found: {project_dir}")
    
    job_cache[job_id]['progress'] = 10
    
    # Install dependencies if needed
    dependencies = file_tree.get('dependencies', {})
    if dependencies.get('has_requirements'):
        job_cache[job_id]['logs'].append(f"📦 Installing {len(dependencies['python'])} dependencies...")
        install_project_dependencies(project_dir, dependencies, job_cache[job_id]['logs'])
    
    job_cache[job_id]['progress'] = 30
    
    # Inject license wrapper
    job_cache[job_id]['logs'].append('🔐 Injecting license validation...')
    entry_point = file_tree['entry_point']
    inject_license_into_multi_folder(project_dir, entry_point, data.license_key or "DEMO-KEY")
    
    job_cache[job_id]['progress'] = 50
    
    # Build Nuitka command
    job_cache[job_id]['logs'].append('🔨 Building with Nuitka...')
    output_name = data.output_name or 'app'
    entry_file = project_dir / entry_point
    
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--output-filename={output_name}.exe",
    ]
    
    # Include all folders as packages
    for folder in file_tree.get('folders', []):
        package = folder.replace("/", ".").replace("\\", ".")
        nuitka_cmd.append(f"--include-package={package}")
        job_cache[job_id]['logs'].append(f"   Including: {package}")
    
    # Add main entry point
    nuitka_cmd.append(str(entry_file))
    
    job_cache[job_id]['progress'] = 60
    job_cache[job_id]['logs'].append('⚙️  Compiling (this may take 2-5 minutes)...')
    
    # Run Nuitka
    result = subprocess.run(
        nuitka_cmd,
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=600  # 10 minute timeout
    )
    
    job_cache[job_id]['progress'] = 95
    
    if result.returncode != 0:
        job_cache[job_id]['logs'].append('❌ Nuitka compilation failed')
        job_cache[job_id]['logs'].append(f"Error: {result.stderr[:500]}")
        raise Exception(f"Nuitka failed: {result.stderr[:200]}")
    
    # Find output executable
    exe_file = project_dir / f"{output_name}.exe"
    if not exe_file.exists():
        # Try to find it
        for f in project_dir.glob("*.exe"):
            exe_file = f
            break
    
    if not exe_file.exists():
        raise Exception("Compiled executable not found")
    
    # Move to output location
    output_dir = UPLOAD_DIR / project_id / "output"
    output_dir.mkdir(exist_ok=True)
    final_exe = output_dir / f"{output_name}.exe"
    shutil.move(str(exe_file), str(final_exe))
    
    file_size = final_exe.stat().st_size / 1024 / 1024
    job_cache[job_id]['logs'].append(f'✅ Executable created: {final_exe.name} ({file_size:.1f} MB)')
    job_cache[job_id]['progress'] = 100


async def compile_single_file_project(job_id: str, project_id: str, data: CompileJobRequest, job_cache: dict):
    """Compile a single-file project using Nuitka."""
    import asyncio
    
    job_cache[job_id]['logs'].append('📄 Single-file project detected')
    job_cache[job_id]['progress'] = 10
    
    # Get the project source file
    project_dir = UPLOAD_DIR / project_id / "source"
    
    if not project_dir.exists():
        # Check for single file upload
        file_dir = UPLOAD_DIR / project_id
        py_files = list(file_dir.glob("*.py"))
        if py_files:
            source_file = py_files[0]
            project_dir = file_dir
        else:
            raise Exception(f"Project source not found: {project_dir}")
    else:
        # Find the entry file
        entry_file_name = data.entry_file
        if entry_file_name:
            source_file = project_dir / entry_file_name
        else:
            # Find the first .py file
            py_files = list(project_dir.glob("*.py"))
            if not py_files:
                raise Exception("No Python files found in project")
            source_file = py_files[0]
    
    if not source_file.exists():
        raise Exception(f"Source file not found: {source_file}")
    
    job_cache[job_id]['logs'].append(f'   Entry file: {source_file.name}')
    job_cache[job_id]['progress'] = 20
    
    # Update DB
    conn = await get_db()
    try:
        await conn.execute("UPDATE compile_jobs SET progress = $1, logs = $2 WHERE id = $3",
                         20, json.dumps(job_cache[job_id]['logs']), job_id)
    finally:
        await release_db(conn)
    
    # Inject license validation if license key provided
    if data.license_key:
        job_cache[job_id]['logs'].append('🔐 Injecting license validation...')
        inject_license_into_single_file(source_file, data.license_key)
        job_cache[job_id]['progress'] = 30
    
    # Build Nuitka command
    job_cache[job_id]['logs'].append('🔨 Building with Nuitka...')
    output_name = data.output_name or source_file.stem
    
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--output-filename={output_name}.exe",
        str(source_file)
    ]
    
    job_cache[job_id]['progress'] = 40
    job_cache[job_id]['logs'].append('⚙️  Compiling (this may take 2-5 minutes)...')
    
    # Update DB
    conn = await get_db()
    try:
        await conn.execute("UPDATE compile_jobs SET progress = $1, logs = $2 WHERE id = $3",
                         40, json.dumps(job_cache[job_id]['logs']), job_id)
    finally:
        await release_db(conn)
    
    # Run Nuitka
    try:
        result = subprocess.run(
            nuitka_cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
    except subprocess.TimeoutExpired:
        raise Exception("Compilation timed out after 10 minutes")
    
    job_cache[job_id]['progress'] = 90
    
    if result.returncode != 0:
        job_cache[job_id]['logs'].append('❌ Nuitka compilation failed')
        error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
        job_cache[job_id]['logs'].append(f"Error: {error_msg}")
        raise Exception(f"Nuitka failed: {error_msg[:200]}")
    
    # Find output executable
    exe_file = project_dir / f"{output_name}.exe"
    if not exe_file.exists():
        # Try to find any .exe file
        for f in project_dir.glob("*.exe"):
            exe_file = f
            break
    
    if not exe_file.exists():
        raise Exception("Compiled executable not found")
    
    # Move to output location
    output_dir = UPLOAD_DIR / project_id / "output"
    output_dir.mkdir(exist_ok=True)
    final_exe = output_dir / f"{output_name}.exe"
    
    # Remove existing if present
    if final_exe.exists():
        final_exe.unlink()
    
    shutil.move(str(exe_file), str(final_exe))
    
    file_size = final_exe.stat().st_size / 1024 / 1024
    job_cache[job_id]['logs'].append(f'✅ Executable created: {final_exe.name} ({file_size:.1f} MB)')
    job_cache[job_id]['progress'] = 100
    
    # Update DB
    conn = await get_db()
    try:
        await conn.execute("UPDATE compile_jobs SET progress = $1, logs = $2 WHERE id = $3",
                         100, json.dumps(job_cache[job_id]['logs']), job_id)
    finally:
        await release_db(conn)


def inject_license_into_single_file(source_file: Path, license_key: str):
    """Inject license validation into a single Python file."""
    original_content = source_file.read_text(encoding='utf-8')
    
    # Backup original
    backup_file = source_file.parent / f"_original_{source_file.name}"
    if not backup_file.exists():
        source_file.rename(backup_file)
        source_file.write_text(original_content, encoding='utf-8')
    
    # Create wrapper code
    wrapper_code = f'''#!/usr/bin/env python3
"""
License-Protected Application
This file has been modified to include license validation.
"""

import sys
import os
import hashlib
import urllib.request
import json
import time

def get_hardware_id():
    """Generate a unique hardware ID."""
    import platform
    info = f"{{platform.node()}}|{{platform.machine()}}|{{platform.processor()}}"
    return hashlib.sha256(info.encode()).hexdigest()[:32]

def validate_license():
    """Validate license before running application."""
    license_key = "{license_key}"
    # Server URL can be overridden via environment variable
    server_url = os.environ.get("LICENSE_SERVER_URL", "{LICENSE_SERVER_URL}") + "/license/validate"
    
    try:
        hwid = get_hardware_id()
        nonce = hashlib.sha256(str(time.time()).encode()).hexdigest()[:32]
        
        payload = json.dumps({{
            "license_key": license_key,
            "hwid": hwid,
            "machine_name": os.environ.get("COMPUTERNAME", "Unknown"),
            "nonce": nonce,
            "timestamp": int(time.time())
        }}).encode('utf-8')
        
        req = urllib.request.Request(
            server_url,
            data=payload,
            headers={{"Content-Type": "application/json"}}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('status') != 'valid':
                print("\\n❌ LICENSE VALIDATION FAILED")
                print(f"Reason: {{result.get('message', 'Unknown error')}}")
                print("\\nPlease contact support for a valid license.")
                input("Press Enter to exit...")
                sys.exit(1)
            
            print("✅ License validated successfully")
            return True
            
    except Exception as e:
        # Allow offline usage with warning (or block - configurable)
        print(f"⚠️  License validation warning: {{e}}")
        print("Running in offline mode...")
        return True

# Validate license first
validate_license()

# ============== ORIGINAL APPLICATION CODE ==============
{original_content}
'''
    
    source_file.write_text(wrapper_code, encoding='utf-8')


def install_project_dependencies(project_dir: Path, dependencies: dict, logs: list):
    """Install dependencies using the workspace venv."""
    if not dependencies.get('has_requirements'):
        return
    
    req_file = project_dir / "requirements.txt"
    if not req_file.exists():
        return
    
    # Use the main venv at project root
    venv_python = Path(__file__).parent.parent / "venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        # Fallback to system python
        venv_python = sys.executable
        logs.append(f"   Warning: Using system Python (venv not found)")
    
    logs.append(f"   Installing to: {venv_python.parent}")
    
    for dep in dependencies['python'][:10]:  # Show first 10
        logs.append(f"     - {dep}")
    
    if len(dependencies['python']) > 10:
        logs.append(f"     ... and {len(dependencies['python']) - 10} more")
    
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(req_file), "--quiet"],
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    if result.returncode != 0:
        logs.append(f"   ⚠️  Warning: Some packages may have failed to install")
        logs.append(f"   {result.stderr[:200]}")
    else:
        logs.append(f"   ✅ Dependencies installed successfully")


def inject_license_into_multi_folder(project_dir: Path, entry_point: str, license_key: str):
    """
    Inject license validation into the entry point of a multi-folder project.
    """
    entry_file = project_dir / entry_point
    
    if not entry_file.exists():
        raise Exception(f"Entry point not found: {entry_point}")
    
    # Read original content
    original_content = entry_file.read_text(encoding='utf-8')
    
    # Copy license_core to project
    license_core_src = Path(__file__).parent.parent / "src" / "license_core"
    license_core_dest = project_dir / "_license_core"
    
    if license_core_dest.exists():
        shutil.rmtree(license_core_dest)
    shutil.copytree(license_core_src, license_core_dest)
    
    # Create wrapper that validates license before running
    wrapper_code = f'''#!/usr/bin/env python3
"""
License-Protected Application
This file has been modified to include license validation.
"""

import sys
import os

# Add license core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '_license_core'))

def validate_license():
    """Validate license before running application"""
    try:
        from checker import LicenseContext
        
        ctx = LicenseContext(
            license_key="{license_key}",
            # Server URL can be overridden via environment variable  
            server_url=os.environ.get("LICENSE_SERVER_URL", "{LICENSE_SERVER_URL}")
        )
        
        if not ctx.is_valid:
            print("\\n❌ LICENSE VALIDATION FAILED")
            print(f"Reason: {{ctx.error_message}}")
            print("\\nPlease contact support for a valid license.")
            input("Press Enter to exit...")
            sys.exit(1)
        
        print("✅ License validated successfully")
        return ctx
    except Exception as e:
        print(f"\\n❌ License validation error: {{e}}")
        input("Press Enter to exit...")
        sys.exit(1)

# Validate license first
license_ctx = validate_license()

# Now run the original application
{original_content}
'''
    
    # Backup original
    backup_file = project_dir / f"_original_{entry_file.name}"
    entry_file.rename(backup_file)
    
    # Write wrapped version
    entry_file.write_text(wrapper_code, encoding='utf-8')



@app.get("/api/v1/compile/{job_id}/status", response_model=CompileJobResponse)
async def get_compile_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get the status of a compilation job."""
    conn = await get_db()
    try:
        job = await conn.fetchrow("""
            SELECT cj.*, p.user_id FROM compile_jobs cj 
            JOIN projects p ON cj.project_id = p.id WHERE cj.id = $1
        """, job_id)
        
        if not job or job['user_id'] != user['id']:
            raise HTTPException(status_code=404, detail="Compile job not found")
        
        # Check cache for live updates
        if job_id in compile_jobs_cache:
            cache_data = compile_jobs_cache[job_id]
            return CompileJobResponse(
                id=job_id,
                project_id=cache_data['project_id'],
                status=cache_data['status'],
                progress=cache_data['progress'],
                output_filename=cache_data.get('output_filename'),
                error_message=cache_data.get('error_message'),
                logs=cache_data['logs'],
                started_at=job['started_at'].isoformat() if job['started_at'] else None,
                completed_at=job['completed_at'].isoformat() if job['completed_at'] else None,
                created_at=job['created_at'].isoformat()
            )
        
        logs = job['logs'] if job['logs'] else []
        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except:
                logs = []
        
        return CompileJobResponse(
            id=str(job['id']),
            project_id=str(job['project_id']),
            status=job['status'],
            progress=job['progress'] or 0,
            output_filename=job['output_filename'],
            error_message=job['error_message'],
            logs=logs,
            started_at=job['started_at'].isoformat() if job['started_at'] else None,
            completed_at=job['completed_at'].isoformat() if job['completed_at'] else None,
            created_at=job['created_at'].isoformat()
        )
    finally:
        await release_db(conn)


@app.get("/api/v1/compile/{job_id}/download")
async def download_compiled_file(job_id: str, user: dict = Depends(get_current_user)):
    """Download the compiled executable."""
    conn = await get_db()
    try:
        # Get job and verify ownership
        job = await conn.fetchrow("""
            SELECT cj.*, p.user_id FROM compile_jobs cj 
            JOIN projects p ON cj.project_id = p.id WHERE cj.id = $1
        """, job_id)
        
        if not job or job['user_id'] != user['id']:
            raise HTTPException(status_code=404, detail="Compile job not found")
        
        if job['status'] != 'completed':
            raise HTTPException(status_code=400, detail="Compilation not completed yet")
        
        if not job['output_filename']:
            raise HTTPException(status_code=404, detail="Output file not found")
        
        # Find the output file
        project_id = job['project_id']
        output_dir = UPLOAD_DIR / project_id / "output"
        output_file = output_dir / job['output_filename']
        
        if not output_file.exists():
            # Try to find any .exe file in the output directory
            exe_files = list(output_dir.glob("*.exe"))
            if exe_files:
                output_file = exe_files[0]
            else:
                raise HTTPException(status_code=404, detail=f"Compiled file not found: {job['output_filename']}")
        
        return FileResponse(
            path=str(output_file),
            filename=job['output_filename'],
            media_type='application/octet-stream'
        )
    finally:
        await release_db(conn)


# =============================================================================
# Dashboard Stats
# =============================================================================

@app.get("/api/v1/stats/dashboard")
@requires_feature('analytics')
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        # Basic counts
        total_projects = await conn.fetchval("SELECT COUNT(*) FROM projects WHERE user_id = $1", user['id'])
        
        license_stats = await conn.fetchrow("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN l.status = 'active' THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN l.status = 'revoked' THEN 1 ELSE 0 END) as revoked
            FROM licenses l JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1
        """, user['id'])
        
        # Note: Active machines count comes from the array below
        
        # Validation stats for last 24 hours
        yesterday = utc_now() - timedelta(days=1)
        val_24h = await conn.fetchrow("""
            SELECT COUNT(*) as total, SUM(CASE WHEN vl.result = 'valid' THEN 1 ELSE 0 END) as successful
            FROM validation_logs vl JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1 AND vl.created_at > $2
        """, user['id'], yesterday)
        
        # Recent Activity - last 10 validation attempts with details
        recent_activity_rows = await conn.fetch("""
            SELECT vl.result, vl.ip_address, vl.created_at, 
                   l.license_key, l.client_name
            FROM validation_logs vl 
            JOIN licenses l ON vl.license_id = l.id
            JOIN projects p ON l.project_id = p.id 
            WHERE p.user_id = $1
            ORDER BY vl.created_at DESC 
            LIMIT 10
        """, user['id'])
        
        recent_activity = [
            {
                "license_key": row['license_key'],
                "result": row['result'],
                "client_name": row['client_name'],
                "ip_address": row['ip_address'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in recent_activity_rows
        ]
        
        # Expiring Soon - licenses expiring within 7 days
        seven_days_from_now = utc_now() + timedelta(days=7)
        expiring_soon_rows = await conn.fetch("""
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
        """, user['id'], seven_days_from_now, utc_now())
        
        expiring_soon = [
            {
                "id": str(row['id']),
                "license_key": row['license_key'],
                "client_name": row['client_name'],
                "expires_at": row['expires_at'].isoformat() if row['expires_at'] else None,
                "project_name": row['project_name']
            }
            for row in expiring_soon_rows
        ]
        
        # Active Machines List - with details for the MachinesList component
        active_machines_rows = await conn.fetch("""
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
        """, user['id'])
        
        active_machines = [
            {
                "hwid": row['hwid'],
                "machine_name": row['machine_name'],
                "license_key": row['license_key'],
                "client_name": row['client_name'],
                "ip_address": row['ip_address'],
                "last_seen": row['last_seen_at'].isoformat() if row['last_seen_at'] else None
            }
            for row in active_machines_rows
        ]
        
        # Validation History - daily counts for the last 7 days for the chart
        seven_days_ago = utc_now() - timedelta(days=7)
        history_rows = await conn.fetch("""
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
        """, user['id'], seven_days_ago)
        
        validation_history = [
            {
                "date": row['date'].isoformat() if row['date'] else None,
                "total": row['total'] or 0,
                "successful": row['successful'] or 0,
                "failed": row['failed'] or 0
            }
            for row in history_rows
        ]
        
        return {
            "projects": total_projects or 0,
            "licenses": {
                "total": license_stats['total'] or 0, 
                "active": license_stats['active'] or 0, 
                "revoked": license_stats['revoked'] or 0
            },
            "validations": {
                "last_24h": {
                    "total": val_24h['total'] or 0, 
                    "successful": val_24h['successful'] or 0
                },
                "history": validation_history
            },
            "active_machines": active_machines,
            "recent_activity": recent_activity,
            "expiring_soon": expiring_soon
        }
    finally:
        await release_db(conn)


# =============================================================================
# Mission Control Live Map - Analytics
# =============================================================================

@app.get("/api/v1/analytics/map-data")
async def get_map_data(user: dict = Depends(get_current_user)):
    """
    Get geolocation data for the Mission Control Live Map.
    Returns the latest validation location for each unique HWID
    for the user's projects in the last 24 hours.
    """
    conn = await get_db()
    try:
        yesterday = utc_now() - timedelta(days=1)
        
        # Get latest validation with geo data per unique HWID
        # Group by location and count unique HWIDs at each location
        rows = await conn.fetch("""
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
        """, user['id'], yesterday)
        
        return [
            {
                "lat": float(row['lat']),
                "lng": float(row['lng']),
                "city": row['city'] or "Unknown",
                "country": row['country'] or "??",
                "count": row['count']
            }
            for row in rows
        ]
    finally:
        await release_db(conn)




# =============================================================================
# CLI Tool Endpoints (for local compilation)
# =============================================================================

CLI_VERSION = "1.0.0"
CLI_DOWNLOAD_URLS = {
    "windows": os.getenv("CLI_DOWNLOAD_WINDOWS", ""),
    "macos": os.getenv("CLI_DOWNLOAD_MACOS", ""),
    "linux": os.getenv("CLI_DOWNLOAD_LINUX", "")
}

@app.get("/api/v1/cli/version")
async def get_cli_version():
    """Get the latest CLI tool version and download URLs."""
    return {
        "version": CLI_VERSION,
        "downloads": {
            "windows": CLI_DOWNLOAD_URLS.get("windows") or None,
            "macos": CLI_DOWNLOAD_URLS.get("macos") or None,
            "linux": CLI_DOWNLOAD_URLS.get("linux") or None
        },
        "changelog": "Initial release with local Nuitka compilation support."
    }


@app.get("/api/v1/projects/{project_id}/compile-config")
async def get_compile_config(
    project_id: str,
    license_key: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get compilation configuration for the CLI tool.
    Returns all settings needed to compile the project locally.
    """
    conn = await get_db()
    try:
        # Verify ownership
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            project_id, user['id']
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        settings = json.loads(project['settings']) if project['settings'] else {}
        
        # Get project files info
        files = await conn.fetch(
            "SELECT original_filename, filename FROM project_files WHERE project_id = $1",
            project_id
        )
        
        # Determine entry file
        entry_file = settings.get('entry_file', 'main.py')
        file_list = [f['original_filename'] for f in files]
        if entry_file not in file_list and file_list:
            entry_file = file_list[0]
        
        # Get file tree for multi-folder projects
        file_tree = settings.get('file_tree', {})
        folders = file_tree.get('folders', [])
        
        # Build Nuitka options
        nuitka_options = {
            "standalone": True,
            "onefile": True,
            "remove_output": True,
            "assume_yes_for_downloads": True
        }
        
        # Add include packages for multi-folder projects
        if folders:
            nuitka_options["include_packages"] = [f for f in folders if f and f != "__pycache__"]
        
        # Server URL for license validation (use production URL if available)
        server_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        
        return {
            "project_id": project_id,
            "project_name": project['name'],
            "entry_file": entry_file,
            "output_name": settings.get('output_name', project['name'].replace(' ', '_').lower()),
            "license_key": license_key,
            "server_url": server_url,
            "nuitka_options": nuitka_options,
            "files": file_list,
            "is_multi_folder": settings.get('is_multi_folder', False),
            "folders": folders
        }
    finally:
        await release_db(conn)


@app.get("/api/v1/projects/{project_id}/bundle")
async def download_project_bundle(
    project_id: str,
    license_key: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Download all project files as a ZIP bundle for local compilation.
    Includes source files and compilation configuration.
    """
    conn = await get_db()
    try:
        # Verify ownership
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            project_id, user['id']
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        settings = json.loads(project['settings']) if project['settings'] else {}
        
        # Check if project has source directory (multi-folder)
        source_dir = UPLOAD_DIR / project_id / "source"
        if source_dir.exists():
            # Multi-folder project - zip the entire source directory
            zip_path = UPLOAD_DIR / project_id / "bundle.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file() and '__pycache__' not in str(file_path):
                        arcname = file_path.relative_to(source_dir)
                        zf.write(file_path, arcname)
                
                # Add compile config
                config = {
                    "project_id": project_id,
                    "project_name": project['name'],
                    "entry_file": settings.get('entry_file', settings.get('file_tree', {}).get('entry_point', 'main.py')),
                    "output_name": settings.get('output_name', project['name'].replace(' ', '_').lower()),
                    "license_key": license_key,
                    "server_url": os.getenv("PUBLIC_API_URL", "http://localhost:8000"),
                    "is_multi_folder": True,
                    "folders": settings.get('file_tree', {}).get('folders', [])
                }
                zf.writestr("_compile_config.json", json.dumps(config, indent=2))
            
            return FileResponse(
                path=str(zip_path),
                filename=f"{project['name']}_bundle.zip",
                media_type='application/zip'
            )
        
        else:
            # Single/flat file project - get files from project_files table
            files = await conn.fetch(
                "SELECT * FROM project_files WHERE project_id = $1",
                project_id
            )
            
            if not files:
                raise HTTPException(status_code=404, detail="No files found in project")
            
            # Create zip
            zip_path = UPLOAD_DIR / project_id / "bundle.zip"
            (UPLOAD_DIR / project_id).mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    file_path = Path(f['file_path'])
                    if file_path.exists():
                        zf.write(file_path, f['original_filename'])
                
                # Add compile config
                entry_file = settings.get('entry_file', files[0]['original_filename'] if files else 'main.py')
                config = {
                    "project_id": project_id,
                    "project_name": project['name'],
                    "entry_file": entry_file,
                    "output_name": settings.get('output_name', project['name'].replace(' ', '_').lower()),
                    "license_key": license_key,
                    "server_url": os.getenv("PUBLIC_API_URL", "http://localhost:8000"),
                    "is_multi_folder": False,
                    "folders": []
                }
                zf.writestr("_compile_config.json", json.dumps(config, indent=2))
            
            return FileResponse(
                path=str(zip_path),
                filename=f"{project['name']}_bundle.zip",
                media_type='application/zip'
            )
    finally:
        await release_db(conn)


@app.get("/api/v1/projects/{project_id}/build-package")
async def download_build_package(
    project_id: str,
    license_key: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Download a complete self-contained build package as ZIP.
    Includes: project source files, CLI tool, config, and build script.
    User just needs to extract and run build.bat
    """
    conn = await get_db()
    try:
        # Verify ownership
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            project_id, user['id']
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        settings = json.loads(project['settings']) if project['settings'] else {}
        project_name_safe = project['name'].replace(' ', '_').lower()
        
        # Create temp directory for package
        package_dir = UPLOAD_DIR / project_id / "build_package"
        package_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = UPLOAD_DIR / project_id / f"build_{project_name_safe}.zip"
        
        # Get entry file
        source_dir = UPLOAD_DIR / project_id / "source"
        if source_dir.exists():
            entry_file = settings.get('entry_file', settings.get('file_tree', {}).get('entry_point', 'main.py'))
        else:
            files = await conn.fetch("SELECT * FROM project_files WHERE project_id = $1", project_id)
            entry_file = settings.get('entry_file', files[0]['original_filename'] if files else 'main.py')
        
        
        server_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        
        # Ensure user has an API key (generate if missing for legacy users)
        api_key = user.get('api_key')
        if not api_key:
            api_key = generate_api_key()
            await conn.execute(
                "UPDATE users SET api_key = $1 WHERE id = $2",
                api_key, user['id']
            )
        
        # Generate build.bat content
        build_bat = f'''@echo off
echo.
echo ==========================================================
echo    License Wrapper - Build Script
echo    Project: {project['name'][:50]}
echo ==========================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+ first.
    echo        Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install nuitka requests -q
if errorlevel 1 (
    echo ERROR: Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)

echo [2/3] Starting compilation with Nuitka...
echo        This may take 2-10 minutes on first run.
echo.

cd /d "%~dp0"
python lw_compiler.py build {project_id}{f' --license {license_key}' if license_key else ''}

echo.
echo ==========================================================
echo    Build complete! Check the 'output' folder.
echo ==========================================================
echo.
pause
'''

        # Generate config.json for CLI
        config_json = {
            "api_key": api_key,  # Now guaranteed to exist
            "api_url": f"{server_url}/api/v1",
            "email": user.get('email', ''),
            "user_name": user.get('name', ''),
            "project_id": project_id,
            "license_key": license_key or ""
        }
        
        # Generate README
        readme_txt = f'''License Wrapper - Build Package
================================

Project: {project['name']}
{'License: ' + license_key if license_key else 'License: None (Demo Mode)'}

HOW TO USE:
-----------
1. Extract this entire folder to any location
2. Double-click build.bat
3. Wait for compilation to finish (2-10 minutes)
4. Your .exe will be in the 'output' folder

REQUIREMENTS:
-------------
- Python 3.8 or higher (https://www.python.org/downloads/)
- Windows 10/11
- Internet connection (for first-time setup)

TROUBLESHOOTING:
----------------
- If "Python not found": Install Python and check "Add to PATH" during install
- If compilation fails: Make sure you have enough disk space (~500MB)

Generated by License Wrapper
'''

        # Read CLI tool
        cli_path = Path(__file__).parent.parent / "cli" / "lw_compiler.py"
        if not cli_path.exists():
            cli_path = Path(__file__).parent / ".." / "cli" / "lw_compiler.py"
        if not cli_path.exists():
            raise HTTPException(status_code=500, detail="CLI tool not found on server")
        
        cli_content = cli_path.read_text(encoding='utf-8')
        
        # Create ZIP package
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add build script
            zf.writestr("build.bat", build_bat)
            
            # Add CLI tool
            zf.writestr("lw_compiler.py", cli_content)
            
            # Add config
            zf.writestr("config.json", json.dumps(config_json, indent=2))
            
            # Add README
            zf.writestr("README.txt", readme_txt)
            
            # Add project source files
            if source_dir.exists():
                # Multi-folder project
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file() and '__pycache__' not in str(file_path):
                        arcname = "source/" + str(file_path.relative_to(source_dir))
                        zf.write(file_path, arcname)
            else:
                # Single file project
                files = await conn.fetch("SELECT * FROM project_files WHERE project_id = $1", project_id)
                for f in files:
                    file_path = Path(f['file_path'])
                    if file_path.exists():
                        zf.write(file_path, "source/" + f['original_filename'])
            
            # Add compile config for CLI
            compile_config = {
                "project_id": project_id,
                "project_name": project['name'],
                "entry_file": entry_file,
                "output_name": project_name_safe,
                "license_key": license_key,
                "server_url": server_url,
                "is_multi_folder": source_dir.exists(),
                "folders": settings.get('file_tree', {}).get('folders', [])
            }
            zf.writestr("source/_compile_config.json", json.dumps(compile_config, indent=2))
        
        return FileResponse(
            path=str(zip_path),
            filename=f"build_{project_name_safe}.zip",
            media_type='application/zip'
        )
    finally:
        await release_db(conn)


# =============================================================================
# Utility Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {"name": "License-Wrapper API", "version": "1.0.0", "mode": f"{ENVIRONMENT} (PostgreSQL)",
            "docs": "/docs", "health": "/health"}

@app.get("/health")
async def health():
    db_ok = False
    try:
        conn = await get_db()
        await conn.fetchval("SELECT 1")
        await release_db(conn)
        db_ok = True
    except:
        pass
    
    return {"status": "healthy" if db_ok else "degraded", "database": "connected" if db_ok else "error",
            "storage": "cloud" if storage_service.is_cloud_enabled() else "local",
            "email": "configured" if email_service.is_configured() else "disabled"}


# =============================================================================
# Admin Endpoints (Admin only)
# =============================================================================

@app.get("/api/v1/admin/stats")
async def get_admin_stats(user: dict = Depends(get_current_admin_user)):
    """Get system-wide statistics (admin only)."""
    conn = await get_db()
    try:
        # Get counts
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_projects = await conn.fetchval("SELECT COUNT(*) FROM projects")
        total_licenses = await conn.fetchval("SELECT COUNT(*) FROM licenses")
        active_licenses = await conn.fetchval("SELECT COUNT(*) FROM licenses WHERE status = 'active'")
        
        # Validations today
        validations_today = await conn.fetchval("""
            SELECT COUNT(*) FROM validation_logs 
            WHERE created_at >= CURRENT_DATE
        """)
        
        # Validations this week
        validations_week = await conn.fetchval("""
            SELECT COUNT(*) FROM validation_logs 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        """)
        
        # Total compile jobs
        total_compiles = await conn.fetchval("SELECT COUNT(*) FROM compile_jobs")
        successful_compiles = await conn.fetchval("SELECT COUNT(*) FROM compile_jobs WHERE status = 'completed'")
        
        return {
            "total_users": total_users or 0,
            "total_projects": total_projects or 0,
            "total_licenses": total_licenses or 0,
            "active_licenses": active_licenses or 0,
            "validations_today": validations_today or 0,
            "validations_week": validations_week or 0,
            "total_compiles": total_compiles or 0,
            "successful_compiles": successful_compiles or 0
        }
    finally:
        await release_db(conn)


@app.get("/api/v1/admin/users")
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
                "license_count": r["license_count"] or 0
            }
            for r in rows
        ]
    finally:
        await release_db(conn)


@app.get("/api/v1/admin/analytics")
async def get_admin_analytics(days: int = 30, user: dict = Depends(get_current_admin_user)):
    """Get analytics data for charts (admin only)."""
    conn = await get_db()
    try:
        # Validations per day
        validation_stats = await conn.fetch("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM validation_logs
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            GROUP BY DATE(created_at)
            ORDER BY date
        """, days)
        
        # New users per day
        user_stats = await conn.fetch("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            GROUP BY DATE(created_at)
            ORDER BY date
        """, days)
        
        # Compile jobs per day
        compile_stats = await conn.fetch("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM compile_jobs
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            GROUP BY DATE(created_at)
            ORDER BY date
        """, days)
        
        # Recent webhook deliveries
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
                {"date": r["date"].isoformat(), "count": r["count"]}
                for r in user_stats
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
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None
                }
                for r in recent_webhooks
            ]
        }
    finally:
        await release_db(conn)


# =============================================================================
# Node.js Compilation Helper
# =============================================================================

async def compile_nodejs_project(job_id: str, project_id: str, data: CompileJobRequest, job_cache: dict):
    """
    Compile a Node.js project.
    """
    print(f"[DEBUG] Starting Node.js compilation for project {project_id}")
    job_cache[job_id]['logs'].append('📦 Node.js project detected')
    
    # Get source directory
    upload_path = UPLOAD_DIR / project_id
    source_dir = upload_path / "source"
    
    # Determine source directory
    if not source_dir.exists():
        source_dir = upload_path
        job_cache[job_id]['logs'].append('   Single file mode')
    else:
        job_cache[job_id]['logs'].append('   Multi-file mode')
        
    entry_file = data.entry_file
    if not entry_file:
        for candidate in ['index.js', 'app.js', 'main.js', 'server.js']:
            if (source_dir / candidate).exists():
                entry_file = candidate
                break
    
    if not entry_file:
        raise Exception("Entry file not specified and could not be auto-detected")
    
    # Validate entry file exists
    entry_path = source_dir / entry_file
    if not entry_path.exists():
        raise Exception(f"Entry file not found: {entry_path}")
        
    job_cache[job_id]['logs'].append(f"   Entry: {entry_file}")
    
    # Prepare output dir
    output_dir = upload_path / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Initialize compiler
    node_modules = Path(__file__).parent / "node_modules"
    compiler = NodeJSCompiler(node_modules_path=node_modules)
    
    async def log_callback(msg):
        job_cache[job_id]['logs'].append(msg)
    
    # Run compilation
    output_name = data.output_name or "app"
    license_key = data.license_key or "DEMO"
    api_url = LICENSE_SERVER_URL + "/api/v1/license/validate"
    options = data.options or {}
    
    try:
        final_exe = await compiler.compile(
            source_dir=source_dir,
            entry_file=entry_file,
            output_dir=output_dir,
            output_name=output_name,
            license_key=license_key,
            api_url=api_url,
            options=options,
            log_callback=log_callback
        )
        
        job_cache[job_id]['progress'] = 100
        job_cache[job_id]['output_filename'] = final_exe.name
        
    except Exception as e:
        raise e


# =============================================================================
# Build Orchestrator Endpoints (Professional Installer System)
# =============================================================================

from compilers import check_build_prerequisites, get_build_orchestrator, BuildConfig

@app.get("/api/v1/build/prerequisites")
async def get_build_prerequisites():
    """
    Check if all build prerequisites (NSIS, pkg, Nuitka) are available.
    Used by desktop app to show prerequisite status.
    """
    return check_build_prerequisites()


class InstallerBuildRequest(BaseModel):
    """Request for building an installer package"""
    project_name: str = Field(..., description="Name of the application")
    project_version: str = Field("1.0.0", description="Version string (e.g., 1.0.0)")
    publisher: str = Field("", description="Publisher name for installer")
    
    source_dir: str = Field(..., description="Path to project source directory")
    entry_file: str = Field(..., description="Entry file (main.py or index.js)")
    language: str = Field("python", description="Language: 'python' or 'nodejs'")
    
    license_key: str = Field("GENERIC_BUILD", description="License key or GENERIC_BUILD")
    api_url: str = Field("", description="License validation API URL")
    license_mode: str = Field("generic", description="'fixed', 'generic', or 'demo'")
    
    distribution_type: str = Field("installer", description="'portable' or 'installer'")
    create_desktop_shortcut: bool = Field(True, description="Create desktop shortcut")
    create_start_menu: bool = Field(True, description="Create Start Menu entry")
    
    output_dir: str = Field(..., description="Output directory for final build")


@app.post("/api/v1/build/installer")
async def build_installer(data: InstallerBuildRequest):
    """
    Build a professional Windows installer for Python or Node.js projects.
    Uses the build orchestrator for multi-step compilation:
    1. Compile to standalone exe (Nuitka/yao-pkg)
    2. Wrap in NSIS installer if requested
    """
    from pathlib import Path
    import asyncio
    
    orchestrator = get_build_orchestrator()
    
    # Create build config
    config = BuildConfig(
        project_name=data.project_name,
        project_version=data.project_version,
        publisher=data.publisher or "Unknown Publisher",
        source_dir=Path(data.source_dir),
        entry_file=data.entry_file,
        language=data.language,
        license_key=data.license_key,
        api_url=data.api_url or LICENSE_SERVER_URL,
        license_mode=data.license_mode,
        distribution_type=data.distribution_type,
        create_desktop_shortcut=data.create_desktop_shortcut,
        create_start_menu=data.create_start_menu,
        output_dir=Path(data.output_dir),
    )
    
    # Log callback for progress
    logs = []
    async def log_callback(msg):
        logs.append(msg)
        print(f"[Build] {msg}")
    
    try:
        output_path = await orchestrator.build(config, log_callback)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "output_name": output_path.name,
            "distribution_type": data.distribution_type,
            "logs": logs
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "logs": logs
        }

if __name__ == "__main__":

    import uvicorn
    print(f"\n{'='*60}\n  License-Wrapper API Server ({ENVIRONMENT})\n{'='*60}")
    print(f"  Database: PostgreSQL")
    print(f"  Storage: {'Cloudflare R2' if storage_service.is_cloud_enabled() else 'Local'}")
    print(f"  Email: {'Enabled' if email_service.is_configured() else 'Disabled'}")
    print(f"  API Docs: http://localhost:8000/docs\n{'='*60}\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
