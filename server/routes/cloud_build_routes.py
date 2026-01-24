from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import json
import httpx
import hmac
import hashlib
import secrets
import re
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from database import get_db, release_db
from storage_service import storage_service
from utils import get_current_user, get_user_tier_limits, get_user_tier
from config import GITHUB_TOKEN, GITHUB_REPO, BUILD_CALLBACK_SECRET, ENVIRONMENT
from middleware.rate_limiter import get_redis_client

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
    compatibility_mode: bool = False  # Toggle for Turbo Mode optimizations


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
    """
    Upload source to R2. Optimizes by checking for existing project-level source.zip first.
    Task 2.4: Use Existing Source ZIPs (No Re-upload)
    """
    import shutil
    
    # Get project_id from source_dir path
    # source_dir = /uploads/{project_id}/source
    project_id = source_dir.parent.name
    
    # Check if project already has a cached source.zip
    project_source_key = f"uploads/{project_id}/source.zip"
    
    if storage_service.is_cloud_enabled() and storage_service.client:
        s3 = storage_service.client
        bucket = storage_service.bucket
        
        # Check if cached source exists
        try:
            s3.head_object(Bucket=bucket, Key=project_source_key)
            # Found cached source - use it
            logger.info(f"Using cached source zip: {project_source_key}")
            return s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': project_source_key},
                ExpiresIn=3600
            )
        except Exception:
            # No cached source - create and upload new zip
            pass
    
    # Create new zip
    zip_path = source_dir.parent / f"source_{build_id}.zip"
    
    try:
        shutil.make_archive(str(zip_path.with_suffix("")), 'zip', source_dir)
        with open(zip_path, "rb") as f:
            content = f.read()
        
        key = f"builds/{build_id}/source.zip"
        
        if storage_service.is_cloud_enabled() and storage_service.client:
            s3 = storage_service.client
            bucket = storage_service.bucket
            
            # Upload build-specific source
            s3.put_object(Bucket=bucket, Key=key, Body=content)
            
            # Also cache at project level for future builds (best effort)
            try:
                s3.put_object(Bucket=bucket, Key=project_source_key, Body=content)
                logger.info(f"Cached source zip at project level: {project_source_key}")
            except Exception as e:
                logger.warning(f"Failed to cache project source: {e}")
            
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
        
        # Validate webhook URL accessibility (especially for ngrok in development)
        if ENVIRONMENT == "development" and "ngrok" in public_api_url.lower():
            logger.warning(f"[CloudBuild] Using ngrok tunnel: {public_api_url}")
            logger.warning("[CloudBuild] Ensure ngrok tunnel is active! Build webhooks will fail if offline.")
        elif not public_api_url or public_api_url == "http://localhost:8000":
            logger.warning("[CloudBuild] Using localhost URL - webhooks may not work from GitHub Actions runners!")
        
        # Convert list of platforms to comma-separated string for GitHub Action
        target_platforms_str = ",".join(config.get("target_platforms", ["windows"]))

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Build workflow inputs - only include inputs the workflow accepts
            # Note: plan_tier requires the updated workflow to be pushed to GitHub
            workflow_inputs = {
                "build_id": build_id,
                "project_id": config["project_id"],
                "language": config["language"],
                "target_platforms": target_platforms_str,
                "source_url": source_url,
                "config_json": json.dumps(config),
                "callback_url": f"{public_api_url}/api/v1/cloud-build/webhook",
                "callback_secret": BUILD_CALLBACK_SECRET or "",
            }
            
            # Conditionally add plan_tier - will be ignored if workflow doesn't support it yet
            # TODO: Remove this conditional once workflow is confirmed deployed with plan_tier input
            plan_tier = config.get("plan_tier", "free")
            if plan_tier != "free":  # Only add if non-default to test workflow support
                workflow_inputs["plan_tier"] = plan_tier
            
            payload = {
                "ref": "main",
                "inputs": workflow_inputs
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
                # Try to get the workflow run ID for cancellation support
                github_run_id = None
                try:
                    # Wait a moment for GitHub to create the run
                    await asyncio.sleep(2)
                    
                    # List recent runs for this workflow
                    runs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/cloud-compile.yml/runs?per_page=5"
                    runs_response = await client.get(runs_url, headers=headers)
                    
                    if runs_response.status_code == 200:
                        runs_data = runs_response.json()
                        for run in runs_data.get("workflow_runs", []):
                            # Match by status (queued or in_progress) and recent creation
                            if run.get("status") in ["queued", "in_progress", "pending"]:
                                github_run_id = str(run.get("id"))
                                logger.info(f"[CloudBuild] Captured GitHub run ID: {github_run_id}")
                                break
                except Exception as e:
                    logger.warning(f"Could not capture GitHub run ID: {e}")
                
                await conn.execute(
                    """UPDATE cloud_builds 
                       SET status = 'queued', progress = 10, started_at = NOW(), github_run_id = $2 
                       WHERE id = $1""",
                    build_id, github_run_id
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
        # 1. Tier Enforcement & Platform Restrictions
        tier = await get_user_tier(user["id"], conn)
        limits = await get_user_tier_limits(user["id"], conn)
        
        # Platform restrictions based on tier
        if tier["tier"] == "free":
            # Free tier: Windows & Linux only (macOS costs 10x GitHub minutes)
            if "macos" in request.target_platforms:
                raise HTTPException(
                    403, 
                    "macOS builds require Pro or Enterprise plan (10x compute cost). "
                    "Upgrade or select Windows/Linux only."
                )
        
        # Credit System Enforcement
        # Enterprise has unlimited builds (no credit deduction)
        if tier["tier"] != "enterprise":
            from config import BUILD_COST_STANDARD
            cost = BUILD_COST_STANDARD
            
            user_credits = await conn.fetchval(
                "SELECT build_credits FROM users WHERE id = $1", 
                user["id"]
            )
            
            if user_credits is None:
                user_credits = 0
                
            if user_credits < cost:
                raise HTTPException(
                    403, 
                    f"Insufficient build credits ({user_credits}). "
                    f"This build requires {cost} credits. "
                    "Upgrade your plan or wait for your monthly refill."
                )
            
            # Deduct credits
            await conn.execute(
                "UPDATE users SET build_credits = build_credits - $1 WHERE id = $2",
                cost, user["id"]
            )
        
        # Global concurrency limit (protect GitHub Actions quota)
        active_builds = await conn.fetchval("""
            SELECT COUNT(*) FROM cloud_builds 
            WHERE status IN ('pending', 'queued', 'running')
            AND created_at > NOW() - INTERVAL '2 hours'
        """)
        
        MAX_CONCURRENT_BUILDS = 15  # Leave headroom for GitHub's 20-job limit
        
        if active_builds >= MAX_CONCURRENT_BUILDS:
            raise HTTPException(
                503, 
                f"Build queue is full ({active_builds} active builds). "
                "Please try again in a few minutes."
            )

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
            "plan_tier": tier["tier"],  # Pass tier for dynamic timeout
            "compatibility_mode": request.compatibility_mode,
        }
        
        # Insert Main Build
        await conn.execute(
            """
            INSERT INTO cloud_builds (
                id, project_id, user_id, language, entry_file, output_name, config_json, status, target_platforms, plan_tier
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', $8, $9)
            """,
            build_id, request.project_id, user["id"], language,
            entry_file, output_name, json.dumps(config), json.dumps(request.target_platforms), tier["tier"]
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
    """Callback from GitHub Actions - with retry logic for transient failures."""
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")
    
    body = await request.body()
    payload = json.loads(body)
    
    build_id = payload.get("build_id")
    platform = payload.get("platform")
    status = payload.get("status")
    github_run_id = payload.get("github_run_id")  # Optional: update run ID from workflow
    
    if not build_id:
        raise HTTPException(400, "Missing build_id")
    
    # Retry logic for database connection issues
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        conn = None
        try:
            conn = await get_db()
            
            # Update GitHub run ID if provided
            if github_run_id:
                await conn.execute(
                    "UPDATE cloud_builds SET github_run_id = $1 WHERE id = $2 AND github_run_id IS NULL",
                    str(github_run_id), build_id
                )
            
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
            if all(s in ["completed", "failed", "cancelled"] for s in all_statuses):
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
            else:
                # Update build status to running if any artifact is in progress
                await conn.execute(
                    "UPDATE cloud_builds SET status = 'running' WHERE id = $1 AND status IN ('pending', 'queued')",
                    build_id
                )
            
            logger.info(f"[CloudBuild] Webhook received: {build_id} - {platform} - {status}")
            return {"status": "ok"}
            
        except Exception as e:
            last_error = e
            logger.warning(f"[CloudBuild] Webhook DB error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1, 2, 4 seconds
            continue
        finally:
            if conn:
                await release_db(conn)
    
    # All retries failed
    logger.error(f"[CloudBuild] Webhook failed after {max_retries} retries: {last_error}")
    raise HTTPException(500, f"Database error after retries: {last_error}")


# WebSocket Connection Manager for real-time log streaming
class ConnectionManager:
    """Manages WebSocket connections for build log streaming."""
    
    def __init__(self):
        # build_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, build_id: str):
        await websocket.accept()
        if build_id not in self.active_connections:
            self.active_connections[build_id] = []
        self.active_connections[build_id].append(websocket)
        logger.debug(f"[WS] Client connected to build {build_id}")
    
    def disconnect(self, websocket: WebSocket, build_id: str):
        if build_id in self.active_connections:
            if websocket in self.active_connections[build_id]:
                self.active_connections[build_id].remove(websocket)
            if not self.active_connections[build_id]:
                del self.active_connections[build_id]
        logger.debug(f"[WS] Client disconnected from build {build_id}")
    
    async def broadcast(self, build_id: str, message: dict):
        """Broadcast a message to all connected clients for a build."""
        if build_id not in self.active_connections:
            return
        
        dead_connections = []
        for connection in self.active_connections[build_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn, build_id)


# Global connection manager instance
ws_manager = ConnectionManager()


@router.websocket("/ws/{build_id}")
async def websocket_build_logs(websocket: WebSocket, build_id: str):
    """WebSocket endpoint for real-time build log streaming.
    
    Connect to receive real-time updates for a specific build.
    Messages are JSON with format:
    {
        "type": "progress" | "log" | "status" | "complete",
        "data": { ... }
    }
    """
    # Validate build exists (simple check, no auth for now)
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT id, status FROM cloud_builds WHERE id = $1",
            build_id
        )
        if not build:
            await websocket.close(code=4004, reason="Build not found")
            return
    finally:
        await release_db(conn)
    
    await ws_manager.connect(websocket, build_id)
    
    try:
        # Send initial status
        conn = await get_db()
        try:
            build = await conn.fetchrow(
                "SELECT status, progress, logs FROM cloud_builds WHERE id = $1",
                build_id
            )
            stage, progress = get_build_stage(dict(build))
            await websocket.send_json({
                "type": "status",
                "data": {
                    "status": build["status"],
                    "progress": progress,
                    "stage": stage,
                }
            })
        finally:
            await release_db(conn)
        
        # Keep connection alive, receive pings
        while True:
            try:
                # Wait for messages (ping/pong or close)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, build_id)


async def broadcast_build_update(build_id: str, update_type: str, data: dict):
    """Helper function to broadcast updates to all connected WebSocket clients."""
    await ws_manager.broadcast(build_id, {
        "type": update_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def scheduled_cloud_build_cleanup():
    """
    Scheduled background task to clean up old cloud builds.
    Runs daily to delete old builds based on tier:
    - Free tier: 7 days retention
    - Pro tier: 30 days retention
    - Enterprise: 90 days retention
    """
    logger.info("[CloudBuild Cleanup] Starting scheduled cleanup task")
    
    while True:
        conn = None
        try:
            conn = await get_db()
            
            # Clean up completed builds based on tier retention
            # Free tier: 7 days
            await conn.execute("""
                UPDATE cloud_builds 
                SET deleted_at = NOW()
                WHERE deleted_at IS NULL
                AND created_at < NOW() - INTERVAL '7 days'
                AND status IN ('completed', 'failed', 'cancelled')
                AND (plan_tier = 'free' OR plan_tier IS NULL)
                AND user_id NOT IN (
                    SELECT user_id FROM subscriptions 
                    WHERE plan_tier IN ('pro', 'enterprise') AND status = 'active'
                )
            """)
            
            # Pro tier: 30 days
            await conn.execute("""
                UPDATE cloud_builds 
                SET deleted_at = NOW()
                WHERE deleted_at IS NULL
                AND created_at < NOW() - INTERVAL '30 days'
                AND status IN ('completed', 'failed', 'cancelled')
                AND plan_tier = 'pro'
            """)
            
            # Enterprise tier: 90 days
            await conn.execute("""
                UPDATE cloud_builds 
                SET deleted_at = NOW()
                WHERE deleted_at IS NULL
                AND created_at < NOW() - INTERVAL '90 days'
                AND status IN ('completed', 'failed', 'cancelled')
                AND plan_tier = 'enterprise'
            """)
            
            # Delete orphaned artifacts from storage for deleted builds
            deleted_builds = await conn.fetch("""
                SELECT id FROM cloud_builds 
                WHERE deleted_at IS NOT NULL 
                AND deleted_at > NOW() - INTERVAL '1 day'
            """)
            
            for build in deleted_builds:
                artifacts = await conn.fetch(
                    "SELECT download_key FROM cloud_build_artifacts WHERE build_id = $1 AND download_key IS NOT NULL",
                    build["id"]
                )
                for artifact in artifacts:
                    try:
                        await storage_service.delete_file(artifact["download_key"], is_local=False)
                    except Exception as e:
                        logger.warning(f"[CloudBuild Cleanup] Failed to delete artifact: {e}")
            
            # Clean up old build logs (older than 30 days)
            await conn.execute("""
                DELETE FROM build_logs 
                WHERE created_at < NOW() - INTERVAL '30 days'
            """)
            
            # Reset stuck builds (running for more than 2 hours)
            await conn.execute("""
                UPDATE cloud_builds 
                SET status = 'failed', error_message = 'Build timed out', completed_at = NOW()
                WHERE status IN ('running', 'queued', 'pending')
                AND started_at < NOW() - INTERVAL '2 hours'
            """)
            
            logger.info("[CloudBuild Cleanup] Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"[CloudBuild Cleanup] Failed: {e}")
        finally:
            if conn:
                await release_db(conn)
        
        # Run every 24 hours
        await asyncio.sleep(86400)


def get_build_stage(build: dict) -> tuple[str, int]:
    """Calculate build stage and detailed progress from build status, logs, and timing."""
    status = build["status"]
    logs = build.get("logs") or []
    started_at = build.get("started_at")
    current_progress = build.get("progress", 0)
    
    if isinstance(logs, str):
        try:
            logs = json.loads(logs)
        except Exception:
            logs = []
    
    if status == "pending":
        return "Queued", 5
    elif status == "queued":
        return "Waiting for runner", 8
    elif status == "running":
        # Check logs for stage keywords
        logs_str = " ".join(str(log).lower() for log in logs)
        log_based_progress = 15  # Default
        stage = "Processing"
        
        if "upload" in logs_str:
            stage = "Uploading artifact"
            log_based_progress = 90
        elif "compil" in logs_str or "nuitka" in logs_str or "pkg" in logs_str:
            stage = "Compiling binary"
            log_based_progress = 55
        elif "inject" in logs_str or "wrapper" in logs_str:
            stage = "Injecting license protection"
            log_based_progress = 35
        elif "dependenc" in logs_str or "install" in logs_str or "pip" in logs_str or "npm" in logs_str:
            stage = "Installing dependencies"
            log_based_progress = 20
        elif "download" in logs_str or "source" in logs_str:
            stage = "Downloading source"
            log_based_progress = 12
        
        # Time-based progress interpolation for smoother updates
        if started_at:
            try:
                elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
                # Estimate ~3-4 minutes for typical build (180-240 seconds)
                estimated_duration = 210  # 3.5 minutes average
                time_progress = min(85, int((elapsed / estimated_duration) * 85) + 10)
                
                # Use the maximum of time-based and log-based progress
                # But never exceed current_progress from webhooks if available
                if current_progress and current_progress > 0:
                    # Webhooks provide more accurate progress
                    final_progress = max(current_progress, time_progress, log_based_progress)
                else:
                    final_progress = max(time_progress, log_based_progress)
                
                return stage, min(95, final_progress)  # Cap at 95% until actually complete
            except Exception:
                pass
        
        # Fallback to log-based or webhook progress
        return stage, max(current_progress or 0, log_based_progress)
    
    elif status == "completed":
        return "Completed", 100
    elif status == "failed":
        return "Failed", 100
    elif status == "cancelling":
        return "Cancelling", build.get("progress", 0)
    elif status == "cancelled":
        return "Cancelled", 100
    else:
        return "Unknown", 0


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

        # Calculate stage and detailed progress
        stage, detailed_progress = get_build_stage(dict(build))
        progress = build["progress"] if build["progress"] else detailed_progress

        # Get build-level error message (from trigger failures or first artifact error)
        build_error = build.get("error_message") if hasattr(build, "get") else build["error_message"] if "error_message" in build.keys() else None
        if not build_error:
            # Check artifacts for errors
            for art in artifact_list:
                if art.get("error"):
                    build_error = art["error"]
                    break
        
        response = {
            "id": build["id"],
            "status": build["status"],
            "stage": stage,
            "progress": progress,
            "target_platforms": json.loads(build["target_platforms"] or '["windows"]'),
            "artifacts": artifact_list,
            "error": build_error,  # Include error at build level for frontend
            "created_at": build["created_at"].isoformat() if build["created_at"] else None,
            "completed_at": build["completed_at"].isoformat() if build["completed_at"] else None,
            "retry_count": build["retry_count"] if build["retry_count"] else 0,
        }
        
        # Backward compatibility for single artifact builds
        if len(artifact_list) == 1:
            response["download_key"] = artifact_list[0].get("download_url")
            response["download_filename"] = artifact_list[0].get("filename")

        return response
    finally:
        await release_db(conn)


@router.post("/{build_id}/cancel")
async def cancel_cloud_build(
    build_id: str, 
    user: dict = Depends(get_current_user)
):
    """
    Cancel a running cloud build.
    1. Updates DB status to 'cancelling'
    2. Calls GitHub API to cancel workflow run
    3. Marks artifacts as cancelled
    """
    conn = await get_db()
    try:
        # Get build and verify ownership
        build = await conn.fetchrow(
            "SELECT id, status, github_run_id FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id, user["id"]
        )
        if not build:
            raise HTTPException(404, "Build not found")
        
        if build["status"] not in ["pending", "queued", "running"]:
            return {"message": "Build already completed or cancelled", "status": build["status"]}
        
        # Update status to cancelling
        await conn.execute(
            "UPDATE cloud_builds SET status = 'cancelling' WHERE id = $1",
            build_id
        )
        
        # Cancel GitHub workflow if running
        if build["github_run_id"] and GITHUB_TOKEN and GITHUB_REPO:
            try:
                async with httpx.AsyncClient() as client:
                    headers = {
                        "Authorization": f"Bearer {GITHUB_TOKEN}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                    repo_owner, repo_name = GITHUB_REPO.split("/")
                    # Cancel workflow run
                    response = await client.post(
                        f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{build['github_run_id']}/cancel",
                        headers=headers
                    )
                    if response.status_code not in [202, 204]:
                        logger.warning(f"GitHub cancel API returned {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"Failed to cancel GitHub workflow: {e}")
        
        # Update artifacts
        await conn.execute(
            "UPDATE cloud_build_artifacts SET status = 'cancelled' WHERE build_id = $1 AND status IN ('pending', 'running')",
            build_id
        )
        
        # Final update
        await conn.execute(
            "UPDATE cloud_builds SET status = 'cancelled', completed_at = NOW() WHERE id = $1",
            build_id
        )
        
        logger.info(f"[CloudBuild] Build {build_id} cancelled by user {user['id']}")
        return {"message": "Build cancellation initiated", "status": "cancelled"}
    finally:
        await release_db(conn)


@router.post("/{build_id}/retry")
async def retry_build(
    build_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Retry a failed build (max 3 attempts)."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            """SELECT id, status, retry_count, project_id, config_json, user_id
               FROM cloud_builds WHERE id = $1 AND user_id = $2""",
            build_id, user["id"]
        )
        
        if not build:
            raise HTTPException(404, "Build not found")
        
        if build["status"] not in ["failed", "cancelled"]:
            return {"message": "Only failed or cancelled builds can be retried", "status": build["status"]}
        
        retry_count = build["retry_count"] or 0
        if retry_count >= 3:
            raise HTTPException(400, "Maximum retry attempts (3) reached")
        
        # Create new build with incremented retry count
        new_build_id = f"bld_{secrets.token_hex(8)}"
        config = json.loads(build["config_json"]) if build["config_json"] else {}
        
        await conn.execute("""
            INSERT INTO cloud_builds (
                id, project_id, user_id, language, entry_file, output_name, 
                config_json, target_platforms, status, retry_count
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', $9)
        """, new_build_id, build["project_id"], user["id"], 
           config.get("language", "python"), config.get("entry_file", "main.py"), 
           config.get("output_name", "app"),
           json.dumps(config), json.dumps(config.get("target_platforms", ["windows"])), 
           retry_count + 1)
        
        # Insert artifacts for new build
        for platform in config.get("target_platforms", ["windows"]):
            await conn.execute(
                """INSERT INTO cloud_build_artifacts (id, build_id, platform, status)
                   VALUES ($1, $2, $3, 'pending')""",
                f"art_{secrets.token_hex(8)}", new_build_id, platform
            )
        
        # Trigger build
        safe_project_dir = validate_safe_path(UPLOAD_DIR, build["project_id"])
        source_dir = safe_project_dir / "source"
        
        if source_dir.exists():
            background_tasks.add_task(trigger_github_build, new_build_id, config, source_dir)
        else:
            raise HTTPException(400, "Source files not found for retry")
        
        logger.info(f"[CloudBuild] Build {build_id} retried as {new_build_id} (attempt {retry_count + 1})")
        return {
            "new_build_id": new_build_id,
            "retry_count": retry_count + 1,
            "status": "pending",
            "message": f"Build retry initiated (attempt {retry_count + 2}/4)"
        }
    finally:
        await release_db(conn)


@router.post("/{build_id}/cleanup")
async def cleanup_build_artifacts(
    build_id: str,
    user: dict = Depends(get_current_user)
):
    """Manually delete build artifacts for a specific build."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT id, download_key, status FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id, user["id"]
        )
        if not build:
            raise HTTPException(404, "Build not found")
        
        # Delete from storage
        artifacts = await conn.fetch(
            "SELECT download_key FROM cloud_build_artifacts WHERE build_id = $1",
            build_id
        )
        
        deleted_count = 0
        for artifact in artifacts:
            if artifact["download_key"]:
                try:
                    await storage_service.delete_file(artifact["download_key"], is_local=False)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete artifact {artifact['download_key']}: {e}")
        
        # Mark as deleted in DB
        await conn.execute(
            "UPDATE cloud_builds SET deleted_at = NOW() WHERE id = $1",
            build_id
        )
        
        logger.info(f"[CloudBuild] Build {build_id} artifacts cleaned up ({deleted_count} files)")
        return {"message": f"Artifacts deleted ({deleted_count} files)", "deleted_count": deleted_count}
    finally:
        await release_db(conn)


@router.get("/history")
async def get_build_history(
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    """Get user's cloud build history."""
    conn = await get_db()
    try:
        builds = await conn.fetch(
            """SELECT id, project_id, status, target_platforms, created_at, completed_at, 
                      retry_count, deleted_at
               FROM cloud_builds 
               WHERE user_id = $1 AND deleted_at IS NULL
               ORDER BY created_at DESC
               LIMIT $2 OFFSET $3""",
            user["id"], limit, offset
        )
        
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM cloud_builds WHERE user_id = $1 AND deleted_at IS NULL",
            user["id"]
        )
        
        return {
            "builds": [
                {
                    "id": b["id"],
                    "project_id": b["project_id"],
                    "status": b["status"],
                    "target_platforms": json.loads(b["target_platforms"] or '["windows"]'),
                    "created_at": b["created_at"].isoformat() if b["created_at"] else None,
                    "completed_at": b["completed_at"].isoformat() if b["completed_at"] else None,
                    "retry_count": b["retry_count"] or 0,
                }
                for b in builds
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        await release_db(conn)


@router.post("/webhook/progress")
async def progress_webhook(request: Request):
    """Receive progress updates from GitHub Actions."""
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")
    
    body = await request.json()
    build_id = body.get("build_id")
    platform = body.get("platform")
    progress = body.get("progress", 0)
    stage = body.get("stage", "")
    github_run_id = body.get("github_run_id")  # Capture from first progress update
    
    if not build_id:
        raise HTTPException(400, "Missing build_id")
    
    conn = await get_db()
    try:
        # Update overall progress and github_run_id if provided
        log_entry = f"{stage}: {progress}%"
        if github_run_id:
            await conn.execute("""
                UPDATE cloud_builds 
                SET progress = $1, 
                    logs = COALESCE(logs, '[]'::jsonb) || $2::jsonb,
                    github_run_id = COALESCE(github_run_id, $4)
                WHERE id = $3
            """, progress, json.dumps([log_entry]), build_id, str(github_run_id))
        else:
            await conn.execute("""
                UPDATE cloud_builds 
                SET progress = $1, 
                    logs = COALESCE(logs, '[]'::jsonb) || $2::jsonb
                WHERE id = $3
            """, progress, json.dumps([log_entry]), build_id)
        
        # Update artifact status if platform specified
        if platform:
            await conn.execute("""
                UPDATE cloud_build_artifacts 
                SET status = 'running'
                WHERE build_id = $1 AND platform = $2 AND status = 'pending'
            """, build_id, platform)
        
        # Broadcast to WebSocket clients
        await broadcast_build_update(build_id, "progress", {
            "stage": stage,
            "progress": progress,
            "platform": platform
        })
        
        logger.debug(f"[CloudBuild] Progress update: {build_id} - {stage} ({progress}%)")
    finally:
        await release_db(conn)
    
    return {"status": "ok"}


# =============================================================================
# Build Queue System (Task 4.1)
# =============================================================================

# In-memory queue processing task (runs in background)
_queue_processor_started = False


async def add_to_queue(build_id: str, config: dict, user_id: int, priority: int, project_id: str):
    """Add a build to the Redis queue."""
    redis_client = await get_redis_client()
    if not redis_client:
        # No Redis - trigger immediately
        return await trigger_build_directly(build_id, config, project_id)
    
    queue_name = "cloud_build_queue"
    queue_item = {
        "build_id": build_id,
        "config": config,
        "user_id": user_id,
        "project_id": project_id,
        "priority": priority,
        "timestamp": int(datetime.now(timezone.utc).timestamp())
    }
    
    # Add to sorted set with priority (lower score = higher priority)
    await redis_client.zadd(
        queue_name,
        {json.dumps(queue_item): priority}
    )
    
    # Start queue processor if not already started
    global _queue_processor_started
    if not _queue_processor_started:
        _queue_processor_started = True
        asyncio.create_task(process_build_queue())
    
    # Get queue position
    position = await redis_client.zrank(queue_name, json.dumps(queue_item))
    
    return {
        "status": "queued",
        "position": position if position is not None else 0,
        "message": "Build queued for processing"
    }


async def process_build_queue():
    """Background task that processes builds from the queue."""
    redis_client = await get_redis_client()
    if not redis_client:
        logger.warning("[Queue] Redis not available, queue processing disabled")
        return
    
    queue_name = "cloud_build_queue"
    logger.info("[Queue] Build queue processor started")
    
    while True:
        try:
            # Get highest priority item (lowest score)
            items = await redis_client.zrange(queue_name, 0, 0, withscores=True)
            
            if items:
                queue_item_json, priority = items[0]
                queue_item = json.loads(queue_item_json)
                
                build_id = queue_item["build_id"]
                config = queue_item["config"]
                project_id = queue_item["project_id"]
                
                # Check if build is still pending
                conn = await get_db()
                try:
                    build = await conn.fetchrow(
                        "SELECT status FROM cloud_builds WHERE id = $1",
                        build_id
                    )
                    
                    if build and build["status"] == "pending":
                        # Get source directory
                        safe_project_dir = validate_safe_path(UPLOAD_DIR, project_id)
                        source_dir = safe_project_dir / "source"
                        
                        if not source_dir.exists():
                            projects_base = UPLOAD_DIR / "projects"
                            safe_alt = validate_safe_path(projects_base, project_id)
                            if (safe_alt / "source").exists():
                                source_dir = safe_alt / "source"
                        
                        if source_dir.exists() and list(source_dir.iterdir()):
                            # Trigger the build
                            logger.info(f"[Queue] Processing build {build_id} (priority: {priority})")
                            await trigger_github_build(build_id, config, source_dir)
                        else:
                            logger.error(f"[Queue] Build {build_id} source not found")
                            await conn.execute(
                                "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
                                "Source files not found", build_id
                            )
                    else:
                        logger.info(f"[Queue] Build {build_id} already processed or cancelled")
                finally:
                    await release_db(conn)
                
                # Remove from queue
                await redis_client.zrem(queue_name, queue_item_json)
            else:
                # Queue empty - wait a bit
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"[Queue] Error processing queue: {e}")
            await asyncio.sleep(5)


async def get_queue_position(build_id: str) -> Optional[int]:
    """Get the position of a build in the queue."""
    redis_client = await get_redis_client()
    if not redis_client:
        return None
    
    queue_name = "cloud_build_queue"
    
    # Find item with matching build_id
    all_items = await redis_client.zrange(queue_name, 0, -1, withscores=True)
    for item_json, _ in all_items:
        item = json.loads(item_json)
        if item["build_id"] == build_id:
            # Get rank (0-based, so add 1 for human-readable)
            rank = await redis_client.zrank(queue_name, item_json)
            return rank + 1 if rank is not None else None
    
    return None


async def trigger_build_directly(build_id: str, config: dict, project_id: str):
    """Fallback: trigger build directly without queue."""
    try:
        safe_project_dir = validate_safe_path(UPLOAD_DIR, project_id)
        source_dir = safe_project_dir / "source"
        
        if not source_dir.exists():
            projects_base = UPLOAD_DIR / "projects"
            safe_alt = validate_safe_path(projects_base, project_id)
            if (safe_alt / "source").exists():
                source_dir = safe_alt / "source"
        
        await trigger_github_build(build_id, config, source_dir)
        return {"status": "running", "message": "Build started immediately"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/{build_id}/queue-position")
async def get_queue_status(build_id: str, user: dict = Depends(get_current_user)):
    """Get queue position for a specific build."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT id, status FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id, user["id"]
        )
        if not build:
            raise HTTPException(404, "Build not found")
        
        if build["status"] != "pending":
            return {"position": None, "status": build["status"], "message": "Not in queue"}
        
        position = await get_queue_position(build_id)
        return {
            "position": position,
            "status": "queued",
            "message": f"Your build is #{position} in queue" if position else "In queue"
        }
    finally:
        await release_db(conn)


@router.get("/queue-info")
async def get_queue_info(user: dict = Depends(get_current_user)):
    """Get overall queue information."""
    redis_client = await get_redis_client()
    if not redis_client:
        return {"enabled": False, "message": "Queue not available"}
    
    queue_name = "cloud_build_queue"
    queue_length = await redis_client.zcard(queue_name)
    
    # Get top 5 items
    items = await redis_client.zrange(queue_name, 0, 4, withscores=True)
    queue_preview = []
    
    for item_json, priority in items:
        item = json.loads(item_json)
        queue_preview.append({
            "build_id": item["build_id"],
            "priority": priority,
            "user_id": item["user_id"]
        })
    
    return {
        "enabled": True,
        "length": queue_length,
        "preview": queue_preview
    }
