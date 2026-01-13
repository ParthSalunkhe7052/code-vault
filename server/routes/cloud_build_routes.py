from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
import logging
import os
import json
import httpx
import hmac
import hashlib
import secrets
import re
from pathlib import Path
from datetime import datetime

from database import get_db, release_db
from storage_service import storage_service
from utils import get_current_user, get_user_tier_limits
from config import GITHUB_TOKEN, GITHUB_REPO, BUILD_CALLBACK_SECRET, ENVIRONMENT

# Import settings directly to avoid circular imports if possible, or use config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cloud-build", tags=["cloud-build"])

# Local upload directory - should match project_routes
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_safe_path(base_dir: Path, user_input: str) -> Path:
    """
    Validate that user input doesn't escape the base directory (path traversal protection).
    
    Args:
        base_dir: The allowed base directory
        user_input: User-provided path component (e.g., project_id)
    
    Returns:
        Safe resolved path within base_dir
    
    Raises:
        HTTPException: If path traversal is detected or input is invalid
    """
    # Strict allowlist: only alphanumeric, dashes, underscores, and dots (no leading dot)
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]*$', user_input):
        raise HTTPException(400, "Invalid path component: only alphanumeric, dashes, underscores allowed")
    
    # Reject obviously malicious patterns
    if ".." in user_input or user_input.startswith("/") or user_input.startswith("\\"):
        raise HTTPException(400, "Invalid path component")
    
    # Build the candidate path
    candidate = base_dir / user_input
    
    # Resolve to absolute path and verify it's within base_dir
    try:
        resolved = candidate.resolve()
        base_resolved = base_dir.resolve()
        
        # Ensure the resolved path is within the base directory
        if not str(resolved).startswith(str(base_resolved)):
            raise HTTPException(400, "Invalid path component")
        
        return resolved
    except (OSError, ValueError):
        raise HTTPException(400, "Invalid path component")


class CloudBuildRequest(BaseModel):
    project_id: str
    license_id: Optional[str] = None
    target_platform: str = "windows"  # windows, macos, linux


class CloudBuildResponse(BaseModel):
    build_id: str
    status: str
    message: str


async def get_license_key(license_id: str, conn) -> str:
    """Helper to fetch license key."""
    row = await conn.fetchrow("SELECT key FROM licenses WHERE id = $1", license_id)
    return row["key"] if row else "GENERIC_BUILD"


async def verify_webhook_signature(request: Request) -> bool:
    """Verify HMAC signature on build completion webhook."""
    signature = request.headers.get("X-Signature")
    if not signature:
        logger.warning("Webhook received without X-Signature header")
        return False
    
    body = await request.body()
    expected = hmac.new(
        BUILD_CALLBACK_SECRET.encode() if BUILD_CALLBACK_SECRET else b"",
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature.lower(), expected.lower())


async def upload_source_to_r2(build_id: str, source_dir: Path) -> str:
    """
    Zip the source directory and upload to R2.
    Returns the presigned URL for the runner to download.
    """
    import shutil
    
    # Create a zip of the source directory
    # The zip will contain the contents of source_dir
    zip_path = source_dir.parent / f"source_{build_id}.zip"
    
    try:
        # Create zip archive - we zip the contents, not the directory itself
        shutil.make_archive(str(zip_path.with_suffix("")), 'zip', source_dir)
        
        # Read the zip file
        with open(zip_path, "rb") as f:
            content = f.read()
        
        key = f"builds/{build_id}/source.zip"
        
        if storage_service.is_cloud_enabled() and storage_service.client:
            s3 = storage_service.client
            bucket = storage_service.bucket
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=content
            )
            # Generate presigned GET url
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=3600
            )
            return url
        else:
            # Fallback for local dev without R2
            if ENVIRONMENT == "production":
                raise HTTPException(
                    500, 
                    "Cloud Builds require R2 storage configuration in production. Please configure R2_ACCESS_KEY_ID, etc."
                )
            
            # In local dev, we might just return a file:// url if the runner was local,
            # but since the runner is GitHub Actions, it MUST be a public URL.
            logger.warning("R2 not enabled. Cloud build will fail on GitHub runner (cannot access localhost).")
            
            # If we are using ngrok, this might work if PUBLIC_API_URL is set correctly
            public_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
            return f"{public_url}/uploads/{build_id}/source.zip"
    finally:
        # Cleanup local zip
        if zip_path.exists():
            zip_path.unlink()


