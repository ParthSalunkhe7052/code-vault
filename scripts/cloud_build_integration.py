"""
CodeVault - Google Cloud Build Integration
This module replaces GitHub Actions API calls with Google Cloud Build API calls
"""

import json
import logging
import os
import re
import sys
import yaml
from typing import Dict, Any, Optional
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account
from google.api_core import exceptions
from google.protobuf import duration_pb2

logger = logging.getLogger(__name__)


def get_gcp_credentials() -> Optional[Any]:
    """
    Get GCP credentials - Priority:
    1. Service account JSON (GCP_SERVICE_ACCOUNT_JSON env var)
    2. Service account file (GOOGLE_APPLICATION_CREDENTIALS)
    3. Workload Identity (if configured and other options fail)
    """
    # FIRST: Check for service account JSON in environment variable (best for Heroku)
    service_account_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(service_account_json),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            logger.info(
                "[CloudBuild] Using service account JSON from environment variable (GCP_SERVICE_ACCOUNT_JSON)"
            )
            return credentials
        except Exception as e:
            logger.error(f"[CloudBuild] Failed to parse GCP_SERVICE_ACCOUNT_JSON: {e}")

    # SECOND: Check for service account file
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        logger.info("[CloudBuild] Using service account file credentials")
        return credentials

    # Check for Workload Identity configuration (Heroku) - LAST RESORT
    workload_pool = os.getenv("GCP_WORKLOAD_IDENTITY_POOL")
    service_account_email = os.getenv("GCP_SERVICE_ACCOUNT")

    if workload_pool and service_account_email:
        try:
            from google.auth import identity_pool

            audience = f"//iam.googleapis.com/{workload_pool}"

            external_credentials = identity_pool.Credentials.from_info(
                {
                    "type": "external_account",
                    "audience": audience,
                    "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
                    "token_url": "https://sts.googleapis.com/v1/token",
                    "credential_source": {
                        "url": "https://heroku.com/dyno/metadata",
                        "format": {
                            "type": "json",
                            "subject_token_field_name": "id_token",
                        },
                    },
                    "service_account_impersonation_url": f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{service_account_email}:generateAccessToken",
                }
            )
            return external_credentials
        except Exception as e:
            logger.error(f"[CloudBuild] Workload Identity failed: {e}")

    # Try Application Default Credentials (ADC)
    try:
        import google.auth

        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return credentials
    except Exception as e:
        logger.error(f"[CloudBuild] Application Default Credentials failed: {e}")

    return None


# Tier-based timeout configuration (in seconds)
TIER_TIMEOUTS = {
    "free": 1800,  # 30 minutes
    "pro": 3600,  # 60 minutes
    "business": 7200,  # 120 minutes
}


