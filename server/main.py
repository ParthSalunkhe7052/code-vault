"""
License Server API - Production Version (PostgreSQL + R2)
FastAPI-based license validation and management server.

NOTE: This file has been refactored. Core functionality is now in:
- config.py - Configuration settings
- database.py - Database connection pool
- models.py - Pydantic models
- utils.py - Utility functions
- routes/ - API route modules
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import re
import sys
from pathlib import Path

# Add project root and scripts directory to sys.path
project_root = Path(__file__).parent.parent
scripts_dir = project_root / "scripts"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# =============================================================================
# Logging Filter to reduce /status endpoint spam
# =============================================================================
class BuildStatusEndpointFilter(logging.Filter):
    """Filter out noisy /status polling requests from uvicorn access logs."""

    _pattern = re.compile(r"GET /api/v1/build/installer/[a-f0-9]+/status")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        # Return False to DROP the log, True to KEEP it
        if self._pattern.search(message):
            return False
        return True


# Apply filter to uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(BuildStatusEndpointFilter())


# =============================================================================
# Security Headers Middleware
# =============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # HSTS - Force HTTPS (only in production)
        if ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Remove server fingerprinting headers
        try:
            del response.headers["Server"]
        except KeyError:
            pass
        try:
            del response.headers["X-Powered-By"]
        except KeyError:
            pass

        return response


# Import from refactored modules
from config import (
    CORS_ORIGINS,
    CORS_ALLOW_ALL,
    ENVIRONMENT,
    REDIS_URL,
    ENABLE_PUBLIC_DOCS,
)
from startup_checks import run_startup_checks
from database import lifespan
from middleware.rate_limiter import init_rate_limiter, close_rate_limiter

# Import background tasks from routers
from routes.build_routes import cleanup_compile_cache


# =============================================================================
# Subscription Expiry Background Job
# =============================================================================


async def check_expired_subscriptions():
    """Background task that runs every hour to check and expire subscriptions.

    Queries subscriptions WHERE status='canceled' AND current_period_end < NOW(),
    then for each: UPDATE users SET plan='free', UPDATE subscriptions SET status='expired'
    """
    from database import get_db, release_db
    import asyncio

    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour

            conn = await get_db()
            try:
                # Find expired subscriptions
                expired_subs = await conn.fetch(
                    """
                    SELECT id, user_id 
                    FROM subscriptions 
                    WHERE status = 'canceled' 
                    AND current_period_end < NOW()
                    """
                )

                if expired_subs:
                    logging.getLogger(__name__).info(
                        f"[Subscription Expiry] Found {len(expired_subs)} expired subscription(s)"
                    )

                    for sub in expired_subs:
                        user_id = sub["user_id"]
                        sub_id = sub["id"]

                        # Downgrade user to free
                        await conn.execute(
                            "UPDATE users SET plan = 'free' WHERE id = $1", user_id
                        )

                        # Mark subscription as expired
                        await conn.execute(
                            """
                            UPDATE subscriptions 
                            SET status = 'expired', updated_at = NOW() 
                            WHERE id = $1
                            """,
                            sub_id,
                        )

                        logging.getLogger(__name__).info(
                            f"[Subscription Expiry] User {user_id} downgraded to free, subscription {sub_id} marked as expired"
                        )
            except Exception as e:
                logging.getLogger(__name__).error(
                    f"[Subscription Expiry] Error checking expired subscriptions: {e}"
                )
            finally:
                await release_db(conn)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.getLogger(__name__).error(
                f"[Subscription Expiry] Outer loop error: {e}"
            )


async def check_expiring_licenses():
    """Background task that runs daily to check and notify about expiring licenses.

    Notifies license holders when their licenses are expiring in 7, 3, and 1 days.
    """
    from database import get_db, release_db
    from email_service import notify_license_expiring
    import asyncio
    from datetime import timedelta

    while True:
        try:
            await asyncio.sleep(86400)  # Run once per day

            conn = await get_db()
            try:
                # Check for licenses expiring in 7 days
                expiring_7_days = await conn.fetch(
                    """
                    SELECT l.id, l.license_key, l.client_name, l.client_email, l.expires_at, p.name as project_name, p.user_id
                    FROM licenses l
                    JOIN projects p ON l.project_id = p.id
                    WHERE l.status = 'active'
                      AND l.expires_at IS NOT NULL
                      AND l.expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'
                      AND l.client_email IS NOT NULL
                    """
                )

                # Check for licenses expiring in 3 days
                expiring_3_days = await conn.fetch(
                    """
                    SELECT l.id, l.license_key, l.client_name, l.client_email, l.expires_at, p.name as project_name, p.user_id
                    FROM licenses l
                    JOIN projects p ON l.project_id = p.id
                    WHERE l.status = 'active'
                      AND l.expires_at IS NOT NULL
                      AND l.expires_at BETWEEN NOW() AND NOW() + INTERVAL '3 days'
                      AND l.client_email IS NOT NULL
                    """
                )

                # Check for licenses expiring in 1 day
                expiring_1_day = await conn.fetch(
                    """
                    SELECT l.id, l.license_key, l.client_name, l.client_email, l.expires_at, p.name as project_name, p.user_id
                    FROM licenses l
                    JOIN projects p ON l.project_id = p.id
                    WHERE l.status = 'active'
                      AND l.expires_at IS NOT NULL
                      AND l.expires_at BETWEEN NOW() AND NOW() + INTERVAL '1 day'
                      AND l.client_email IS NOT NULL
                    """
                )

                # Send notifications (7 days)
                for lic in expiring_7_days:
                    try:
                        await notify_license_expiring(
                            lic["client_name"] or "Customer",
                            lic["client_email"],
                            lic["license_key"],
                            lic["project_name"],
                            lic["expires_at"],
                            7,
                        )
                    except Exception as e:
                        logging.getLogger(__name__).warning(
                            f"[License Expiry] Failed to send 7-day notice for {lic['license_key']}: {e}"
                        )

                # Send notifications (3 days)
                for lic in expiring_3_days:
                    try:
                        await notify_license_expiring(
                            lic["client_name"] or "Customer",
                            lic["client_email"],
                            lic["license_key"],
                            lic["project_name"],
                            lic["expires_at"],
                            3,
                        )
                    except Exception as e:
                        logging.getLogger(__name__).warning(
                            f"[License Expiry] Failed to send 3-day notice for {lic['license_key']}: {e}"
                        )

                # Send notifications (1 day)
                for lic in expiring_1_day:
                    try:
                        await notify_license_expiring(
                            lic["client_name"] or "Customer",
                            lic["client_email"],
                            lic["license_key"],
                            lic["project_name"],
                            lic["expires_at"],
                            1,
                        )
                    except Exception as e:
                        logging.getLogger(__name__).warning(
                            f"[License Expiry] Failed to send 1-day notice for {lic['license_key']}: {e}"
                        )

                total_notifications = (
                    len(expiring_7_days) + len(expiring_3_days) + len(expiring_1_day)
                )
                if total_notifications > 0:
                    logging.getLogger(__name__).info(
                        f"[License Expiry] Sent notifications for {total_notifications} expiring license(s)"
                    )

            except Exception as e:
                logging.getLogger(__name__).error(
                    f"[License Expiry] Error checking expiring licenses: {e}"
                )
            finally:
                await release_db(conn)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.getLogger(__name__).error(f"[License Expiry] Outer loop error: {e}")


# =============================================================================
# FastAPI App Initialization
# =============================================================================


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    try:
        run_startup_checks()
    except Exception as e:
        if ENVIRONMENT == "production":
            raise e

    # Initialize rate limiter with Redis
    if REDIS_URL:
        await init_rate_limiter(REDIS_URL)
        logging.getLogger(__name__).info(
            "[Startup] Rate limiter initialized with Redis"
        )
    else:
        logging.getLogger(__name__).warning(
            "[Startup] REDIS_URL not configured - rate limiting disabled"
        )

    async with lifespan(app):
        import asyncio
        from routes.cloud_build_routes import scheduled_cloud_build_cleanup
        from webhook_retry import start_retry_processor
        from monitoring import start_health_monitoring

        _background_tasks = []
        _background_tasks.append(asyncio.create_task(cleanup_compile_cache()))
        _background_tasks.append(asyncio.create_task(scheduled_cloud_build_cleanup()))
        _background_tasks.append(
            asyncio.create_task(start_retry_processor(interval_seconds=60))
        )
        _background_tasks.append(
            asyncio.create_task(start_health_monitoring(interval_seconds=60))
        )
        _background_tasks.append(asyncio.create_task(check_expired_subscriptions()))
        _background_tasks.append(asyncio.create_task(check_expiring_licenses()))
        logging.getLogger(__name__).info("[Startup] Background cleanup tasks started")
        logging.getLogger(__name__).info("[Startup] Webhook retry processor started")
        logging.getLogger(__name__).info("[Startup] Health monitoring started")
        logging.getLogger(__name__).info(
            "[Startup] Subscription expiry checker started"
        )
        logging.getLogger(__name__).info(
            "[Startup] License expiry notification checker started"
        )
        yield

        # Cancel background tasks on shutdown
        for task in _background_tasks:
            task.cancel()

    # Cleanup on shutdown
    await close_rate_limiter()


app = FastAPI(
    title="CodeVault API",
    description="Enterprise-grade Licensing-as-a-Service (LaaS) API. Supports Ed25519 asymmetric signing, binary integrity checking, floating licenses, and usage-based billing.",
    version="1.1.0",
    lifespan=app_lifespan,
    docs_url="/docs" if ENABLE_PUBLIC_DOCS else None,
    redoc_url="/redoc" if ENABLE_PUBLIC_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_PUBLIC_DOCS else None,
)

# =============================================================================
# Security Middleware (Order matters!)
# =============================================================================

# 1. Security Headers - Add first to protect all responses
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS middleware - SECURITY FIX: Don't allow wildcard with credentials
# When allow_origins is ["*"], credentials must be False per CORS spec
if CORS_ALLOW_ALL:
    # Development mode: Allow all origins but NO credentials
    # This prevents the browser from sending cookies/auth headers cross-origin
    if ENVIRONMENT == "production":
        logging.getLogger(__name__).warning(
            "[CORS] CORS_ALLOW_ALL is enabled in production - this is NOT recommended!"
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # SECURITY: Must be False when origins is wildcard
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production mode: Strict origin list with credentials allowed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# =============================================================================
# Include Route Modules
# =============================================================================

from routes.polar_routes import router as polar_router
from routes.auth_routes import router as auth_router
from routes.webhook_routes import router as webhook_router
from routes.license_routes import router as license_router
from routes.admin_routes import router as admin_router
from routes.analytics_routes import router as analytics_router
from routes.project_routes import router as project_router
from routes.build_routes import router as build_router
from routes.cloud_build_routes import router as cloud_build_router
from routes.system_routes import router as system_router

app.include_router(polar_router)
app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(license_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(project_router)
app.include_router(build_router)
app.include_router(cloud_build_router)
app.include_router(system_router)

if __name__ == "__main__":
    import uvicorn
    from email_service import email_service
    from storage_service import storage_service

    separator = "=" * 60
    print(f"\n{separator}\n  License-Wrapper API Server ({ENVIRONMENT})\n{separator}")
    print("  Database: PostgreSQL")
    storage_type = "Cloudflare R2" if storage_service.is_cloud_enabled() else "Local"
    print(f"  Storage: {storage_type}")
    email_status = "Enabled" if email_service.is_configured() else "Disabled"
    print(f"  Email: {email_status}")
    print(f"  API Docs: http://localhost:8000/docs\n{separator}\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
