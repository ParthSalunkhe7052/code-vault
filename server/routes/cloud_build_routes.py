from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import json
import hmac
import hashlib
import secrets
import re
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from database import get_db, release_db
from storage_service import storage_service
from utils import get_current_user, get_current_admin_user, get_user_tier
from config import (
    BUILD_CALLBACK_SECRET,
    ENVIRONMENT,
    GCP_PROJECT_ID,
)
from middleware.rate_limiter import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cloud-build", tags=["cloud-build"])

# Local upload directory - should match project_routes
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_safe_path(base_dir: Path, user_input: str) -> Path:
    """Validate that user input doesn't escape the base directory."""
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]*$", user_input):
        raise HTTPException(
            400,
            "Invalid path component: only alphanumeric, dashes, underscores allowed",
        )

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


def get_remote_build_id(build_row) -> Optional[str]:
    """Return the Cloud Build ID from modern or legacy columns."""
    if not build_row:
        return None
    return build_row.get("gcp_build_id") or build_row.get("github_run_id")


def generate_gcs_signed_url(download_key: str) -> Optional[str]:
    """Generate signed URL for GCS artifacts (Cloud Build) or R2 artifacts (GitHub Actions)"""
    try:
        # Check if download_key is from GCS (Cloud Build) or R2 (GitHub Actions)
        # GCS keys: builds/{build_id}/platform/filename
        # Both use same format, but storage location differs

        # Try GCS first (for Cloud Build artifacts)
        try:
            from google.cloud import storage as gcs_storage
            from datetime import timedelta

            # Initialize GCS client
            gcs_client = gcs_storage.Client()
            bucket = gcs_client.bucket("codevault-builds")
            blob = bucket.blob(download_key)

            # Check if blob exists in GCS
            if blob.exists():
                # Generate signed URL (valid for 1 hour)
                signed_url = blob.generate_signed_url(
                    version="v4", expiration=timedelta(hours=1), method="GET"
                )
                logger.info(f"[CloudBuild] Generated GCS signed URL for {download_key}")
                return signed_url
        except Exception as gcs_error:
            logger.debug(f"[CloudBuild] Not in GCS or error: {gcs_error}")

        # Fallback to R2 (for GitHub Actions artifacts)
        if storage_service.is_cloud_enabled() and storage_service.client:
            r2_url = storage_service.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": storage_service.bucket, "Key": download_key},
                ExpiresIn=3600,
            )
            logger.info(f"[CloudBuild] Generated R2 signed URL for {download_key}")
            return r2_url

        logger.warning(f"[CloudBuild] Could not generate signed URL for {download_key}")
        return None

    except Exception as e:
        logger.error(f"[CloudBuild] Error generating signed URL: {e}")
        return None


async def verify_webhook_signature(request: Request) -> bool:
    signature = request.headers.get("X-Signature")
    if not signature:
        logger.warning("Webhook received without X-Signature header")
        return False

    body = await request.body()
    expected = hmac.new(
        BUILD_CALLBACK_SECRET.encode() if BUILD_CALLBACK_SECRET else b"",
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature.lower(), expected.lower())


async def invalidate_cached_source(project_id: str):
    """
    Invalidate cached source for a project when files are uploaded/changed.
    This ensures fresh source is always used for new builds.
    """
    if not storage_service.is_cloud_enabled() or not storage_service.client:
        return

    project_source_key = f"uploads/{project_id}/source.zip"

    try:
        s3 = storage_service.client
        bucket = storage_service.bucket

        # Check if cached source exists and delete it
        try:
            s3.head_object(Bucket=bucket, Key=project_source_key)
            s3.delete_object(Bucket=bucket, Key=project_source_key)
            logger.info(f"[Cache] Invalidated cached source: {project_source_key}")
        except Exception:
            # Cache doesn't exist, that's fine
            pass
    except Exception as e:
        logger.warning(f"[Cache] Failed to invalidate source cache: {e}")


