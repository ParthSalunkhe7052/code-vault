import os
import json
import secrets
import time
import logging

import zipfile
import re
import asyncio
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

from database import get_db, release_db
from utils import (
    get_current_user,
    safe_join,
    validate_project_id,
    SecurityError,
    get_user_tier,
)
from storage_service import LOCAL_UPLOAD_DIR as UPLOAD_DIR
from config import LICENSE_SERVER_URL, CLI_VERSION
from compilers import check_build_prerequisites, get_build_orchestrator, BuildConfig
from middleware.rate_limiter import RateLimitDependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["build"])

# =============================================================================
# Cache & Background Tasks
# =============================================================================

compile_jobs_cache = {}


async def cleanup_compile_cache():
    """Background task to remove completed jobs from cache after 1 hour."""
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
            logger.info(f"[Cache Cleanup] Removed {len(to_remove)} old compile jobs")


# =============================================================================
# Models
# =============================================================================


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


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/build/prerequisites")
async def get_build_prerequisites():
    """Check if all build prerequisites are available."""
    return check_build_prerequisites()


@router.post("/build/installer")
async def build_installer(
    data: InstallerBuildRequest,
    user: dict = Depends(get_current_user),
    _rate_limit: None = Depends(
        RateLimitDependency(
            max_requests=3, window_seconds=300, prefix="build:installer"
        )
    ),
):
    """Start a professional Windows installer build job (async)."""
    # Security: Validate source_dir and output_dir are within allowed directories
    try:
        validated_source = safe_join(UPLOAD_DIR, data.source_dir)
        validated_output = safe_join(UPLOAD_DIR, data.output_dir)
    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid source or output directory path")

    # Override user-supplied paths with validated ones
    data.source_dir = str(validated_source)
    data.output_dir = str(validated_output)

    job_id = secrets.token_hex(16)

    # Initialize job in cache — store user_id for ownership enforcement (C2 FIX)
    compile_jobs_cache[job_id] = {
        "status": "pending",
        "progress": 0,
        "logs": ["Build job created..."],
        "project_name": data.project_name,
        "distribution_type": data.distribution_type,
        "output_path": None,
        "error_message": None,
        "cancelled": False,  # Flag to support cancellation
        "user_id": user["id"],  # C2 FIX: bind job to requesting user
    }

    # Run build in background
    asyncio.create_task(_run_installer_build_job(job_id, data))

    return {"job_id": job_id, "status": "pending", "message": "Build job started"}


async def _run_installer_build_job(job_id: str, data: InstallerBuildRequest):
    """Background task to run the actual build."""
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
        logger.debug(f"[Build {job_id[:8]}] {msg}")

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
        logger.error(f"[Build {job_id[:8]}] Build failed with exception", exc_info=True)
        compile_jobs_cache[job_id]["status"] = "failed"
        # Store full error server-side for admin debugging (never returned to client)
        compile_jobs_cache[job_id]["_internal_error"] = str(e)
        # H5 FIX: Never expose raw exception strings (which contain internal
        # filesystem paths and compiler details) in the client-visible logs list.
        # The sanitized error_message is sufficient for the user; full details
        # are available to admins via server logs (exc_info=True above).
        compile_jobs_cache[job_id]["error_message"] = "Build failed. Please try again or contact support."
        compile_jobs_cache[job_id]["logs"].append("❌ Build failed. Check server logs for details.")
        compile_jobs_cache[job_id]["completed_time"] = time.time()


@router.get("/build/installer/{job_id}/status")
async def get_installer_build_status(
    job_id: str, user: dict = Depends(get_current_user)
):
    """Get the status of an installer build job."""
    if job_id not in compile_jobs_cache:
        raise HTTPException(status_code=404, detail="Build job not found")

    job = compile_jobs_cache[job_id]

    # C2 FIX: Enforce ownership — only the user who started the job may poll it.
    if job.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Build job not found")

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "logs": job["logs"][-20:],  # Last 20 log entries
        "output_path": job.get("output_path"),
        "output_filename": job.get("output_filename"),
        "error_message": job.get("error_message"),
    }


@router.delete("/build/installer/{job_id}/cancel")
async def cancel_installer_build(job_id: str, user: dict = Depends(get_current_user)):
    """Cancel a running installer build job."""
    if job_id not in compile_jobs_cache:
        raise HTTPException(status_code=404, detail="Build job not found")

    job = compile_jobs_cache[job_id]

    # C2 FIX: Enforce ownership — only the user who started the job may cancel it.
    if job.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Build job not found")

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
# CLI / Local Compilation Endpoints
# =============================================================================


