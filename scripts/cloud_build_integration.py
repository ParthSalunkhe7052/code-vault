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

        # Save cache
        steps.append(self._create_save_cache_step(gcs_bucket))

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

echo "[Cloud Build] Cache restore complete"
"""

        return {
            "name": "gcr.io/cloud-builders/gsutil",
            "args": ["-c", script],
            "entrypoint": "bash",
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
            "args": ["-c", script],
            "entrypoint": "bash",
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
            "args": ["-c", script],
            "entrypoint": "bash",
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
            "args": ["-c", script],
            "entrypoint": "bash",
        }

    def _create_python_build_steps(
        self, target_platforms: str, output_name: str, gcs_bucket: str, build_id: str
    ) -> list:
        """Create Python-specific build and upload steps."""
        steps = []

        # Linux build step - FIXED: Package entire .dist folder for standalone builds
        linux_build_script = f"""set -e
if [[ "{target_platforms}" != *"linux"* ]]; then
  echo "[Cloud Build] Skipping Linux build"
  echo "skipped" > /workspace/build_status_linux
  exit 0
fi

echo "[Cloud Build] ===== Building for Linux ====="
pip install --quiet --disable-pip-version-check nuitka==2.4.8 ordered-set zstandard requests cryptography

if [ ! -f "./project/source/.github/scripts/cloud_runner.py" ]; then
  echo "cloud_runner.py not found" > ./project/source/error_message.txt
  echo "failed" > /workspace/build_status_linux
  exit 0
fi

decoded_config=$$(cat /workspace/config.json)
export NUITKA_JOBS=6
export NUITKA_CACHE_DIR=/workspace/.nuitka-cache
mkdir -p $$NUITKA_CACHE_DIR

if [ -d /workspace/.nuitka-cache ]; then
  mkdir -p $$HOME/.cache/Nuitka
  cp -r /workspace/.nuitka-cache/. $$HOME/.cache/Nuitka/ 2>/dev/null || true
fi

python3 "./project/source/.github/scripts/cloud_runner.py" --config "$$decoded_config" --source "./project/source" || true

cd "./project/source"

linux_artifacts=""
linux_status="failed"
linux_error=""

# Check for standalone output (build_output_linux/{output_name}.dist folder)
dist_dir="build_output_linux/{output_name}.dist"

if [ -d "$$dist_dir" ]; then
  echo "[Cloud Build] Found standalone .dist folder: $$dist_dir"
  # Zip the entire .dist folder with all dependencies (including python dlls)
  tar -czf "/workspace/{output_name}.tar.gz" -C "build_output_linux" "{output_name}.dist"
  linux_artifacts="{output_name}.tar.gz"
  linux_status="completed"
  echo "[Cloud Build] Linux artifact ready: $$linux_artifacts (standalone folder with dependencies)"
elif [ -d "build_output_linux" ]; then
  # Fallback: Check for onefile mode (single binary)
  found_binary=$$(find build_output_linux -type f -name "{output_name}" 2>/dev/null | head -1)
  if [ -n "$$found_binary" ]; then
    cp "$$found_binary" ./
  fi
  
  if [ -f "{output_name}" ]; then
    chmod +x "{output_name}"
    tar -czf "/workspace/{output_name}.tar.gz" "{output_name}"
    linux_artifacts="{output_name}.tar.gz"
    linux_status="completed"
    echo "[Cloud Build] Linux artifact ready: $$linux_artifacts (onefile binary)"
  else
    if [ -f "error_message.txt" ]; then
      linux_error=$$(cat error_message.txt)
    else
      linux_error="Linux build output '{output_name}' not found"
    fi
  fi
else
  if [ -f "error_message.txt" ]; then
    linux_error=$$(cat error_message.txt)
  else
    linux_error="Linux build output directory not found"
  fi
fi

echo "$$linux_status" > /workspace/build_status_linux
echo "$$linux_artifacts" > /workspace/linux_artifacts
echo "$$linux_error" > /workspace/linux_error

if [ -d "$$HOME/.cache/Nuitka" ]; then
  mkdir -p /workspace/.nuitka-cache
  cp -r $$HOME/.cache/Nuitka/. /workspace/.nuitka-cache/ 2>/dev/null || true
fi
"""

        steps.append(
            {
                "name": "gcr.io/cloudbuild-486309/codevault-builder:latest",
                "args": ["-c", linux_build_script],
                "entrypoint": "bash",
            }
        )

        # Linux upload step
        linux_upload_script = f"""linux_status=$$(cat /workspace/build_status_linux 2>/dev/null || echo "pending")