async def upload_source_to_r2(build_id: str, source_dir: Path) -> str:
    """
    Upload source to R2. Creates fresh zip for each build.
    Cache invalidation ensures new files are always used.
    """
    import shutil

    # Security: Validate source_dir is within allowed base directory
    # This path is constructed from validated project_id via validate_safe_path
    source_dir = source_dir.resolve()
    if not str(source_dir).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(400, "Invalid source directory path")

    # Create new zip (always fresh, no caching to avoid stale files)
    zip_path = source_dir.parent / f"source_{build_id}.zip"

    try:
        # Copy cloud_runner.py to source directory so it's available in Cloud Build
        try:
            # Path calculation: cloud_build_routes.py is at server/routes/
            # Go up 2 levels to reach project root: server/routes -> server -> root
            project_root = Path(__file__).parent.parent.parent
            script_source = project_root / ".github" / "scripts" / "cloud_runner.py"

            logger.info(f"[Upload] Looking for cloud_runner.py at: {script_source}")

            # If not found, try alternative paths
            if not script_source.exists():
                # Try from current working directory
                alt_source = Path.cwd() / ".github" / "scripts" / "cloud_runner.py"
                if alt_source.exists():
                    script_source = alt_source
                    logger.info(f"[Upload] Found cloud_runner.py at cwd: {alt_source}")

            script_dest = source_dir / ".github" / "scripts" / "cloud_runner.py"

            if script_source.exists():
                script_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(script_source, script_dest)
                # Verify copy succeeded
                if script_dest.exists():
                    logger.info(
                        f"[Upload] Successfully copied cloud_runner.py to source ({script_dest.stat().st_size} bytes)"
                    )
                else:
                    logger.error(
                        f"[Upload] Copy appeared to succeed but file not found at: {script_dest}"
                    )
            else:
                logger.error(f"[Upload] cloud_runner.py NOT FOUND at: {script_source}")
                logger.error(f"[Upload] Project root resolved to: {project_root}")
                logger.error(
                    f"[Upload] Files in .github/scripts: {list((project_root / '.github' / 'scripts').glob('*')) if (project_root / '.github' / 'scripts').exists() else 'directory does not exist'}"
                )
        except Exception as e:
            logger.error(f"[Upload] Failed to copy cloud_runner.py: {e}")
            import traceback

            logger.error(f"[Upload] Traceback: {traceback.format_exc()}")

        # Log source directory contents
        total_size = sum(f.stat().st_size for f in source_dir.rglob("*") if f.is_file())
        file_count = len([f for f in source_dir.rglob("*") if f.is_file()])
        logger.info(
            f"[Upload] Creating zip from {file_count} files ({total_size} bytes total)"
        )

        shutil.make_archive(str(zip_path.with_suffix("")), "zip", source_dir)
        zip_size = zip_path.stat().st_size
        logger.info(f"[Upload] Created zip: {zip_size} bytes")

        with open(zip_path, "rb") as f:
            content = f.read()

        if len(content) != zip_size:
            logger.error(
                f"[Upload] Size mismatch: file={zip_size}, read={len(content)}"
            )
            raise ValueError("Zip file size mismatch")

        key = f"builds/{build_id}/source.zip"

        if storage_service.is_cloud_enabled() and storage_service.client:
            s3 = storage_service.client
            bucket = storage_service.bucket

            # Upload build-specific source
            s3.put_object(Bucket=bucket, Key=key, Body=content)

            return s3.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
            )
        else:
            if ENVIRONMENT == "production":
                raise HTTPException(500, "Cloud Builds require R2 in production.")

            public_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
            return f"{public_url}/uploads/{build_id}/source.zip"
    finally:
        if zip_path.exists():
            zip_path.unlink()


async def trigger_cloud_build(build_id: str, config: dict, source_dir: Path) -> bool:
    """Trigger a Cloud Build job using gcloud CLI wrapper."""
    # Security: Validate source_dir is within allowed base directory
    # This path is constructed from validated project_id via validate_safe_path
    source_dir = source_dir.resolve()
    if not str(source_dir).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(400, "Invalid source directory path")

    conn = None
    try:
        # Import Cloud Build client
        import sys
        from pathlib import Path as PathLib

        # Add parent directory to path to import modules from CodeVault root
        wrapper_path = PathLib(__file__).parent.parent.parent
        if str(wrapper_path) not in sys.path:
            sys.path.insert(0, str(wrapper_path))

        # Use Cloud Build API on Windows to avoid cmd.exe interpreting & characters in URLs
        if sys.platform == "win32":
            from cloud_build_integration import CloudBuildClient

            logger.info("[CloudBuild] Using Cloud Build API client (Windows detected)")
        else:
            from cloud_build_cli_wrapper import CloudBuildClient

            logger.info("[CloudBuild] Using gcloud CLI wrapper")

        # Upload source to R2 (still needed for Cloud Build to download)
        source_url = await upload_source_to_r2(build_id, source_dir)

        public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")

        # Validate webhook URL accessibility (especially for ngrok in development)
        if ENVIRONMENT == "development" and "ngrok" in public_api_url.lower():
            logger.warning(f"[CloudBuild] Using ngrok tunnel: {public_api_url}")
            logger.warning(
                "[CloudBuild] Ensure ngrok tunnel is active! Build webhooks will fail if offline."
            )
        elif not public_api_url or public_api_url == "http://localhost:8000":
            logger.warning(
                "[CloudBuild] Using localhost URL - webhooks may not work from Cloud Build runners!"
            )

        # Convert list of platforms to comma-separated string
        target_platforms_str = ",".join(config.get("target_platforms", ["windows"]))

        # Build config dict for Cloud Build
        build_config = {
            "build_id": build_id,
            "project_id": config["project_id"],
            "language": config["language"],
            "target_platforms": target_platforms_str,
            "source_url": source_url,
            "config": config,
            "callback_url": f"{public_api_url}/api/v1/cloud-build/webhook",
            "callback_secret": BUILD_CALLBACK_SECRET or "",
            "plan_tier": config.get("plan_tier", "free"),
            "compatibility_mode": config.get("compatibility_mode", False),
            "fast_build": config.get("fast_build", False),
        }

        # Trigger build via CLI wrapper
        logger.info(f"[CloudBuild] Triggering Cloud Build for {build_id}")
        cloud_build = CloudBuildClient(project_id=GCP_PROJECT_ID)
        result = cloud_build.trigger_build(build_config)

        # Store Cloud Build ID in modern column and legacy fallback column
        gcp_build_id = result["build_id"]
        logs_url = result.get("logs_url", "")

        conn = await get_db()
        await conn.execute(
            """UPDATE cloud_builds 
               SET status = 'queued', progress = 10, started_at = NOW(),
                   gcp_build_id = $2,
                   github_run_id = COALESCE(github_run_id, $2),
                   logs = $3
               WHERE id = $1""",
            build_id,
            gcp_build_id,
            json.dumps([f"Cloud Build triggered: {gcp_build_id}", f"Logs: {logs_url}"]),
        )

        logger.info(
            f"[CloudBuild] Successfully triggered build {build_id} -> GCP Build {gcp_build_id}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to trigger Cloud Build: {e}")
        if conn is None:
            conn = await get_db()
        await conn.execute(
            "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
            str(e),
            build_id,
        )
        return False
    finally:
        if conn:
            await release_db(conn)


