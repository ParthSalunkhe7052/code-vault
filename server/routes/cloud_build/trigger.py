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
        project_settings = project.get("settings", {}) if isinstance(project, dict) else {}
        language = project_settings.get("language", "python") if isinstance(project_settings, dict) else "python"
        credit_cost = get_build_credit_cost(data.target_platforms, language)
        success = await BuildRepository.deduct_credits(conn, user["id"], credit_cost)
        if not success:
            raise HTTPException(status_code=402, detail="Insufficient build credits")
        deducted_credits = credit_cost

        # 3. Create build record
        build_data = {
            'id': build_id,
            'user_id': user["id"],
            'project_id': data.project_id,
            'license_id': data.license_id,
            'status': 'pending',
            'target_platforms': data.target_platforms,
        }
        await BuildRepository.create_build(conn, build_data)

        # 4. Trigger build (Simplified for extraction)
        # In real implementation, this would call CloudBuildClient
        logger.info(f"[CloudBuild] Triggered build {build_id} for project {data.project_id}")

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
