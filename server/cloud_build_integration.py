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
                - config_url: URL to download build config
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
        gcs_bucket = os.getenv("GCS_BUILDS_BUCKET", "codevault-builds")

        # Create build name
        build_name = f"codevault-{build_id}"

        # Generate inline build steps
        # This eliminates the substitution mismatch issue with external YAML
        steps = self._generate_build_steps(
            build_id=build_id,
            project_id=build_config.get("project_id", ""),
            language=language,
            target_platforms=target_platforms,
            source_url=build_config.get("source_url", ""),
            config_url=build_config.get("config_url", ""),
            output_name=build_config.get("output_name", "app"),
            gcs_bucket=gcs_bucket,
            callback_url=build_config.get("callback_url", ""),
            callback_secret=build_config.get("callback_secret", ""),
        )

        # Create the build configuration with inline steps
        # Note: Artifacts are uploaded manually via gsutil in build steps
        # Note: dynamic_substitutions is NOT used because our scripts use shell variables,
        # not Cloud Build substitution syntax. Enabling it causes validation errors for
        # variables like NUITKA_CACHE_DIR which are not built-in substitutions.
        build = self.cloudbuild_v1.Build(
            name=build_name,
            steps=steps,
            timeout={"seconds": 3600},  # 1 hour timeout
            options={
                "logging": "CLOUD_LOGGING_ONLY",
            },
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

    def _generate_build_steps(
        self,
        build_id: str,
        project_id: str,
        language: str,
        target_platforms: str,
        source_url: str,
        config_url: str,
        output_name: str,
        gcs_bucket: str,
        callback_url: str,
        callback_secret: str,
    ) -> list:
        """Generate Cloud Build steps based on language and platforms.

        Args:
            build_id: Unique build identifier
            project_id: CodeVault project ID
            language: 'python' or 'nodejs'
            target_platforms: Comma-separated platforms
            source_url: URL to download source code
            config_url: URL to download build config
            output_name: Output binary name
            gcs_bucket: GCS bucket for artifacts
            callback_url: Webhook URL for status updates
            callback_secret: Secret for webhook verification

        Returns:
            List of Cloud Build step dictionaries
        """
        steps = []

        # Step 1: Restore cache
        steps.append(self._create_restore_cache_step(gcs_bucket))

        # Step 2: Download source
        steps.append(
            self._create_download_source_step(
                build_id,
                project_id,
                language,
                target_platforms,
                output_name,
                source_url,
            )
        )

        # Step 3: Extract source
        steps.append(self._create_extract_source_step())

        # Step 4: Download config
        steps.append(self._create_download_config_step(config_url, target_platforms))

        # Language-specific build steps
        if language == "python":
            steps.extend(
                self._create_python_build_steps(
                    target_platforms, output_name, gcs_bucket, build_id
                )
            )
        elif language == "nodejs":
            steps.extend(
                self._create_nodejs_build_steps(
                    target_platforms, output_name, gcs_bucket, build_id
                )
            )

        # Save cache - waitFor depends on which upload steps were created for this language
        steps.append(self._create_save_cache_step(gcs_bucket, language))

        # Webhook callback
        steps.append(
            self._create_webhook_step(
                callback_url, callback_secret, build_id, gcs_bucket
            )
        )

        return steps

    def _create_restore_cache_step(self, gcs_bucket: str) -> Dict[str, Any]:
        """Create cache restore step."""
        script = f"""set +e
echo "[Cloud Build] Attempting to restore cache..."

# Restore pip cache
if gsutil -q stat "gs://{gcs_bucket}/cache/pip-cache-default.tar.gz" 2>/dev/null; then
  echo "[Cloud Build] Restoring pip cache..."
  gsutil cp "gs://{gcs_bucket}/cache/pip-cache-default.tar.gz" /tmp/pip-cache.tar.gz
  mkdir -p /root/.cache/pip
  tar -xzf /tmp/pip-cache.tar.gz -C /root/.cache/pip 2>/dev/null || true
  echo "[Cloud Build] pip cache restored"
else
  echo "[Cloud Build] pip cache not found"
fi

# Restore ccache
if gsutil -q stat "gs://{gcs_bucket}/cache/ccache-default.tar.gz" 2>/dev/null; then
  echo "[Cloud Build] Restoring ccache..."
  gsutil cp "gs://{gcs_bucket}/cache/ccache-default.tar.gz" /tmp/ccache.tar.gz
  mkdir -p /workspace/.ccache
  tar -xzf /tmp/ccache.tar.gz -C /workspace/.ccache 2>/dev/null || true
  echo "[Cloud Build] ccache restored"
else
  echo "[Cloud Build] ccache not found"
fi

# Restore MinGW cache (Windows cross-compilation toolchain - avoids ~300MB re-download each build)
if gsutil -q stat "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz" 2>/dev/null; then
  mingw_size=$$(gsutil du "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz" 2>/dev/null | awk '{{print $$1}}' | cut -d'.' -f1)
  if [ -n "$$mingw_size" ] && [ "$$mingw_size" -gt 524288000 ]; then
    echo "[Cloud Build] Skipping MinGW cache (too large: $$mingw_size bytes)"
  else
    echo "[Cloud Build] Restoring MinGW cache..."
    gsutil cp "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz" /tmp/mingw-cache.tar.gz
    mkdir -p /workspace/.mingw-cache
    tar -xzf /tmp/mingw-cache.tar.gz -C /workspace/.mingw-cache 2>/dev/null || true
    echo "[Cloud Build] MinGW cache restored"
  fi
else
  echo "[Cloud Build] MinGW cache not found (first build or cache expired)"
fi

echo "[Cloud Build] Cache restore complete"
"""

        return {
            "name": "gcr.io/cloud-builders/gsutil",
            "id": "restore-cache",
            "args": ["-c", script],
            "entrypoint": "bash",
            "wait_for": ["-"],
        }

    def _create_download_source_step(
        self,
        build_id: str,
        project_id: str,
        language: str,
        target_platforms: str,
        output_name: str,
        source_url: str,
    ) -> Dict[str, Any]:
        """Create source download step."""
        script = f"""echo "Building: {build_id} for {project_id} ({language})"
echo "Target: {target_platforms}, Output: {output_name}"
if [[ "{source_url}" == gs://* ]]; then
  gsutil cp "{source_url}" source.zip
else
  curl -L -o source.zip "{source_url}"
fi
"""

        return {
            "name": "gcr.io/cloud-builders/gsutil",
            "id": "download-source",
            "args": ["-c", script],
            "entrypoint": "bash",
            "wait_for": ["restore-cache"],
        }

    def _create_extract_source_step(self) -> Dict[str, Any]:
        """Create source extraction step."""
        script = """set -e
apt-get update -qq && apt-get install -y -qq unzip > /dev/null 2>&1
echo "[Cloud Build] Extracting source..."
unzip -q source.zip -d ./extracted
mkdir -p ./project/source
if [ -d "./extracted/.github" ]; then
  cp -r ./extracted/. ./project/source/
elif [ -d "./extracted/source" ]; then
  cp -r ./extracted/source/. ./project/source/
  if [ -d "./extracted/.github" ]; then cp -r ./extracted/.github ./project/source/ 2>/dev/null || true; fi
else
  cp -r ./extracted/. ./project/source/ 2>/dev/null || true
fi
echo "[Cloud Build] Source prepared"
"""

        return {
            "name": "ubuntu",
            "id": "extract-source",
            "args": ["-c", script],
            "entrypoint": "bash",
            "wait_for": ["download-source"],
        }

    def _create_download_config_step(
        self, config_url: str, target_platforms: str
    ) -> Dict[str, Any]:
        """Create config download step."""
        # Skip config download if URL is empty
        if not config_url:
            script = """echo "[Cloud Build] No config URL provided, skipping config download"
echo '{}' > /workspace/config.json
"""
        else:
            script = f"""if [[ "{target_platforms}" == "" ]]; then
  exit 0
fi
echo "[Cloud Build] Downloading config..."
if [[ "{config_url}" == gs://* ]]; then
  gsutil cp "{config_url}" /workspace/config.json
else
  curl -L -o /workspace/config.json "{config_url}"
fi
"""

        return {
            "name": "gcr.io/cloud-builders/gsutil",
            "id": "download-config",
            "args": ["-c", script],
            "entrypoint": "bash",
            "wait_for": ["extract-source"],
        }

    def _create_python_build_steps(
        self, target_platforms: str, output_name: str, gcs_bucket: str, build_id: str
    ) -> list:
        """Create Python-specific build and upload steps."""
        steps = []
        from pathlib import Path

        # Linux build step - FIXED: Package entire .dist folder for standalone builds
        linux_build_script = Path("scripts/build_python_linux.sh").read_text().replace("{target_platforms}", target_platforms).replace("{output_name}", output_name)

        # Linux and Windows build steps run in PARALLEL (both wait_for download-config)
        steps.append(
            {
                "name": "gcr.io/cloudbuild-486309/codevault-builder:latest",
                "id": "build-linux",
                "args": ["-c", linux_build_script],
                "entrypoint": "bash",
                "wait_for": ["download-config"],
            }
        )

        # Linux upload step (with 3-retry logic)
        linux_upload_script = Path("scripts/upload_linux.sh").read_text().replace("{gcs_bucket}", gcs_bucket).replace("{build_id}", build_id)

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "id": "upload-linux",
                "args": ["-c", linux_upload_script],
                "entrypoint": "bash",
                "wait_for": ["build-linux"],
            }
        )

        # Windows build step - FIXED: Package entire .dist folder for standalone builds
        windows_build_script = Path("scripts/build_python_windows.sh").read_text().replace("{target_platforms}", target_platforms).replace("{output_name}", output_name)

        # Windows build step also waits for download-config (runs PARALLEL to Linux)
        steps.append(
            {
                "name": "docker.io/tobix/pywine:3.11",
                "id": "build-windows",
                "args": ["-c", windows_build_script],
                "entrypoint": "bash",
                "wait_for": ["download-config"],
            }
        )

        # Windows upload step (with 3-retry logic)
        windows_upload_script = Path("scripts/upload_windows.sh").read_text().replace("{gcs_bucket}", gcs_bucket).replace("{build_id}", build_id)

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "id": "upload-windows",
                "args": ["-c", windows_upload_script],
                "entrypoint": "bash",
                "wait_for": ["build-windows"],
            }
        )

        return steps

    def _create_nodejs_build_steps(
        self, target_platforms: str, output_name: str, gcs_bucket: str, build_id: str
    ) -> list:
        """Create Node.js-specific build and upload steps."""
        steps = []
        from pathlib import Path

        # Node.js build step (handles both Windows and Linux)
        # IMPORTANT: No fallback! If cloud_runner_nodejs.py fails, the build fails.
        # This ensures all builds have proper license protection and error handling.
        build_script = Path("scripts/build_nodejs.sh").read_text().replace("{output_name}", output_name)

        steps.append(
            {
                "name": "node:20-slim",
                "id": "build-nodejs",
                "args": ["-c", build_script],
                "entrypoint": "bash",
                "wait_for": ["download-config"],
            }
        )

        # Windows upload
        windows_upload_script = Path("scripts/upload_windows.sh").read_text().replace("{gcs_bucket}", gcs_bucket).replace("{build_id}", build_id)

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "id": "upload-nodejs",
                "args": ["-c", windows_upload_script],
                "entrypoint": "bash",
                "wait_for": ["build-nodejs"],
            }
        )

        # Linux upload
        linux_upload_script = Path("scripts/upload_linux.sh").read_text().replace("{gcs_bucket}", gcs_bucket).replace("{build_id}", build_id)

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "id": "upload-nodejs-linux",
                "args": ["-c", linux_upload_script],
                "entrypoint": "bash",
                "wait_for": ["build-nodejs"],
            }
        )

        return steps

    def _create_save_cache_step(
        self, gcs_bucket: str, language: str = "python"
    ) -> Dict[str, Any]:
        """Create cache save step."""
        script = f"""set +e
echo "[Cloud Build] Saving cache..."

if [ -d /root/.cache/pip ]; then
  pip_cache_size=$$(du -s /root/.cache/pip 2>/dev/null | cut -f1)
  if [ "$$pip_cache_size" -gt 1000 ]; then
    tar -czf /tmp/pip-cache.tar.gz -C /root/.cache/pip . 2>/dev/null
    gsutil cp /tmp/pip-cache.tar.gz "gs://{gcs_bucket}/cache/pip-cache-default.tar.gz"
    echo "[Cloud Build] Saved pip cache ($$pip_cache_size KB)"
  fi
fi

if [ -d /workspace/.ccache ]; then
  ccache_size=$$(du -s /workspace/.ccache 2>/dev/null | cut -f1)
  if [ "$$ccache_size" -gt 1000 ]; then
    tar -czf /tmp/ccache.tar.gz -C /workspace/.ccache . 2>/dev/null
    gsutil cp /tmp/ccache.tar.gz "gs://{gcs_bucket}/cache/ccache-default.tar.gz"
    echo "[Cloud Build] Saved ccache ($$ccache_size KB)"
  fi
fi

# Save MinGW cache (staged by Windows build step; 10MB < size < 600MB)
if [ -d /workspace/.mingw-cache ]; then
  mingw_cache_size=$$(du -s /workspace/.mingw-cache 2>/dev/null | cut -f1)
  if [ -n "$$mingw_cache_size" ] && [ "$$mingw_cache_size" -gt 10000 ] && [ "$$mingw_cache_size" -lt 600000 ]; then
    echo "[Cloud Build] Saving MinGW cache ($$mingw_cache_size KB)..."
    tar -czf /tmp/mingw-cache.tar.gz -C /workspace/.mingw-cache . 2>/dev/null
    gsutil cp /tmp/mingw-cache.tar.gz "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz"
    echo "[Cloud Build] Saved MinGW cache"
  else
    echo "[Cloud Build] Skipping MinGW cache save (size: $$mingw_cache_size KB, limit: 600MB)"
  fi
fi

echo "[Cloud Build] Skipping Nuitka cache save (disabled)"
echo "[Cloud Build] Cache save complete"
"""

        # waitFor must only reference step IDs that exist for this language
        if language == "nodejs":
            wait_for = ["upload-nodejs", "upload-nodejs-linux"]
        else:
            wait_for = ["upload-linux", "upload-windows"]

        return {
            "name": "gcr.io/cloud-builders/gsutil",
            "id": "save-cache",
            "args": ["-c", script],
            "entrypoint": "bash",
            "wait_for": wait_for,
        }

    def _create_webhook_step(
        self, callback_url: str, callback_secret: str, build_id: str, gcs_bucket: str
    ) -> Dict[str, Any]:
        """Create webhook callback step."""
        script = f"""set +e
echo "============================================"
echo "[Cloud Build] Preparing webhook callback..."
echo "============================================"

# Download config
gsutil cp "gs://{gcs_bucket}/builds/{build_id}/config.json" /workspace/config.json 2>/dev/null || echo "Config not found"

linux_status=$$(cat /workspace/build_status_linux 2>/dev/null || echo "pending")
windows_status=$$(cat /workspace/build_status_windows 2>/dev/null || echo "pending")
windows_artifact=$$(cat /workspace/windows_artifacts 2>/dev/null || echo "")
linux_artifact=$$(cat /workspace/linux_artifacts 2>/dev/null || echo "")

linux_error=$$(cat /workspace/linux_error 2>/dev/null || echo "")
windows_error=$$(cat /workspace/windows_error 2>/dev/null || echo "")

echo "[Cloud Build] Linux: $$linux_status, Windows: $$windows_status"

all_skipped=true
any_completed=false
if [[ "$$linux_status" != "skipped" ]]; then all_skipped=false; fi
if [[ "$$windows_status" != "skipped" ]]; then all_skipped=false; fi
if [[ "$$linux_status" == "completed" || "$$windows_status" == "completed" ]]; then any_completed=true; fi

if [[ "$$any_completed" == "true" ]]; then
  overall_status="completed"
elif [[ "$$all_skipped" == "true" ]]; then
  overall_status="cancelled"
else
  overall_status="failed"
fi

echo "[Cloud Build] Overall: $$overall_status"

linux_download_key=""
windows_download_key=""
filename=""

if [[ "$$linux_status" == "completed" && -n "$$linux_artifact" ]]; then
  linux_download_key="builds/{build_id}/linux/$$linux_artifact"
  filename="$$linux_artifact"
fi

if [[ "$$windows_status" == "completed" && -n "$$windows_artifact" ]]; then
  windows_download_key="builds/{build_id}/windows/$$windows_artifact"
  if [[ -z "$$filename" ]]; then
    filename="$$windows_artifact"
  fi
fi

error_msg=""
if [[ "$$overall_status" == "failed" ]]; then
  if [[ -n "$$linux_error" ]]; then error_msg="Linux: $$linux_error; "; fi
  if [[ -n "$$windows_error" ]]; then error_msg="$${{error_msg}}Windows: $$windows_error"; fi
  if [[ -z "$$error_msg" ]]; then error_msg="Build failed"; fi
fi

error_msg_escaped=$$(echo "$$error_msg" | sed 's/"/\\"/g' | tr '\\n' ' ')

# Note: BUILD_ID is a Cloud Build built-in substitution, not a shell variable
payload='{{"build_id":"{build_id}","cloud_build_id":"'$BUILD_ID'","status":"'$$overall_status'","linux_status":"'$$linux_status'","windows_status":"'$$windows_status'","linux_download_key":"'$$linux_download_key'","windows_download_key":"'$$windows_download_key'","filename":"'$$filename'","error":"'$$error_msg_escaped'","timestamp":'$$(date +%s)'}}'

if [ -n "{callback_secret}" ]; then
  sig=$$(echo -n "$$payload" | openssl dgst -sha256 -hmac "{callback_secret}" | awk '{{print $$2}}')
else
  sig=""
fi

echo "[Cloud Build] Sending webhook to: {callback_url}"
echo "[Cloud Build] Payload: $$payload"

max_retries=2
retry_delay=2
for i in $$(seq 1 $$max_retries); do
  echo "[Cloud Build] Attempt $$i/$$max_retries..."
  
  if [ -n "$$sig" ]; then
    response=$$(curl -s -w "\\n%{{http_code}}" -X POST "{callback_url}" -H "Content-Type: application/json" -H "X-Signature: $$sig" -d "$$payload" --connect-timeout 5 --max-time 10 2>&1)
  else
    response=$$(curl -s -w "\\n%{{http_code}}" -X POST "{callback_url}" -H "Content-Type: application/json" -d "$$payload" --connect-timeout 5 --max-time 10 2>&1)
  fi
  
  http_code=$$(echo "$$response" | tail -1)
  echo "[Cloud Build] Response: HTTP $$http_code"
  
  if [[ "$$http_code" == "200" || "$$http_code" == "201" ]]; then
    echo "[Cloud Build] Success (HTTP $$http_code)"
    break
  else
    echo "[Cloud Build] Failed (HTTP $$http_code)"
    if [[ $$i -lt $$max_retries ]]; then
      echo "[Cloud Build] Retrying in $${{retry_delay}}s..."
      sleep $$retry_delay
      retry_delay=$$((retry_delay + 2))
    fi
  fi
done

echo "[Cloud Build] Webhook completed"
"""

        return {
            "name": "gcr.io/cloud-builders/curl",
            "id": "webhook-callback",
            "args": ["-c", script],
            "entrypoint": "bash",
            "wait_for": ["save-cache"],
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

                # Handle DatetimeWithNanoseconds (google.api_core.datetime_helpers)
                # This is returned by newer google-cloud-build versions
                if hasattr(ts, "isoformat") and callable(
                    getattr(ts, "isoformat", None)
                ):
                    # Already a datetime-like object
                    return ts.isoformat()

                # Handle raw protobuf Timestamp (has seconds and nanos attributes)
                if hasattr(ts, "seconds") and hasattr(ts, "nanos"):
                    dt = datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9)
                    return dt.isoformat()

                # Fallback: try to convert to string
                return str(ts)

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