async def trigger_github_build(build_id: str, config: dict, source_dir: Path):
    """Trigger GitHub Actions workflow."""
    conn = None
    try:
        if not GITHUB_TOKEN or not GITHUB_REPO:
            raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be configured for cloud builds.")

        # 1. Upload source to R2 and get presigned URL
        source_url = await upload_source_to_r2(build_id, source_dir)
        
        # 2. Trigger GitHub Actions
        # We need the public API URL for the callback
        public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        if "localhost" in public_api_url and ENVIRONMENT == "production":
             logger.warning("PUBLIC_API_URL is set to localhost in production. Webhooks will fail.")

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            payload = {
                "ref": "main",
                "inputs": {
                    "build_id": build_id,
                    "project_id": config["project_id"],
                    "language": config["language"],
                    "source_url": source_url,
                    "config_json": json.dumps(config),
                    "callback_url": f"{public_api_url}/api/v1/cloud-build/webhook",
                    "callback_secret": BUILD_CALLBACK_SECRET or ""
                }
            }
            
            repo_owner, repo_name = GITHUB_REPO.split("/")
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/cloud-compile.yml/dispatches"
            
            response = await client.post(url, headers=headers, json=payload)
            
            conn = await get_db()
            if response.status_code != 204:
                logger.error(f"GitHub API Error: {response.text}")
                await conn.execute(
                    "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
                    f"GitHub Trigger Failed: {response.text}", build_id
                )
            else:
                await conn.execute(
                    "UPDATE cloud_builds SET status = 'queued', progress = 10, started_at = NOW() WHERE id = $1",
                    build_id
                )

    except Exception as e:
        logger.error(f"Failed to trigger build: {e}")
        # Only acquire connection if not already acquired
        if conn is None:
            conn = await get_db()
        await conn.execute(
            "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
            str(e), build_id
        )
    finally:
        if conn:
            await release_db(conn)


