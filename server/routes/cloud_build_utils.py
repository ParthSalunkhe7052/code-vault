"""
CodeVault Cloud Build - Utility Functions

Common utility functions for the cloud build system.
"""

import json
import os
import re
import hmac
import hashlib
import logging
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from database import get_db, release_db
from config import GCP_PROJECT_ID
from storage_service import storage_service

logger = logging.getLogger(__name__)


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
        base_resolved = base_dir.resolve()
        candidate_resolved = candidate.resolve()
        # Check if candidate is within base_dir using relative_to
        candidate_resolved.relative_to(base_resolved)
        return candidate_resolved
    except (ValueError, OSError):
        raise HTTPException(400, "Invalid path component")


async def generate_gcs_signed_url(download_key: str) -> Optional[str]:
    """Generate signed URL for GCS artifacts"""
    try:
        from google.cloud import storage as gcs_storage
        from datetime import timedelta

        # Initialize GCS client
        gcs_client = gcs_storage.Client()
        bucket = gcs_client.bucket("codevault-builds")
        blob = bucket.blob(download_key)

        # Check if blob exists in GCS
        if blob.exists():
            # Generate signed URL valid for 1 hour
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=1),
                method="GET",
            )
            return url
        return None
    except Exception as e:
        logger.error(f"[CloudBuild] Failed to generate GCS signed URL: {e}")
        return None


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature of webhook payload"""
    try:
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"[CloudBuild] Signature verification failed: {e}")
        return False


async def invalidate_cached_source(project_id: str) -> None:
    """Invalidate cached source for a project when files are uploaded/changed."""
    from storage_service import storage_service

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
