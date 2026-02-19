"""
Google Cloud Build Integration Module

Provides a client for triggering and managing builds on Google Cloud Build.
"""

import os
import json
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class CloudBuildClient:
    """Client for interacting with Google Cloud Build API."""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize Cloud Build client.

        Args:
            project_id: GCP project ID. If not provided, uses GCP_PROJECT_ID env var.
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        if not self.project_id:
            raise ValueError("GCP project ID is required")

        # Import here to avoid dependency issues if not using Cloud Build
        try:
            from google.cloud.devtools import cloudbuild_v1
            from google.oauth2 import service_account

            self.cloudbuild_v1 = cloudbuild_v1
            self.service_account = service_account
        except ImportError as e:
            logger.error(f"Failed to import Google Cloud Build libraries: {e}")
            raise

        # Initialize client with credentials
        self.client = self._create_client()

    def _create_client(self):
        """Create Cloud Build client with appropriate credentials."""
        # Try service account JSON first
        service_account_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            try:
                credentials = (
                    self.service_account.Credentials.from_service_account_info(
                        json.loads(service_account_json),
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                )
                return self.cloudbuild_v1.CloudBuildClient(credentials=credentials)
            except Exception as e:
                logger.warning(f"Failed to use GCP_SERVICE_ACCOUNT_JSON: {e}")

        # Try credentials file
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            try:
                credentials = (
                    self.service_account.Credentials.from_service_account_file(
                        credentials_path,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                )
                return self.cloudbuild_v1.CloudBuildClient(credentials=credentials)
            except Exception as e:
                logger.warning(f"Failed to use credentials file: {e}")

        # Fallback to default credentials (Workload Identity, etc.)
        try:
            return self.cloudbuild_v1.CloudBuildClient()
        except Exception as e:
            logger.error(f"Failed to create Cloud Build client: {e}")
            raise

    def trigger_build(self, build_config: Dict[str, Any]) -> Dict[str, str]:
        """Trigger a new Cloud Build.

        Args:
            build_config: Build configuration dict containing:
                - build_id: Unique build ID
                - project_id: CodeVault project ID
                - language: 'python' or 'nodejs'
                - target_platforms: Comma-separated platforms (windows,linux,macos)
                - source_url: URL to download source code
                - config: Full build configuration
                - callback_url: Webhook URL for status updates
                - callback_secret: Secret for webhook verification
                - plan_tier: User's subscription tier
                - compatibility_mode: Enable compatibility mode
                - fast_build: Enable fast build mode
                - signing_public_key: Ed25519 public key for signing
                - signing_private_key: Ed25519 private key for signing
                - heartbeat_interval: Heartbeat interval in seconds
                - binary_hash_tracking: Enable binary hash tracking
                - enable_ed25519_signatures: Enable Ed25519 signatures

        Returns:
            Dict with 'build_id' (GCP build ID) and 'logs_url'
        """
        build_id = build_config.get("build_id", "unknown")
        language = build_config.get("language", "python")
        target_platforms = build_config.get("target_platforms", "windows")

        # Create build name
        build_name = f"codevault-{build_id}"

        # Create substitutions for the build
        substitutions = {
            "_BUILD_ID": build_id,
            "_PROJECT_ID": build_config.get("project_id", ""),
            "_LANGUAGE": language,
            "_TARGET_PLATFORMS": target_platforms,
            "_SOURCE_URL": build_config.get("source_url", ""),
            "_CALLBACK_URL": build_config.get("callback_url", ""),
            "_CALLBACK_SECRET": build_config.get("callback_secret", ""),
            "_PLAN_TIER": build_config.get("plan_tier", "free"),
            "_COMPATIBILITY_MODE": str(
                build_config.get("compatibility_mode", False)
            ).lower(),
            "_FAST_BUILD": str(build_config.get("fast_build", False)).lower(),
            "_SIGNING_PUBLIC_KEY": build_config.get("signing_public_key", ""),
            "_SIGNING_PRIVATE_KEY": build_config.get("signing_private_key", ""),
            "_HEARTBEAT_INTERVAL": str(build_config.get("heartbeat_interval", 300)),
            "_BINARY_HASH_TRACKING": str(
                build_config.get("binary_hash_tracking", True)
            ).lower(),
            "_ENABLE_ED25519_SIGNATURES": str(
                build_config.get("enable_ed25519_signatures", False)
            ).lower(),
        }

        # Create the build configuration
        build = self.cloudbuild_v1.Build(
            name=build_name,
            substitutions=substitutions,
            # Cloud Build configuration - uses cloudbuild.yaml in repo
            source=self.cloudbuild_v1.Source(
                storage_source=self.cloudbuild_v1.StorageSource(
                    bucket=os.getenv("GCS_BUILD_SCRIPTS_BUCKET", "codevault-builds"),
                    object_="cloudbuild.yaml",
                )
            ),
            # Add labels for tracking
            tags=[
                f"codevault-{build_id}",
                f"project-{build_config.get('project_id', 'unknown')}",
                f"language-{language}",
            ],
        )

        # Submit the build using CreateBuildRequest
        parent = f"projects/{self.project_id}/locations/global"
        request = self.cloudbuild_v1.CreateBuildRequest(
            parent=parent,
            build=build,
        )
        operation = self.client.create_build(request=request)

        # Wait for the operation to complete (this is async, we don't wait)
        gcp_build = operation.metadata
        gcp_build_id = gcp_build.build.id

        # Generate logs URL
        logs_url = f"https://console.cloud.google.com/cloud-build/builds/{gcp_build_id}?project={self.project_id}"

        logger.info(
            f"[CloudBuild] Triggered build {build_id} -> GCP Build {gcp_build_id}"
        )

        return {
            "build_id": gcp_build_id,
            "logs_url": logs_url,
        }

    def get_build_status(self, gcp_build_id: str) -> Dict[str, Any]:
        """Get the status of a Cloud Build.

        Args:
            gcp_build_id: The GCP build ID (not CodeVault build ID)

        Returns:
            Dict with 'status', 'logs_url', and other build details
        """
        name = f"projects/{self.project_id}/locations/global/builds/{gcp_build_id}"

        try:
            request = self.cloudbuild_v1.GetBuildRequest(name=name)
            build = self.client.get_build(request=request)

            # Map GCP status to our format
            status_map = {
                "STATUS_UNKNOWN": "unknown",
                "PENDING": "pending",
                "QUEUED": "queued",
                "WORKING": "running",
                "SUCCESS": "SUCCESS",
                "FAILURE": "FAILURE",
                "INTERNAL_ERROR": "FAILURE",
                "TIMEOUT": "EXPIRED",
                "CANCELLED": "CANCELLED",
                "EXPIRED": "EXPIRED",
            }

            status = status_map.get(build.status.name, "unknown")

            logs_url = f"https://console.cloud.google.com/cloud-build/builds/{gcp_build_id}?project={self.project_id}"

            # Convert protobuf Timestamp to datetime then to ISO format string
            def timestamp_to_iso(ts):
                if ts is None:
                    return None
                from datetime import datetime

                # Convert seconds and nanos to datetime
                dt = datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9)
                return dt.isoformat()

            return {
                "status": status,
                "logs_url": logs_url,
                "gcp_status": build.status.name,
                "create_time": timestamp_to_iso(build.create_time),
                "start_time": timestamp_to_iso(build.start_time),
                "finish_time": timestamp_to_iso(build.finish_time),
            }

        except Exception as e:
            logger.error(
                f"[CloudBuild] Failed to get build status for {gcp_build_id}: {e}"
            )
            raise

    def cancel_build(self, gcp_build_id: str) -> bool:
        """Cancel a running Cloud Build.

        Args:
            gcp_build_id: The GCP build ID to cancel

        Returns:
            True if cancelled successfully
        """
        name = f"projects/{self.project_id}/locations/global/builds/{gcp_build_id}"

        try:
            request = self.cloudbuild_v1.CancelBuildRequest(name=name)
            self.client.cancel_build(request=request)
            logger.info(f"[CloudBuild] Cancelled build {gcp_build_id}")
            return True
        except Exception as e:
            logger.error(f"[CloudBuild] Failed to cancel build {gcp_build_id}: {e}")
            raise

    def list_builds(
        self, filter_tag: Optional[str] = None, page_size: int = 10
    ) -> list:
        """List recent Cloud Builds.

        Args:
            filter_tag: Optional tag to filter by
            page_size: Number of builds to return

        Returns:
            List of build dicts
        """
        parent = f"projects/{self.project_id}/locations/global"

        try:
            request = self.cloudbuild_v1.ListBuildsRequest(
                parent=parent,
                page_size=page_size,
            )

            if filter_tag:
                request.filter = f'tags="{filter_tag}"'

            response = self.client.list_builds(request=request)

            builds = []
            for build in response.builds:
                builds.append(
                    {
                        "id": build.id,
                        "status": build.status.name,
                        "tags": list(build.tags),
                        "create_time": build.create_time.isoformat()
                        if build.create_time
                        else None,
                    }
                )

            return builds

        except Exception as e:
            logger.error(f"[CloudBuild] Failed to list builds: {e}")
            raise
