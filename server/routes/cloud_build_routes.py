from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
import secrets
import json
import httpx
import logging
import hmac
import hashlib
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

from database import get_db, release_db
from utils import get_current_user, get_user_tier_limits, get_user_tier, utc_now
from storage_service import storage_service
from config import GITHUB_TOKEN, GITHUB_REPO, BUILD_CALLBACK_SECRET, ENVIRONMENT, ADMIN_EMAIL

# Import settings directly to avoid circular imports if possible, or use config
import config as settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cloud-build", tags=["cloud-build"])

# Local upload directory - redefined to match project_routes
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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

async def upload_source_to_r2(build_id: str, source_dir: Path) -> str:
    """
    Zip the source directory and upload to R2.
    Returns the presigned URL for the runner to download.
    """
    import shutil
    
    # create a zip of the source directory
    zip_path = source_dir.parent / f"source_{build_id}.zip"
    
    # We need to zip the contents of source_dir, not source_dir itself
    shutil.make_archive(str(zip_path.with_suffix("")), 'zip', source_dir)
    
    # Read the zip file
    with open(zip_path, "rb") as f:
        content = f.read()
    
    key = f"builds/{build_id}/source.zip"
    
    try:
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
                    "callback_secret": BUILD_CALLBACK_SECRET
                }
            }
            
            response = await client.post(
                f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/cloud-compile.yml/dispatches",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 204:
                logger.error(f"Failed to trigger GitHub workflow: {response.text}")
                # Update status to failed
                conn = await get_db()
                try:
                    await conn.execute(
                        "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
                        f"GitHub API Error: {response.status_code}", build_id
                    )
                finally:
                    await release_db(conn)
            else:
                logger.info(f"Triggered GitHub build for {build_id}")

    except Exception as e:
        logger.error(f"Error triggering cloud build: {e}", exc_info=True)
        # Update status to failed
        conn = await get_db()
        try:
            await conn.execute(
                "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
                str(e), build_id
            )
        finally:
            await release_db(conn)

async def verify_webhook_signature(request: Request) -> bool:
    """Verify HMAC signature on build completion webhook."""
    signature = request.headers.get("X-Signature")
    if not signature:
        return False
    
    body = await request.body()
    expected = hmac.new(
        BUILD_CALLBACK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

import os

@router.post("/start", response_model=CloudBuildResponse)
async def start_cloud_build(
    data: CloudBuildRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Start a cloud compilation job."""
    conn = await get_db()
    try:
        # Check tier limits
        limits = await get_user_tier_limits(user["id"], conn)
        max_builds = limits.get("cloud_builds_per_month", 0)
        
        if max_builds == 0:
            raise HTTPException(403, "Cloud builds require Pro subscription")
        
        if max_builds != -1:
            current_month_builds = await conn.fetchval("""
                SELECT COUNT(*) FROM cloud_builds 
                WHERE user_id = $1 
                AND created_at >= DATE_TRUNC('month', NOW())
            """, user["id"])
            
            if current_month_builds >= max_builds:
                raise HTTPException(403, f"Monthly cloud build limit reached ({max_builds})")
        
        # Get project and validate
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            data.project_id, user["id"]
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        settings = json.loads(project["settings"]) if project["settings"] else {}
        
        # Validate project has source files
        source_dir = UPLOAD_DIR / data.project_id / "source"
        if not source_dir.exists():
            raise HTTPException(400, "No source files. Upload a ZIP first.")
        
        # Create build record
        build_id = secrets.token_hex(16)
        
        tier_info = await get_user_tier(user["id"], conn)
        public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        
        config = {
            "project_id": data.project_id,
            "project_name": project["name"],
            "language": project["language"],
            "entry_file": settings.get("entry_file", "main.py"),
            "output_name": settings.get("output_name", project["name"].replace(" ", "_")),
            "license_key": await get_license_key(data.license_id, conn) if data.license_id else "GENERIC_BUILD",
            "api_url": f"{public_api_url}/api/v1/license/validate",
            "show_branding": not tier_info["can_remove_branding"],
        }
        
        await conn.execute("""
            INSERT INTO cloud_builds (id, project_id, user_id, language, entry_file, output_name, config_json, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
        """, build_id, data.project_id, user["id"], project["language"], 
            config["entry_file"], config["output_name"], json.dumps(config))
        
        # Start build in background
        background_tasks.add_task(trigger_github_build, build_id, config, source_dir)
        
        return CloudBuildResponse(
            build_id=build_id,
            status="pending",
            message="Cloud build started. Check status for updates."
        )
    finally:
        await release_db(conn)

@router.get("/{build_id}/status")
async def get_build_status(build_id: str, user: dict = Depends(get_current_user)):
    """Get status of a cloud build."""
    conn = await get_db()
    try:
        build = await conn.fetchrow("""
            SELECT * FROM cloud_builds 
            WHERE id = $1 AND user_id = $2
        """, build_id, user["id"])
        
        if not build:
            raise HTTPException(404, "Build not found")
        
        # Generate download URL if completed
        download_url = None
        if build["status"] == "completed":
             # Generate presigned URL (valid for 1 hour)
            if storage_service.is_cloud_enabled() and storage_service.client:
                s3 = storage_service.client
                bucket = storage_service.bucket
                download_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': build["download_key"]},
                    ExpiresIn=3600
                )
        
        return {
            "build_id": build["id"],
            "status": build["status"],
            "progress": build["progress"],
            "download_url": download_url,
            "filename": build["download_filename"],
            "error": build["error_message"],
            "started_at": build["started_at"].isoformat() if build["started_at"] else None,
            "completed_at": build["completed_at"].isoformat() if build["completed_at"] else None,
        }
    finally:
        await release_db(conn)

@router.post("/webhook")
async def build_completion_webhook(request: Request):
    """Webhook called by GitHub Actions when build completes."""
    # Verify HMAC signature
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")
    
    body = await request.json()
    build_id = body["build_id"]
    
    conn = await get_db()
    try:
        if body["status"] == "completed":
            await conn.execute("""
                UPDATE cloud_builds 
                SET status = 'completed',
                    progress = 100,
                    download_key = $2,
                    download_filename = $3,
                    completed_at = NOW(),
                    expires_at = NOW() + INTERVAL '7 days'
                WHERE id = $1
            """, build_id, body["download_key"], body["filename"])
            
            # TODO: Send email notification
        else:
            await conn.execute("""
                UPDATE cloud_builds 
                SET status = 'failed',
                    error_message = $2,
                    completed_at = NOW()
                WHERE id = $1
            """, build_id, body.get("error", "Unknown error"))
        
        return {"status": "ok"}
    finally:
        await release_db(conn)

@router.get("/{build_id}/download")
async def download_build(build_id: str, user: dict = Depends(get_current_user)):
    """Get presigned download URL for completed build."""
    conn = await get_db()
    try:
        build = await conn.fetchrow("""
            SELECT * FROM cloud_builds 
            WHERE id = $1 AND user_id = $2 AND status = 'completed'
        """, build_id, user["id"])
        
        if not build:
            raise HTTPException(404, "Build not found or not ready")
        
        # UTC Check
        if build["expires_at"] and build["expires_at"] < utc_now().replace(tzinfo=None):
            raise HTTPException(410, "Download link has expired")
        
        # Generate presigned URL (valid for 1 hour)
        url = None
        if storage_service.is_cloud_enabled() and storage_service.client:
            s3 = storage_service.client
            bucket = storage_service.bucket
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': build["download_key"]},
                ExpiresIn=3600
            )
        
        return {"download_url": url, "filename": build["download_filename"]}
    finally:
        await release_db(conn)
