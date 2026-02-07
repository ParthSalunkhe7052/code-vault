"""
CodeVault - Simple Cloud Build Wrapper using gcloud CLI
This uses gcloud CLI which is already authenticated
"""

import subprocess
import json
import os
import sys
import shutil
import base64
from typing import Dict, Any


class CloudBuildClient:
    """Simple wrapper around gcloud builds submit"""

    def __init__(self, project_id: str = "cloudbuild-486309"):
        self.project_id = project_id
        self.gcloud_cmd = self._find_gcloud()

    def _find_gcloud(self) -> str:
        """Find gcloud executable path"""
        # Try to find gcloud in PATH
        gcloud_path = shutil.which("gcloud")
        if gcloud_path:
            return gcloud_path

        # On Windows, gcloud might be gcloud.cmd
        if sys.platform == "win32":
            gcloud_cmd = shutil.which("gcloud.cmd")
            if gcloud_cmd:
                return gcloud_cmd

            # Try common Windows installation paths
            common_paths = [
                r"C:\Users\parth\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
                r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
                r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
            ]

            for path in common_paths:
                if os.path.exists(path):
                    return path

        # Fallback to just "gcloud" and let it fail with a better error
        return "gcloud"

    def trigger_build(self, build_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a Cloud Build job using gcloud CLI

        Args:
            build_config: Dictionary containing build configuration

        Returns:
            Dictionary with build information:
                - build_id: Cloud Build ID
                - status: Build status
                - logs_url: URL to view build logs
                - created_at: Timestamp

        Raises:
            Exception: If the build trigger fails
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

        # Upload config to GCS to avoid 8KB substitution limit
        # Cloud Build has an 8KB limit on substitution variable values
        from google.cloud import storage as gcs_storage

        gcs_client = gcs_storage.Client()
        config_bucket = gcs_client.bucket("codevault-builds")
        config_blob = config_bucket.blob(f"builds/{build_id}/config.json")
        config_blob.upload_from_string(
            json.dumps(config), content_type="application/json"
        )
        config_url = f"gs://codevault-builds/builds/{build_id}/config.json"
        callback_secret = build_config.get("callback_secret", "")

        substitutions = [
            f"_BUILD_ID={build_id}",
            f"_PROJECT_ID={project_id}",
            f"_LANGUAGE={language}",
            f"_TARGET_PLATFORMS={platforms}",
            f"_SOURCE_URL={source_url}",
            f"_CONFIG_URL={config_url}",
            f"_CALLBACK_URL={callback_url}",
            f"_CALLBACK_SECRET=",  # Provided via Secret Manager in YAML, but needs default for API
            f"_OUTPUT_NAME={config.get('output_name', 'app')}",
        ]

        substitutions_str = ",".join(substitutions)

        # Find cloudbuild.yaml
        cloudbuild_path = os.path.join(os.path.dirname(__file__), "cloudbuild.yaml")

        if not os.path.exists(cloudbuild_path):
            raise FileNotFoundError(f"cloudbuild.yaml not found at {cloudbuild_path}")

        try:
            # Run gcloud builds submit
            cmd = [
                self.gcloud_cmd,
                "builds",
                "submit",
                "--config",
                cloudbuild_path,
                "--no-source",
                "--project",
                self.project_id,
                "--substitutions",
                substitutions_str,
                "--format",
                "json",
                "--async",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, shell=True
            )

            # Parse JSON output
            output = json.loads(result.stdout) if result.stdout else {}

            gcp_build_id = output.get("id", "unknown")
            logs_url = output.get(
                "logUrl",
                f"https://console.cloud.google.com/cloud-build/builds/{gcp_build_id}?project={self.project_id}",
            )

            return {
                "build_id": gcp_build_id,
                "status": "QUEUED",
                "logs_url": logs_url,
                "created_at": output.get("createTime"),
                "project": self.project_id,
            }

        except subprocess.CalledProcessError as e:
            raise Exception(f"Cloud Build trigger failed: {e.stderr}")
        except json.JSONDecodeError:
            raise Exception("Failed to parse gcloud output")
        except Exception as e:
            raise Exception(f"Cloud Build error: {str(e)}")

    def get_build_status(self, build_id: str) -> Dict[str, Any]:
        """Get the status of a Cloud Build job"""
        try:
            cmd = [
                self.gcloud_cmd,
                "builds",
                "describe",
                build_id,
                "--project",
                self.project_id,
                "--format",
                "json",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, shell=True
            )
            output = json.loads(result.stdout)

            return {
                "build_id": output.get("id"),
                "status": output.get("status"),
                "create_time": output.get("createTime"),
                "start_time": output.get("startTime"),
                "finish_time": output.get("finishTime"),
                "logs_url": output.get("logUrl"),
            }
        except Exception as e:
            raise Exception(f"Failed to get build status: {str(e)}")

    def cancel_build(self, build_id: str) -> bool:
        """Cancel a running Cloud Build job"""
        try:
            cmd = [
                self.gcloud_cmd,
                "builds",
                "cancel",
                build_id,
                "--project",
                self.project_id,
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to cancel build: {str(e)}")