class CloudBuildClient:
    """Client for triggering and managing Google Cloud Build jobs"""

    def __init__(
        self,
        project_id: str = "cloudbuild-486309",
        credentials_path: Optional[str] = None,
    ):
        self.project_id = project_id

        credentials = None
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        else:
            credentials = get_gcp_credentials()

        if credentials:
            self.client = cloudbuild_v1.CloudBuildClient(credentials=credentials)
            self.credentials = credentials
        else:
            self.client = cloudbuild_v1.CloudBuildClient()
            self.credentials = None

    def trigger_build(self, build_config: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a Cloud Build job"""
        # Extract build parameters
        build_id = build_config.get("build_id", "unknown")
        project_id = build_config.get("project_id", "unknown")
        language = build_config.get("language", "python")
        platforms = build_config.get("target_platforms", "windows,linux,macos")
        source_url = build_config.get("source_url", "")
        config = build_config.get("config", {})
        callback_url = build_config.get("callback_url", "")

        # Create build object
        build = cloudbuild_v1.Build()

        # Load cloudbuild.yaml from project root (not scripts/ directory)
        project_root = os.path.dirname(os.path.dirname(__file__))
        cloudbuild_path = os.path.join(project_root, "cloudbuild.yaml")
        if not os.path.exists(cloudbuild_path):
            raise FileNotFoundError(f"cloudbuild.yaml not found at {cloudbuild_path}")

        with open(cloudbuild_path, "r") as f:
            build_config_yaml = yaml.safe_load(f)

        # Helper to convert keys
        def camel_to_snake(name):
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        def convert_keys(obj):
            if isinstance(obj, dict):
                return {camel_to_snake(k): convert_keys(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_keys(item) for item in obj]
            return obj

        # Set steps and options
        if "steps" in build_config_yaml:
            converted_steps = convert_keys(build_config_yaml["steps"])
            build.steps = [cloudbuild_v1.BuildStep(**step) for step in converted_steps]

        if "options" in build_config_yaml:
            converted_options = convert_keys(build_config_yaml["options"])
            build.options = cloudbuild_v1.BuildOptions(**converted_options)

        # Set timeout and machine type based on tier
        tier = build_config.get("plan_tier", "free")
        build.timeout = duration_pb2.Duration(seconds=TIER_TIMEOUTS.get(tier, 3600))

        # OPTIMIZED: Choose machine type based on platform + tier
        # Windows/Wine can't use parallel jobs effectively, so use smaller machines
        # Linux builds benefit from 8 cores with 6 parallel Nuitka jobs
        MachineType = cloudbuild_v1.BuildOptions.MachineType

        is_windows_only = platforms == "windows" or (
            isinstance(platforms, str)
            and "windows" in platforms
            and "linux" not in platforms
        )

        if is_windows_only:
            # Windows/Wine: Single-threaded Nuitka, no need for 8 cores
            # E2_MEDIUM (1 vCPU, 4GB) is sufficient for single-threaded builds
            # Cost savings: $0.003/min vs $0.0156/min (5x cheaper!)
            build.options.machine_type = MachineType.E2_MEDIUM
            logger.info(
                f"[CloudBuild] Windows-only build: using E2_MEDIUM (single-threaded Nuitka)"
            )
        else:
            # Linux builds: Benefit from 8 cores with 6 parallel jobs
            machine_types = {
                "business": MachineType.N1_HIGHCPU_8,
                "pro": MachineType.E2_HIGHCPU_8,
                "free": MachineType.E2_MEDIUM,
            }
            build.options.machine_type = machine_types.get(tier, MachineType.E2_MEDIUM)

        # Upload config to GCS
        from google.cloud import storage as gcs_storage

        gcs_client = gcs_storage.Client(
            credentials=self.credentials, project=self.project_id
        )
        config_bucket = gcs_client.bucket("codevault-builds")
        config_blob = config_bucket.blob(f"builds/{build_id}/config.json")
        config_blob.upload_from_string(
            json.dumps(config), content_type="application/json"
        )
        config_url = f"gs://codevault-builds/builds/{build_id}/config.json"

        # Set Substitutions (GCB expects these to start with _)
        # IMPORTANT: Only include substitutions that are USED in cloudbuild.yaml steps
        # Config data (entry_file, license_key, api_url, etc.) is passed via config.json
        # which is downloaded from _CONFIG_URL - this avoids the 8KB limit and unused var errors
        callback_secret = build_config.get("callback_secret", "")
        build.substitutions = {
            "_BUILD_ID": build_id,
            "_PROJECT_ID": project_id,
            "_LANGUAGE": language,
            "_TARGET_PLATFORMS": platforms,
            "_SOURCE_URL": source_url,
            "_CONFIG_URL": config_url,
            "_CALLBACK_URL": callback_url,
            "_CALLBACK_SECRET": callback_secret,
            "_OUTPUT_NAME": config.get("output_name", "app"),
            "_GCS_BUCKET": "codevault-builds",
        }

        try:
            operation = self.client.create_build(
                project_id=self.project_id, build=build
            )
            build_result = operation.metadata.build if operation.metadata else None

            created_at = None
            if (
                build_result
                and hasattr(build_result, "create_time")
                and build_result.create_time
            ):
                created_at = build_result.create_time.isoformat()

            return {
                "build_id": build_result.id if build_result else "unknown",
                "status": "QUEUED",
                "logs_url": f"https://console.cloud.google.com/cloud-build/builds/{build_result.id}?project={self.project_id}",
                "created_at": created_at,
                "project": self.project_id,
            }
        except exceptions.GoogleAPIError as e:
            raise Exception(f"Cloud Build API error: {str(e)}")

    def get_build_status(self, build_id: str) -> Dict[str, Any]:
        """Get the status of a Cloud Build job"""
        try:
            build = self.client.get_build(project_id=self.project_id, id=build_id)

            def format_time(ts):
                if not ts:
                    return None
                return ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

            return {
                "build_id": build.id,
                "status": build.status.name,
                "create_time": format_time(build.create_time),
                "start_time": format_time(build.start_time),
                "finish_time": format_time(build.finish_time),
                "logs_url": build.log_url,
            }
        except exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to get build status: {str(e)}")

    def cancel_build(self, build_id: str) -> bool:
        """Cancel a running Cloud Build job"""
        try:
            self.client.cancel_build(project_id=self.project_id, id=build_id)
            return True
        except exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to cancel build: {str(e)}")