@router.post("/start", response_model=CloudBuildResponse)
async def start_cloud_build(
    request: CloudBuildRequest, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Start a new cloud build process."""
    conn = await get_db()
    try:
        # 1. Check Tier Limits
        limits = await get_user_tier_limits(user["id"], conn)
        
        # Check if cloud_compilation is enabled for this tier
        if not limits.get("cloud_compilation", False):
            raise HTTPException(403, "Cloud compilation requires Pro tier or higher")
        
        # Check monthly usage
        max_builds = limits.get("cloud_builds_per_month", 0)
        if max_builds == 0:
            raise HTTPException(403, "Cloud builds not available on your current plan")
        
        if max_builds != -1:  # -1 means unlimited
            current_month_builds = await conn.fetchval("""
                SELECT COUNT(*) FROM cloud_builds 
                WHERE user_id = $1 
                AND created_at >= DATE_TRUNC('month', NOW())
            """, user["id"])
            
            if current_month_builds >= max_builds:
                raise HTTPException(403, f"Monthly cloud build limit reached ({max_builds}). Upgrade your plan for more builds.")
            
        # 2. Get Project Info
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            request.project_id, user["id"]
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        # Parse project settings
        project_settings = project["settings"] or {}
        if isinstance(project_settings, str):
            project_settings = json.loads(project_settings) if project_settings else {}
            
        # 3. Validate source directory exists
        # FIX: The correct path is UPLOAD_DIR / project_id / "source"
        # Security: Validate project_id to prevent path traversal attacks
        safe_project_dir = validate_safe_path(UPLOAD_DIR, request.project_id)
        source_dir = safe_project_dir / "source"
        
        if not source_dir.exists():
            # Try alternate path structure
            projects_base = UPLOAD_DIR / "projects"
            projects_base.mkdir(parents=True, exist_ok=True)
            safe_alt_project_dir = validate_safe_path(projects_base, request.project_id)
            alt_source_dir = safe_alt_project_dir / "source"
            if alt_source_dir.exists():
                source_dir = alt_source_dir
            else:
                raise HTTPException(
                    400, 
                    "No source files found. Please upload a ZIP file first using the project upload feature."
                )
        
        # Check if source directory has files
        source_files = list(source_dir.iterdir()) if source_dir.exists() else []
        if not source_files:
            raise HTTPException(400, "Source directory is empty. Please upload project files first.")
        
        # 4. Create Build Record
        build_id = f"bld_{secrets.token_hex(8)}"
        
        # Determine entry file
        language = project.get("language", "python") if hasattr(project, "get") else project["language"]
        entry_file = project_settings.get("entry_file")
        if not entry_file:
            entry_file = "main.py" if language == "python" else "index.js"
        
        # Determine output name
        output_name = project_settings.get("output_name")
        if not output_name:
            project_name = project.get("name", "app") if hasattr(project, "get") else project["name"]
            output_name = project_name.replace(" ", "_")
        
        # Get license key if specified
        license_key = "GENERIC_BUILD"
        if request.license_id:
            license_key = await get_license_key(request.license_id, conn)
        
        # Get public API URL for license validation
        public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        
        # Prepare Config
        config = {
            "project_id": request.project_id,
            "project_name": project.get("name", "Project") if hasattr(project, "get") else project["name"],
            "language": language,
            "entry_file": entry_file,
            "output_name": output_name,
            "target_platform": request.target_platform,
            "license_key": license_key,
            "api_url": f"{public_api_url}/api/v1/license/validate",
        }
        
        await conn.execute(
            """
            INSERT INTO cloud_builds (
                id, project_id, user_id, language, entry_file, output_name, config_json, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
            """,
            build_id, request.project_id, user["id"], language,
            entry_file, output_name, json.dumps(config)
        )
        
        # 5. Trigger Background Task
        background_tasks.add_task(trigger_github_build, build_id, config, source_dir)
        
        return CloudBuildResponse(
            build_id=build_id, 
            status="pending", 
            message="Cloud build started. Check status for updates."
        )
        
    finally:
        await release_db(conn)


@router.post("/webhook")
async def build_webhook(request: Request):
    """Callback from GitHub Actions when build completes."""
    # Verify HMAC signature (secure method only - query param auth removed for security)
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid webhook signature")
    
    # Re-read body since it was consumed by verify_webhook_signature
    body_bytes = await request.body()
    payload = json.loads(body_bytes)
    
    build_id = payload.get("build_id")
    if not build_id:
        raise HTTPException(400, "Missing build_id in payload")
    
    status = payload.get("status")  # completed, failed
    download_key = payload.get("download_key")
    filename = payload.get("filename")
    error = payload.get("error")
    
    conn = await get_db()
    try:
        # Verify build exists
        existing = await conn.fetchrow("SELECT id FROM cloud_builds WHERE id = $1", build_id)
        if not existing:
            raise HTTPException(404, "Build not found")
        
        if status == "completed":
            await conn.execute(
                """
                UPDATE cloud_builds 
                SET status = 'completed', progress = 100, 
                    download_key = $1, download_filename = $2,
                    completed_at = NOW(),
                    expires_at = NOW() + INTERVAL '7 days'
                WHERE id = $3
                """,
                download_key, filename, build_id
            )
            logger.info(f"Cloud build {build_id} completed successfully")
        else:
            await conn.execute(
                """
                UPDATE cloud_builds 
                SET status = 'failed', error_message = $1, completed_at = NOW()
                WHERE id = $2
                """,
                error or "Unknown error", build_id
            )
            logger.warning(f"Cloud build {build_id} failed: {error}")
            
    finally:
        await release_db(conn)
        
    return {"status": "ok"}


@router.get("/{build_id}")
async def get_build_status(build_id: str, user: dict = Depends(get_current_user)):
    """Poll build status."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id, user["id"]
        )
        if not build:
            raise HTTPException(404, "Build not found")
            
        result = {
            "id": build["id"],
            "project_id": build["project_id"],
            "status": build["status"],
            "progress": build["progress"] or 0,
            "language": build["language"],
            "entry_file": build["entry_file"],
            "output_name": build["output_name"],
            "error_message": build["error_message"],
            "created_at": build["created_at"].isoformat() if build["created_at"] else None,
            "started_at": build["started_at"].isoformat() if build["started_at"] else None,
            "completed_at": build["completed_at"].isoformat() if build["completed_at"] else None,
        }
        
        # If completed, generate download URL
        if build["status"] == "completed" and build["download_key"]:
            if storage_service.is_cloud_enabled() and storage_service.client:
                url = storage_service.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': storage_service.bucket, 'Key': build["download_key"]},
                    ExpiresIn=3600
                )
                result["download_url"] = url
                result["download_filename"] = build["download_filename"]
                
        return result
    finally:
        await release_db(conn)


