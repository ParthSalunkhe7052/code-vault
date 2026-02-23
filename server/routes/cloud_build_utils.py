"""
CodeVault Cloud Build - Utility Functions

Common utility functions for the cloud build system.
"""

import os
import re
import hmac
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import timedelta

from fastapi import HTTPException
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
        candidate_resolved.relative_to(base_resolved)
        return candidate_resolved
    except (ValueError, OSError):
        raise HTTPException(400, "Invalid path component")


def get_gcs_client_with_credentials():
    """Get GCS client with proper credentials (same as CloudBuildClient)."""
    import json
    from google.cloud import storage as gcs_storage
    from google.oauth2 import service_account

    service_account_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(service_account_json),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return gcs_storage.Client(credentials=credentials), credentials
        except Exception as e:
            logger.warning(
                f"[CloudBuild] Failed to use GCP_SERVICE_ACCOUNT_JSON for GCS: {e}"
            )

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return gcs_storage.Client(credentials=credentials), credentials
        except Exception as e:
            logger.warning(f"[CloudBuild] Failed to use credentials file for GCS: {e}")

    try:
        return gcs_storage.Client(), None
    except Exception as e:
        logger.error(f"[CloudBuild] Failed to create GCS client: {e}")
        return None, None


def check_gcs_blob_exists(download_key: str) -> bool:
    """Check if a blob exists in GCS before generating signed URL."""
    try:
        from config import GCS_BUILDS_BUCKET

        gcs_client, _ = get_gcs_client_with_credentials()
        if not gcs_client:
            return False

        bucket = gcs_client.bucket(GCS_BUILDS_BUCKET)
        blob = bucket.blob(download_key)
        return blob.exists()
    except Exception as e:
        logger.debug(
            f"[CloudBuild] Blob existence check failed for {download_key}: {e}"
        )
        return False


def find_artifact_in_gcs(build_id: str, platform: str) -> Optional[Tuple[str, str]]:
    """Find artifact in GCS by listing the build directory.

    Returns:
        Tuple of (download_key, filename) or None if not found.
    """
    try:
        from config import GCS_BUILDS_BUCKET

        gcs_client, _ = get_gcs_client_with_credentials()
        if not gcs_client:
            return None

        bucket = gcs_client.bucket(GCS_BUILDS_BUCKET)
        prefix = f"builds/{build_id}/{platform}/"

        blobs = list(bucket.list_blobs(prefix=prefix, max_results=20))

        # Priority order for different artifact types
        # .tar.gz is preferred for Python builds (contains .dist folder with all DLLs)
        # .exe is for onefile builds or Node.js builds
        extensions_priority = [".tar.gz", ".exe", ".zip", ""]

        for ext in extensions_priority:
            for blob in blobs:
                name = blob.name
                if name == prefix:
                    continue
                if ext and name.endswith(ext):
                    filename = name.split("/")[-1]
                    logger.info(f"[CloudBuild] Found artifact in GCS: {name}")
                    return name, filename
                elif not ext and not name.endswith("/"):
                    filename = name.split("/")[-1]
                    if "." not in filename or filename.endswith(
                        (".exe", ".zip", ".tar.gz")
                    ):
                        logger.info(f"[CloudBuild] Found artifact in GCS: {name}")
                        return name, filename

        logger.warning(f"[CloudBuild] No artifact found in GCS at {prefix}")
        return None
    except Exception as e:
        logger.error(f"[CloudBuild] GCS listing failed: {e}")
        return None


