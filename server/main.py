"""
License Server API - Production Version (PostgreSQL + R2)
FastAPI-based license validation and management server.
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

# Security and Logging Helpers
class BuildStatusEndpointFilter(logging.Filter):
    _pattern = re.compile(r"GET /api/v1/build/installer/[a-f0-9]+/status")
    def filter(self, record: logging.LogRecord) -> bool:
        return not self._pattern.search(record.getMessage())

logging.getLogger("uvicorn.access").addFilter(BuildStatusEndpointFilter())

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=(), usb=(), magnetometer=(), gyroscope=()"
        return response

from config import CORS_ORIGINS, CORS_ALLOW_ALL, ENVIRONMENT, REDIS_URL, ENABLE_PUBLIC_DOCS
from startup_checks import run_startup_checks
from database import lifespan
from middleware.rate_limiter import init_rate_limiter, close_rate_limiter
from tasks.scheduler import start_background_tasks
from routes.build_routes import cleanup_compile_cache

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    if ENVIRONMENT == "production":
        run_startup_checks()
    if REDIS_URL:
        await init_rate_limiter(REDIS_URL)
    
    async with lifespan(app):
        import asyncio
        from webhook_retry import start_retry_processor
        from monitoring import start_health_monitoring
        
        # Start modularized tasks
        await start_background_tasks()
        
        # Start other background tasks
        asyncio.create_task(cleanup_compile_cache())
        asyncio.create_task(start_retry_processor(interval_seconds=60))
        asyncio.create_task(start_health_monitoring(interval_seconds=60))
        
        yield

    await close_rate_limiter()

app = FastAPI(
    title="CodeVault API",
    description="Enterprise-grade Licensing-as-a-Service (LaaS) API.",
    version="1.1.0",
    lifespan=app_lifespan,
    docs_url="/docs" if ENABLE_PUBLIC_DOCS else None,
)

app.add_middleware(SecurityHeadersMiddleware)
if CORS_ALLOW_ALL:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
else:
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Requested-With"])

# Route Inclusions
from routes.polar_routes import router as polar_router
from routes.auth_routes import router as auth_router
from routes.webhook_routes import router as webhook_router
from routes.license_routes import router as license_router
from routes.admin_routes import router as admin_router
from routes.analytics_routes import router as analytics_router
from routes.project_routes import router as project_router
from routes.build_routes import router as build_router
from routes.cloud_build import router as cloud_build_router
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

if __name__ == \"__main__\":
    import uvicorn
    uvicorn.run(app, host=\"0.0.0.0\", port=8000)