@router.get("/{build_id}/download")
async def download_build(build_id: str, user: dict = Depends(get_current_user)):
    """Get presigned download URL for completed build."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            """
            SELECT * FROM cloud_builds 
            WHERE id = $1 AND user_id = $2 AND status = 'completed'
            """, 
            build_id, user["id"]
        )
        
        if not build:
            raise HTTPException(404, "Build not found or not ready")
        
        if build["expires_at"] and build["expires_at"] < datetime.utcnow():
            raise HTTPException(410, "Download link has expired. Please rebuild.")
        
        if not build["download_key"]:
            raise HTTPException(404, "No download available for this build")
        
        # Generate presigned URL (valid for 1 hour)
        if storage_service.is_cloud_enabled() and storage_service.client:
            url = storage_service.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': storage_service.bucket, 'Key': build["download_key"]},
                ExpiresIn=3600
            )
            return {"download_url": url, "filename": build["download_filename"]}
        else:
            raise HTTPException(500, "Cloud storage not configured")
    finally:
        await release_db(conn)


@router.get("")
async def list_builds(user: dict = Depends(get_current_user)):
    """List all cloud builds for the current user."""
    conn = await get_db()
    try:
        builds = await conn.fetch(
            """
            SELECT cb.*, p.name as project_name 
            FROM cloud_builds cb
            JOIN projects p ON cb.project_id = p.id
            WHERE cb.user_id = $1 
            ORDER BY cb.created_at DESC
            LIMIT 50
            """,
            user["id"]
        )
        
        return [
            {
                "id": b["id"],
                "project_id": b["project_id"],
                "project_name": b["project_name"],
                "status": b["status"],
                "progress": b["progress"] or 0,
                "language": b["language"],
                "created_at": b["created_at"].isoformat() if b["created_at"] else None,
                "completed_at": b["completed_at"].isoformat() if b["completed_at"] else None,
                "error_message": b["error_message"],
            }
            for b in builds
        ]
    finally:
        await release_db(conn)


@router.delete("/{build_id}")
async def cancel_build(build_id: str, user: dict = Depends(get_current_user)):
    """Cancel a pending or queued build."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id, user["id"]
        )
        
        if not build:
            raise HTTPException(404, "Build not found")
        
        if build["status"] not in ("pending", "queued"):
            raise HTTPException(400, f"Cannot cancel build with status: {build['status']}")
        
        await conn.execute(
            "UPDATE cloud_builds SET status = 'cancelled', completed_at = NOW() WHERE id = $1",
            build_id
        )
        
        return {"status": "cancelled", "build_id": build_id}
    finally:
        await release_db(conn)