def get_artifact_filename_priority(
    platform: str, language: str, output_name: str
) -> List[str]:
    """Get prioritized list of possible artifact filenames.

    Order based on:
    - Language (nodejs -> exe/binary, python -> tar.gz with dependencies)
    - Platform (windows -> tar.gz/exe, linux -> tar.gz/binary)
    - Build type (standalone -> tar.gz with .dist folder, onefile -> single exe)

    For Python builds:
    - Standalone mode (default): Creates .tar.gz containing .dist folder with all DLLs
    - Onefile mode: Creates single .exe (but has higher AV false positive risk)
    """
    filenames = []

    if platform == "windows":
        if language == "nodejs":
            filenames.append(f"{output_name}.exe")
        else:
            # Python builds: .tar.gz contains .dist folder with all dependencies (python311.dll, etc.)
            filenames.append(f"{output_name}.tar.gz")
            filenames.append(f"{output_name}.exe")
            filenames.append(f"{output_name}-windows.zip")
            filenames.append(f"{output_name}.zip")
    elif platform == "linux":
        if language == "nodejs":
            filenames.append(f"{output_name}")
            filenames.append(f"{output_name}.bin")
        else:
            # Python builds: .tar.gz contains .dist folder with all dependencies
            filenames.append(f"{output_name}.tar.gz")
            filenames.append(f"{output_name}-linux.tar.gz")
            filenames.append(f"{output_name}")
    elif platform == "macos":
        if language == "nodejs":
            filenames.append(f"{output_name}")
        else:
            filenames.append(f"{output_name}")
            filenames.append(f"{output_name}-macos.zip")
            filenames.append(f"{output_name}.zip")

    filenames.append(f"{platform}_build.zip")
    filenames.append(f"{platform}_build.exe")

    return filenames


def generate_gcs_signed_url(
    download_key: str, verify_exists: bool = True
) -> Optional[str]:
    """Generate signed URL for GCS artifacts (Cloud Build) or R2 artifacts (GitHub Actions).

    Priority:
    1. Try GCS first (for Cloud Build artifacts)
    2. Fallback to R2 (for GitHub Actions artifacts)

    Args:
        download_key: The GCS/R2 object key
        verify_exists: If True, verify blob exists before generating URL

    Returns signed URL valid for 1 hour, or None if generation fails.
    """
    try:
        from config import GCS_BUILDS_BUCKET

        gcs_client, credentials = get_gcs_client_with_credentials()
        if not gcs_client:
            logger.error(
                "[CloudBuild] No GCS client available for signed URL generation"
            )
            return None

        bucket = gcs_client.bucket(GCS_BUILDS_BUCKET)
        blob = bucket.blob(download_key)

        # Verify blob exists if requested
        if verify_exists:
            if not blob.exists():
                logger.warning(f"[CloudBuild] Blob does not exist: {download_key}")
                return None

        try:
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=1),
                method="GET",
            )
            logger.info(f"[CloudBuild] Generated GCS signed URL for {download_key}")
            return signed_url
        except Exception as sign_error:
            logger.debug(
                f"[CloudBuild] Signed URL generation failed for {download_key}: {sign_error}"
            )
            return None
    except Exception as gcs_error:
        logger.warning(f"[CloudBuild] GCS signed URL failed: {gcs_error}")

    if storage_service.is_cloud_enabled() and storage_service.client:
        try:
            r2_url = storage_service.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": storage_service.bucket, "Key": download_key},
                ExpiresIn=3600,
            )
            logger.info(f"[CloudBuild] Generated R2 signed URL for {download_key}")
            return r2_url
        except Exception as r2_error:
            logger.debug(f"[CloudBuild] R2 signed URL failed: {r2_error}")

    logger.warning(f"[CloudBuild] Could not generate signed URL for {download_key}")
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

    if not storage_service.is_cloud_enabled() or not storage_service.client:
        return

    project_source_key = f"uploads/{project_id}/source.zip"

    try:
        s3 = storage_service.client
        bucket = storage_service.bucket

        try:
            s3.head_object(Bucket=bucket, Key=project_source_key)
            s3.delete_object(Bucket=bucket, Key=project_source_key)
            logger.info(f"[Cache] Invalidated cached source: {project_source_key}")
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"[Cache] Failed to invalidate source cache: {e}")
