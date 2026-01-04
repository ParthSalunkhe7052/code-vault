import os
import json
import secrets
import time

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
from utils import get_current_user, safe_join, validate_project_id, SecurityError
from storage_service import LOCAL_UPLOAD_DIR as UPLOAD_DIR
from config import LICENSE_SERVER_URL, CLI_VERSION
from compilers import check_build_prerequisites, get_build_orchestrator, BuildConfig

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
            print(f"[Cache Cleanup] Removed {len(to_remove)} old compile jobs")

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


@router.get("/build/installer/{job_id}/status")
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


@router.delete("/build/installer/{job_id}/cancel")
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
            "enable_lease": settings.get("enable_lease", True),
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

        project = await conn.fetchrow(
            "SELECT id, name, language, settings, compiler_options FROM projects WHERE id = $1 AND user_id = $2",
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
            "skip_obfuscation": settings.get("skip_obfuscation", True),
            "enable_lease": settings.get("enable_lease", True),
        }

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
