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

import os
import time
import json
import zipfile
import shutil
from typing import Optional, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field
import secrets
import logging
import re


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

# Import from refactored modules
from config import (
    CORS_ORIGINS,
    CORS_ALLOW_ALL,
    ENVIRONMENT,
    LICENSE_SERVER_URL,
    PRICING_CONFIG,
)
from startup_checks import run_startup_checks
from database import get_db, release_db, lifespan
from utils import (
    utc_now,
    get_current_user,
    safe_join,
    validate_project_id,
    SecurityError,
)

# Import storage and email services
from storage_service import storage_service, upload_project_file, LOCAL_UPLOAD_DIR
from models import (
    CompileJobRequest,
    CompileJobResponse,
    ProjectCreateRequest,
    ProjectConfigRequest,
)

# Local upload directory
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


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

    async with lifespan(app):
        import asyncio

        asyncio.create_task(cleanup_compile_cache())
        yield


app = FastAPI(
    title="CodeVault API",
    description="API for CodeVault License Management SaaS",
    version="1.0.0",
    lifespan=app_lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ALLOW_ALL else CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Include Route Modules
# =============================================================================

from routes.stripe_routes import router as stripe_router
from routes.auth_routes import router as auth_router
from routes.webhook_routes import router as webhook_router
from routes.license_routes import router as license_router
from routes.admin_routes import router as admin_router
from routes.analytics_routes import router as analytics_router

app.include_router(stripe_router)
app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(license_router)
app.include_router(admin_router)
app.include_router(analytics_router)


# =============================================================================
# Health Check & Config Endpoints
# =============================================================================


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Tauri desktop app."""
    nodejs_available = shutil.which("pkg") is not None
    nuitka_available = shutil.which("nuitka") or shutil.which("python") is not None

    return {
        "status": "healthy",
        "version": "1.0.0",
        "compilers": {"nodejs": nodejs_available, "python": nuitka_available},
    }


@app.get("/api/v1/config/pricing")
async def get_pricing_config():
    """Get pricing configuration for the frontend."""
    return PRICING_CONFIG


@app.get("/")
async def root():
    return {
        "name": "License-Wrapper API",
        "version": "1.0.0",
        "mode": f"{ENVIRONMENT} (PostgreSQL)",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
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


# =============================================================================
# Compilation Cache & Background Tasks
# =============================================================================

compile_jobs_cache = {}


async def cleanup_compile_cache():
    """Background task to remove completed jobs from cache after 1 hour."""
    import asyncio

    while True:
        await asyncio.sleep(3600)
        now = time.time()
        to_remove = [
            job_id
            for job_id, data in list(compile_jobs_cache.items())
            if data.get("status") in ["completed", "failed"]
            and data.get("completed_time", 0) < now - 3600
        ]
        for job_id in to_remove:
            del compile_jobs_cache[job_id]
        if to_remove:
            print(f"[Cache Cleanup] Removed {len(to_remove)} old compile jobs")


# =============================================================================
# Project Endpoints (kept in main.py due to complexity/dependencies)
# =============================================================================


@app.get("/api/v1/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        rows = await conn.fetch(
            """
            SELECT p.id, p.name, p.description, p.created_at, p.language,
                   (SELECT COUNT(*) FROM licenses l WHERE l.project_id = p.id) as license_count
            FROM projects p WHERE p.user_id = $1 ORDER BY p.created_at DESC
        """,
            user["id"],
        )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "language": r.get("language", "python"),
                "created_at": r["created_at"].isoformat(),
                "license_count": r["license_count"],
                "local_path": str(LOCAL_UPLOAD_DIR / r["id"]),
            }
            for r in rows
        ]
    finally:
        await release_db(conn)


@app.post("/api/v1/projects")
async def create_project(
    data: ProjectCreateRequest, user: dict = Depends(get_current_user)
):
    from utils import get_user_tier_limits

    conn = await get_db()
    try:
        limits = await get_user_tier_limits(user["id"], conn)
        max_projects = limits.get("max_projects", 1)

        if max_projects != -1:
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM projects WHERE user_id = $1", user["id"]
            )
            if current_count >= max_projects:
                raise HTTPException(
                    status_code=403,
                    detail=f"Project limit reached ({max_projects}). Upgrade your plan.",
                )

        project_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO projects (id, user_id, name, description, language, compiler_options) 
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            project_id,
            user["id"],
            data.name,
            data.description,
            data.language,
            json.dumps(data.compiler_options),
        )
        return {
            "id": project_id,
            "name": data.name,
            "description": data.description,
            "language": data.language,
            "compiler_options": data.compiler_options,
            "created_at": utc_now().isoformat(),
            "license_count": 0,
            "local_path": str(LOCAL_UPLOAD_DIR / project_id),
        }
    finally:
        await release_db(conn)


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await storage_service.delete_project_files(project_id)
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)


@app.get("/api/v1/projects/{project_id}/config")
async def get_project_config(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, name, settings, compiler_options, language FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        settings = project["settings"] or {}
        if isinstance(settings, str):
            settings = json.loads(settings) if settings else {}

        compiler_opts = project.get("compiler_options") or {}
        if isinstance(compiler_opts, str):
            compiler_opts = json.loads(compiler_opts)

        language = project.get("language", "python")

        files = await conn.fetch(
            """
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
        """,
            project_id,
        )

        # Get server URL for license validation API
        server_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        api_url = f"{server_url}/api/v1/license/validate"

        # Get selected license if stored in settings
        selected_license_id = settings.get("selected_license_id")

        return {
            "project_name": project["name"],
            "entry_file": settings.get("entry_file"),
            "output_name": settings.get("output_name"),
            "include_modules": settings.get("include_modules", []),
            "exclude_modules": settings.get("exclude_modules", []),
            "nuitka_options": settings.get("nuitka_options", {}),
            "pkg_options": settings.get("pkg_options", {}),
            "compiler_options": compiler_opts,
            "language": language,
            "api_url": api_url,
            "server_url": server_url,
            "selected_license_id": selected_license_id,
            "files": [
                {
                    "id": f["id"],
                    "filename": f["filename"],
                    "original_filename": f["original_filename"],
                    "file_size": f["file_size"],
                    "file_hash": f["file_hash"],
                    "created_at": f["created_at"].isoformat(),
                }
                for f in files
            ],
        }
    finally:
        await release_db(conn)


@app.put("/api/v1/projects/{project_id}/config")
async def update_project_config(
    project_id: str, data: ProjectConfigRequest, user: dict = Depends(get_current_user)
):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, settings FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        current_settings = (
            json.loads(project["settings"])
            if isinstance(project["settings"], str)
            else (project["settings"] or {})
        )

        current_settings.update(
            {
                "entry_file": data.entry_file,
                "output_name": data.output_name,
                "include_modules": data.include_modules,
                "exclude_modules": data.exclude_modules,
                "nuitka_options": data.nuitka_options,
            }
        )

        await conn.execute(
            """
            UPDATE projects 
            SET settings = $1, compiler_options = $2, updated_at = NOW() 
            WHERE id = $3
        """,
            json.dumps(current_settings),
            json.dumps(data.compiler_options),
            project_id,
        )

        return await get_project_config(project_id, user)
    finally:
        await release_db(conn)


@app.post("/api/v1/projects/{project_id}/upload")
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        uploaded = []
        for upload_file in files:
            content = await upload_file.read()

            from storage_service import validate_file_size

            is_valid, error_msg = validate_file_size(len(content), is_zip=False)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{upload_file.filename}': {error_msg}",
                )

            stored = await upload_project_file(
                project_id, upload_file.filename, content
            )

            file_id = secrets.token_hex(16)
            await conn.execute(
                """
                INSERT INTO project_files (id, project_id, filename, original_filename, file_path, file_hash, file_size, is_cloud)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                file_id,
                project_id,
                Path(stored.key).name,
                upload_file.filename,
                stored.key,
                stored.hash,
                stored.size,
                not stored.is_local,
            )

            uploaded.append(
                {
                    "id": file_id,
                    "filename": Path(stored.key).name,
                    "original_filename": upload_file.filename,
                    "file_size": stored.size,
                    "file_hash": stored.hash,
                    "created_at": utc_now().isoformat(),
                }
            )
        return uploaded
    finally:
        await release_db(conn)