@router.post("/start", response_model=CloudBuildResponse)
async def start_cloud_build(
    request: CloudBuildRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Start a new cloud build process."""
    conn = await get_db()
    deducted_credits = 0
    queue_accepted = False
    build_id = None
    try:
        # 1. Tier Enforcement & Platform Restrictions
        tier = await get_user_tier(user["id"], conn)
        # limits = await get_user_tier_limits(user["id"], conn)  # Unused

        # macOS cloud builds are currently unsupported by the active runner setup.
        if "macos" in request.target_platforms:
            raise HTTPException(
                400,
                "macOS cloud builds are temporarily unavailable. Select Windows and/or Linux.",
            )

        # Credit System Enforcement
        # Business has unlimited builds (no credit deduction)
        if tier["tier"] != "business":
            from config import BUILD_COST_STANDARD

            cost = BUILD_COST_STANDARD

            user_credits = await conn.fetchval(
                "SELECT build_credits FROM users WHERE id = $1", user["id"]
            )

            if user_credits is None:
                user_credits = 0

            if user_credits < cost:
                raise HTTPException(
                    403,
                    f"Insufficient build credits ({user_credits}). "
                    f"This build requires {cost} credits. "
                    "Upgrade your plan or wait for your monthly refill.",
                )

            # Deduct credits atomically
            updated_credits = await conn.fetchval(
                """
                UPDATE users
                SET build_credits = build_credits - $1
                WHERE id = $2 AND build_credits >= $1
                RETURNING build_credits
                """,
                cost,
                user["id"],
            )
            if updated_credits is None:
                raise HTTPException(
                    403,
                    "Insufficient build credits. Please refresh and try again.",
                )
            deducted_credits = cost

        # Global concurrency limit (protect Cloud Build quota)
        active_builds = await conn.fetchval("""
            SELECT COUNT(*) FROM cloud_builds 
            WHERE status IN ('pending', 'queued', 'running')
            AND created_at > NOW() - INTERVAL '2 hours'
        """)

        MAX_CONCURRENT_BUILDS = 15  # Cloud Build concurrent build limit

        if active_builds >= MAX_CONCURRENT_BUILDS:
            raise HTTPException(
                503,
                f"Build queue is full ({active_builds} active builds). "
                "Please try again in a few minutes.",
            )

        # 2. Project Info
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
            request.project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(404, "Project not found")

        project_settings = project["settings"] or {}
        if isinstance(project_settings, str):
            project_settings = json.loads(project_settings) if project_settings else {}

        # 3. Source Validation
        # Security: Validate project_id and construct safe source directory path
        safe_project_dir = validate_safe_path(UPLOAD_DIR, request.project_id)
        source_dir = safe_project_dir / "source"

        # Validate the constructed path is within UPLOAD_DIR
        source_dir = source_dir.resolve()
        if not str(source_dir).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(400, "Invalid source directory path")

        if not source_dir.exists():
            # Fallback path logic
            projects_base = UPLOAD_DIR / "projects"
            projects_base.mkdir(parents=True, exist_ok=True)
            safe_alt = validate_safe_path(projects_base, request.project_id)
            if (safe_alt / "source").exists():
                source_dir = safe_alt / "source"
                # Re-validate after path change
                source_dir = source_dir.resolve()
                if not str(source_dir).startswith(str(projects_base.resolve())):
                    raise HTTPException(400, "Invalid source directory path")
            else:
                raise HTTPException(400, "No source files found.")

        if not list(source_dir.iterdir()):
            raise HTTPException(400, "Source directory is empty.")

        # 4. Create Build Records
        build_id = f"bld_{secrets.token_hex(8)}"
        language = (
            project.get("language", "python")
            if hasattr(project, "get")
            else project["language"]
        )

        # Helper to get setting or default
        def get_setting(key, default):
            val = project_settings.get(key)
            return val if val else default

        entry_file = get_setting(
            "entry_file", "main.py" if language == "python" else "index.js"
        )

        # Fix: Ensure output_name is never empty
        project_name = (
            project.get("name", "app") if hasattr(project, "get") else project["name"]
        )
        # Sanitize project name for use as filename
        project_name_safe = "".join(
            c for c in project_name.replace(" ", "_") if c.isalnum() or c in "-_"
        )
        if not project_name_safe:
            project_name_safe = "app"

        output_name = get_setting("output_name", project_name_safe)

        # CRITICAL: Triple-check output_name is never empty
        if not output_name or not output_name.strip():
            output_name = project_name_safe or "app"
            logger.warning(
                f"[CloudBuild] output_name was empty, using fallback: {output_name}"
            )

        license_key = "GENERIC_BUILD"
        if request.license_id:
            license_key = await get_license_key(request.license_id, conn)

        public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")

        config = {
            "project_id": request.project_id,
            "project_name": project.get("name", "Project")
            if hasattr(project, "get")
            else project["name"],
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
            build_id,
            request.project_id,
            user["id"],
            language,
            entry_file,
            output_name,
            json.dumps(config),
            json.dumps(request.target_platforms),
            tier["tier"],
        )

        # Insert Artifacts
        for platform in request.target_platforms:
            await conn.execute(
                """
                INSERT INTO cloud_build_artifacts (
                    id, build_id, platform, status
                ) VALUES ($1, $2, $3, 'pending')
                """,
                f"art_{secrets.token_hex(8)}",
                build_id,
                platform,
            )

        # 5. Add to Queue (Priority based on Tier)
        priority = 10  # Default (Pro)
        if tier["tier"] == "business":
            priority = 1
        elif tier["tier"] == "free":
            priority = 50

        # Use the Redis queue system instead of immediate background task
        queue_result = await add_to_queue(
            build_id, config, user["id"], priority, request.project_id
        )
        queue_status = queue_result.get("status")
        if queue_status not in {"queued", "running"}:
            raise HTTPException(
                500, queue_result.get("message", "Failed to enqueue cloud build")
            )
        queue_accepted = True

        return CloudBuildResponse(
            build_id=build_id,
            status="pending",
            message=queue_result.get("message", "Cloud build queued."),
        )

    except Exception:
        if deducted_credits > 0 and not queue_accepted:
            try:
                await conn.execute(
                    "UPDATE users SET build_credits = build_credits + $1 WHERE id = $2",
                    deducted_credits,
                    user["id"],
                )
                if build_id:
                    await conn.execute(
                        """
                        UPDATE cloud_builds
                        SET status = 'failed',
                            error_message = COALESCE(error_message, 'Build failed before enqueue/trigger. Credit refunded.')
                        WHERE id = $1
                        """,
                        build_id,
                    )
                logger.info(
                    f"[CloudBuild] Refunded {deducted_credits} credit(s) for user {user['id']} after enqueue failure"
                )
            except Exception as refund_error:
                logger.error(f"[CloudBuild] Failed to refund credits: {refund_error}")
        raise
    finally:
        await release_db(conn)


@router.post("/webhook")
async def build_webhook(request: Request):
    """Callback from Cloud Build - with retry logic for transient failures."""
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")

    body = await request.body()
    payload = json.loads(body)

    build_id = payload.get("build_id")
    platform = payload.get("platform")
    status = payload.get("status")
    remote_build_id = payload.get("cloud_build_id") or payload.get("github_run_id")

    if not build_id:
        raise HTTPException(400, "Missing build_id")

    # Retry logic for database connection issues
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        conn = None
        try:
            conn = await get_db()

            # Update Cloud Build ID if provided
            if remote_build_id:
                await conn.execute(
                    """
                    UPDATE cloud_builds
                    SET gcp_build_id = COALESCE(gcp_build_id, $1),
                        github_run_id = COALESCE(github_run_id, $1)
                    WHERE id = $2
                    """,
                    str(remote_build_id),
                    build_id,
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
                    status,
                    payload.get("download_key"),
                    payload.get("filename"),
                    payload.get("error"),
                    build_id,
                    platform,
                )

            # Overall callbacks may omit per-platform statuses (for unsupported targets),
            # so mark remaining in-flight artifacts terminal based on overall result.
            if not platform and status in ["completed", "failed", "cancelled"]:
                fallback_status = "cancelled" if status == "cancelled" else "failed"
                fallback_error = None
                if fallback_status == "failed":
                    fallback_error = payload.get("error") or "No platform artifact callback received"

                await conn.execute(
                    """
                    UPDATE cloud_build_artifacts
                    SET status = $1,
                        error_message = COALESCE(error_message, $2),
                        completed_at = NOW()
                    WHERE build_id = $3 AND status IN ('pending', 'running')
                    """,
                    fallback_status,
                    fallback_error,
                    build_id,
                )

            # Check if all artifacts are done
            artifacts = await conn.fetch(
                "SELECT status FROM cloud_build_artifacts WHERE build_id = $1", build_id
            )

            all_statuses = [a["status"] for a in artifacts]
            if all(s in ["completed", "failed", "cancelled"] for s in all_statuses):
                if all_statuses and all(s == "cancelled" for s in all_statuses):
                    final_status = "cancelled"
                elif "completed" in all_statuses:
                    final_status = "completed"
                else:
                    final_status = "failed"

                # If we only have one artifact, sync its download key to the main table for backward compatibility
                download_key = None
                filename = None
                if len(artifacts) == 1 and final_status == "completed":
                    # Get the single artifact data
                    art = await conn.fetchrow(
                        "SELECT download_key, download_filename FROM cloud_build_artifacts WHERE build_id = $1",
                        build_id,
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
                    final_status,
                    download_key,
                    filename,
                    build_id,
                )
            else:
                # Update build status to running if any artifact is in progress
                await conn.execute(
                    "UPDATE cloud_builds SET status = 'running' WHERE id = $1 AND status IN ('pending', 'queued')",
                    build_id,
                )

            logger.info(
                f"[CloudBuild] Webhook received: {build_id} - {platform} - {status}"
            )
            return {"status": "ok"}

        except Exception as e:
            last_error = e
            logger.warning(
                f"[CloudBuild] Webhook DB error (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff: 1, 2, 4 seconds
            continue
        finally:
            if conn:
                await release_db(conn)

    # All retries failed
    logger.error(
        f"[CloudBuild] Webhook failed after {max_retries} retries: {last_error}"
    )
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
            "SELECT id, status FROM cloud_builds WHERE id = $1", build_id
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
                build_id,
            )
            stage, progress = get_build_stage(dict(build))
            await websocket.send_json(
                {
                    "type": "status",
                    "data": {
                        "status": build["status"],
                        "progress": progress,
                        "stage": stage,
                    },
                }
            )
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
    await ws_manager.broadcast(
        build_id,
        {
            "type": update_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def scheduled_cloud_build_cleanup():
    """
    Scheduled background task to clean up old cloud builds.
    Runs daily to delete old builds based on tier:
    - Free tier: 7 days retention
    - Pro tier: 30 days retention
    - Business: 90 days retention
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
                    WHERE plan_tier IN ('pro', 'business') AND status = 'active'
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

            # Business tier: 90 days
            await conn.execute("""
                UPDATE cloud_builds 
                SET deleted_at = NOW()
                WHERE deleted_at IS NULL
                AND created_at < NOW() - INTERVAL '90 days'
                AND status IN ('completed', 'failed', 'cancelled')
                AND plan_tier = 'business'
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
                    build["id"],
                )
                for artifact in artifacts:
                    try:
                        await storage_service.delete_file(
                            artifact["download_key"], is_local=False
                        )
                    except Exception as e:
                        logger.warning(
                            f"[CloudBuild Cleanup] Failed to delete artifact: {e}"
                        )

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
        elif (
            "dependenc" in logs_str
            or "install" in logs_str
            or "pip" in logs_str
            or "npm" in logs_str
        ):
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
                    final_progress = max(
                        current_progress, time_progress, log_based_progress
                    )
                else:
                    final_progress = max(time_progress, log_based_progress)

                return stage, min(
                    95, final_progress
                )  # Cap at 95% until actually complete
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
async def get_build_status(
    build_id: str, user: dict = Depends(get_current_user), sync: bool = False
):
    """
    Get build status.
    If sync=true, syncs with Cloud Build to get real status.
    """
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id,
            user["id"],
        )
        if not build:
            raise HTTPException(404, "Build not found")

        remote_build_id = get_remote_build_id(build)

        # Sync with Cloud Build if requested and build has GCP ID
        if (
            sync
            and remote_build_id
            and build["status"] in ["pending", "queued", "running"]
        ):
            try:
                import sys
                from pathlib import Path as PathLib

                wrapper_path = PathLib(__file__).parent.parent.parent
                if str(wrapper_path) not in sys.path:
                    sys.path.insert(0, str(wrapper_path))

                if sys.platform == "win32":
                    from cloud_build_integration import CloudBuildClient
                else:
                    from cloud_build_cli_wrapper import CloudBuildClient

                cloud_build = CloudBuildClient(project_id=GCP_PROJECT_ID)
                gcp_status = cloud_build.get_build_status(remote_build_id)

                # Map GCP status to our status
                real_gcp_status = gcp_status.get("status", "")
                if real_gcp_status in ["SUCCESS", "FAILURE", "CANCELLED", "EXPIRED"]:
                    status_map = {
                        "SUCCESS": "completed",
                        "FAILURE": "failed",
                        "CANCELLED": "cancelled",
                        "EXPIRED": "failed",
                    }
                    db_status = status_map.get(real_gcp_status, "failed")

                    # Update DB if status changed
                    if db_status != build["status"]:
                        await conn.execute(
                            """UPDATE cloud_builds 
                               SET status = $1, completed_at = NOW(),
                                   error_message = COALESCE(error_message, $2)
                               WHERE id = $3""",
                            db_status,
                            gcp_status.get(
                                "status", f"Build {db_status} in Cloud Build"
                            ),
                            build_id,
                        )

                        # Refresh build data
                        build = await conn.fetchrow(
                            "SELECT * FROM cloud_builds WHERE id = $1", build_id
                        )

                        logger.info(
                            f"[CloudBuild] Synced build {build_id} status from {build['status']} to {db_status}"
                        )

            except Exception as e:
                logger.warning(f"[CloudBuild] Failed to sync status: {e}")

        # Get artifacts
        artifacts = await conn.fetch(
            "SELECT * FROM cloud_build_artifacts WHERE build_id = $1", build_id
        )

        artifact_list = []
        for art in artifacts:
            download_url = None
            if art["status"] == "completed" and art["download_key"]:
                download_url = generate_gcs_signed_url(art["download_key"])

            artifact_list.append(
                {
                    "platform": art["platform"],
                    "status": art["status"],
                    "download_url": download_url,
                    "filename": art["download_filename"],
                    "error": art["error_message"],
                }
            )

        # Calculate stage and detailed progress
        stage, detailed_progress = get_build_stage(dict(build))
        progress = build["progress"] if build["progress"] else detailed_progress

        # Get build-level error message (from trigger failures or first artifact error)
        build_error = (
            build.get("error_message")
            if hasattr(build, "get")
            else build["error_message"]
            if "error_message" in build.keys()
            else None
        )
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
            "created_at": build["created_at"].isoformat()
            if build["created_at"]
            else None,
            "completed_at": build["completed_at"].isoformat()
            if build["completed_at"]
            else None,
            "retry_count": build["retry_count"] if build["retry_count"] else 0,
            "synced": sync,  # Indicate if sync was attempted
        }

        # Backward compatibility for single artifact builds
        if len(artifact_list) == 1:
            response["download_key"] = artifact_list[0].get("download_url")
            response["download_filename"] = artifact_list[0].get("filename")

        return response
    finally:
        await release_db(conn)


@router.post("/{build_id}/sync")
async def sync_build_status(build_id: str, user: dict = Depends(get_current_user)):
    """
    Force sync build status with Cloud Build.
    Useful when webhook hasn't updated the status or status seems stale.
    """
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id,
            user["id"],
        )
        if not build:
            raise HTTPException(404, "Build not found")

        remote_build_id = get_remote_build_id(build)
        if not remote_build_id:
            return {
                "message": "Build not yet submitted to Cloud Build",
                "status": build["status"],
                "synced": False,
            }

        try:
            import sys
            from pathlib import Path as PathLib

            wrapper_path = PathLib(__file__).parent.parent.parent
            if str(wrapper_path) not in sys.path:
                sys.path.insert(0, str(wrapper_path))

            if sys.platform == "win32":
                from cloud_build_integration import CloudBuildClient
            else:
                from cloud_build_cli_wrapper import CloudBuildClient

            cloud_build = CloudBuildClient(project_id=GCP_PROJECT_ID)
            gcp_status = cloud_build.get_build_status(remote_build_id)

            real_gcp_status = gcp_status.get("status", "")

            # Map GCP status
            status_map = {
                "QUEUED": "queued",
                "WORKING": "running",
                "SUCCESS": "completed",
                "FAILURE": "failed",
                "CANCELLED": "cancelled",
                "EXPIRED": "failed",
            }

            db_status = status_map.get(real_gcp_status, build["status"])

            # Only update if status changed
            if db_status != build["status"]:
                await conn.execute(
                    """UPDATE cloud_builds 
                       SET status = $1, 
                           completed_at = CASE WHEN $1 IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END,
                           error_message = COALESCE(error_message, $2)
                       WHERE id = $3""",
                    db_status,
                    gcp_status.get(
                        "status_details", f"Build {db_status} in Cloud Build"
                    ),
                    build_id,
                )

                logger.info(
                    f"[CloudBuild] Manual sync: Build {build_id} status changed from {build['status']} to {db_status}"
                )

                return {
                    "message": "Status synced from Cloud Build",
                    "previous_status": build["status"],
                    "current_status": db_status,
                    "cloud_status": real_gcp_status,
                    "synced": True,
                }
            else:
                return {
                    "message": "Status is already up to date",
                    "status": db_status,
                    "cloud_status": real_gcp_status,
                    "synced": True,
                }

        except Exception as e:
            logger.error(f"[CloudBuild] Manual sync failed: {e}")
            raise HTTPException(500, f"Failed to sync with Cloud Build: {str(e)}")

    finally:
        await release_db(conn)


@router.post("/{build_id}/cancel")
async def cancel_cloud_build(build_id: str, user: dict = Depends(get_current_user)):
    """
    Cancel a running cloud build.
    1. Syncs with Cloud Build to get real status
    2. Updates DB status to 'cancelling'
    3. Calls Cloud Build API to cancel
    4. Marks artifacts as cancelled
    """
    conn = await get_db()
    try:
        # Get build and verify ownership
        build = await conn.fetchrow(
            "SELECT id, status, gcp_build_id, github_run_id FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id,
            user["id"],
        )
        if not build:
            raise HTTPException(404, "Build not found")

        remote_build_id = get_remote_build_id(build)

        # First, sync with Cloud Build to get real status
        if remote_build_id:
            try:
                import sys
                from pathlib import Path as PathLib

                wrapper_path = PathLib(__file__).parent.parent.parent
                if str(wrapper_path) not in sys.path:
                    sys.path.insert(0, str(wrapper_path))

                if sys.platform == "win32":
                    from cloud_build_integration import CloudBuildClient
                else:
                    from cloud_build_cli_wrapper import CloudBuildClient

                cloud_build = CloudBuildClient(project_id=GCP_PROJECT_ID)
                gcp_status = cloud_build.get_build_status(remote_build_id)

                # If build already completed/failed in GCP, update DB to match
                real_status = gcp_status.get("status", build["status"])
                if real_status in ["SUCCESS", "FAILURE", "CANCELLED", "EXPIRED"]:
                    # Map GCP status to our status
                    status_map = {
                        "SUCCESS": "completed",
                        "FAILURE": "failed",
                        "CANCELLED": "cancelled",
                        "EXPIRED": "failed",
                    }
                    db_status = status_map.get(real_status, "failed")

                    # Update DB with real status
                    await conn.execute(
                        """UPDATE cloud_builds 
                           SET status = $1, completed_at = NOW(), 
                               error_message = COALESCE(error_message, $2)
                           WHERE id = $3""",
                        db_status,
                        gcp_status.get("status", "Build failed in Cloud Build"),
                        build_id,
                    )

                    logger.info(
                        f"[CloudBuild] Build {build_id} already {db_status} in GCP, synced DB"
                    )
                    return {
                        "message": f"Build already {db_status}",
                        "status": db_status,
                        "synced_from_cloud": True,
                    }

            except Exception as e:
                logger.warning(f"[CloudBuild] Failed to sync status before cancel: {e}")
                # Continue with cancel attempt anyway

        # Check current status (after potential sync)
        build = await conn.fetchrow(
            "SELECT status, gcp_build_id, github_run_id FROM cloud_builds WHERE id = $1",
            build_id,
        )
        remote_build_id = get_remote_build_id(build)

        if build["status"] not in ["pending", "queued", "running", "cancelling"]:
            return {
                "message": "Build already completed or cancelled",
                "status": build["status"],
            }

        # Update status to cancelling
        await conn.execute(
            "UPDATE cloud_builds SET status = 'cancelling' WHERE id = $1", build_id
        )

        # Cancel Cloud Build job if running
        if remote_build_id:
            try:
                import sys
                from pathlib import Path as PathLib

                wrapper_path = PathLib(__file__).parent.parent.parent
                if str(wrapper_path) not in sys.path:
                    sys.path.insert(0, str(wrapper_path))

                if sys.platform == "win32":
                    from cloud_build_integration import CloudBuildClient
                else:
                    from cloud_build_cli_wrapper import CloudBuildClient

                cloud_build = CloudBuildClient(project_id=GCP_PROJECT_ID)
                cloud_build.cancel_build(remote_build_id)
                logger.info(
                    f"[CloudBuild] Successfully cancelled GCP Build {remote_build_id}"
                )
            except Exception as e:
                logger.error(f"[CloudBuild] Failed to cancel Cloud Build: {e}")
                # Continue to mark as cancelled in DB even if API call failed

        # Update artifacts
        await conn.execute(
            "UPDATE cloud_build_artifacts SET status = 'cancelled' WHERE build_id = $1 AND status IN ('pending', 'running')",
            build_id,
        )

        # Final update
        await conn.execute(
            "UPDATE cloud_builds SET status = 'cancelled', completed_at = NOW() WHERE id = $1",
            build_id,
        )

        logger.info(f"[CloudBuild] Build {build_id} cancelled by user {user['id']}")
        return {"message": "Build cancelled successfully", "status": "cancelled"}
    finally:
        await release_db(conn)


@router.post("/{build_id}/retry")
async def retry_build(
    build_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Retry a failed build (max 3 attempts)."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            """SELECT id, status, retry_count, project_id, config_json, user_id
               FROM cloud_builds WHERE id = $1 AND user_id = $2""",
            build_id,
            user["id"],
        )

        if not build:
            raise HTTPException(404, "Build not found")

        if build["status"] not in ["failed", "cancelled"]:
            return {
                "message": "Only failed or cancelled builds can be retried",
                "status": build["status"],
            }

        retry_count = build["retry_count"] or 0
        if retry_count >= 3:
            raise HTTPException(400, "Maximum retry attempts (3) reached")

        # Create new build with incremented retry count
        new_build_id = f"bld_{secrets.token_hex(8)}"
        config = json.loads(build["config_json"]) if build["config_json"] else {}

        await conn.execute(
            """
            INSERT INTO cloud_builds (
                id, project_id, user_id, language, entry_file, output_name, 
                config_json, target_platforms, status, retry_count
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', $9)
        """,
            new_build_id,
            build["project_id"],
            user["id"],
            config.get("language", "python"),
            config.get("entry_file", "main.py"),
            config.get("output_name", "app"),
            json.dumps(config),
            json.dumps(config.get("target_platforms", ["windows"])),
            retry_count + 1,
        )

        # Insert artifacts for new build
        for platform in config.get("target_platforms", ["windows"]):
            await conn.execute(
                """INSERT INTO cloud_build_artifacts (id, build_id, platform, status)
                   VALUES ($1, $2, $3, 'pending')""",
                f"art_{secrets.token_hex(8)}",
                new_build_id,
                platform,
            )

        # Trigger build
        # Security: Validate project_id and construct safe source directory path
        safe_project_dir = validate_safe_path(UPLOAD_DIR, build["project_id"])
        source_dir = safe_project_dir / "source"

        # Validate the constructed path is within UPLOAD_DIR
        source_dir = source_dir.resolve()
        if not str(source_dir).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(400, "Invalid source directory path")

        if source_dir.exists():
            background_tasks.add_task(
                trigger_cloud_build, new_build_id, config, source_dir
            )
        else:
            raise HTTPException(400, "Source files not found for retry")

        logger.info(
            f"[CloudBuild] Build {build_id} retried as {new_build_id} (attempt {retry_count + 1})"
        )
        return {
            "new_build_id": new_build_id,
            "retry_count": retry_count + 1,
            "status": "pending",
            "message": f"Build retry initiated (attempt {retry_count + 2}/4)",
        }
    finally:
        await release_db(conn)


@router.post("/{build_id}/cleanup")
async def cleanup_build_artifacts(
    build_id: str, user: dict = Depends(get_current_user)
):
    """Manually delete build artifacts for a specific build."""
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            "SELECT id, download_key, status FROM cloud_builds WHERE id = $1 AND user_id = $2",
            build_id,
            user["id"],
        )
        if not build:
            raise HTTPException(404, "Build not found")

        # Delete from storage
        artifacts = await conn.fetch(
            "SELECT download_key FROM cloud_build_artifacts WHERE build_id = $1",
            build_id,
        )

        deleted_count = 0
        for artifact in artifacts:
            if artifact["download_key"]:
                try:
                    await storage_service.delete_file(
                        artifact["download_key"], is_local=False
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to delete artifact {artifact['download_key']}: {e}"
                    )

        # Mark as deleted in DB
        await conn.execute(
            "UPDATE cloud_builds SET deleted_at = NOW() WHERE id = $1", build_id
        )

        logger.info(
            f"[CloudBuild] Build {build_id} artifacts cleaned up ({deleted_count} files)"
        )
        return {
            "message": f"Artifacts deleted ({deleted_count} files)",
            "deleted_count": deleted_count,
        }
    finally:
        await release_db(conn)


@router.get("/history")
async def get_build_history(
    limit: int = 20, offset: int = 0, user: dict = Depends(get_current_user)
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
            user["id"],
            limit,
            offset,
        )

        total = await conn.fetchval(
            "SELECT COUNT(*) FROM cloud_builds WHERE user_id = $1 AND deleted_at IS NULL",
            user["id"],
        )

        return {
            "builds": [
                {
                    "id": b["id"],
                    "project_id": b["project_id"],
                    "status": b["status"],
                    "target_platforms": json.loads(
                        b["target_platforms"] or '["windows"]'
                    ),
                    "created_at": b["created_at"].isoformat()
                    if b["created_at"]
                    else None,
                    "completed_at": b["completed_at"].isoformat()
                    if b["completed_at"]
                    else None,
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
    """Receive progress updates from Cloud Build."""
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")

    body = await request.json()
    build_id = body.get("build_id")
    platform = body.get("platform")
    progress = body.get("progress", 0)
    stage = body.get("stage", "")
    remote_build_id = body.get("cloud_build_id") or body.get("github_run_id")

    if not build_id:
        raise HTTPException(400, "Missing build_id")

    conn = await get_db()
    try:
        # Update overall progress and Cloud Build ID if provided
        log_entry = f"{stage}: {progress}%"
        if remote_build_id:
            await conn.execute(
                """
                UPDATE cloud_builds 
                SET progress = $1, 
                    logs = COALESCE(logs, '[]'::jsonb) || $2::jsonb,
                    gcp_build_id = COALESCE(gcp_build_id, $4),
                    github_run_id = COALESCE(github_run_id, $4)
                WHERE id = $3
            """,
                progress,
                json.dumps([log_entry]),
                build_id,
                str(remote_build_id),
            )
        else:
            await conn.execute(
                """
                UPDATE cloud_builds 
                SET progress = $1, 
                    logs = COALESCE(logs, '[]'::jsonb) || $2::jsonb
                WHERE id = $3
            """,
                progress,
                json.dumps([log_entry]),
                build_id,
            )

        # Update artifact status if platform specified
        if platform:
            await conn.execute(
                """
                UPDATE cloud_build_artifacts 
                SET status = 'running'
                WHERE build_id = $1 AND platform = $2 AND status = 'pending'
            """,
                build_id,
                platform,
            )

        # Broadcast to WebSocket clients
        await broadcast_build_update(
            build_id,
            "progress",
            {"stage": stage, "progress": progress, "platform": platform},
        )

        logger.debug(
            f"[CloudBuild] Progress update: {build_id} - {stage} ({progress}%)"
        )
    finally:
        await release_db(conn)

    return {"status": "ok"}


# =============================================================================
# Build Queue System (Task 4.1)
# =============================================================================

# In-memory queue processing task (runs in background)
_queue_processor_started = False


async def add_to_queue(
    build_id: str, config: dict, user_id: str, priority: int, project_id: str
):
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
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    }

    # Add to sorted set with priority (lower score = higher priority)
    await redis_client.zadd(queue_name, {json.dumps(queue_item): priority})

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
        "message": "Build queued for processing",
    }


async def process_build_queue():
    """Background task that processes builds from the queue."""
    try:
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
                            "SELECT status FROM cloud_builds WHERE id = $1", build_id
                        )

                        if build and build["status"] == "pending":
                            # Get source directory
                            safe_project_dir = validate_safe_path(
                                UPLOAD_DIR, project_id
                            )
                            source_dir = safe_project_dir / "source"

                            if not source_dir.exists():
                                projects_base = UPLOAD_DIR / "projects"
                                safe_alt = validate_safe_path(projects_base, project_id)
                                if (safe_alt / "source").exists():
                                    source_dir = safe_alt / "source"

                            if source_dir.exists() and list(source_dir.iterdir()):
                                # Trigger the build
                                logger.info(
                                    f"[Queue] Processing build {build_id} (priority: {priority})"
                                )
                                await trigger_cloud_build(build_id, config, source_dir)
                            else:
                                logger.error(
                                    f"[Queue] Build {build_id} source not found"
                                )
                                await conn.execute(
                                    "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
                                    "Source files not found",
                                    build_id,
                                )
                        else:
                            logger.info(
                                f"[Queue] Build {build_id} already processed or cancelled"
                            )
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
    except Exception as e:
        logger.error(f"[Queue] Fatal error in queue processor: {e}")
        raise


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
        # Security: Validate project_id and construct safe source directory path
        safe_project_dir = validate_safe_path(UPLOAD_DIR, project_id)
        source_dir = safe_project_dir / "source"

        # Validate the constructed path is within UPLOAD_DIR
        source_dir = source_dir.resolve()
        if not str(source_dir).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(400, "Invalid source directory path")

        if not source_dir.exists():
            projects_base = UPLOAD_DIR / "projects"
            safe_alt = validate_safe_path(projects_base, project_id)
            if (safe_alt / "source").exists():
                source_dir = safe_alt / "source"
                # Re-validate after path change
                source_dir = source_dir.resolve()
                if not str(source_dir).startswith(str(projects_base.resolve())):
                    raise HTTPException(400, "Invalid source directory path")

        started = await trigger_cloud_build(build_id, config, source_dir)
        if not started:
            return {"status": "error", "message": "Failed to start cloud build"}
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
            build_id,
            user["id"],
        )
        if not build:
            raise HTTPException(404, "Build not found")

        if build["status"] != "pending":
            return {
                "position": None,
                "status": build["status"],
                "message": "Not in queue",
            }

        position = await get_queue_position(build_id)
        return {
            "position": position,
            "status": "queued",
            "message": f"Your build is #{position} in queue"
            if position
            else "In queue",
        }
    finally:
        await release_db(conn)


@router.get("/queue-info")
async def get_queue_info(user: dict = Depends(get_current_admin_user)):
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
        queue_preview.append(
            {
                "build_id": item["build_id"],
                "priority": priority,
                "user_id": item["user_id"],
            }
        )

    return {"enabled": True, "length": queue_length, "preview": queue_preview}