if [[ "$$linux_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Linux upload (status: $$linux_status)"
  exit 0
fi
linux_artifact=$$(cat /workspace/linux_artifacts 2>/dev/null)
if [ -z "$$linux_artifact" ]; then
  exit 0
fi
echo "[Cloud Build] Uploading Linux: $$linux_artifact"
gsutil cp "/workspace/$$linux_artifact" "gs://{gcs_bucket}/builds/{build_id}/linux/$$linux_artifact"
"""

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "args": ["-c", linux_upload_script],
                "entrypoint": "bash",
            }
        )

        # Windows build step - FIXED: Package entire .dist folder for standalone builds
        windows_build_script = f"""set -e
if [[ "{target_platforms}" != *"windows"* ]]; then
  echo "[Cloud Build] Skipping Windows build"
  echo "skipped" > /workspace/build_status_windows
  exit 0
fi

echo "[Cloud Build] ===== Building for Windows ====="
export NUITKA_CACHE_DIR=/workspace/.nuitka-cache
mkdir -p $$NUITKA_CACHE_DIR

wine python -m pip install --upgrade --quiet --disable-pip-version-check nuitka ordered-set zstandard requests cryptography pefile

if [ ! -f "./project/source/.github/scripts/cloud_runner.py" ]; then
  echo "cloud_runner.py not found" > ./project/source/error_message.txt
  echo "failed" > /workspace/build_status_windows
  exit 0
fi

nuitka_depends_py=$$(find /opt/wineprefix -name "DependsExe.py" | grep "freezer" | head -1)
if [ -n "$$nuitka_depends_py" ]; then
  if [ -f "./project/source/.github/scripts/nuitka_patch.py" ]; then
    wine python "./project/source/.github/scripts/nuitka_patch.py" "$$nuitka_depends_py"
  fi
fi

decoded_config=$$(cat /workspace/config.json)
wine python "./project/source/.github/scripts/cloud_runner.py" --config "$$decoded_config" --source "$$(winepath -w $$(realpath ./project/source))"

windows_artifacts=""
windows_status="failed"
windows_error=""

# Check for standalone output (build_output_windows_wine/{output_name}.dist folder)
dist_dir="./project/source/build_output_windows_wine/{output_name}.dist"

if [ -d "$$dist_dir" ]; then
  echo "[Cloud Build] Found standalone .dist folder: $$dist_dir"
  # List contents for debugging
  echo "[Cloud Build] .dist folder contents:"
  ls -la "$$dist_dir/" 2>/dev/null || true
  
  # Zip the entire .dist folder with all dependencies (including python311.dll)
  cd ./project/source/build_output_windows_wine
  tar -czf "/workspace/{output_name}.tar.gz" "{output_name}.dist"
  cd /workspace
  
  if [ -f "/workspace/{output_name}.tar.gz" ]; then
    archive_size=$$(ls -lh "/workspace/{output_name}.tar.gz" | awk '{{print $$5}}')
    echo "[Cloud Build] Archive size: $$archive_size"
    windows_artifacts="{output_name}.tar.gz"
    windows_status="completed"
    echo "[Cloud Build] Windows artifact ready: $$windows_artifacts (standalone folder with dependencies)"
  else
    windows_error="Failed to create tar.gz from .dist folder"
  fi
else
  # Fallback: Check for onefile mode (single EXE)
  echo "[Cloud Build] No .dist folder found, checking for onefile EXE..."
  found_exe=""
  
  if [ -f "./project/source/build_output_windows_wine/{output_name}.exe" ]; then
    found_exe="./project/source/build_output_windows_wine/{output_name}.exe"
    echo "[Cloud Build] Found onefile EXE: $$found_exe"
  else
    found_exe=$$(find ./project/source/build_output_windows_wine -type f -name "*.exe" 2>/dev/null | head -1)
    if [ -n "$$found_exe" ]; then
      echo "[Cloud Build] Found EXE: $$found_exe"
    fi
  fi

  if [ -n "$$found_exe" ] && [ -f "$$found_exe" ]; then
    exe_size=$$(ls -lh "$$found_exe" | awk '{{print $$5}}')
    echo "[Cloud Build] EXE size: $$exe_size"
    cp "$$found_exe" "/workspace/{output_name}.exe"
    if [ -f "/workspace/{output_name}.exe" ]; then
      windows_artifacts="{output_name}.exe"
      windows_status="completed"
      echo "[Cloud Build] Windows artifact ready: $$windows_artifacts (self-contained onefile EXE)"
    else
      windows_error="Failed to copy EXE to artifacts"
    fi
  else
    if [ -f "./project/source/error_message.txt" ]; then
      windows_error=$$(cat ./project/source/error_message.txt)
    else
      windows_error="Windows EXE not found in build output"
    fi
  fi
fi

echo "$$windows_status" > /workspace/build_status_windows
echo "$$windows_artifacts" > /workspace/windows_artifacts
echo "$$windows_error" > /workspace/windows_error
"""

        steps.append(
            {
                "name": "docker.io/tobix/pywine:3.11",
                "args": ["-c", windows_build_script],
                "entrypoint": "bash",
            }
        )

        # Windows upload step
        windows_upload_script = f"""windows_status=$$(cat /workspace/build_status_windows 2>/dev/null || echo "pending")
if [[ "$$windows_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Windows upload (status: $$windows_status)"
  exit 0
fi
windows_artifact=$$(cat /workspace/windows_artifacts 2>/dev/null)
if [ -z "$$windows_artifact" ]; then
  exit 0
fi
echo "[Cloud Build] Uploading Windows: $$windows_artifact"
gsutil cp "/workspace/$$windows_artifact" "gs://{gcs_bucket}/builds/{build_id}/windows/$$windows_artifact"
"""

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "args": ["-c", windows_upload_script],
                "entrypoint": "bash",
            }
        )

        return steps

    def _create_nodejs_build_steps(
        self, target_platforms: str, output_name: str, gcs_bucket: str, build_id: str
    ) -> list:
        """Create Node.js-specific build and upload steps."""
        steps = []

        # Node.js build step (handles both Windows and Linux)
        # IMPORTANT: No fallback! If cloud_runner_nodejs.py fails, the build fails.
        # This ensures all builds have proper license protection and error handling.
        build_script = f"""set -e
echo "[Cloud Build] ===== Building for Node.js ====="

apt-get update -qq && apt-get install -y -qq python3 > /dev/null 2>&1
npm install -g @yao-pkg/pkg --quiet

cd "./project/source"

echo "[Cloud Build] Directory contents:"
ls -la
echo ""

echo "[Cloud Build] Config:"
cat /workspace/config.json
echo ""

# Check for cloud_runner_nodejs.py - required for all builds
if [ ! -f ".github/scripts/cloud_runner_nodejs.py" ]; then
  echo "[Cloud Build] ERROR: cloud_runner_nodejs.py not found!"
  echo "[Cloud Build] This file should be included in the source upload."
  echo "failed" > /workspace/build_status_windows
  echo "failed" > /workspace/build_status_linux
  echo "cloud_runner_nodejs.py not found - cannot proceed without license wrapper" > /workspace/windows_error
  echo "cloud_runner_nodejs.py not found - cannot proceed without license wrapper" > /workspace/linux_error
  exit 1
fi

echo "[Cloud Build] Running cloud_runner_nodejs.py..."
echo "[Cloud Build] This will inject license protection and build for all target platforms."

# Run the runner - if it fails, the build fails (no fallback!)
python3 .github/scripts/cloud_runner_nodejs.py --config "$$(cat /workspace/config.json)" --source "$$(pwd)" 2>&1
runner_exit_code=$$?

if [ $$runner_exit_code -ne 0 ]; then
  echo "[Cloud Build] ERROR: cloud_runner_nodejs.py failed with exit code $$runner_exit_code"
  echo "[Cloud Build] Build cannot proceed without license wrapper."
  echo "failed" > /workspace/build_status_windows
  echo "failed" > /workspace/build_status_linux
  echo "License wrapper injection failed - check build logs for details" > /workspace/windows_error
  echo "License wrapper injection failed - check build logs for details" > /workspace/linux_error
  exit 1
fi

echo "[Cloud Build] cloud_runner_nodejs.py completed successfully"

echo "[Cloud Build] Artifacts directory contents:"
ls -la /workspace/ 2>/dev/null || echo "Workspace empty"

# Parse target platforms from config
target_plats=$$(cat /workspace/config.json | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('target_platforms', ['windows'])))" 2>/dev/null || echo "windows")
echo "[Cloud Build] Target platforms: $$target_plats"

# Windows artifact - strict: only accept expected output file
if [[ "$$target_plats" == *"windows"* ]]; then
  if [ -f "build_output_windows/{output_name}.exe" ]; then
    exe_size=$$(stat -c%s "build_output_windows/{output_name}.exe" 2>/dev/null || echo "0")
    echo "[Cloud Build] Found Windows exe: build_output_windows/{output_name}.exe ($$exe_size bytes)"
    if [ "$$exe_size" -lt 10000 ]; then
      echo "[Cloud Build] WARNING: EXE seems too small, may be corrupted"
      echo "failed" > /workspace/build_status_windows
      echo "Windows EXE file is too small ($$exe_size bytes) - likely corrupted" > /workspace/windows_error
    else
      cp "build_output_windows/{output_name}.exe" /workspace/
      echo "completed" > /workspace/build_status_windows
      echo "{output_name}.exe" > /workspace/windows_artifacts
      echo "[Cloud Build] Windows artifact ready: {output_name}.exe"
    fi
  else
    echo "[Cloud Build] ERROR: Expected output not found at build_output_windows/{output_name}.exe"
    echo "[Cloud Build] Build output directory contents:"
    ls -la build_output_windows/ 2>/dev/null || echo "Directory does not exist"
    echo "failed" > /workspace/build_status_windows
    echo "Windows build output not found at expected location" > /workspace/windows_error
  fi
else
  echo "skipped" > /workspace/build_status_windows
fi

# Linux artifact - strict: only accept expected output file
if [[ "$$target_plats" == *"linux"* ]]; then
  if [ -f "build_output_linux/{output_name}" ]; then
    linux_size=$$(stat -c%s "build_output_linux/{output_name}" 2>/dev/null || echo "0")
    echo "[Cloud Build] Found Linux binary: build_output_linux/{output_name} ($$linux_size bytes)"
    if [ "$$linux_size" -lt 10000 ]; then
      echo "[Cloud Build] WARNING: Binary seems too small, may be corrupted"
      echo "failed" > /workspace/build_status_linux
      echo "Linux binary file is too small ($$linux_size bytes) - likely corrupted" > /workspace/linux_error
    else
      cp "build_output_linux/{output_name}" /workspace/
      chmod +x "/workspace/{output_name}"
      echo "completed" > /workspace/build_status_linux
      echo "{output_name}" > /workspace/linux_artifacts
      echo "[Cloud Build] Linux artifact ready: {output_name}"
    fi
  else
    echo "[Cloud Build] ERROR: Expected output not found at build_output_linux/{output_name}"
    echo "[Cloud Build] Build output directory contents:"
    ls -la build_output_linux/ 2>/dev/null || echo "Directory does not exist"
    echo "failed" > /workspace/build_status_linux
    echo "Linux build output not found at expected location" > /workspace/linux_error
  fi
else
  echo "skipped" > /workspace/build_status_linux
fi

echo "[Cloud Build] Node.js build step complete"
"""

        steps.append(
            {
                "name": "node:20-slim",
                "args": ["-c", build_script],
                "entrypoint": "bash",
            }
        )

        # Windows upload
        windows_upload_script = f"""windows_status=$$(cat /workspace/build_status_windows 2>/dev/null || echo "pending")
if [[ "$$windows_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Node.js Windows upload (status: $$windows_status)"
  exit 0
fi
windows_artifact=$$(cat /workspace/windows_artifacts 2>/dev/null)
if [ -z "$$windows_artifact" ]; then
  exit 0
fi
echo "[Cloud Build] Uploading Node.js Windows: $$windows_artifact"
gsutil cp "/workspace/$$windows_artifact" "gs://{gcs_bucket}/builds/{build_id}/windows/$$windows_artifact"
"""

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "args": ["-c", windows_upload_script],
                "entrypoint": "bash",
            }
        )

        # Linux upload
        linux_upload_script = f"""linux_status=$$(cat /workspace/build_status_linux 2>/dev/null || echo "pending")
if [[ "$$linux_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Node.js Linux upload (status: $$linux_status)"
  exit 0
fi
linux_artifact=$$(cat /workspace/linux_artifacts 2>/dev/null)
if [ -z "$$linux_artifact" ]; then
  exit 0
fi
echo "[Cloud Build] Uploading Node.js Linux: $$linux_artifact"
gsutil cp "/workspace/$$linux_artifact" "gs://{gcs_bucket}/builds/{build_id}/linux/$$linux_artifact"
"""

        steps.append(
            {
                "name": "gcr.io/cloud-builders/gsutil",
                "args": ["-c", linux_upload_script],
                "entrypoint": "bash",
            }
        )

        return steps

    def _create_save_cache_step(self, gcs_bucket: str) -> Dict[str, Any]:
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

echo "[Cloud Build] Skipping Nuitka cache save (disabled)"
echo "[Cloud Build] Cache save complete"
"""

        return {
            "name": "gcr.io/cloud-builders/gsutil",
            "args": ["-c", script],
            "entrypoint": "bash",
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
            "args": ["-c", script],
            "entrypoint": "bash",
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
