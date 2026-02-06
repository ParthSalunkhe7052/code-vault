"""
CodeVault - Google Cloud Build Integration
This module replaces GitHub Actions API calls with Google Cloud Build API calls
"""

import json
import os
import re
import yaml
import base64
from typing import Dict, Any, Optional
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account
from google.api_core import exceptions
from google.protobuf import duration_pb2


class CloudBuildClient:
    """Client for triggering and managing Google Cloud Build jobs"""

    def __init__(
        self,
        project_id: str = "cloudbuild-486309",
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize Cloud Build client

        Args:
            project_id: Google Cloud project ID
            credentials_path: Path to service account JSON key file
                            If None, will use gcloud auth credentials
        """
        self.project_id = project_id

        # Load credentials - use gcloud auth by default
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self.client = cloudbuild_v1.CloudBuildClient(credentials=credentials)
        else:
            # Use gcloud auth credentials (automatically discovered)
            # This works with: gcloud auth login
            self.client = cloudbuild_v1.CloudBuildClient()

    def trigger_build(self, build_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a Cloud Build job

        Args:
            build_config: Dictionary containing build configuration:
                - build_id: Unique build identifier
                - project_id: User's project ID
                - language: 'python' or 'nodejs'
                - target_platforms: Comma-separated list (e.g., 'windows,linux,macos')
                - source_url: Presigned URL to download source code
                - config: Build configuration dict (entry_file, output_name, etc.)
                - callback_url: Webhook URL for completion notification
                - plan_tier: User's plan tier (free/pro/enterprise)
                - compatibility_mode: Boolean for compatibility mode
                - fast_build: Boolean for fast build mode

        Returns:
            Dictionary with build information:
                - build_id: Cloud Build ID
                - status: Build status
                - logs_url: URL to view build logs
                - created_at: Timestamp

        Raises:
            exceptions.GoogleAPIError: If the API call fails
        """
        # Extract build parameters
        build_id = build_config.get("build_id", "unknown")
        project_id = build_config.get("project_id", "unknown")
        language = build_config.get("language", "python")
        platforms = build_config.get("target_platforms", "windows,linux,macos")
        source_url = build_config.get("source_url", "")
        config = build_config.get("config", {})
        callback_url = build_config.get("callback_url", "")
        plan_tier = build_config.get("plan_tier", "free")
        compatibility_mode = str(build_config.get("compatibility_mode", False)).lower()
        fast_build = str(build_config.get("fast_build", False)).lower()

        # Create build object
        build = cloudbuild_v1.Build()

        # Load cloudbuild.yaml from local file (not from GitHub repo)
        cloudbuild_path = os.path.join(os.path.dirname(__file__), "cloudbuild.yaml")

        if not os.path.exists(cloudbuild_path):
            raise FileNotFoundError(f"cloudbuild.yaml not found at {cloudbuild_path}")

        with open(cloudbuild_path, "r") as f:
            build_config_yaml = yaml.safe_load(f)

        # Helper function to convert camelCase to snake_case
        def camel_to_snake(name):
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        # Convert dict keys from camelCase to snake_case recursively
        def convert_keys(obj):
            if isinstance(obj, dict):
                return {camel_to_snake(k): convert_keys(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_keys(item) for item in obj]
            else:
                return obj

        # Set steps from cloudbuild.yaml
        if "steps" in build_config_yaml:
            converted_steps = convert_keys(build_config_yaml["steps"])
            build.steps = [cloudbuild_v1.BuildStep(**step) for step in converted_steps]

        # Set options (convert camelCase to snake_case)
        if "options" in build_config_yaml:
            converted_options = convert_keys(build_config_yaml["options"])
            build.options = cloudbuild_v1.BuildOptions(**converted_options)

        # Set timeout based on plan tier - use duration_pb2.Duration
        tier = build_config.get("plan_tier", "free")
        timeout_seconds = {
            "free": 1800,  # 30 minutes
            "pro": 3600,  # 60 minutes
            "business": 7200,  # 120 minutes
        }.get(tier, 3600)
        build.timeout = duration_pb2.Duration(seconds=timeout_seconds)

        # Set machine type based on plan tier
        # Access MachineType via BuildOptions to avoid import errors
        MachineType = cloudbuild_v1.BuildOptions.MachineType

        machine_types = {
            "business": MachineType.N1_HIGHCPU_8,  # Faster, more expensive (~7-8 min builds)
            "pro": MachineType.E2_HIGHCPU_8,  # Balanced (~8-9 min builds)
            "free": MachineType.E2_MEDIUM,  # Budget (free tier) (~12-15 min builds)
        }
        machine_type = machine_types.get(tier, MachineType.E2_MEDIUM)
        build.options.machine_type = machine_type

        # Set secrets
        if "availableSecrets" in build_config_yaml:
            secrets_data = convert_keys(build_config_yaml["availableSecrets"])
            build.available_secrets = cloudbuild_v1.Secrets(**secrets_data)

        # Upload config to GCS to avoid substitution size limits (8KB max)
        # Cloud Build substitutions have an 8KB limit, so we store large configs in GCS
        from google.cloud import storage as gcs_storage

        gcs_client = gcs_storage.Client()
        config_bucket = gcs_client.bucket("codevault-builds")
        config_blob = config_bucket.blob(f"builds/{build_id}/config.json")
        config_blob.upload_from_string(
            json.dumps(config), content_type="application/json"
        )
        config_url = f"gs://codevault-builds/builds/{build_id}/config.json"

        # Add substitution variables (parameters for cloudbuild.yaml)
        # Use GCS URL for config to avoid 8KB substitution limit
        build.substitutions = {
            "_BUILD_ID": build_id,
            "_PROJECT_ID": project_id,
            "_LANGUAGE": language,
            "_TARGET_PLATFORMS": platforms,
            "_SOURCE_URL": source_url,
            "_CONFIG_URL": config_url,
            "_CALLBACK_URL": callback_url,
            "_OUTPUT_NAME": config.get("output_name", "app"),
        }

        try:
            # Submit build
            operation = self.client.create_build(
                project_id=self.project_id, build=build
            )

            # Get build metadata - operation.metadata.build IS the Build object
            build_result = operation.metadata.build if operation.metadata else None

            # Convert create_time to ISO format string
            created_at = None
            if (
                build_result
                and hasattr(build_result, "create_time")
                and build_result.create_time
            ):
                created_at = build_result.create_time.isoformat()

            build_id_result = build_result.id if build_result else "unknown"

            return {
                "build_id": build_id_result,
                "status": "QUEUED",
                "logs_url": f"https://console.cloud.google.com/cloud-build/builds/{build_id_result}?project={self.project_id}",
                "created_at": created_at,
                "project": self.project_id,
            }

        except exceptions.GoogleAPIError as e:
            raise Exception(f"Cloud Build API error: {str(e)}")

    def get_build_status(self, build_id: str) -> Dict[str, Any]:
        """
        Get the status of a Cloud Build job

        Args:
            build_id: Cloud Build ID

        Returns:
            Dictionary with build status information
        """
        try:
            build = self.client.get_build(project_id=self.project_id, id=build_id)

            return {
                "build_id": build.id,
                "status": build.status.name,  # QUEUED, WORKING, SUCCESS, FAILURE, etc.
                "create_time": build.create_time.ToJsonString()
                if build.create_time
                else None,
                "start_time": build.start_time.ToJsonString()
                if build.start_time
                else None,
                "finish_time": build.finish_time.ToJsonString()
                if build.finish_time
                else None,
                "logs_url": build.log_url,
            }

        except exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to get build status: {str(e)}")

    def cancel_build(self, build_id: str) -> bool:
        """
        Cancel a running Cloud Build job

        Args:
            build_id: Cloud Build ID

        Returns:
            True if successful
        """
        try:
            self.client.cancel_build(project_id=self.project_id, id=build_id)
            return True

        except exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to cancel build: {str(e)}")


# ============================================
# Example Usage for Your Backend
# ============================================


def example_usage():
    """
    Example: How to use this in your backend
    """

    # Initialize client (one-time setup)
    # Make sure to set GOOGLE_APPLICATION_CREDENTIALS environment variable
    # or pass credentials_path directly
    cloud_build = CloudBuildClient(
        project_id="cloudbuild-486309",
        credentials_path="/path/to/service-account-key.json",  # Or use env var
    )

    # Trigger a build (replace GitHub Actions call with this)
    build_config = {
        "build_id": "build-12345",
        "project_id": "user-project-123",
        "language": "python",
        "target_platforms": "windows,linux",
        "source_url": "https://your-r2-bucket.com/presigned-url/source.zip",
        "config": {
            "entry_file": "main.py",
            "output_name": "my-app",
            "license_key": "GENERIC_BUILD",
            "api_url": "https://your-api.com/validate",
        },
        "callback_url": "https://your-api.com/webhook/build-complete",
        "plan_tier": "free",
        "compatibility_mode": False,
        "fast_build": False,
    }

    try:
        # Trigger the build
        result = cloud_build.trigger_build(build_config)

        print(f"Build started!")
        print(f"  Build ID: {result['build_id']}")
        print(f"  Status: {result['status']}")
        print(f"  Logs: {result['logs_url']}")

        # Store build ID in your database for tracking
        # db.store_build_id(user_id, result['build_id'])

        return result

    except Exception as e:
        print(f"Error triggering build: {e}")
        return None


def check_build_status_example():
    """
    Example: Check status of a running build
    """
    cloud_build = CloudBuildClient(project_id="cloudbuild-486309")

    try:
        status = cloud_build.get_build_status("build-id-from-trigger")

        print(f"Build Status: {status['status']}")
        print(f"Started: {status['start_time']}")
        print(f"Finished: {status['finish_time']}")

        return status

    except Exception as e:
        print(f"Error checking build status: {e}")
        return None


# ============================================
# Integration with Your Existing Backend
# ============================================


class BuildTrigger:
    """
    Drop-in replacement for your existing GitHub Actions trigger
    """

    def __init__(self, use_cloud_build: bool = True):
        """
        Initialize build trigger

        Args:
            use_cloud_build: If True, use Cloud Build. If False, use GitHub Actions
        """
        self.use_cloud_build = use_cloud_build

        if use_cloud_build:
            self.cloud_build = CloudBuildClient(project_id="cloudbuild-486309")

    def trigger(self, build_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a build using either Cloud Build or GitHub Actions

        This is a drop-in replacement for your existing trigger_build() function
        """
        if self.use_cloud_build:
            # Use Google Cloud Build
            return self.cloud_build.trigger_build(build_data)
        else:
            # Use GitHub Actions (your existing code)
            return self._trigger_github_actions(build_data)

    def _trigger_github_actions(self, build_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Your existing GitHub Actions trigger code
        (Keep this for backward compatibility during migration)
        NOTE: GitHub Actions has been deprecated, this method always raises an error.
        """
        raise NotImplementedError(
            "GitHub Actions support has been removed. Please use Cloud Build."
        )


if __name__ == "__main__":
    # Run example
    print("Cloud Build Integration - Example Usage")
    print("=" * 50)
    example_usage()
