from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import json
import httpx
import hmac
import hashlib
import secrets
import re
from pathlib import Path
from datetime import datetime, timezone

from database import get_db, release_db
from storage_service import storage_service
from utils import get_current_user, get_user_tier_limits, get_user_tier
from config import GITHUB_TOKEN, GITHUB_REPO, BUILD_CALLBACK_SECRET, ENVIRONMENT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cloud-build", tags=["cloud-build"])

# Local upload directory - should match project_routes
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_safe_path(base_dir: Path, user_input: str) -> Path:
    """Validate that user input doesn't escape the base directory."""
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]*$', user_input):
        raise HTTPException(400, "Invalid path component: only alphanumeric, dashes, underscores allowed")
    
    if ".." in user_input or "/" in user_input or "\\" in user_input:
        raise HTTPException(400, "Invalid path component")
    
    candidate = base_dir / os.path.basename(user_input)
    
    try:
        resolved = candidate.resolve()
        base_resolved = base_dir.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise HTTPException(400, "Invalid path component")
        return resolved
    except (OSError, ValueError):
        raise HTTPException(400, "Invalid path component")


class CloudBuildRequest(BaseModel):
    project_id: str
    license_id: Optional[str] = None
    target_platforms: List[str] = ["windows"]  # windows, macos, linux


class CloudBuildResponse(BaseModel):
    build_id: str
    status: str
    message: str


async def get_license_key(license_id: str, conn) -> str:
    row = await conn.fetchrow("SELECT key FROM licenses WHERE id = $1", license_id)
    return row["key"] if row else "GENERIC_BUILD"


async def verify_webhook_signature(request: Request) -> bool:
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
    import shutil
    zip_path = source_dir.parent / f"source_{build_id}.zip"
    
    try:
        shutil.make_archive(str(zip_path.with_suffix("")), 'zip', source_dir)
        with open(zip_path, "rb") as f:
            content = f.read()
        
        key = f"builds/{build_id}/source.zip"
        
        if storage_service.is_cloud_enabled() and storage_service.client:
            s3 = storage_service.client
            bucket = storage_service.bucket
            s3.put_object(Bucket=bucket, Key=key, Body=content)
            return s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=3600
            )
        else:
            if ENVIRONMENT == "production":
                raise HTTPException(500, "Cloud Builds require R2 in production.")
            
            public_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
            return f"{public_url}/uploads/{build_id}/source.zip"
    finally:
        if zip_path.exists():
            zip_path.unlink()


async def trigger_github_build(build_id: str, config: dict, source_dir: Path):
    conn = None
    try:
        if not GITHUB_TOKEN or not GITHUB_REPO:
            raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be configured.")

        source_url = await upload_source_to_r2(build_id, source_dir)
        
        public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        
        # Convert list of platforms to comma-separated string for GitHub Action
        target_platforms_str = ",".join(config.get("target_platforms", ["windows"]))

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
                    "target_platforms": target_platforms_str,
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
        # 1. Tier Enforcement
        tier = await get_user_tier(user["id"], conn)
        limits = await get_user_tier_limits(user["id"], conn)
        
        # Free Tier Restrictions
        if tier["tier"] == "free":
            # Limit 1: Windows only
            if any(p != "windows" for p in request.target_platforms):
                raise HTTPException(403, "Free plan supports Windows builds only. Upgrade to Pro for macOS/Linux.")
            
            # Limit 2: 5 builds per month
            current_month_builds = await conn.fetchval("""
                SELECT COUNT(*) FROM cloud_builds 
                WHERE user_id = $1 
                AND created_at >= DATE_TRUNC('month', NOW())
            """, user["id"])
            
            if current_month_builds >= 5:
                raise HTTPException(403, "Free plan limit reached (5 builds/month). Upgrade for more.")
        
        # Pro/Enterprise Limit Check
        max_builds = limits.get("cloud_builds_per_month", 0)
        if max_builds != -1 and tier["tier"] != "free":
            current_month_builds = await conn.fetchval("""
                SELECT COUNT(*) FROM cloud_builds 
                WHERE user_id = $1 
                AND created_at >= DATE_TRUNC('month', NOW())
            """, user["id"])
            if current_month_builds >= max_builds:
                 raise HTTPException(403, f"Monthly cloud build limit reached ({max_builds}).")

        # 2. Project Info
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            request.project_id, user["id"]
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        project_settings = project["settings"] or {}
        if isinstance(project_settings, str):
            project_settings = json.loads(project_settings) if project_settings else {}
            
        # 3. Source Validation
        safe_project_dir = validate_safe_path(UPLOAD_DIR, request.project_id)
        source_dir = safe_project_dir / "source"
        
        if not source_dir.exists():
            # Fallback path logic
            projects_base = UPLOAD_DIR / "projects"
            projects_base.mkdir(parents=True, exist_ok=True)
            safe_alt = validate_safe_path(projects_base, request.project_id)
            if (safe_alt / "source").exists():
                source_dir = safe_alt / "source"
            else:
                raise HTTPException(400, "No source files found.")
        
        if not list(source_dir.iterdir()):
             raise HTTPException(400, "Source directory is empty.")
        
        # 4. Create Build Records
        build_id = f"bld_{secrets.token_hex(8)}"
        language = project.get("language", "python") if hasattr(project, "get") else project["language"]
        entry_file = project_settings.get("entry_file", "main.py" if language == "python" else "index.js")
        output_name = project_settings.get("output_name", (project.get("name", "app") if hasattr(project, "get") else project["name"]).replace(" ", "_"))
        
        license_key = "GENERIC_BUILD"
        if request.license_id:
            license_key = await get_license_key(request.license_id, conn)
            
        public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        
        config = {
            "project_id": request.project_id,
            "project_name": project.get("name", "Project") if hasattr(project, "get") else project["name"],
            "language": language,
            "entry_file": entry_file,
            "output_name": output_name,
            "target_platforms": request.target_platforms,
            "license_key": license_key,
            "api_url": f"{public_api_url}/api/v1/license/validate",
        }
        
        # Insert Main Build
        await conn.execute(
            """
            INSERT INTO cloud_builds (
                id, project_id, user_id, language, entry_file, output_name, config_json, status, target_platforms
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', $8)
            """,
            build_id, request.project_id, user["id"], language,
            entry_file, output_name, json.dumps(config), json.dumps(request.target_platforms)
        )
        
        # Insert Artifacts
        for platform in request.target_platforms:
            await conn.execute(
                """
                INSERT INTO cloud_build_artifacts (
                    id, build_id, platform, status
                ) VALUES ($1, $2, $3, 'pending')
                """,
                f"art_{secrets.token_hex(8)}", build_id, platform
            )
        
        background_tasks.add_task(trigger_github_build, build_id, config, source_dir)
        
        return CloudBuildResponse(
            build_id=build_id, 
            status="pending", 
            message="Cloud build started."
        )
        
    finally:
        await release_db(conn)


