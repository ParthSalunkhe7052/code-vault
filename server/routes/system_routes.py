import shutil
from fastapi import APIRouter
from config import PRICING_CONFIG, ENVIRONMENT
from database import get_db, release_db
from storage_service import storage_service

router = APIRouter(tags=["system"])

@router.get("/api/health")
async def health_check():
    """Health check endpoint for Tauri desktop app."""
    nodejs_available = shutil.which("pkg") is not None
    nuitka_available = shutil.which("nuitka") is not None

    return {
        "status": "healthy",
        "version": "1.0.0",
        "compilers": {"nodejs": nodejs_available, "python": nuitka_available},
    }

@router.get("/api/v1/config/pricing")
async def get_pricing_config():
    """Get pricing configuration for the frontend."""
    return PRICING_CONFIG

@router.get("/")
async def root():
    return {
        "name": "License-Wrapper API",
        "version": "1.0.0",
        "mode": f"{ENVIRONMENT} (PostgreSQL)",
        "docs": "/docs",
        "health": "/health",
    }

@router.get("/health")
@router.get("/api/v1/health")
async def health():
    db_ok = False
    try:
        conn = await get_db()
        await conn.fetchval("SELECT 1")
        await release_db(conn)
        db_ok = True
    except Exception:
        pass

    from email_service import email_service

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "storage": "cloud" if storage_service.is_cloud_enabled() else "local",
        "email": "configured" if email_service.is_configured() else "disabled",
    }
