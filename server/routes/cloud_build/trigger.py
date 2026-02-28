from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
import logging
import os
import json
import secrets
import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone

from database import get_db, release_db
from repositories.build_repo import BuildRepository
from repositories.project_repo import ProjectRepository
from storage_service import storage_service
from utils import (
    get_current_user,
    get_user_tier,
    compute_ed25519_signature,
    compute_signature,
    SECRET_KEY,
)
from config import (
    ENVIRONMENT,
    GCP_PROJECT_ID,
    get_build_credit_cost,
)
from routes.cloud_build_utils import (
    validate_safe_path,
    invalidate_cached_source,
)
from cloud_build_integration import CloudBuildClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Local upload directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"

class CloudBuildRequest(BaseModel):
    project_id: str
    license_id: Optional[str] = None
    target_platforms: List[str] = ["windows"]
    compatibility_mode: bool = False
    license_mode: Optional[str] = "generic"
    demo_duration: Optional[int] = 60

    @validator("target_platforms")
    def validate_platforms(cls, v):
        allowed = {"windows", "macos", "linux"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid platforms: {invalid}")
        return v

class CloudBuildResponse(BaseModel):
    build_id: str
    status: str
    message: str

@router.post("/start", response_model=CloudBuildResponse)
async def start_cloud_build(
    data: CloudBuildRequest,
    user: dict = Depends(get_current_user),
):
    """Initiate a cloud build process."""
    conn = await get_db()
    build_id = secrets.token_hex(16)
    deducted_credits = 0
    
    try:
        # 1. Verify project ownership
        project = await ProjectRepository.get_project_by_id(conn, data.project_id, user["id"])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2. Check credits - get language from project settings
        project_dict = dict(project)
        project_settings = project_dict.get("settings")
        if isinstance(project_settings, str):
            project_settings = json.loads(project_settings)
        project_settings = project_settings or {}
        
        language = project_dict.get("language") or project_settings.get("language", "python")
        credit_cost = get_build_credit_cost(data.target_platforms, language)
        success = await BuildRepository.deduct_credits(conn, user["id"], credit_cost)
        if not success:
            raise HTTPException(status_code=402, detail="Insufficient build credits")
        deducted_credits = credit_cost

        # 3. Create build record
        compiler_options = project_dict.get("compiler_options")
        if isinstance(compiler_options, str):
            compiler_options = json.loads(compiler_options)
        compiler_options = compiler_options or {}
        
        build_data = {
            "id": build_id,
            "user_id": user["id"],
            "project_id": data.project_id,
            "license_id": data.license_id,
            "status": "pending",
            "target_platforms": data.target_platforms,
            "language": language,
            "entry_file": project_settings.get("entry_file", "main.py"),
            "output_name": project_settings.get("output_name", "app"),
            "config_json": {
                "compatibility_mode": data.compatibility_mode,
                "license_mode": data.license_mode,
                "demo_duration": data.demo_duration,
                "compiler_options": compiler_options,
            },
        }
        await BuildRepository.create_build(conn, build_data)

        # 4. Trigger build
        try:
            from config import (
                PUBLIC_API_URL,
                BUILD_CALLBACK_SECRET,
                GCS_BUILDS_BUCKET,
            )
            
            # Use storage service to get a signed URL for the source code
            # Note: The ZIP should already be uploaded to storage
            source_key = f"projects/{data.project_id}/source.zip"
            source_url = await storage_service.get_signed_url(
                GCS_BUILDS_BUCKET, source_key, expires_in=3600
            )
            
            # Prepare config for GCP build
            build_config = {
                "build_id": build_id,
                "project_id": data.project_id,
                "language": language,
                "target_platforms": ",".join(data.target_platforms),
                "source_url": source_url,
                "callback_url": f"{PUBLIC_API_URL}/api/v1/cloud-build/webhook",
                "callback_secret": BUILD_CALLBACK_SECRET,
                "output_name": project_settings.get("output_name", "app"),
                "compatibility_mode": data.compatibility_mode,
                "license_mode": data.license_mode,
                "demo_duration": data.demo_duration,
            }
            
            # Initialize client and trigger
            cb_client = CloudBuildClient()
            cb_result = cb_client.trigger_build(build_config)
            
            # Update build record with GCP ID
            await BuildRepository.update_build_status(
                conn, build_id, "pending", None
            )
            # We should probably add a method to update GCP ID, but status update is enough for now
            # since update_build_status is already there. Let's add gcp_build_id if repo supports it.
            await conn.execute(
                "UPDATE cloud_builds SET gcp_build_id = $1 WHERE id = $2",
                cb_result["build_id"],
                build_id,
            )
            
            logger.info(f"[CloudBuild] Triggered build {build_id} -> GCP {cb_result['build_id']}")

        except Exception as trigger_err:
            logger.error(f"[CloudBuild] Trigger failed: {trigger_err}")
            # Even if trigger fails, we return the build_id so user can see it in history
            # But we update status to failed
            await BuildRepository.update_build_status(
                conn, build_id, "failed", f"Trigger failed: {str(trigger_err)}"
            )

        return CloudBuildResponse(
            build_id=build_id,
            status="pending",
            message="Cloud build initiated successfully",
        )

    except Exception as e:
        if deducted_credits > 0:
            await BuildRepository.refund_credits(conn, user["id"], deducted_credits)
        logger.error(f"[CloudBuild] Failed to start build: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await release_db(conn)