@router.get("/cli/version")
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


@router.get("/projects/{project_id}/compile-config")
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

        server_url = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000")

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
            # Build options
            "skip_obfuscation": settings.get("skip_obfuscation", True),
            "enable_lease": settings.get("enable_lease", False),
        }
    finally:
        await release_db(conn)


@router.get("/projects/{project_id}/build-bundle")
async def get_build_bundle(
    project_id: str,
    license_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Download a build bundle for local CLI compilation."""
    import tempfile

    conn = await get_db()
    try:
        validate_project_id(project_id)

        # C3 FIX: Fetch signing_public_key (Ed25519 public key for client-side
        # signature verification) but NOT signing_secret (HMAC server secret).
        # The HMAC secret must never leave the server — only the public key is
        # needed by the CLI to verify server-signed validation responses.
        project = await conn.fetchrow(
            "SELECT id, name, language, settings, compiler_options, signing_public_key FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        settings = json.loads(project["settings"]) if project["settings"] else {}
        compiler_options = (
            json.loads(project["compiler_options"])
            if isinstance(project["compiler_options"], str)
            else (project["compiler_options"] or {})
        )

        # Debug: Log settings
        logger.debug(
            "[BUNDLE DEBUG] Project %s: Settings from DB=%s, skip_obfuscation=%s, enable_lease=%s",
            project_id,
            settings,
            settings.get("skip_obfuscation"),
            settings.get("enable_lease"),
        )

        language = (
            project.get("language", "python")
            if hasattr(project, "get")
            else project["language"]
        )

        project_dir = safe_join(UPLOAD_DIR, project_id)
        source_dir = safe_join(project_dir, "source")

        if not source_dir.exists():
            raise HTTPException(
                status_code=400,
                detail="No source files found. Please upload a project ZIP first.",
            )

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

        server_url = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000")
        api_url = f"{server_url}/api/v1/license/validate"

        # Get user tier info for white-label branding
        tier_info = await get_user_tier(user["id"], conn)

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
            # C3 FIX: Include Ed25519 public key (for client verification) —
            # NEVER include signing_secret (HMAC server-only credential).
            "signing_public_key": project.get("signing_public_key") or "",
            "nuitka_options": settings.get("nuitka_options", {}),
            "pkg_options": settings.get("pkg_options", {}),
            "compiler_options": compiler_options,
            "is_multi_folder": settings.get("is_multi_folder", False),
            "file_tree": settings.get("file_tree", {}),
            "include_modules": settings.get("include_modules", []),
            "exclude_modules": settings.get("exclude_modules", []),
            "skip_obfuscation": settings.get("skip_obfuscation", True),
            "enable_lease": settings.get("enable_lease", False),
            # White-label branding: show branding for free tier users
            "tier": tier_info["tier"],
            "is_pro": tier_info["is_pro"],
            "show_branding": not tier_info["can_remove_branding"],  # True for free tier
        }

        # Debug: Log final config being written to bundle
        # CodeQL: These fields are non-sensitive configuration flags, not secrets.
        logger.debug(
            "[BUNDLE DEBUG] Final config for bundle: skip_obfuscation=%s, enable_lease=%s, show_branding=%s, tier=%s",
            str(config.get("skip_obfuscation")),
            str(config.get("enable_lease")),
            str(config.get("show_branding")),
            str(config.get("tier")),
        )

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".zip", delete=False
        ) as tmp_file:
            zip_path = tmp_file.name

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("config.json", json.dumps(config, indent=2))

                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = f"source/{file_path.relative_to(source_dir)}"
                        zf.write(file_path, arcname)

                assets_dir = safe_join(project_dir, "assets")
                if assets_dir.exists():
                    for file_path in assets_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = f"assets/{file_path.relative_to(assets_dir)}"
                            zf.write(file_path, arcname)

            filename = f"{project['name'].replace(' ', '_')}_bundle.zip"

            def cleanup_temp_file():
                if os.path.exists(zip_path):
                    os.unlink(zip_path)

            return FileResponse(
                path=zip_path,
                filename=filename,
                media_type="application/zip",
                background=BackgroundTask(cleanup_temp_file),
            )
        except Exception as e:
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            raise HTTPException(
                status_code=500, detail=f"Failed to create build bundle: {str(e)}"
            )

    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    finally:
        await release_db(conn)


# =============================================================================
# Build Protection Report Endpoints
# =============================================================================


class ProtectionReportData(BaseModel):
    """Data for generating a protection report"""

    build_id: str
    project_id: Optional[str] = None
    protection_level: str  # 'basic', 'standard', 'advanced', 'enterprise'
    protection_layers: list = Field(default_factory=list)
    estimated_reversal_difficulty: str  # 'easy', 'moderate', 'hard', 'very_hard'
    obfuscation_enabled: bool = False
    ed25519_signatures: bool = False
    binary_hash_verification: bool = False
    hwid_binding_enabled: bool = False
    offline_lease_enabled: bool = False
    heartbeat_enabled: bool = False
    license_type: str  # 'fixed', 'generic', 'demo', 'floating'
    license_tier: str  # 'free', 'pro', 'business', 'enterprise'


@router.post("/build/protection-report")
async def create_protection_report(
    data: ProtectionReportData,
    user: dict = Depends(get_current_user),
):
    """Generate and store a build protection report."""
    conn = await get_db()
    try:
        # Build the report data
        report_data = {
            "summary": {
                "protection_level": data.protection_level,
                "difficulty": data.estimated_reversal_difficulty,
                "total_layers": len(data.protection_layers),
            },
            "layers": data.protection_layers,
            "security_features": {
                "obfuscation": data.obfuscation_enabled,
                "ed25519_signatures": data.ed25519_signatures,
                "binary_hash_verification": data.binary_hash_verification,
                "hwid_binding": data.hwid_binding_enabled,
                "offline_lease": data.offline_lease_enabled,
                "heartbeat": data.heartbeat_enabled,
            },
            "license_info": {"type": data.license_type, "tier": data.license_tier},
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }

        # Insert into database
        await conn.execute(
            """
            INSERT INTO build_protection_reports (
                build_id, project_id, user_id, protection_level, protection_layers,
                estimated_reversal_difficulty, obfuscation_enabled, ed25519_signatures,
                binary_hash_verification, hwid_binding_enabled, offline_lease_enabled,
                heartbeat_enabled, license_type, license_tier, report_data
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """,
            data.build_id,
            data.project_id,
            user["id"],
            data.protection_level,
            json.dumps(data.protection_layers),
            data.estimated_reversal_difficulty,
            data.obfuscation_enabled,
            data.ed25519_signatures,
            data.binary_hash_verification,
            data.hwid_binding_enabled,
            data.offline_lease_enabled,
            data.heartbeat_enabled,
            data.license_type,
            data.license_tier,
            json.dumps(report_data),
        )

        logger.info(f"[Protection Report] Created report for build {data.build_id}")
        return {"status": "success", "build_id": data.build_id}
    finally:
        await release_db(conn)


@router.get("/build/protection-report/{build_id}")
async def get_protection_report(
    build_id: str,
    user: dict = Depends(get_current_user),
):
    """Retrieve a build protection report."""
    conn = await get_db()
    try:
        report = await conn.fetchrow(
            """
            SELECT * FROM build_protection_reports 
            WHERE build_id = $1 AND user_id = $2
            ORDER BY created_at DESC LIMIT 1
            """,
            build_id,
            user["id"],
        )

        if not report:
            raise HTTPException(status_code=404, detail="Protection report not found")

        return {
            "build_id": report["build_id"],
            "project_id": report["project_id"],
            "created_at": report["created_at"],
            "protection_level": report["protection_level"],
            "estimated_reversal_difficulty": report["estimated_reversal_difficulty"],
            "protection_layers": report["protection_layers"],
            "security_features": {
                "obfuscation": report["obfuscation_enabled"],
                "ed25519_signatures": report["ed25519_signatures"],
                "binary_hash_verification": report["binary_hash_verification"],
                "hwid_binding": report["hwid_binding_enabled"],
                "offline_lease": report["offline_lease_enabled"],
                "heartbeat": report["heartbeat_enabled"],
            },
            "license_info": {
                "type": report["license_type"],
                "tier": report["license_tier"],
            },
            "report_data": report["report_data"],
        }
    finally:
        await release_db(conn)


@router.get("/build/protection-reports")
async def list_protection_reports(
    project_id: Optional[str] = None,
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """List protection reports for the user."""
    conn = await get_db()
    try:
        if project_id:
            reports = await conn.fetch(
                """
                SELECT build_id, project_id, created_at, protection_level, 
                       estimated_reversal_difficulty, license_tier
                FROM build_protection_reports 
                WHERE user_id = $1 AND project_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                user["id"],
                project_id,
                limit,
            )
        else:
            reports = await conn.fetch(
                """
                SELECT build_id, project_id, created_at, protection_level, 
                       estimated_reversal_difficulty, license_tier
                FROM build_protection_reports 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                user["id"],
                limit,
            )

        return {"reports": [dict(r) for r in reports]}
    finally:
        await release_db(conn)