@app.get("/api/v1/projects/{project_id}/files")
async def list_files(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        files = await conn.fetch(
            """
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
        """,
            project_id,
        )
        return [
            {
                "id": f["id"],
                "filename": f["filename"],
                "original_filename": f["original_filename"],
                "file_size": f["file_size"],
                "file_hash": f["file_hash"],
                "created_at": f["created_at"].isoformat(),
            }
            for f in files
        ]
    finally:
        await release_db(conn)


@app.delete("/api/v1/projects/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str, file_id: str, user: dict = Depends(get_current_user)
):
    conn = await get_db()
    try:
        file_row = await conn.fetchrow(
            """
            SELECT pf.id, pf.file_path, pf.is_cloud FROM project_files pf
            JOIN projects p ON pf.project_id = p.id
            WHERE pf.id = $1 AND p.user_id = $2
        """,
            file_id,
            user["id"],
        )
        if not file_row:
            raise HTTPException(status_code=404, detail="File not found")

        await storage_service.delete_file(
            file_row["file_path"], not file_row["is_cloud"]
        )
        await conn.execute("DELETE FROM project_files WHERE id = $1", file_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)


# Import project helper functions
from routes.project_helpers import scan_project_structure, scan_nodejs_project_structure


@app.post("/api/v1/projects/{project_id}/upload-zip")
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload an entire project as a ZIP file."""
    conn = await get_db()
    try:
        # Security: Validate project_id format before any path operations
        validate_project_id(project_id)

        project = await conn.fetchrow(
            "SELECT id, name, language FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="File must be a .zip file")

        # Use safe_join for all path operations
        project_dir = safe_join(UPLOAD_DIR, project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        zip_path = safe_join(project_dir, "project.zip")
        content = await file.read()

        from storage_service import validate_file_size

        is_valid, error_msg = validate_file_size(len(content), is_zip=True)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        with open(zip_path, "wb") as f:
            f.write(content)

        source_dir = safe_join(project_dir, "source")
        if source_dir.exists():
            shutil.rmtree(source_dir)
        source_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(source_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")

        language = (
            project.get("language", "python")
            if hasattr(project, "get")
            else project["language"]
        )

        if language == "nodejs":
            file_tree = scan_nodejs_project_structure(source_dir)
        else:
            file_tree = scan_project_structure(source_dir)

        if file_tree["total_files"] == 0:
            lang_name = "JavaScript/TypeScript" if language == "nodejs" else "Python"
            raise HTTPException(
                status_code=400, detail=f"No {lang_name} files found in ZIP"
            )

        settings = await conn.fetchval(
            "SELECT settings FROM projects WHERE id = $1", project_id
        )
        settings = (
            json.loads(settings) if isinstance(settings, str) and settings else {}
        )

        settings["file_tree"] = file_tree
        settings["is_multi_folder"] = True
        settings["zip_uploaded_at"] = utc_now().isoformat()

        await conn.execute(
            "UPDATE projects SET settings = $1, updated_at = NOW() WHERE id = $2",
            json.dumps(settings),
            project_id,
        )

        zip_path.unlink()

        return {
            "success": True,
            "file_count": file_tree["total_files"],
            "structure": file_tree,
            "message": f"Successfully uploaded {file_tree['total_files']} files",
        }
    except HTTPException:
        raise
    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        import logging

        logging.error(f"Failed to process ZIP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process ZIP file")
    finally:
        await release_db(conn)


# =============================================================================
# Build Orchestrator Endpoints
# =============================================================================

from compilers import check_build_prerequisites


@app.get("/api/v1/build/prerequisites")
async def get_build_prerequisites():
    """Check if all build prerequisites are available."""
    return check_build_prerequisites()


class InstallerBuildRequest(BaseModel):
    """Request for building an installer package"""

    project_name: str = Field(..., description="Name of the application")
    project_version: str = Field("1.0.0", description="Version string")
    publisher: str = Field("", description="Publisher name")
    source_dir: str = Field(..., description="Path to project source directory")
    entry_file: str = Field(..., description="Entry file (main.py or index.js)")
    language: str = Field("python", description="Language: 'python' or 'nodejs'")
    license_key: str = Field("GENERIC_BUILD", description="License key")
    api_url: str = Field("", description="License validation API URL")
    license_mode: str = Field("generic", description="'fixed', 'generic', or 'demo'")
    distribution_type: str = Field("installer", description="'portable' or 'installer'")
    create_desktop_shortcut: bool = Field(True)
    create_start_menu: bool = Field(True)
    output_dir: str = Field(..., description="Output directory for final build")


@app.post("/api/v1/build/installer")
async def build_installer(data: InstallerBuildRequest):
    """Start a professional Windows installer build job (async)."""

    job_id = secrets.token_hex(16)

    # Initialize job in cache
    compile_jobs_cache[job_id] = {
        "status": "pending",
        "progress": 0,
        "logs": ["Build job created..."],
        "project_name": data.project_name,
        "distribution_type": data.distribution_type,
        "output_path": None,
        "error_message": None,
        "cancelled": False,  # Flag to support cancellation
    }

    # Run build in background
    import asyncio

    asyncio.create_task(_run_installer_build_job(job_id, data))

    return {"job_id": job_id, "status": "pending", "message": "Build job started"}


async def _run_installer_build_job(job_id: str, data: InstallerBuildRequest):
    """Background task to run the actual build."""
    from compilers import get_build_orchestrator, BuildConfig

    orchestrator = get_build_orchestrator()

    config = BuildConfig(
        project_name=data.project_name,
        project_version=data.project_version,
        publisher=data.publisher or "Unknown Publisher",
        source_dir=Path(data.source_dir),
        entry_file=data.entry_file,
        language=data.language,
        license_key=data.license_key,
        api_url=data.api_url
        if "/license/validate" in (data.api_url or "")
        else f"{data.api_url or LICENSE_SERVER_URL}/api/v1/license/validate",
        license_mode=data.license_mode,
        distribution_type=data.distribution_type,
        create_desktop_shortcut=data.create_desktop_shortcut,
        create_start_menu=data.create_start_menu,
        output_dir=Path(data.output_dir),
    )

    # Update to running
    compile_jobs_cache[job_id]["status"] = "running"
    compile_jobs_cache[job_id]["progress"] = 5
    compile_jobs_cache[job_id]["logs"].append("Starting build process...")

    async def log_callback(msg):
        """Update progress based on log messages."""
        if job_id in compile_jobs_cache:
            compile_jobs_cache[job_id]["logs"].append(msg)

            # PRIORITY: Check for explicit progress annotation from compiler
            progress_match = re.search(r"\[progress: (\d+)%\]", msg)
            if progress_match:
                compile_jobs_cache[job_id]["progress"] = int(progress_match.group(1))
            # Fallback: Estimate progress based on stage keywords
            elif "compil" in msg.lower():
                compile_jobs_cache[job_id]["progress"] = max(
                    compile_jobs_cache[job_id]["progress"], 20
                )
            elif "packaging" in msg.lower() or "pkg" in msg.lower():
                compile_jobs_cache[job_id]["progress"] = max(
                    compile_jobs_cache[job_id]["progress"], 50
                )
            elif "nsis" in msg.lower() or "installer" in msg.lower():
                compile_jobs_cache[job_id]["progress"] = max(
                    compile_jobs_cache[job_id]["progress"], 70
                )
            elif "complete" in msg.lower() or "success" in msg.lower():
                compile_jobs_cache[job_id]["progress"] = max(
                    compile_jobs_cache[job_id]["progress"], 90
                )
        print(f"[Build {job_id[:8]}] {msg}")

    try:
        output_path = await orchestrator.build(config, log_callback)

        compile_jobs_cache[job_id]["status"] = "completed"
        compile_jobs_cache[job_id]["progress"] = 100
        compile_jobs_cache[job_id]["output_path"] = str(output_path)
        compile_jobs_cache[job_id]["output_filename"] = output_path.name
        compile_jobs_cache[job_id]["logs"].append(
            f"✅ Build complete: {output_path.name}"
        )
        compile_jobs_cache[job_id]["completed_time"] = time.time()

    except Exception as e:
        import traceback

        traceback.print_exc()
        compile_jobs_cache[job_id]["status"] = "failed"
        # Always expose full error for debugging (logged server-side anyway)
        compile_jobs_cache[job_id]["error_message"] = str(e)
        compile_jobs_cache[job_id]["logs"].append(f"❌ Build failed: {str(e)}")
        compile_jobs_cache[job_id]["completed_time"] = time.time()


@app.get("/api/v1/build/installer/{job_id}/status")
async def get_installer_build_status(job_id: str):
    """Get the status of an installer build job."""
    if job_id not in compile_jobs_cache:
        raise HTTPException(status_code=404, detail="Build job not found")

    job = compile_jobs_cache[job_id]

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "logs": job["logs"][-20:],  # Last 20 log entries
        "output_path": job.get("output_path"),
        "output_filename": job.get("output_filename"),
        "error_message": job.get("error_message"),
    }


@app.delete("/api/v1/build/installer/{job_id}/cancel")
async def cancel_installer_build(job_id: str):
    """Cancel a running installer build job."""
    if job_id not in compile_jobs_cache:
        raise HTTPException(status_code=404, detail="Build job not found")

    job = compile_jobs_cache[job_id]

    if job["status"] not in ["pending", "running"]:
        return {
            "job_id": job_id,
            "status": job["status"],
            "message": f"Build is not running (current status: {job['status']})",
        }

    # Set cancellation flag - the build loop will check this
    job["cancelled"] = True
    job["status"] = "cancelled"
    job["logs"].append("🛑 Build cancelled by user")
    job["completed_time"] = time.time()

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Build cancelled successfully",
    }


# =============================================================================
# Compilation Endpoints (kept here due to complex state management)
# =============================================================================

from middleware.tier_enforcement import requires_feature
from routes.compile_helpers import run_compilation_job


async def check_feature_access(user_id: str, feature: str, conn):
    """Check if user has access to a feature based on their tier."""
    from utils import get_user_tier_limits

    limits = await get_user_tier_limits(user_id, conn)
    if not limits.get(feature, False):
        raise HTTPException(
            status_code=403, detail=f"Feature '{feature}' requires a higher tier"
        )


@app.post("/api/v1/compile/start", response_model=CompileJobResponse)
@requires_feature("cloud_compilation")
async def start_compilation(
    data: CompileJobRequest, project_id: str, user: dict = Depends(get_current_user)
):
    """Start a compilation job for a project."""
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, settings, language FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.get("language") == "nodejs":
            await check_feature_access(user["id"], "node_support", conn)

        settings = (
            json.loads(project["settings"])
            if isinstance(project["settings"], str)
            else (project["settings"] or {})
        )

        file_count = await conn.fetchval(
            "SELECT COUNT(*) FROM project_files WHERE project_id = $1", project_id
        )
        has_file_tree = settings.get("file_tree") is not None

        if file_count == 0 and not has_file_tree:
            raise HTTPException(status_code=400, detail="No files uploaded to project")

        job_id = secrets.token_hex(16)
        created_at = utc_now()

        await conn.execute(
            """
            INSERT INTO compile_jobs (id, project_id, status, progress, created_at) 
            VALUES ($1, $2, $3, $4, $5)
        """,
            job_id,
            project_id,
            "pending",
            0,
            created_at,
        )

        compile_jobs_cache[job_id] = {
            "status": "pending",
            "progress": 0,
            "logs": ["Compilation job created..."],
            "project_id": project_id,
            "entry_file": data.entry_file,
            "output_name": data.output_name,
            "options": data.options,
        }

        import asyncio

        asyncio.create_task(
            run_compilation_job(
                job_id, project_id, data, compile_jobs_cache, UPLOAD_DIR
            )
        )

        return CompileJobResponse(
            id=job_id,
            project_id=project_id,
            status="pending",
            progress=0,
            output_filename=None,
            error_message=None,
            logs=["Compilation job created..."],
            started_at=None,
            completed_at=None,
            created_at=created_at.isoformat(),
        )
    finally:
        await release_db(conn)


@app.get("/api/v1/compile/{job_id}/status", response_model=CompileJobResponse)
async def get_compile_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get the status of a compilation job."""
    conn = await get_db()
    try:
        job = await conn.fetchrow(
            """
            SELECT cj.*, p.user_id FROM compile_jobs cj 
            JOIN projects p ON cj.project_id = p.id WHERE cj.id = $1
        """,
            job_id,
        )

        if not job or job["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Compile job not found")

        if job_id in compile_jobs_cache:
            cache_data = compile_jobs_cache[job_id]
            return CompileJobResponse(
                id=job_id,
                project_id=cache_data["project_id"],
                status=cache_data["status"],
                progress=cache_data["progress"],
                output_filename=cache_data.get("output_filename"),
                error_message=cache_data.get("error_message"),
                logs=cache_data["logs"],
                started_at=job["started_at"].isoformat() if job["started_at"] else None,
                completed_at=job["completed_at"].isoformat()
                if job["completed_at"]
                else None,
                created_at=job["created_at"].isoformat(),
            )

        logs = job["logs"] if job["logs"] else []
        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except Exception:
                logs = []

        return CompileJobResponse(
            id=str(job["id"]),
            project_id=str(job["project_id"]),
            status=job["status"],
            progress=job["progress"] or 0,
            output_filename=job["output_filename"],
            error_message=job["error_message"],
            logs=logs,
            started_at=job["started_at"].isoformat() if job["started_at"] else None,
            completed_at=job["completed_at"].isoformat()
            if job["completed_at"]
            else None,
            created_at=job["created_at"].isoformat(),
        )
    finally:
        await release_db(conn)


@app.get("/api/v1/compile/{job_id}/download")
async def download_compiled_file(job_id: str, user: dict = Depends(get_current_user)):
    """Download the compiled executable."""
    conn = await get_db()
    try:
        job = await conn.fetchrow(
            """
            SELECT cj.*, p.user_id FROM compile_jobs cj 
            JOIN projects p ON cj.project_id = p.id WHERE cj.id = $1
        """,
            job_id,
        )

        if not job or job["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Compile job not found")

        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Compilation not completed yet")

        if not job["output_filename"]:
            raise HTTPException(status_code=404, detail="Output file not found")

        project_id = job["project_id"]

        # Security: Validate project_id and use safe paths
        validate_project_id(project_id)
        project_base = safe_join(UPLOAD_DIR, project_id)
        output_dir = safe_join(project_base, "output")
        output_file = safe_join(output_dir, job["output_filename"])

        if not output_file.exists():
            exe_files = list(output_dir.glob("*.exe"))
            if exe_files:
                output_file = exe_files[0]
            else:
                raise HTTPException(status_code=404, detail="Compiled file not found")

        return FileResponse(
            path=str(output_file),
            filename=job["output_filename"],
            media_type="application/octet-stream",
        )
    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    finally:
        await release_db(conn)


# =============================================================================
# CLI Endpoints (for local compilation)
# =============================================================================

CLI_VERSION = "1.0.0"


@app.get("/api/v1/cli/version")
async def get_cli_version():
    """Get the latest CLI tool version and download URLs."""
    return {
        "version": CLI_VERSION,
        "downloads": {
            "windows": os.getenv("CLI_DOWNLOAD_WINDOWS") or None,
            "macos": os.getenv("CLI_DOWNLOAD_MACOS") or None,
            "linux": os.getenv("CLI_DOWNLOAD_LINUX") or None,
        },
        "changelog": "Initial release with local Nuitka compilation support.",
    }


@app.get("/api/v1/projects/{project_id}/compile-config")
async def get_compile_config(
    project_id: str,
    license_key: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get compilation configuration for the CLI tool."""
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        settings = json.loads(project["settings"]) if project["settings"] else {}

        files = await conn.fetch(
            "SELECT original_filename, filename FROM project_files WHERE project_id = $1",
            project_id,
        )

        entry_file = settings.get("entry_file", "main.py")
        file_list = [f["original_filename"] for f in files]
        if entry_file not in file_list and file_list:
            entry_file = file_list[0]

        file_tree = settings.get("file_tree", {})
        folders = file_tree.get("folders", [])

        nuitka_options = {
            "standalone": True,
            "onefile": True,
            "remove_output": True,
            "assume_yes_for_downloads": True,
        }

        if folders:
            nuitka_options["include_packages"] = [
                f for f in folders if f and f != "__pycache__"
            ]

        server_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")

        return {
            "project_id": project_id,
            "project_name": project["name"],
            "entry_file": entry_file,
            "output_name": settings.get(
                "output_name", project["name"].replace(" ", "_").lower()
            ),
            "license_key": license_key,
            "server_url": server_url,
            "nuitka_options": nuitka_options,
            "files": file_list,
            "is_multi_folder": settings.get("is_multi_folder", False),
            "folders": folders,
            "language": project.get("language", "python"),
        }
    finally:
        await release_db(conn)


@app.get("/api/v1/projects/{project_id}/build-bundle")
async def get_build_bundle(
    project_id: str,
    license_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Download a build bundle for local CLI compilation.

    Returns a ZIP containing:
    - source/ folder (all project files)
    - config.json (entry_file, output_name, license_key, api_url, options)
    - assets/ folder (icon if provided)
    """
    import tempfile

    conn = await get_db()
    try:
        # Security: Validate project_id format
        validate_project_id(project_id)

        # Fetch project details
        project = await conn.fetchrow(
            "SELECT id, name, language, settings, compiler_options FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Parse settings
        settings = json.loads(project["settings"]) if project["settings"] else {}
        compiler_options = (
            json.loads(project["compiler_options"])
            if isinstance(project["compiler_options"], str)
            else (project["compiler_options"] or {})
        )
        language = (
            project.get("language", "python")
            if hasattr(project, "get")
            else project["language"]
        )

        # Check source directory exists
        project_dir = safe_join(UPLOAD_DIR, project_id)
        source_dir = safe_join(project_dir, "source")

        if not source_dir.exists():
            raise HTTPException(
                status_code=400,
                detail="No source files found. Please upload a project ZIP first.",
            )

        # Get license info if license_id provided
        license_key = None
        if license_id:
            license_row = await conn.fetchrow(
                """SELECT license_key FROM licenses 
                   WHERE id = $1 AND project_id = $2""",
                license_id,
                project_id,
            )
            if license_row:
                license_key = license_row["license_key"]

        # Get server URL for license validation
        server_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        api_url = f"{server_url}/api/v1/license/validate"

        # Build config.json
        config = {
            "project_id": project_id,
            "project_name": project["name"],
            "language": language,
            "entry_file": settings.get(
                "entry_file", "main.py" if language == "python" else "index.js"
            ),
            "output_name": settings.get(
                "output_name", project["name"].replace(" ", "_").lower()
            ),
            "license_key": license_key,
            "api_url": api_url,
            "server_url": server_url,
            "nuitka_options": settings.get("nuitka_options", {}),
            "pkg_options": settings.get("pkg_options", {}),
            "compiler_options": compiler_options,
            "is_multi_folder": settings.get("is_multi_folder", False),
            "file_tree": settings.get("file_tree", {}),
            "include_modules": settings.get("include_modules", []),
            "exclude_modules": settings.get("exclude_modules", []),
        }

        # Create temp ZIP file
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".zip", delete=False
        ) as tmp_file:
            zip_path = tmp_file.name

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add config.json
                zf.writestr("config.json", json.dumps(config, indent=2))

                # Add source files
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = f"source/{file_path.relative_to(source_dir)}"
                        zf.write(file_path, arcname)

                # Add assets folder if exists (icon, etc.)
                assets_dir = safe_join(project_dir, "assets")
                if assets_dir.exists():
                    for file_path in assets_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = f"assets/{file_path.relative_to(assets_dir)}"
                            zf.write(file_path, arcname)

            # Return the ZIP file with cleanup task
            filename = f"{project['name'].replace(' ', '_')}_bundle.zip"

            def cleanup_temp_file():
                """Delete temp file after response is sent."""
                if os.path.exists(zip_path):
                    os.unlink(zip_path)

            return FileResponse(
                path=zip_path,
                filename=filename,
                media_type="application/zip",
                background=BackgroundTask(cleanup_temp_file),
            )
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            raise HTTPException(
                status_code=500, detail=f"Failed to create build bundle: {str(e)}"
            )

    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    finally:
        await release_db(conn)


if __name__ == "__main__":
    import uvicorn
    from email_service import email_service

    print(f"\n{'=' * 60}\n  License-Wrapper API Server ({ENVIRONMENT})\n{'=' * 60}")
    print("  Database: PostgreSQL")
    print(
        f"  Storage: {'Cloudflare R2' if storage_service.is_cloud_enabled() else 'Local'}"
    )
    print(f"  Email: {'Enabled' if email_service.is_configured() else 'Disabled'}")
    print(f"  API Docs: http://localhost:8000/docs\n{'=' * 60}\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