@router.post("/webhook")
async def build_webhook(request: Request):
    """Callback from GitHub Actions."""
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")
    
    body = await request.body()
    payload = json.loads(body)
    
    build_id = payload.get("build_id")
    platform = payload.get("platform")
    status = payload.get("status")
    
    if not build_id:
        raise HTTPException(400, "Missing build_id")
        
    conn = await get_db()
    try:
        # Update Artifact
        if platform:
            await conn.execute(
                """
                UPDATE cloud_build_artifacts
                SET status = $1, download_key = $2, download_filename = $3, 
                    error_message = $4, completed_at = NOW()
                WHERE build_id = $5 AND platform = $6
                """,
                status, payload.get("download_key"), payload.get("filename"),
                payload.get("error"), build_id, platform
            )
            
        # Check if all artifacts are done
        artifacts = await conn.fetch(
            "SELECT status FROM cloud_build_artifacts WHERE build_id = $1",
            build_id
        )
        
        all_statuses = [a["status"] for a in artifacts]
        if all(s in ["completed", "failed"] for s in all_statuses):
            final_status = "completed" if "completed" in all_statuses else "failed"
            
            # If we only have one artifact, sync its download key to the main table for backward compatibility
            download_key = None
            filename = None
            if len(artifacts) == 1 and final_status == "completed":
                # Get the single artifact data
                art = await conn.fetchrow(
                    "SELECT download_key, download_filename FROM cloud_build_artifacts WHERE build_id = $1",
                    build_id
                )
                download_key = art["download_key"]
                filename = art["download_filename"]

            await conn.execute(
                """
                UPDATE cloud_builds
                SET status = $1, progress = 100, completed_at = NOW(),
                    download_key = $2, download_filename = $3
                WHERE id = $4
                """,
                final_status, download_key, filename, build_id
            )
            
    finally:
        await release_db(conn)
        
    return {"status": "ok"}


@router.get("/{build_id}/status")
async def get_build_status(build_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id, user["id"]
        )
        if not build:
            raise HTTPException(404, "Build not found")
            
        # Get artifacts
        artifacts = await conn.fetch(
            "SELECT * FROM cloud_build_artifacts WHERE build_id = $1",
            build_id
        )
        
        artifact_list = []
        for art in artifacts:
            download_url = None
            if art["status"] == "completed" and art["download_key"]:
                if storage_service.is_cloud_enabled() and storage_service.client:
                    download_url = storage_service.client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': storage_service.bucket, 'Key': art["download_key"]},
                        ExpiresIn=3600
                    )
            
            artifact_list.append({
                "platform": art["platform"],
                "status": art["status"],
                "download_url": download_url,
                "filename": art["download_filename"],
                "error": art["error_message"]
            })

        return {
            "id": build["id"],
            "status": build["status"],
            "target_platforms": json.loads(build["target_platforms"] or '["windows"]'),
            "artifacts": artifact_list,
            "created_at": build["created_at"].isoformat() if build["created_at"] else None,
            "completed_at": build["completed_at"].isoformat() if build["completed_at"] else None,
        }
    finally:
        await release_db(conn)
