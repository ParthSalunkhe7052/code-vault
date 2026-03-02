from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
import logging
import os
import json
import hmac
import hashlib
import secrets
import asyncio
import time
import base64
import ast
from pathlib import Path
from datetime import datetime, timezone

from database import get_db, release_db
from storage_service import storage_service
from utils import (
    get_current_user,
    get_current_admin_user,
    get_user_tier,
    compute_ed25519_signature,
    compute_signature,
    SECRET_KEY,
)
from middleware.tier_enforcement import requires_feature
from config import (
    BUILD_CALLBACK_SECRET,
    ENVIRONMENT,
    GCP_PROJECT_ID,
    get_build_credit_cost,
)
from middleware.rate_limiter import get_redis_client
from routes.cloud_build_websocket import (
    ws_manager,
    broadcast_build_update,
    get_build_stage,
)
from routes.cloud_build_utils import (
    validate_safe_path,
    generate_gcs_signed_url,
)
from cloud_build_integration import CloudBuildClient

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cloud-build",
    tags=["cloud-build"],
)

# Local upload directory - should match project_routes
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_python_syntax(file_path: Path, context: str = "") -> tuple[bool, str]:
    """Validate that a Python file has valid syntax.

    Args:
        file_path: Path to the Python file to validate
        context: Context string for error messages (e.g., "cloud_runner_nodejs.py")

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if not file_path.exists():
            return False, f"{context}: File not found at {file_path}"

        source = file_path.read_text(encoding="utf-8")
        ast.parse(source)
        return True, ""
    except SyntaxError as e:
        error_msg = f"{context}: Syntax error at line {e.lineno}: {e.msg}"
        logger.error(f"[Validation] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"{context}: Validation error: {str(e)}"
        logger.error(f"[Validation] {error_msg}")
        return False, error_msg


# =============================================================================
# Webhook Payload Validation Models (Task 2.2 - Structured Validation)
# =============================================================================


class CloudBuildWebhookPayload(BaseModel):
    """Validated payload for /api/v1/cloud-build/webhook endpoint."""

    build_id: str = Field(..., min_length=1, max_length=100)
    status: Optional[str] = Field(
        None, pattern=r"^(pending|queued|running|completed|failed|cancelled)$"
    )
    platform: Optional[str] = Field(None, pattern=r"^(windows|linux|macos)$")
    cloud_build_id: Optional[str] = Field(None, max_length=100)
    github_run_id: Optional[str] = Field(None, max_length=100)
    download_key: Optional[str] = Field(None, max_length=500)
    download_url: Optional[str] = Field(None, max_length=1000)
    linux_download_key: Optional[str] = Field(None, max_length=500)
    windows_download_key: Optional[str] = Field(None, max_length=500)
    linux_status: Optional[str] = Field(
        None, pattern=r"^(pending|queued|running|completed|failed|cancelled|skipped)$"
    )
    windows_status: Optional[str] = Field(
        None, pattern=r"^(pending|queued|running|completed|failed|cancelled|skipped)$"
    )
    filename: Optional[str] = Field(None, max_length=255)
    error: Optional[str] = Field(None, max_length=2000)
    progress: Optional[int] = Field(None, ge=0, le=100)

    @validator("build_id")
    def validate_build_id(cls, v):
        if not v or not v.strip():
            raise ValueError("build_id cannot be empty")
        return v.strip()


class ProgressWebhookPayload(BaseModel):
    """Validated payload for /api/v1/cloud-build/webhook/progress endpoint."""

    build_id: str = Field(..., min_length=1, max_length=100)
    platform: Optional[str] = Field(None, pattern=r"^(windows|linux|macos)$")
    progress: int = Field(0, ge=0, le=100)
    stage: Optional[str] = Field(None, max_length=100)
    cloud_build_id: Optional[str] = Field(None, max_length=100)
    github_run_id: Optional[str] = Field(None, max_length=100)

    @validator("build_id")
    def validate_build_id(cls, v):
        if not v or not v.strip():
            raise ValueError("build_id cannot be empty")
        return v.strip()


# =============================================================================
# Idempotency Helper Functions (Task 2.1 - Idempotency Handling)
# =============================================================================


async def check_and_record_webhook_event(
    conn, event_id: str, event_type: str = "cloud_build_webhook"
) -> bool:
    """Check if webhook event was already processed and record it if not.

    Returns:
        True if this is a new event (should process), False if duplicate.
    """
    try:
        existing = await conn.fetchval(
            "SELECT event_id FROM processed_webhook_events WHERE event_id = $1",
            event_id,
        )
        if existing:
            logger.info(f"[Webhook] Duplicate event detected: {event_id}")
            return False

        await conn.execute(
            """INSERT INTO processed_webhook_events (event_id, event_type, processed_at)
               VALUES ($1, $2, NOW())
               ON CONFLICT (event_id) DO NOTHING""",
            event_id,
            event_type,
        )
        return True
    except Exception as e:
        logger.error(f"[Webhook] Error checking idempotency: {e}")
        return True


def generate_webhook_event_id(
    build_id: str,
    platform: Optional[str],
    status: Optional[str],
    progress: Optional[int] = None,
) -> str:
    """Generate a deterministic event ID for deduplication.

    Dedupe by (build_id, stage, progress) or message id.
    """
    if platform and status:
        key = f"{build_id}:{platform}:{status}"
    elif platform and progress is not None:
        key = f"{build_id}:{platform}:progress:{progress}"
    elif status:
        key = f"{build_id}:overall:{status}"
    else:
        key = f"{build_id}:unknown:{secrets.token_hex(8)}"

    return hashlib.sha256(key.encode()).hexdigest()[:64]


# =============================================================================
# Phase 5: Build Provenance Tokens
# =============================================================================


def create_build_provenance_token(
    build_id: str,
    project_id: str,
    platform: str,
    artifact_hash: str,
    private_key_pem: Optional[str] = None,
    secret: Optional[str] = None,
) -> str:
    """Create a signed build provenance token for cloud artifacts.

    This token proves the artifact was built in the cloud and includes:
    - build_id: unique build identifier
    - project_id: the project this build belongs to
    - platform: target platform (windows, linux, macos)
    - artifact_hash: SHA-256 hash of the artifact
    - timestamp: when the token was created
    - is_cloud: True for cloud builds, False for local

    The token is signed with Ed25519 (preferred) or HMAC (legacy).
    """
    timestamp = int(time.time())
    jti = secrets.token_hex(16)

    provenance_payload = {
        "build_id": build_id,
        "project_id": project_id,
        "platform": platform,
        "artifact_hash": artifact_hash,
        "timestamp": timestamp,
        "jti": jti,
        "is_cloud": True,
    }

    # Sign the token
    if private_key_pem:
        signature = compute_ed25519_signature(provenance_payload, private_key_pem)
    else:
        active_secret = secret or SECRET_KEY
        signature = compute_signature(provenance_payload, active_secret)

    token_data = json.dumps({"payload": provenance_payload, "signature": signature})

    return base64.b64encode(token_data.encode()).decode()


def create_local_build_provenance_token(
    project_id: str,
    artifact_hash: str,
) -> str:
    """Create a local build provenance token (no cloud verification).

    Local builds are supported but explicitly marked as local-trust.
    """
    timestamp = int(time.time())
    jti = secrets.token_hex(16)

    provenance_payload = {
        "project_id": project_id,
        "artifact_hash": artifact_hash,
        "timestamp": timestamp,
        "jti": jti,
        "is_cloud": False,
    }

    token_data = json.dumps(provenance_payload)
    return base64.b64encode(token_data.encode()).decode()


class CloudBuildRequest(BaseModel):
    project_id: str
    license_id: Optional[str] = None
    target_platforms: List[str] = ["windows"]
    compatibility_mode: bool = False
    license_mode: Optional[str] = "generic"  # 'generic' or 'demo'
    demo_duration: Optional[int] = 60  # minutes

    @validator("target_platforms")
    def validate_platforms(cls, v):
        allowed = {"windows", "macos", "linux"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid platforms: {invalid}. Allowed: {allowed}")
        if not v:
            raise ValueError("At least one platform must be specified")
        return v


class CloudBuildResponse(BaseModel):
    build_id: str
    status: str
    message: str


async def get_license_key(license_id: str, conn) -> str:
    row = await conn.fetchrow(
        "SELECT license_key FROM licenses WHERE id = $1", license_id
    )
    return row["license_key"] if row else "GENERIC_BUILD"


def get_remote_build_id(build_row) -> Optional[str]:
    """Return the Cloud Build ID from modern or legacy columns."""
    if not build_row:
        return None
    return build_row.get("gcp_build_id") or build_row.get("github_run_id")


async def verify_webhook_signature(request: Request) -> bool:
    signature = request.headers.get("X-Signature")
    if not signature:
        logger.warning("Webhook received without X-Signature header")
        return False

    if not BUILD_CALLBACK_SECRET:
        logger.error("BUILD_CALLBACK_SECRET is not configured; rejecting webhook")
        return False

    normalized_signature = signature.strip()
    if normalized_signature.lower().startswith("sha256="):
        normalized_signature = normalized_signature.split("=", 1)[1]

    body = await request.body()
    expected = hmac.new(
        BUILD_CALLBACK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(normalized_signature.lower(), expected.lower())


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
        # Copy build scripts to source directory so they're available in Cloud Build
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

                    # Validate Python syntax before triggering Cloud Build
                    is_valid, error_msg = validate_python_syntax(
                        script_dest, "cloud_runner.py"
                    )
                    if not is_valid:
                        logger.error(f"[Upload] Aborting build - {error_msg}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Build script validation failed: {error_msg}. Please contact support.",
                        )
                    logger.info("[Upload] cloud_runner.py syntax validation passed")
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

            # Removed nuitka_patch.py logic as Nuitka natively supports pefile under Wine in 2.x

            # Also copy cloud_runner_nodejs.py for Node.js builds
            nodejs_runner_source = (
                project_root / ".github" / "scripts" / "cloud_runner_nodejs.py"
            )
            if nodejs_runner_source.exists():
                nodejs_runner_dest = (
                    source_dir / ".github" / "scripts" / "cloud_runner_nodejs.py"
                )
                shutil.copy2(nodejs_runner_source, nodejs_runner_dest)
                logger.info(
                    f"[Upload] Successfully copied cloud_runner_nodejs.py to source"
                )

                # Validate Python syntax before triggering Cloud Build
                is_valid, error_msg = validate_python_syntax(
                    nodejs_runner_dest, "cloud_runner_nodejs.py"
                )
                if not is_valid:
                    logger.error(f"[Upload] Aborting build - {error_msg}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Build script validation failed: {error_msg}. Please contact support.",
                    )
                logger.info("[Upload] cloud_runner_nodejs.py syntax validation passed")
            else:
                logger.warning(
                    f"[Upload] cloud_runner_nodejs.py not found at {nodejs_runner_source}"
                )
        except Exception as e:
            logger.error(f"[Upload] Failed to copy build scripts: {e}")
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
            logger.info(f"[Upload] Uploading source to EXACT R2 bucket='{bucket}', key='{key}', size={len(content)}")
            s3.put_object(Bucket=bucket, Key=key, Body=content)
            logger.info(f"[Upload] Successfully uploaded to R2")

            presigned = s3.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
            )
            logger.info(f"[Upload] Generated presigned source url for '{key}': {presigned[:100]}...")
            return presigned
        else:
            if ENVIRONMENT == "production":
                raise HTTPException(500, "Cloud Builds require R2 in production.")

            public_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
            return f"{public_url}/uploads/{build_id}/source.zip"
    finally:
        if zip_path.exists():
            zip_path.unlink()


async def upload_config_to_r2(build_id: str, config: dict) -> str:
    """Upload build config to R2 and return presigned URL."""
    import json

    config_json = json.dumps(config)
    config_bytes = config_json.encode("utf-8")

    key = f"builds/{build_id}/config.json"

    if storage_service.is_cloud_enabled() and storage_service.client:
        s3 = storage_service.client
        bucket = storage_service.bucket

        # Upload config JSON
        logger.info(f"[Upload] Uploading config to EXACT R2 bucket='{bucket}', key='{key}', size={len(config_bytes)}")
        s3.put_object(Bucket=bucket, Key=key, Body=config_bytes)
        logger.info(f"[Upload] Successfully uploaded config to R2")

        presigned = s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
        )
        logger.info(f"[Upload] Generated presigned config url for '{key}': {presigned[:100]}...")
        return presigned
    else:
        if ENVIRONMENT == "production":
            raise HTTPException(500, "Cloud Builds require R2 in production.")

        public_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
        return f"{public_url}/uploads/{build_id}/config.json"


async def trigger_cloud_build(build_id: str, config: dict, source_dir: Path) -> bool:
    """Trigger a Cloud Build job using gcloud CLI wrapper."""
    # Security: Validate source_dir is within allowed base directory
    # This path is constructed from validated project_id via validate_safe_path
    source_dir = source_dir.resolve()
    if not str(source_dir).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(400, "Invalid source directory path")

    conn = None
    try:
        # Always use Cloud Build API client (supports Workload Identity on Heroku)
        # CloudBuildClient imported at top of file

        logger.info("[CloudBuild] Using Cloud Build API client")

        # Upload source to R2 (still needed for Cloud Build to download)
        source_url = await upload_source_to_r2(build_id, source_dir)

        # Upload config to R2 for Cloud Build to download
        config_url = await upload_config_to_r2(build_id, config)
        logger.info(f"[CloudBuild] Config uploaded to R2: {config_url[:50]}...")

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

        # SECURITY SYNC: Fetch Ed25519 keys and heartbeat config from project
        # This ensures cloud builds have the same security as local CLI builds
        project_id = config.get("project_id", "")
        signing_public_key = ""
        signing_private_key = ""
        heartbeat_interval = config.get("heartbeat_interval", 300)

        if project_id:
            try:
                conn = await get_db()
                project = await conn.fetchrow(
                    "SELECT signing_public_key, signing_private_key FROM projects WHERE id = $1",
                    project_id,
                )
                if project:
                    signing_public_key = project.get("signing_public_key", "") or ""
                    signing_private_key = project.get("signing_private_key", "") or ""
            except Exception as e:
                logger.warning(
                    f"[CloudBuild] Could not fetch project signing keys: {e}"
                )

        # Build config dict for Cloud Build
        build_config = {
            "build_id": build_id,
            "project_id": config["project_id"],
            "language": config["language"],
            "target_platforms": target_platforms_str,
            "source_url": source_url,
            "config_url": config_url,
            "config": config,
            "output_name": config.get("output_name", "app"),
            "callback_url": f"{public_api_url}/api/v1/cloud-build/webhook",
            "callback_secret": BUILD_CALLBACK_SECRET or "",
            "plan_tier": config.get("plan_tier", "free"),
            "compatibility_mode": config.get("compatibility_mode", False),
            "fast_build": config.get("fast_build", False),
            # SECURITY SYNC: Ed25519 signatures, binary hash verification, heartbeat
            "signing_public_key": signing_public_key,
            "signing_private_key": signing_private_key,
            "heartbeat_interval": heartbeat_interval,
            "binary_hash_tracking": True,
            "enable_ed25519_signatures": bool(signing_public_key),
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
                   gcp_build_id = $2::text,
                   github_run_id = COALESCE(github_run_id, $2::text),
                   logs = $3
               WHERE id = $1""",
            build_id,
            gcp_build_id,
            [f"Cloud Build triggered: {gcp_build_id}", f"Logs: {logs_url}"],
        )

        logger.info(
            f"[CloudBuild] Successfully triggered build {build_id} -> GCP Build {gcp_build_id}"
        )
        return True

    except Exception as e:
        import traceback

        error_msg = str(e)
        error_traceback = traceback.format_exc()

        # Clean up error message - filter out long HTML responses
        clean_error = error_msg
        # Filter out long HTML responses from error messages
        if "<!doctype html>" in error_msg or "<html" in error_msg.lower():
            if "Unable to retrieve" in error_msg:
                clean_error = "Unable to retrieve Identity Pool subject token - check Workload Identity configuration in GCP"
            elif "DefaultCredentialsError" in error_msg:
                clean_error = "GCP credentials not found - check Workload Identity or service account configuration"
            else:
                clean_error = (
                    "GCP authentication failed - check Workload Identity configuration"
                )

        # Also clean up the traceback - remove HTML content
        clean_traceback = error_traceback
        if "<!doctype html>" in error_traceback or "<html" in error_traceback.lower():
            # Extract just the relevant Python traceback
            lines = error_traceback.split("\n")
            clean_lines = []
            for line in lines:
                if "<!" in line or "<html" in line.lower() or len(line) > 200:
                    break
                clean_lines.append(line)
            clean_traceback = "\n".join(clean_lines)
            if not clean_traceback:
                clean_traceback = clean_error

        logger.error(f"Failed to trigger Cloud Build: {clean_error}")
        if conn is None:
            conn = await get_db()
        # Store both error message and traceback for admin debugging
        await conn.execute(
            """UPDATE cloud_builds 
               SET status = 'failed', 
                   error_message = $1,
                   admin_error_details = $2
               WHERE id = $3""",
            clean_error,
            clean_traceback,
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
    _: None = Depends(requires_feature("cloud_compilation")),
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
        source_dir = None

        # First, try to find source directory from zip upload
        safe_project_dir = validate_safe_path(UPLOAD_DIR, request.project_id)
        zip_source_dir = safe_project_dir / "source"
        zip_source_dir = zip_source_dir.resolve()

        if str(zip_source_dir).startswith(str(UPLOAD_DIR.resolve())):
            if zip_source_dir.exists() and list(zip_source_dir.iterdir()):
                source_dir = zip_source_dir

        # If no zip source, check project_files table for single file uploads
        if not source_dir:
            project_files = await conn.fetch(
                """SELECT id, filename, original_filename, file_path, is_cloud 
                   FROM project_files WHERE project_id = $1""",
                request.project_id,
            )

            if project_files:
                import shutil

                # Create permanent source directory for this project
                persistent_source_dir = safe_project_dir / "source"
                persistent_source_dir.mkdir(parents=True, exist_ok=True)
                persistent_source_dir = persistent_source_dir.resolve()

                # Validate path
                if not str(persistent_source_dir).startswith(str(UPLOAD_DIR.resolve())):
                    raise HTTPException(400, "Invalid source directory path")

                for pf in project_files:
                    try:
                        file_content = await storage_service.download_file(
                            pf["file_path"], not pf["is_cloud"]
                        )
                        if file_content:
                            safe_filename = pf["original_filename"] or pf["filename"]
                            safe_filename = "".join(
                                c for c in safe_filename if c.isalnum() or c in "._-"
                            )
                            if not safe_filename:
                                safe_filename = f"file_{pf['id']}"
                            dest_path = persistent_source_dir / safe_filename
                            dest_path.write_bytes(file_content)
                            logger.info(
                                f"[CloudBuild] Downloaded project file to source: {safe_filename}"
                            )
                        else:
                            logger.warning(
                                f"[CloudBuild] Could not download file: {pf['file_path']}"
                            )
                    except Exception as dl_err:
                        logger.warning(
                            f"[CloudBuild] Error downloading file {pf['filename']}: {dl_err}"
                        )

                if list(persistent_source_dir.iterdir()):
                    source_dir = persistent_source_dir
                    logger.info(
                        f"[CloudBuild] Created source dir from project_files: {source_dir}"
                    )

        if not source_dir:
            raise HTTPException(
                400, "No source files found. Upload a ZIP or individual files first."
            )

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

        # Determine entry file - check settings first, then auto-detect from source
        entry_file = get_setting("entry_file", None)

        if not entry_file:
            source_files = list(source_dir.iterdir())
            py_files = [f.name for f in source_files if f.suffix == ".py"]
            js_files = [f.name for f in source_files if f.suffix in (".js", ".ts")]

            if language == "python":
                if len(py_files) == 1:
                    entry_file = py_files[0]
                elif "main.py" in py_files:
                    entry_file = "main.py"
                elif "app.py" in py_files:
                    entry_file = "app.py"
                elif py_files:
                    entry_file = py_files[0]
                else:
                    entry_file = "main.py"
            elif language == "nodejs":
                if len(js_files) == 1:
                    entry_file = js_files[0]
                elif "index.js" in js_files:
                    entry_file = "index.js"
                elif "main.js" in js_files:
                    entry_file = "main.js"
                elif js_files:
                    entry_file = js_files[0]
                else:
                    entry_file = "index.js"
            else:
                entry_file = "main.py"

        logger.info(f"[CloudBuild] Using entry file: {entry_file}")

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

        # Strict validation for output_name to prevent command injection
        if output_name:
            import re
            output_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "", output_name)

        # CRITICAL: Triple-check output_name is never empty
        if not output_name or not output_name.strip():
            output_name = project_name_safe or "app"
            logger.warning(
                f"[CloudBuild] output_name was empty or invalid, using fallback: {output_name}"
            )

        license_key = "GENERIC_BUILD"
        if request.license_id:
            license_key = await get_license_key(request.license_id, conn)

        # Cloud builds MUST use the production API URL for license validation
        # Fallback chain: PUBLIC_API_URL env -> Heroku default URL
        public_api_url = os.getenv("PUBLIC_API_URL", "")
        if not public_api_url or "localhost" in public_api_url:
            # SECURITY: Require PUBLIC_API_URL to be set properly for cloud builds
            logger.warning(
                "[CloudBuild] PUBLIC_API_URL not set or is localhost - cloud build license validation may fail"
            )
            if ENVIRONMENT == "production":
                raise HTTPException(
                    500,
                    "PUBLIC_API_URL must be configured for cloud builds in production",
                )

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
            "license_mode": request.license_mode or "generic",
            "demo_duration": request.demo_duration or 60,
            "api_url": f"{public_api_url}/api/v1/license/validate",
            "plan_tier": tier["tier"],  # Pass tier for dynamic timeout
            "compatibility_mode": request.compatibility_mode,
            "skip_obfuscation": project_settings.get("skip_obfuscation", True),
            "enable_lease": project_settings.get("enable_lease", False),
            # Build mode options
            "use_onefile": project_settings.get("use_onefile", False),
            "is_gui_app": project_settings.get("is_gui_app", False),
        }

        # CVE-003 FIX: Wrap credit deduction + build records in transaction
        # If queue fails later, the except block handles refund
        # If anything fails here, transaction rolls back (automatic refund)
        async with conn.transaction():
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

            # Credit System Enforcement
            # All tiers (including Business) consume credits.
            # Enterprise unlimited tier (-1 credits_per_month) skips deduction.
            from config import TIER_LIMITS

            tier_credits_per_month = TIER_LIMITS.get(
                tier["tier"], {}
            ).get("credits_per_month", 0)

            if tier_credits_per_month != -1:
                # Per-platform cost calculation
                cost = get_build_credit_cost(
                    request.target_platforms, language
                )

                # Deduct credits atomically with validation
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
                        "Insufficient build credits. Please upgrade your plan or wait "
                        "for your monthly credit refill.",
                    )
                deducted_credits = cost

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

        # Transaction committed here - credits deducted, build records created
        # Queue operation happens outside transaction (external Redis operation)

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
            error_message = queue_result.get("message", "Failed to enqueue cloud build")
            # Get detailed error from database if available
            try:
                conn = await get_db()
                build_error = await conn.fetchrow(
                    "SELECT error_message, admin_error_details FROM cloud_builds WHERE id = $1",
                    build_id,
                )
                if build_error and build_error.get("admin_error_details"):
                    # Re-raise with detailed error for admin users
                    if user.get("role") == "admin":
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "message": "Cloud build failed",
                                "error": build_error.get(
                                    "error_message", error_message
                                ),
                                "traceback": build_error.get("admin_error_details"),
                                "build_id": build_id,
                            },
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[CloudBuild] Error fetching build details: {e}")

            raise HTTPException(500, error_message)
        queue_accepted = True

        return CloudBuildResponse(
            build_id=build_id,
            status="pending",
            message=queue_result.get("message", "Cloud build queued."),
        )

    except Exception as e:
        import traceback

        error_msg = str(e)
        error_traceback = traceback.format_exc()

        # Clean up error message - filter out long HTML responses
        clean_error = error_msg
        # Filter out long HTML responses from error messages
        if "<!doctype html>" in error_msg or "<html" in error_msg.lower():
            if "Unable to retrieve" in error_msg:
                clean_error = "Unable to retrieve Identity Pool subject token - check Workload Identity configuration in GCP"
            elif "DefaultCredentialsError" in error_msg:
                clean_error = "GCP credentials not found - check Workload Identity or service account configuration"
            else:
                clean_error = (
                    "GCP authentication failed - check Workload Identity configuration"
                )
        elif len(error_msg) > 500:
            # Extract just the key error message
            if "Unable to retrieve" in error_msg:
                clean_error = "Unable to retrieve Identity Pool subject token - check Workload Identity configuration"
            elif "DefaultCredentialsError" in error_msg:
                clean_error = "GCP credentials not found - check Workload Identity or service account configuration"
            else:
                # Just take first 200 chars
                clean_error = error_msg[:200] + "..."

        # Log detailed error for debugging
        logger.error(
            f"[CloudBuild] Build start failed for user {user['id']}: {clean_error}"
        )

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
                            error_message = COALESCE(error_message, $2),
                            admin_error_details = $3
                        WHERE id = $1
                        """,
                        build_id,
                        f"Build failed before enqueue/trigger. Credit refunded. Error: {error_msg}",
                        error_traceback if user.get("role") == "admin" else None,
                    )
                logger.info(
                    f"[CloudBuild] Refunded {deducted_credits} credit(s) for user {user['id']} after enqueue failure"
                )
            except Exception as refund_error:
                logger.error(f"[CloudBuild] Failed to refund credits: {refund_error}")

        # Re-raise with admin details if user is admin
        if user.get("role") == "admin":
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Cloud build failed",
                    "error": error_msg,
                    "traceback": error_traceback,
                    "build_id": build_id,
                },
            )
        raise
    finally:
        await release_db(conn)


@router.post("/webhook")
async def build_webhook(request: Request):
    """Callback from Cloud Build - with retry logic, idempotency, and structured validation."""
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")

    body = await request.body()
    try:
        raw_payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(f"[CloudBuild] Invalid JSON payload: {e}")
        raise HTTPException(400, f"Invalid JSON payload: {e}")

    # Structured validation - return 400 on malformed payload (never crash)
    try:
        payload = CloudBuildWebhookPayload(**raw_payload)
    except Exception as e:
        logger.error(f"[CloudBuild] Payload validation failed: {e}")
        raise HTTPException(400, f"Invalid payload schema: {e}")

    build_id = payload.build_id
    platform = payload.platform
    status = payload.status
    remote_build_id = payload.cloud_build_id or payload.github_run_id

    linux_download_key = payload.linux_download_key
    windows_download_key = payload.windows_download_key
    download_url = payload.download_url
    download_key = payload.download_key
    filename = payload.filename
    # Fix #3: Strip whitespace from error field — build scripts send " " when no error
    error = payload.error.strip() if payload.error else None
    if error == "":
        error = None
    linux_status = payload.linux_status
    windows_status = payload.windows_status

    # Generate event ID for idempotency
    event_id = generate_webhook_event_id(build_id, platform, status)

    # Retry logic for database connection issues
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        conn = None
        try:
            conn = await get_db()

            # Idempotency check - skip if already processed
            if not await check_and_record_webhook_event(
                conn, event_id, "cloud_build_webhook"
            ):
                logger.info(
                    f"[CloudBuild] Skipping duplicate webhook for build {build_id}"
                )
                return {"status": "ok", "duplicate": True}

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

            # Update Artifact (platform-specific callback)
            if platform:
                # Determine download key: new GCS format or legacy
                if platform == "linux" and linux_download_key:
                    artifact_download_key = linux_download_key
                elif platform == "windows" and windows_download_key:
                    artifact_download_key = windows_download_key
                elif download_key:
                    artifact_download_key = download_key
                elif download_url:
                    artifact_download_key = download_url
                else:
                    artifact_download_key = None

                await conn.execute(
                    """
                    UPDATE cloud_build_artifacts
                    SET status = $1, download_key = $2, download_filename = $3, 
                        error_message = $4, completed_at = NOW()
                    WHERE build_id = $5 AND platform = $6
                    """,
                    status,
                    artifact_download_key,
                    filename,
                    error,
                    build_id,
                    platform,
                )

            # Update individual artifacts with download keys from overall callback
            # This handles the case where webhook sends both linux_download_key and windows_download_key
            if not platform:
                if linux_download_key:
                    linux_filename = linux_download_key.split("/")[-1]
                    linux_artifact_status = linux_status or "completed"
                    # Fix #1A: Removed status IN filter — it silently blocked download_key storage
                    # when artifact status was set by a previous sync or race condition.
                    result = await conn.execute(
                        """
                        UPDATE cloud_build_artifacts
                        SET status = $1, download_key = $2, download_filename = $3, 
                            completed_at = NOW()
                        WHERE build_id = $4 AND platform = 'linux'
                        """,
                        linux_artifact_status,
                        linux_download_key,
                        linux_filename,
                        build_id,
                    )
                    rows_updated = int(result.split()[-1]) if result else 0
                    if rows_updated == 0:
                        logger.warning(
                            f"[CloudBuild] Linux artifact UPDATE matched 0 rows for build_id={build_id} — artifact record may be missing"
                        )
                    else:
                        logger.info(
                            f"[CloudBuild] Updated Linux artifact with key: {linux_download_key}, status: {linux_artifact_status}"
                        )
                elif linux_status:
                    await conn.execute(
                        """
                        UPDATE cloud_build_artifacts
                        SET status = $1, error_message = $2, completed_at = NOW()
                        WHERE build_id = $3 AND platform = 'linux' AND status NOT IN ('completed', 'failed', 'cancelled')
                        """,
                        linux_status,
                        error if linux_status == "failed" else None,
                        build_id,
                    )

                if windows_download_key:
                    windows_filename = windows_download_key.split("/")[-1]
                    windows_artifact_status = windows_status or "completed"
                    # Fix #1A: Removed status IN filter — same race condition fix as Linux
                    result = await conn.execute(
                        """
                        UPDATE cloud_build_artifacts
                        SET status = $1, download_key = $2, download_filename = $3, 
                            completed_at = NOW()
                        WHERE build_id = $4 AND platform = 'windows'
                        """,
                        windows_artifact_status,
                        windows_download_key,
                        windows_filename,
                        build_id,
                    )
                    rows_updated = int(result.split()[-1]) if result else 0
                    if rows_updated == 0:
                        logger.warning(
                            f"[CloudBuild] Windows artifact UPDATE matched 0 rows for build_id={build_id} — artifact record may be missing"
                        )
                    else:
                        logger.info(
                            f"[CloudBuild] Updated Windows artifact with key: {windows_download_key}, status: {windows_artifact_status}"
                        )
                elif windows_status:
                    await conn.execute(
                        """
                        UPDATE cloud_build_artifacts
                        SET status = $1, error_message = $2, completed_at = NOW()
                        WHERE build_id = $3 AND platform = 'windows' AND status NOT IN ('completed', 'failed', 'cancelled')
                        """,
                        windows_status,
                        error if windows_status == "failed" else None,
                        build_id,
                    )

            # Overall callbacks may omit per-platform statuses (for unsupported targets),
            # so mark remaining in-flight artifacts terminal based on overall result.
            if not platform and status in ["failed", "cancelled"]:
                fallback_status = "cancelled" if status == "cancelled" else "failed"
                fallback_error = None
                if fallback_status == "failed":
                    fallback_error = error or "No platform artifact callback received"

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

                # For overall callback, use GCS blob keys from new payload format
                # For platform callbacks, get from artifacts table
                # Priority: linux_download_key > windows_download_key > download_key > download_url
                final_download_key = (
                    linux_download_key
                    or windows_download_key
                    or download_key
                    or download_url
                )
                final_filename = filename

                if not final_download_key or not final_filename:
                    # Try to get from artifacts if not provided in overall callback
                    if final_status == "completed":
                        art = await conn.fetchrow(
                            "SELECT download_key, download_filename FROM cloud_build_artifacts WHERE build_id = $1 AND status = 'completed' LIMIT 1",
                            build_id,
                        )
                        if art:
                            final_download_key = (
                                final_download_key or art["download_key"]
                            )
                            final_filename = final_filename or art["download_filename"]

                await conn.execute(
                    """
                    UPDATE cloud_builds
                    SET status = $1, progress = 100, completed_at = NOW(),
                        download_key = $2, download_filename = $3
                    WHERE id = $4
                    """,
                    final_status,
                    final_download_key,
                    final_filename,
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


@router.websocket("/ws/{build_id}")
async def websocket_build_logs(
    websocket: WebSocket, build_id: str, token: Optional[str] = None
):
    """WebSocket endpoint for real-time build log streaming.

    Connect to receive real-time updates for a specific build.
    Messages are JSON with format:
    {
        "type": "progress" | "log" | "status" | "complete",
        "data": { ... }
    }

    Requires JWT token passed as query parameter: ?token=<jwt>
    """
    # Authenticate the connection
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Verify JWT token
    try:
        from config import JWT_SECRET, JWT_ALGORITHM
        import jwt

        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4001, reason="Token expired")
        return
    except jwt.PyJWTError as e:
        logger.warning(f"[WebSocket] Invalid token for build {build_id}: {e}")
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Validate build exists and belongs to authenticated user
    conn = await get_db()
    try:
        build = await conn.fetchrow(
            """SELECT cb.id, cb.status, p.user_id 
                FROM cloud_builds cb 
                JOIN projects p ON cb.project_id = p.id 
                WHERE cb.id = $1""",
            build_id,
        )
        if not build:
            await websocket.close(code=4004, reason="Build not found")
            return

        # Verify build belongs to authenticated user
        if str(build["user_id"]) != str(user_id):
            logger.warning(
                f"[WebSocket] User {user_id} attempted to access build {build_id} "
                f"owned by user {build['user_id']}"
            )
            await websocket.close(code=4003, reason="Access denied")
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


@router.get("/{build_id}/status")
async def get_build_status(
    build_id: str,
    user: dict = Depends(get_current_user),
    sync: bool = False,
    _: None = Depends(requires_feature("cloud_compilation")),
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

                        # CRITICAL FIX: Also update artifacts if the build is terminal
                        # This ensures the frontend doesn't get stuck waiting for artifacts
                        if db_status in ["failed", "cancelled", "completed"]:
                            if db_status == "completed":
                                # Get output_name for filename recovery
                                output_name = build.get("output_name") or "app"

                                # Get artifacts that need updating
                                pending_artifacts = await conn.fetch(
                                    "SELECT * FROM cloud_build_artifacts WHERE build_id = $1 AND status IN ('pending', 'running')",
                                    build_id,
                                )

                                for art in pending_artifacts:
                                    # Mark as completed
                                    await conn.execute(
                                        """UPDATE cloud_build_artifacts
                                           SET status = 'completed', completed_at = NOW()
                                           WHERE id = $1""",
                                        art["id"],
                                    )

                                    # Try to recover download key
                                    possible_filenames = [
                                        f"{output_name}-{art['platform']}.zip",
                                        f"{output_name}-{art['platform']}.tar.gz"
                                        if art["platform"] == "linux"
                                        else None,
                                        f"{art['platform']}_build.zip",
                                    ]
                                    possible_filenames = [
                                        f for f in possible_filenames if f
                                    ]

                                    for filename_guess in possible_filenames:
                                        guessed_key = f"builds/{build_id}/{art['platform']}/{filename_guess}"
                                        try:
                                            test_url = generate_gcs_signed_url(
                                                guessed_key
                                            )
                                            if test_url:
                                                await conn.execute(
                                                    """UPDATE cloud_build_artifacts 
                                                       SET download_key = $1, download_filename = $2 
                                                       WHERE id = $3""",
                                                    guessed_key,
                                                    filename_guess,
                                                    art["id"],
                                                )
                                                logger.info(
                                                    f"[CloudBuild] Sync recovered key: {guessed_key}"
                                                )
                                                break
                                        except Exception:
                                            continue
                            else:
                                # Failed or cancelled
                                await conn.execute(
                                    """UPDATE cloud_build_artifacts
                                       SET status = $1::text, 
                                           error_message = COALESCE(error_message, 'Build finished with status: ' || $1::text)
                                       WHERE build_id = $2::text AND status IN ('pending', 'running')""",
                                    db_status,
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

        language = build.get("language") or "python"

        artifact_list = []
        for art in artifacts:
            download_url = None
            download_key = art["download_key"]

            # Also check build-level download_key as fallback
            build_download_key = build.get("download_key")

            if (
                art["status"] in ["completed", "pending", "running"]
                and not download_key
            ):
                # Try build-level download_key first as fallback
                if build_download_key and art["platform"] in build_download_key:
                    download_key = build_download_key
                    logger.info(
                        f"[CloudBuild] Using build-level download_key for {art['platform']}: {download_key}"
                    )
                if build["status"] == "completed" or art["status"] == "completed":
                    output_name = build.get("output_name") or "app"

                    if art["status"] in ["pending", "running"]:
                        await conn.execute(
                            "UPDATE cloud_build_artifacts SET status = 'completed' WHERE id = $1",
                            art["id"],
                        )
                        logger.info(
                            f"[CloudBuild] Fixed artifact status from {art['status']} to completed"
                        )
                        art = await conn.fetchrow(
                            "SELECT * FROM cloud_build_artifacts WHERE id = $1",
                            art["id"],
                        )

                    # Use new priority-based filename detection
                    from routes.cloud_build_utils import (
                        get_artifact_filename_priority,
                        find_artifact_in_gcs,
                        check_gcs_blob_exists,
                    )

                    possible_filenames = get_artifact_filename_priority(
                        art["platform"], language, output_name
                    )

                    for filename_guess in possible_filenames:
                        guessed_key = (
                            f"builds/{build_id}/{art['platform']}/{filename_guess}"
                        )

                        try:
                            # Check if file exists before generating URL
                            if check_gcs_blob_exists(guessed_key):
                                download_key = guessed_key
                                logger.info(
                                    f"[CloudBuild] Recovered missing download key: {download_key}"
                                )

                                await conn.execute(
                                    "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2, status = 'completed' WHERE id = $3",
                                    download_key,
                                    filename_guess,
                                    art["id"],
                                )
                                break
                        except Exception as recovery_error:
                            logger.debug(
                                f"[CloudBuild] Recovery attempt failed for {guessed_key}: {recovery_error}"
                            )
                            continue

                    # If still not found, use GCS listing
                    if not download_key:
                        found = find_artifact_in_gcs(build_id, art["platform"])
                        if found:
                            download_key, filename = found
                            logger.info(
                                f"[CloudBuild] Found artifact via GCS listing: {download_key}"
                            )
                            await conn.execute(
                                "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2, status = 'completed' WHERE id = $3",
                                download_key,
                                filename,
                                art["id"],
                            )

            if art["status"] == "completed" and not download_key:
                # Even if status is completed, if there's no download_key, try to recover it
                logger.info(
                    f"[CloudBuild] Artifact {art['platform']} is completed but missing download_key, attempting recovery"
                )
                output_name = build.get("output_name") or "app"

                from routes.cloud_build_utils import (
                    get_artifact_filename_priority,
                    find_artifact_in_gcs,
                    check_gcs_blob_exists,
                )

                possible_filenames = get_artifact_filename_priority(
                    art["platform"], language, output_name
                )

                for filename_guess in possible_filenames:
                    guessed_key = (
                        f"builds/{build_id}/{art['platform']}/{filename_guess}"
                    )
                    try:
                        if check_gcs_blob_exists(guessed_key):
                            download_key = guessed_key
                            logger.info(
                                f"[CloudBuild] Recovered download key: {download_key}"
                            )
                            await conn.execute(
                                "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2 WHERE id = $3",
                                download_key,
                                filename_guess,
                                art["id"],
                            )
                            break
                    except Exception:
                        continue

                if not download_key:
                    found = find_artifact_in_gcs(build_id, art["platform"])
                    if found:
                        download_key, filename = found
                        logger.info(
                            f"[CloudBuild] Found via GCS listing: {download_key}"
                        )
                        await conn.execute(
                            "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2 WHERE id = $3",
                            download_key,
                            filename,
                            art["id"],
                        )

            if art["status"] == "completed" and download_key:
                download_url = generate_gcs_signed_url(download_key)

            artifact_list.append(
                {
                    "platform": art["platform"],
                    "status": art["status"],
                    "download_url": download_url,
                    "download_key": download_key,
                    "filename": art["download_filename"]
                    or f"{art['platform']}_build.zip",
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

        # Add admin debug info if user is admin
        if user.get("role") == "admin" and dict(build).get("admin_error_details"):
            response["admin_error_details"] = {
                "error": build.get("error_message") or build_error,
                "traceback": build.get("admin_error_details"),
                "build_id": build["id"]
            }

        # Phase 5: Add provenance tokens for completed cloud builds
        if build["status"] == "completed" and build.get("project_id"):
            # Get project signing keys
            project = await conn.fetchrow(
                "SELECT signing_private_key, signing_secret FROM projects WHERE id = $1",
                build["project_id"],
            )

            signing_private_key = (
                project.get("signing_private_key") if project else None
            )
            signing_secret = project.get("signing_secret") if project else None

            # Add provenance to each artifact
            for art in artifact_list:
                if art.get("status") == "completed" and art.get("download_url"):
                    # Create artifact hash (using download_key as proxy)
                    artifact_hash = hashlib.sha256(
                        art.get("download_key", "").encode()
                    ).hexdigest()

                    provenance_token = create_build_provenance_token(
                        build_id=build["id"],
                        project_id=build["project_id"],
                        platform=art["platform"],
                        artifact_hash=artifact_hash,
                        private_key_pem=signing_private_key,
                        secret=signing_secret,
                    )
                    art["provenance_token"] = provenance_token

        # Fix #1B: Belt-and-suspenders — if a single-artifact build completed but the
        # artifact-level download_url is still None (e.g., download_key wasn't recovered),
        # generate it directly from the build-level download_key stored by the webhook.
        if build["status"] == "completed" and len(artifact_list) == 1:
            if not artifact_list[0].get("download_url"):
                build_dk = build.get("download_key")
                if build_dk:
                    recovered_url = generate_gcs_signed_url(build_dk)
                    if recovered_url:
                        artifact_list[0]["download_url"] = recovered_url
                        logger.info(
                            f"[CloudBuild] Fix #1B: Recovered download URL from build-level key for {build_id}"
                        )

        # Backward compatibility for single artifact builds
        if len(artifact_list) == 1:
            response["download_key"] = artifact_list[0].get("download_url")
            response["download_url"] = artifact_list[0].get(
                "download_url"
            )  # A3: Top-level download_url
            response["download_filename"] = artifact_list[0].get("filename")
        elif len(artifact_list) > 1:
            # A3: For multi-platform, provide primary platform URL (windows preferred, then linux)
            for art in artifact_list:
                if art.get("platform") == "windows" and art.get("download_url"):
                    response["download_url"] = art["download_url"]
                    response["download_key"] = art["download_url"]
                    response["download_filename"] = art["filename"]
                    break
            else:
                for art in artifact_list:
                    if art.get("download_url"):
                        response["download_url"] = art["download_url"]
                        response["download_key"] = art["download_url"]
                        response["download_filename"] = art["filename"]
                        break

        return response
    finally:
        await release_db(conn)


@router.post("/{build_id}/sync")
async def sync_build_status(
    build_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(requires_feature("cloud_compilation")),
):
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

        cloud_build = CloudBuildClient(project_id=GCP_PROJECT_ID)
        gcp_status = cloud_build.get_build_status(remote_build_id)

        real_gcp_status = gcp_status.get("status", "")

        status_map = {
            "QUEUED": "queued",
            "WORKING": "running",
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "CANCELLED": "cancelled",
            "EXPIRED": "failed",
        }

        db_status = status_map.get(real_gcp_status, build["status"])

        if db_status != build["status"]:
            await conn.execute(
                """UPDATE cloud_builds 
                   SET status = $1, 
                       completed_at = CASE WHEN $1 IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END,
                       error_message = COALESCE(error_message, $2)
                   WHERE id = $3""",
                db_status,
                gcp_status.get("status_details", f"Build {db_status} in Cloud Build"),
                build_id,
            )

            if db_status == "completed":
                artifacts = await conn.fetch(
                    "SELECT * FROM cloud_build_artifacts WHERE build_id = $1",
                    build_id,
                )

                output_name = build.get("output_name") or "app"

                for art in artifacts:
                    if art["status"] in ["pending", "running"]:
                        await conn.execute(
                            """UPDATE cloud_build_artifacts 
                               SET status = 'completed', completed_at = NOW() 
                               WHERE id = $1""",
                            art["id"],
                        )
                        logger.info(
                            f"[CloudBuild] Sync marked artifact {art['platform']} as completed"
                        )

                    if not art["download_key"]:
                        # Use the new priority-based filename detection
                        from routes.cloud_build_utils import (
                            get_artifact_filename_priority,
                            find_artifact_in_gcs,
                            check_gcs_blob_exists,
                        )

                        language = build.get("language") or "python"
                        possible_filenames = get_artifact_filename_priority(
                            art["platform"], language, output_name
                        )

                        for filename_guess in possible_filenames:
                            guessed_key = (
                                f"builds/{build_id}/{art['platform']}/{filename_guess}"
                            )
                            try:
                                if check_gcs_blob_exists(guessed_key):
                                    await conn.execute(
                                        "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2 WHERE id = $3",
                                        guessed_key,
                                        filename_guess,
                                        art["id"],
                                    )
                                    logger.info(
                                        f"[CloudBuild] Sync recovered download key for {art['platform']}: {guessed_key}"
                                    )
                                    break
                            except Exception:
                                continue

                        if not art.get("download_key"):
                            found = find_artifact_in_gcs(build_id, art["platform"])
                            if found:
                                download_key, filename = found
                                await conn.execute(
                                    "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2 WHERE id = $3",
                                    download_key,
                                    filename,
                                    art["id"],
                                )
                                logger.info(
                                    f"[CloudBuild] Sync found artifact via GCS listing: {download_key}"
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


@router.get("/{build_id}/gcp-sync")
async def gcp_direct_sync(
    build_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(requires_feature("cloud_compilation")),
):
    """
    Direct sync with GCP Cloud Build API.
    Bypasses webhook issues by querying GCP directly.
    Returns full build status with artifact recovery.
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
        gcp_status_obtained = False
        real_gcp_status = None

        # Try to get status from GCP if we have the build ID
        if remote_build_id:
            try:
                cloud_build = CloudBuildClient(project_id=GCP_PROJECT_ID)
                gcp_status = cloud_build.get_build_status(remote_build_id)
                real_gcp_status = gcp_status.get("status", "")
                gcp_status_obtained = True

                status_map = {
                    "QUEUED": "queued",
                    "WORKING": "running",
                    "SUCCESS": "completed",
                    "FAILURE": "failed",
                    "CANCELLED": "cancelled",
                    "EXPIRED": "failed",
                }
                db_status = status_map.get(real_gcp_status, build["status"])
            except Exception as e:
                logger.warning(
                    f"[CloudBuild] Could not get GCP status for {remote_build_id}: {e}"
                )
                db_status = build["status"]
        else:
            # No GCP build ID stored - try to recover via GCS listing
            db_status = build["status"]

        # If build is still pending/running and we don't have GCP status, check GCS for artifacts
        # This handles the case where webhook failed and we never got the GCP build ID
        if build["status"] in ["pending", "queued", "running"]:
            if not remote_build_id or not gcp_status_obtained:
                # Try to find artifacts directly in GCS
                output_name = build.get("output_name") or "app"
                target_platforms = json.loads(
                    build.get("target_platforms") or '["windows"]'
                )

                artifacts_found = False
                for platform in target_platforms:
                    try:
                        from google.cloud import storage as gcs_storage
                        from config import GCS_BUILDS_BUCKET

                        gcs_client = gcs_storage.Client()
                        bucket = gcs_client.bucket(GCS_BUILDS_BUCKET)
                        prefix = f"builds/{build_id}/{platform}/"

                        blobs = list(bucket.list_blobs(prefix=prefix, max_results=10))
                        for blob in blobs:
                            if blob.name.endswith((".zip", ".exe", ".tar.gz")):
                                artifacts_found = True
                                break
                        if artifacts_found:
                            break
                    except Exception as list_err:
                        logger.warning(f"[CloudBuild] GCS listing failed: {list_err}")

                if artifacts_found:
                    db_status = "completed"
                    real_gcp_status = "SUCCESS"
                    logger.info(
                        f"[CloudBuild] Found artifacts in GCS, marking as completed: {build_id}"
                    )

        # Update status if changed
        if db_status != build["status"]:
            await conn.execute(
                """UPDATE cloud_builds 
                   SET status = $1, 
                       completed_at = CASE WHEN $1 IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END,
                       error_message = COALESCE(error_message, $2)
                   WHERE id = $3""",
                db_status,
                f"Build {db_status} in Cloud Build",
                build_id,
            )

        # Handle completed builds - recover artifacts
        if db_status == "completed":
            output_name = build.get("output_name") or "app"
            artifacts = await conn.fetch(
                "SELECT * FROM cloud_build_artifacts WHERE build_id = $1",
                build_id,
            )

            for art in artifacts:
                if art["status"] in ["pending", "running"]:
                    await conn.execute(
                        "UPDATE cloud_build_artifacts SET status = 'completed' WHERE id = $1",
                        art["id"],
                    )

                if not art["download_key"]:
                    # Try multiple filename patterns (prioritize onefile EXE for Windows)
                    possible_filenames = []

                    if art["platform"] == "windows":
                        # Onefile mode: single self-contained EXE
                        possible_filenames.append(f"{output_name}.exe")
                        # Fallback: zip file with DLLs (standalone mode)
                        possible_filenames.append(f"{output_name}-windows.zip")

                    if art["platform"] == "linux":
                        # Onefile mode: single binary
                        possible_filenames.append(f"{output_name}")
                        # Fallback: tar.gz
                        possible_filenames.append(f"{output_name}-linux.tar.gz")
                        possible_filenames.append(f"{output_name}.tar.gz")

                    for filename_guess in possible_filenames:
                        guessed_key = (
                            f"builds/{build_id}/{art['platform']}/{filename_guess}"
                        )
                        try:
                            test_url = generate_gcs_signed_url(guessed_key)
                            if test_url:
                                await conn.execute(
                                    "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2 WHERE id = $3",
                                    guessed_key,
                                    filename_guess,
                                    art["id"],
                                )
                                logger.info(
                                    f"[CloudBuild] GCP sync recovered: {guessed_key}"
                                )
                                break
                        except Exception:
                            continue

                    # If still no download key, try GCS listing
                    if not art.get("download_key"):
                        try:
                            from google.cloud import storage as gcs_storage
                            from config import GCS_BUILDS_BUCKET

                            gcs_client = gcs_storage.Client()
                            bucket = gcs_client.bucket(GCS_BUILDS_BUCKET)
                            prefix = f"builds/{build_id}/{art['platform']}/"
                            blobs = list(
                                bucket.list_blobs(prefix=prefix, max_results=10)
                            )
                            for blob in blobs:
                                if blob.name.endswith((".zip", ".exe", ".tar.gz")):
                                    await conn.execute(
                                        "UPDATE cloud_build_artifacts SET download_key = $1, download_filename = $2 WHERE id = $3",
                                        blob.name,
                                        blob.name.split("/")[-1],
                                        art["id"],
                                    )
                                    logger.info(
                                        f"[CloudBuild] GCP sync found via listing: {blob.name}"
                                    )
                                    break
                        except Exception as list_err:
                            logger.warning(
                                f"[CloudBuild] GCS listing failed: {list_err}"
                            )

        # Refresh data after updates
        build = await conn.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1", build_id
        )
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
                    "filename": art["download_filename"]
                    or f"{art['platform']}_build.zip",
                    "error": art["error_message"],
                }
            )

        return {
            "id": build["id"],
            "status": build["status"],
            "gcp_status": real_gcp_status or "unknown",
            "artifacts": artifact_list,
            "synced": True,
            "message": f"Synced from GCP: {real_gcp_status or 'via artifact detection'}",
        }

    except Exception as e:
        import traceback

        logger.error(f"[CloudBuild] GCP sync failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"Failed to sync with GCP: {str(e)}")
    finally:
        await release_db(conn)


@router.post("/{build_id}/cancel")
async def cancel_cloud_build(
    build_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(requires_feature("cloud_compilation")),
):
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
    _: None = Depends(requires_feature("cloud_compilation")),
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
        new_build_id = secrets.token_hex(16)
        config = json.loads(build["config_json"]) if build["config_json"] else {}
        
        output_name = config.get("output_name", "app")
        if not output_name or not str(output_name).strip():
            output_name = "app"
            config["output_name"] = "app"

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
            output_name,
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
    build_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(requires_feature("cloud_compilation")),
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


@router.get("/{build_id}/download/{platform}")
async def proxy_download(
    build_id: str,
    platform: str,
):
    """Proxy download for cloud build artifacts to bypass Workload Identity signed URL limits.
    
    Streams in 64KB chunks instead of loading the full artifact into memory,
    preventing OOM on Heroku dynos when artifacts are large.
    """
    conn = await get_db()
    try:
        # Note: Removing get_current_user dependency here to make it easier for the frontend
        # to download via a simple window.location.href or <a> tag without injecting JWT headers.
        # As long as the build_id is a secure unguessable ID, it acts as a capability URL.
        build = await conn.fetchrow(
            "SELECT id FROM cloud_builds WHERE id = $1",
            build_id
        )
        if not build:
            raise HTTPException(404, "Build not found")
            
        art = await conn.fetchrow(
            "SELECT download_key, download_filename FROM cloud_build_artifacts WHERE build_id = $1 AND platform = $2",
            build_id, platform
        )
        if not art or not art["download_key"]:
            raise HTTPException(404, "Artifact not found or not completed")
            
        download_key = art["download_key"]
        filename = art["download_filename"] or f"{platform}_build.zip"
        
        from routes.cloud_build_utils import get_gcs_client_with_credentials
        from config import GCS_BUILDS_BUCKET
        from fastapi.responses import StreamingResponse
        
        CHUNK_SIZE = 64 * 1024  # 64KB chunks — avoids OOM on Heroku 512MB dynos
        
        # 1. Try GCS first — stream in chunks, not all-at-once
        gcs_client, _ = get_gcs_client_with_credentials()
        if gcs_client:
            bucket = gcs_client.bucket(GCS_BUILDS_BUCKET)
            blob = bucket.blob(download_key)
            if blob.exists():
                # Reload metadata to get accurate size for Content-Length
                blob.reload()
                blob_size = blob.size

                def gcs_chunk_generator():
                    with blob.open("rb") as f:
                        while True:
                            chunk = f.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            yield chunk

                headers = {
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "application/zip"
                    if filename.endswith(".zip")
                    else "application/octet-stream",
                }
                if blob_size:
                    headers["Content-Length"] = str(blob_size)
                return StreamingResponse(
                    gcs_chunk_generator(),
                    media_type=headers["Content-Type"],
                    headers=headers,
                )
                
        # 2. Fallback to R2 — stream response body in chunks
        if storage_service.is_cloud_enabled() and storage_service.client:
            try:
                r2_response = storage_service.client.get_object(
                    Bucket=storage_service.bucket, Key=download_key
                )
                body = r2_response["Body"]
                content_length = r2_response.get("ContentLength")

                def r2_chunk_generator():
                    while True:
                        chunk = body.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        yield chunk

                headers = {
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "application/zip"
                    if filename.endswith(".zip")
                    else "application/octet-stream",
                }
                if content_length:
                    headers["Content-Length"] = str(content_length)
                return StreamingResponse(
                    r2_chunk_generator(),
                    media_type=headers["Content-Type"],
                    headers=headers,
                )
            except Exception as e:
                logger.debug(f"[CloudBuild] Proxy download failed for R2: {e}")
                

                
        raise HTTPException(404, "Artifact file not found in storage")
    finally:
        await release_db(conn)


@router.get("/history")
async def get_build_history(
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user),
    _: None = Depends(requires_feature("cloud_compilation")),
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
    """Receive progress updates from Cloud Build - with idempotency and structured validation."""
    if not await verify_webhook_signature(request):
        raise HTTPException(401, "Invalid signature")

    # Structured validation - return 400 on malformed payload (never crash)
    try:
        raw_body = await request.json()
        payload = ProgressWebhookPayload(**raw_body)
    except Exception as e:
        logger.error(f"[CloudBuild] Progress payload validation failed: {e}")
        raise HTTPException(400, f"Invalid payload schema: {e}")

    build_id = payload.build_id
    platform = payload.platform
    progress = payload.progress
    stage = payload.stage or ""
    remote_build_id = payload.cloud_build_id or payload.github_run_id

    # Generate event ID for idempotency
    event_id = generate_webhook_event_id(build_id, platform, None, progress)

    conn = await get_db()
    try:
        # Idempotency check - skip if already processed
        if not await check_and_record_webhook_event(
            conn, event_id, "cloud_build_progress"
        ):
            logger.info(
                f"[CloudBuild] Skipping duplicate progress update for build {build_id}"
            )
            return {"status": "ok", "duplicate": True}

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
_queue_processor_task: Optional[asyncio.Task] = None


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
    global _queue_processor_task
    if _queue_processor_task is None or _queue_processor_task.done():
        _queue_processor_task = asyncio.create_task(process_build_queue())

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

                                # If still no source, try to download from project_files
                                if not source_dir.exists() or not list(
                                    source_dir.iterdir()
                                ):
                                    project_files = await conn.fetch(
                                        """SELECT id, filename, original_filename, file_path, is_cloud 
                                           FROM project_files WHERE project_id = $1""",
                                        project_id,
                                    )
                                    if project_files:
                                        import shutil

                                        persistent_source = safe_project_dir / "source"
                                        persistent_source.mkdir(
                                            parents=True, exist_ok=True
                                        )

                                        for pf in project_files:
                                            try:
                                                file_content = (
                                                    await storage_service.download_file(
                                                        pf["file_path"],
                                                        not pf["is_cloud"],
                                                    )
                                                )
                                                if file_content:
                                                    safe_fn = (
                                                        pf["original_filename"]
                                                        or pf["filename"]
                                                    )
                                                    safe_fn = "".join(
                                                        c
                                                        for c in safe_fn
                                                        if c.isalnum() or c in "._-"
                                                    )
                                                    if not safe_fn:
                                                        safe_fn = f"file_{pf['id']}"
                                                    (
                                                        persistent_source / safe_fn
                                                    ).write_bytes(file_content)
                                            except Exception as dl_err:
                                                logger.warning(
                                                    f"Error downloading file {pf['filename']}: {dl_err}"
                                                )

                                        if list(persistent_source.iterdir()):
                                            source_dir = persistent_source
                                        else:
                                            shutil.rmtree(
                                                persistent_source, ignore_errors=True
                                            )

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
    import traceback

    conn = None
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

        # If still no source, try to download from project_files
        if not source_dir.exists() or not list(source_dir.iterdir()):
            conn = await get_db()
            try:
                project_files = await conn.fetch(
                    """SELECT id, filename, original_filename, file_path, is_cloud 
                       FROM project_files WHERE project_id = $1""",
                    project_id,
                )
                if project_files:
                    import shutil

                    persistent_source = safe_project_dir / "source"
                    persistent_source.mkdir(parents=True, exist_ok=True)

                    for pf in project_files:
                        try:
                            file_content = await storage_service.download_file(
                                pf["file_path"], not pf["is_cloud"]
                            )
                            if file_content:
                                safe_fn = pf["original_filename"] or pf["filename"]
                                safe_fn = "".join(
                                    c for c in safe_fn if c.isalnum() or c in "._-"
                                )
                                if not safe_fn:
                                    safe_fn = f"file_{pf['id']}"
                                (persistent_source / safe_fn).write_bytes(file_content)
                        except Exception as dl_err:
                            logger.warning(
                                f"Error downloading file {pf['filename']}: {dl_err}"
                            )

                    if list(persistent_source.iterdir()):
                        source_dir = persistent_source
                    else:
                        shutil.rmtree(persistent_source, ignore_errors=True)
            finally:
                if conn:
                    await release_db(conn)
                    conn = None

        started = await trigger_cloud_build(build_id, config, source_dir)
        if not started:
            return {
                "status": "error",
                "message": "Failed to start cloud build - check logs",
            }
        return {"status": "running", "message": "Build started immediately"}
    except Exception as e:
        error_msg = str(e)
        error_traceback = traceback.format_exc()

        # Clean up error message - filter out long HTML responses
        clean_error = error_msg
        if "<!doctype html>" in error_msg or "<html" in error_msg.lower():
            if "Unable to retrieve" in error_msg:
                clean_error = "Unable to retrieve Identity Pool subject token - check Workload Identity configuration in GCP"
            elif "DefaultCredentialsError" in error_msg:
                clean_error = "GCP credentials not found - check Workload Identity or service account configuration"
            else:
                clean_error = (
                    "GCP authentication failed - check Workload Identity configuration"
                )

        # Clean traceback
        clean_traceback = error_traceback
        if "<!doctype html>" in error_traceback or "<html" in error_traceback.lower():
            lines = error_traceback.split("\n")
            clean_lines = []
            for line in lines:
                if "<!" in line or "<html" in line.lower() or len(line) > 200:
                    break
                clean_lines.append(line)
            clean_traceback = "\n".join(clean_lines)
            if not clean_traceback:
                clean_traceback = clean_error

        logger.error(f"[CloudBuild] trigger_build_directly failed: {clean_error}")

        # Store detailed error in database
        try:
            conn = await get_db()
            await conn.execute(
                """UPDATE cloud_builds 
                   SET status = 'failed', 
                       error_message = $1,
                       admin_error_details = $2
                   WHERE id = $3""",
                clean_error,
                clean_traceback,
                build_id,
            )
        except Exception as db_err:
            logger.error(f"[CloudBuild] Failed to store error in DB: {db_err}")

        return {
            "status": "error",
            "message": f"Failed to start cloud build: {error_msg}",
        }


@router.get("/{build_id}/queue-position")
async def get_queue_status(
    build_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(requires_feature("cloud_compilation")),
):
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
