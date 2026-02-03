"""
CodeVault - Google Cloud Build Integration
This module replaces GitHub Actions API calls with Google Cloud Build API calls
"""

import json
import os
from typing import Dict, Any, Optional
from google.cloud import cloudbuild_v1
from google.oauth2 import service_account
from google.api_core import exceptions


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
                            If None, will try to use GOOGLE_APPLICATION_CREDENTIALS env var
        """
        self.project_id = project_id

        # Load credentials
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self.client = cloudbuild_v1.CloudBuildClient(credentials=credentials)
        else:
            # Will use GOOGLE_APPLICATION_CREDENTIALS environment variable
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

        # Set source (pull from GitHub repo)
        build.source = cloudbuild_v1.Source()
        build.source.repo_source = cloudbuild_v1.RepoSource()
        # Replace with your actual GitHub repo connection name
        # You need to connect your GitHub repo to Cloud Build first
        build.source.repo_source.repo_name = "github_ParthSalunkhe7052_code-vault"
        build.source.repo_source.branch_name = "main"

        # Add substitution variables (parameters for cloudbuild.yaml)
        build.substitutions = {
            "_BUILD_ID": build_id,
            "_PROJECT_ID": project_id,
            "_LANGUAGE": language,
            "_TARGET_PLATFORMS": platforms,
            "_SOURCE_URL": source_url,
            "_CONFIG_JSON": json.dumps(config),
            "_CALLBACK_URL": callback_url,
            "_ENTRY_FILE": config.get("entry_file", "main.py"),
            "_OUTPUT_NAME": config.get("output_name", "app"),
            "_PLAN_TIER": plan_tier,
            "_COMPATIBILITY_MODE": compatibility_mode,
            "_FAST_BUILD": fast_build,
        }

        try:
            # Submit build
            operation = self.client.create_build(
                project_id=self.project_id, build=build
            )

            # Get build metadata
            build_result = operation.metadata

            return {
                "build_id": build_result.build.id,
                "status": "QUEUED",
                "logs_url": f"https://console.cloud.google.com/cloud-build/builds/{build_result.build.id}?project={self.project_id}",
                "created_at": build_result.build.create_time.isoformat()
                if build_result.build.create_time
                else None,
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
                "create_time": build.create_time.isoformat()
                if build.create_time
                else None,
                "start_time": build.start_time.isoformat()
                if build.start_time
                else None,
                "finish_time": build.finish_time.isoformat()
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
    Example: How to use this in your Digital Ocean backend
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
        """
        import requests

        # Your existing GitHub Actions trigger logic here
        # ...
        pass


if __name__ == "__main__":
    # Run example
    print("Cloud Build Integration - Example Usage")
    print("=" * 50)
    example_usage()
