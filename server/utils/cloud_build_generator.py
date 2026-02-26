"""Cloud Build Step Generator

Generates inline build steps for Google Cloud Build API.
Eliminates dependency on external cloudbuild.yaml file.
"""

from typing import List, Dict, Any


def generate_build_steps(
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
) -> List[Dict[str, Any]]:
    """Generate Cloud Build steps based on language and platforms.

    Args:
        build_id: Unique build identifier
        project_id: CodeVault project ID
        language: 'python' or 'nodejs'
        target_platforms: Comma-separated platforms (windows,linux)
        source_url: URL to download source code
        config_url: URL to download build config
        output_name: Output binary name
        gcs_bucket: GCS bucket for artifacts
        callback_url: Webhook URL for status updates
        callback_secret: Secret for webhook verification

    Returns:
        List of build step dictionaries
    """
    steps = []

    # Step 1: Restore cache
    steps.append(_generate_restore_cache_step(gcs_bucket))

    # Step 2: Download source
    steps.append(
        _generate_download_source_step(
            build_id, project_id, language, target_platforms, output_name, source_url
        )
    )

    # Step 3: Extract source
    steps.append(_generate_extract_source_step())

    # Step 4: Download config
    steps.append(_generate_download_config_step(config_url, target_platforms))

    # Language-specific build steps
    if language == "python":
        # Python Linux build
        steps.append(
            _generate_python_linux_build_step(target_platforms, output_name, gcs_bucket)
        )

        # Python Linux upload
        steps.append(
            _generate_python_linux_upload_step(target_platforms, gcs_bucket, build_id)
        )

        # Python Windows build
        steps.append(
            _generate_python_windows_build_step(
                target_platforms, output_name, gcs_bucket
            )
        )

        # Python Windows upload
        steps.append(
            _generate_python_windows_upload_step(
                target_platforms, gcs_bucket, build_id, output_name
            )
        )

    elif language == "nodejs":
        # Node.js build (Windows + Linux)
        steps.append(
            _generate_nodejs_build_step(target_platforms, output_name, gcs_bucket)
        )

        # Node.js Windows upload
        steps.append(
            _generate_nodejs_windows_upload_step(target_platforms, gcs_bucket, build_id)
        )

        # Node.js Linux upload
        steps.append(
            _generate_nodejs_linux_upload_step(target_platforms, gcs_bucket, build_id)
        )

    # Save cache
    steps.append(_generate_save_cache_step(gcs_bucket))

    # Webhook callback
    steps.append(
        _generate_webhook_step(callback_url, callback_secret, build_id, gcs_bucket)
    )

    return steps


def _generate_restore_cache_step(gcs_bucket: str) -> Dict[str, Any]:
    """Generate cache restore step."""
    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "restore-cache",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""set +e
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

# Restore MinGW cache (for Windows cross-compilation speedup)
if gsutil -q stat "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz" 2>/dev/null; then
  mingw_size=$(gsutil du "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz" 2>/dev/null | awk '{{print $1}}' | cut -d'.' -f1)
  if [ -n "$mingw_size" ] && [ "$mingw_size" -gt 524288000 ]; then
    echo "[Cloud Build] Skipping MinGW cache (too large: $mingw_size bytes)"
  else
    echo "[Cloud Build] Restoring MinGW cache..."
    gsutil cp "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz" /tmp/mingw-cache.tar.gz
    mkdir -p /workspace/.mingw-cache
    tar -xzf /tmp/mingw-cache.tar.gz -C /workspace/.mingw-cache 2>/dev/null || true
    echo "[Cloud Build] MinGW cache restored"
  fi
else
  echo "[Cloud Build] MinGW cache not found"
fi

# Restore Nuitka cache
if gsutil -q stat "gs://{gcs_bucket}/cache/nuitka-cache-default.tar.gz" 2>/dev/null; then
  cache_size=$(gsutil du "gs://{gcs_bucket}/cache/nuitka-cache-default.tar.gz" 2>/dev/null | awk '{{print $1}}' | cut -d'.' -f1)
  if [ -n "$cache_size" ] && [ "$cache_size" -gt 104857600 ]; then
    echo "[Cloud Build] Skipping Nuitka cache (too large: $cache_size bytes)"
  else
    echo "[Cloud Build] Restoring Nuitka cache..."
    gsutil cp "gs://{gcs_bucket}/cache/nuitka-cache-default.tar.gz" /tmp/nuitka-cache.tar.gz
    mkdir -p /workspace/.nuitka-cache
    tar -xzf /tmp/nuitka-cache.tar.gz -C /workspace/.nuitka-cache 2>/dev/null || true
    echo "[Cloud Build] Nuitka cache restored"
  fi
else
  echo "[Cloud Build] Nuitka cache not found"
fi

echo "[Cloud Build] Cache restore complete"
""",
        ],
        "waitFor": ["-"],
    }


def _generate_download_source_step(
    build_id: str,
    project_id: str,
    language: str,
    target_platforms: str,
    output_name: str,
    source_url: str,
) -> Dict[str, Any]:
    """Generate source download step."""
    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "download-source",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""echo "Building: {build_id} for {project_id} ({language})"
echo "Target: {target_platforms}, Output: {output_name}"
if [[ "{source_url}" == gs://* ]]; then
  gsutil cp "{source_url}" source.zip
else
  curl -L -o source.zip "{source_url}"
fi""",
        ],
        "waitFor": ["restore-cache"],
    }


def _generate_extract_source_step() -> Dict[str, Any]:
    """Generate source extraction step."""
    return {
        "name": "ubuntu",
        "id": "extract-source",
        "entrypoint": "bash",
        "args": [
            "-c",
            """set -e
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
echo "[Cloud Build] Source prepared""",
        ],
        "waitFor": ["download-source"],
    }


def _generate_download_config_step(
    config_url: str, target_platforms: str
) -> Dict[str, Any]:
    """Generate config download step."""
    # Skip config download if URL is empty
    if not config_url:
        script = """echo "[Cloud Build] No config URL provided, skipping config download"
echo '{}' > /workspace/config.json"""
    else:
        script = f"""if [[ "{target_platforms}" == "" ]]; then
  exit 0
fi
echo "[Cloud Build] Downloading config..."
if [[ "{config_url}" == gs://* ]]; then
  gsutil cp "{config_url}" /workspace/config.json
else
  curl -L -o /workspace/config.json "{config_url}"
fi"""

    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "download-config",
        "entrypoint": "bash",
        "args": ["-c", script],
        "waitFor": ["extract-source"],
    }


def _generate_python_linux_build_step(
    target_platforms: str, output_name: str, gcs_bucket: str
) -> Dict[str, Any]:
    """Generate Python Linux build step."""
    return {
        "name": "gcr.io/cloudbuild-486309/codevault-builder:latest",
        "id": "build-linux",
        "entrypoint": "bash",
        "env": ["NUITKA_JOBS=4"],
        "args": [
            "-c",
            f"""set -e
# Check if Linux build is requested
if [[ "{target_platforms}" != *"linux"* ]]; then
  echo "[Cloud Build] Skipping Linux build"
  echo "skipped" > /workspace/artifacts/build_status_linux
  exit 0
fi

echo "[Cloud Build] ===== Building for Linux ====="

# Install Nuitka
pip install --quiet --disable-pip-version-check nuitka==2.4.8 ordered-set zstandard requests cryptography

if [ ! -f "./project/source/.github/scripts/cloud_runner.py" ]; then
  echo "cloud_runner.py not found" > ./project/source/error_message.txt
  echo "failed" > /workspace/build_status_linux
  exit 0
fi

decoded_config=$(cat /workspace/config.json)

# Check build mode from config
use_onefile=$(echo "$decoded_config" | python3 -c "import sys,json; print(json.load(sys.stdin).get('use_onefile', False))" 2>/dev/null || echo "False")
echo "[Cloud Build] Build mode: use_onefile=$use_onefile"

export NUITKA_JOBS=4
export NUITKA_CACHE_DIR=/workspace/.nuitka-cache
mkdir -p $NUITKA_CACHE_DIR

# Restore Nuitka cache
if [ -d /workspace/.nuitka-cache ]; then
  echo "[Cloud Build] Restoring Nuitka cache..."
  mkdir -p $HOME/.cache/Nuitka
  cp -r /workspace/.nuitka-cache/. $HOME/.cache/Nuitka/ 2>/dev/null || true
fi

python3 "./project/source/.github/scripts/cloud_runner.py" --config "$decoded_config" --source "./project/source" || true

cd "./project/source"
output_name="{output_name}"

# Check for standalone build first (directory with binary + libs)
dist_dir="build_output_linux/${{output_name}}.dist"

if [ -d "$dist_dir" ]; then
  echo "[Cloud Build] Found standalone build directory: $dist_dir"
  
  # Create ZIP of standalone build
  mkdir -p /workspace/artifacts
  cd "$dist_dir/.."
  tar -czf "/workspace/artifacts/${{output_name}}.tar.gz" "${{output_name}}.dist"
  zip_size=$(ls -lh "/workspace/artifacts/${{output_name}}.tar.gz" | awk '{{print $5}}')
  echo "[Cloud Build] Created standalone archive: $zip_size"
  
  echo "completed" > /workspace/artifacts/build_status_linux
  echo "${{output_name}}.tar.gz" > /workspace/artifacts/linux_artifacts
  echo "standalone" > /workspace/artifacts/build_mode_linux
  echo "[Cloud Build] Linux artifact ready: ${{output_name}}.tar.gz (standalone mode)"
elif [ -d "build_output_linux" ]; then
  found_binary=$(find build_output_linux -type f -name "$output_name" 2>/dev/null | head -1)
  if [ -n "$found_binary" ]; then
    chmod +x "$found_binary"
    tar -czf "$output_name.tar.gz" -C "$(dirname $found_binary)" "$(basename $found_binary)"
    mkdir -p /workspace/artifacts
    mv "$output_name.tar.gz" /workspace/artifacts/
    echo "completed" > /workspace/artifacts/build_status_linux
    echo "$output_name.tar.gz" > /workspace/artifacts/linux_artifacts
    echo "onefile" > /workspace/artifacts/build_mode_linux
    echo "[Cloud Build] Linux artifact ready: $output_name.tar.gz (onefile mode)"
  fi
fi

# Handle errors
if [ ! -f "/workspace/artifacts/linux_artifacts" ]; then
  if [ -f "error_message.txt" ]; then
    linux_error=$(cat error_message.txt)
  else
    linux_error="Linux build output not found"
  fi
  echo "failed" > /workspace/artifacts/build_status_linux
  echo "$linux_error" > /workspace/artifacts/linux_error
fi

# Save Nuitka cache
if [ -d "$HOME/.cache/Nuitka" ]; then
  mkdir -p /workspace/.nuitka-cache
  cp -r $HOME/.cache/Nuitka/. /workspace/.nuitka-cache/ 2>/dev/null || true
fi
""",
        ],
        "waitFor": ["download-config"],
        "volumes": [
            {"name": "ccache", "path": "/workspace/.ccache"},
            {"name": "artifacts", "path": "/workspace/artifacts"},
        ],
    }


def _generate_python_linux_upload_step(
    target_platforms: str, gcs_bucket: str, build_id: str
) -> Dict[str, Any]:
    """Generate Python Linux upload step."""
    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "upload-linux",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""linux_status=$(cat /workspace/artifacts/build_status_linux 2>/dev/null || echo "pending")
if [[ "$linux_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Linux upload (status: $linux_status)"
  exit 0
fi
linux_artifact=$(cat /workspace/artifacts/linux_artifacts 2>/dev/null)
if [ -z "$linux_artifact" ]; then
  exit 0
fi

max_retries=3
retry_count=0
upload_success=false

while [ $retry_count -lt $max_retries ] && [ "$upload_success" = "false" ]; do
  if [ $retry_count -gt 0 ]; then
    echo "[Cloud Build] Retrying upload (attempt $((retry_count+1))/$max_retries)..."
    sleep 2
  fi
  
  echo "[Cloud Build] Uploading Linux: $linux_artifact"
  if gsutil cp "/workspace/artifacts/$linux_artifact" "gs://{gcs_bucket}/builds/{build_id}/linux/$linux_artifact" 2>/dev/null; then
    upload_success=true
    echo "[Cloud Build] Linux upload successful"
  else
    retry_count=$((retry_count+1))
  fi
done

if [ "$upload_success" != "true" ]; then
  echo "[Cloud Build] Linux upload failed after $max_retries attempts"
  exit 1
fi""",
        ],
        "waitFor": ["build-linux"],
        "volumes": [{"name": "artifacts", "path": "/workspace/artifacts"}],
    }


def _generate_python_windows_build_step(
    target_platforms: str, output_name: str, gcs_bucket: str
) -> Dict[str, Any]:
    """Generate Python Windows build step."""
    return {
        "name": "docker.io/tobix/pywine:3.11",
        "id": "build-windows",
        "entrypoint": "bash",
        "env": ["NUITKA_JOBS=4"],
        "args": [
            "-c",
            f"""set -e
# Check if Windows build is requested
if [[ "{target_platforms}" != *"windows"* ]]; then
  echo "[Cloud Build] Skipping Windows build"
  echo "skipped" > /workspace/artifacts/build_status_windows
  exit 0
fi

echo "[Cloud Build] ===== Building for Windows ====="

export NUITKA_JOBS=4
export NUITKA_CACHE_DIR=/workspace/.nuitka-cache
mkdir -p $NUITKA_CACHE_DIR

# Restore MinGW cache if available (faster builds)
if [ -d /workspace/.mingw-cache ]; then
  echo "[Cloud Build] Restoring MinGW cache..."
  mkdir -p /root/.cache/Nuitka/downloads
  cp -r /workspace/.mingw-cache/. /root/.cache/Nuitka/downloads/ 2>/dev/null || true
fi

wine python -m pip install --upgrade --quiet --disable-pip-version-check nuitka ordered-set zstandard requests cryptography pefile

if [ ! -f "./project/source/.github/scripts/cloud_runner.py" ]; then
  echo "cloud_runner.py not found" > ./project/source/error_message.txt
  echo "failed" > /workspace/build_status_windows
  exit 0
fi

nuitka_depends_py=$(find /opt/wineprefix -name "DependsExe.py" | grep "freezer" | head -1)
if [ -n "$nuitka_depends_py" ]; then
  if [ -f "./project/source/.github/scripts/nuitka_patch.py" ]; then
    wine python "./project/source/.github/scripts/nuitka_patch.py" "$nuitka_depends_py"
  fi
fi

decoded_config=$(cat /workspace/config.json)

# Check build mode from config
use_onefile=$(echo "$decoded_config" | python3 -c "import sys,json; print(json.load(sys.stdin).get('use_onefile', False))" 2>/dev/null || echo "False")
echo "[Cloud Build] Build mode: use_onefile=$use_onefile"

wine python "./project/source/.github/scripts/cloud_runner.py" --config "$decoded_config" --source "$(winepath -w $(realpath ./project/source))"

output_name="{output_name}"
echo "[Cloud Build] Looking for Windows build output..."

found_exe=""
# Look for ANY .dist folder (Nuitka names it after entry file, not output name)
# e.g., main.py -> main.dist, not ${{output_name}}.dist
dist_dir=$(find ./project/source/build_output_windows_wine -type d -name "*.dist" 2>/dev/null | head -1)

# Check for standalone build first (directory with EXE + DLLs)
if [ -n "$dist_dir" ] && [ -d "$dist_dir" ]; then
  dist_name=$(basename "$dist_dir")
  echo "[Cloud Build] Found standalone build directory: $dist_dir (name: $dist_name)"
  if [ -f "$dist_dir/${{output_name}}.exe" ]; then
    found_exe="$dist_dir/${{output_name}}.exe"
  else
    found_exe=$(find "$dist_dir" -type f -name "*.exe" 2>/dev/null | head -1)
  fi

  if [ -n "$found_exe" ]; then
    exe_size=$(ls -lh "$found_exe" | awk '{{print $5}}')
    echo "[Cloud Build] EXE size: $exe_size"

    # Create ZIP of standalone build - try apt-get zip first, fallback to Python
    mkdir -p /workspace/artifacts
    parent_dir=$(dirname "$dist_dir")
    cd "$parent_dir"
    if command -v zip &> /dev/null; then
      zip -r "/workspace/artifacts/${{output_name}}.zip" "$dist_name" -x "*.pyc" -x "__pycache__/*"
    else
      python3 -c "
import zipfile, os, sys
dn, on = '$dist_name', '${{output_name}}'
zf = zipfile.ZipFile(f'/workspace/artifacts/{on}.zip', 'w', zipfile.ZIP_DEFLATED)
for r, ds, fs in os.walk(dn):
  ds[:] = [d for d in ds if d != '__pycache__']
  for f in fs:
    if f.endswith('.pyc'): continue
    zf.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), '.'))
zf.close()
"
    fi
    zip_size=$(ls -lh "/workspace/artifacts/${{output_name}}.zip" | awk '{{print $5}}')
    echo "[Cloud Build] Created standalone ZIP: $zip_size"

    echo "completed" > /workspace/artifacts/build_status_windows
    echo "${{output_name}}.zip" > /workspace/artifacts/windows_artifacts
    echo "standalone" > /workspace/artifacts/build_mode_windows
    echo "[Cloud Build] Windows artifact ready: ${{output_name}}.zip (standalone mode)"
  fi
elif [ -f "./project/source/build_output_windows_wine/${{output_name}}.exe" ]; then
  found_exe="./project/source/build_output_windows_wine/${{output_name}}.exe"
  echo "[Cloud Build] Found onefile EXE: $found_exe"
fi

# Handle onefile build
if [ -z "$found_exe" ] || [ ! -f "$found_exe" ]; then
  found_exe=$(find ./project/source/build_output_windows_wine -type f -name "*.exe" 2>/dev/null | head -1)
  if [ -n "$found_exe" ]; then
    echo "[Cloud Build] Found EXE: $found_exe"
  fi
fi

# If we found an EXE but haven't created artifacts yet (onefile mode)
if [ -n "$found_exe" ] && [ -f "$found_exe" ] && [ ! -f "/workspace/artifacts/windows_artifacts" ]; then
  exe_size=$(ls -lh "$found_exe" | awk '{{print $5}}')
  echo "[Cloud Build] EXE size: $exe_size"
  
  mkdir -p /workspace/artifacts
  cp "$found_exe" "/workspace/artifacts/${{output_name}}.exe"
  
  if [ -f "/workspace/artifacts/${{output_name}}.exe" ]; then
    echo "completed" > /workspace/artifacts/build_status_windows
    echo "${{output_name}}.exe" > /workspace/artifacts/windows_artifacts
    echo "onefile" > /workspace/artifacts/build_mode_windows
    echo "[Cloud Build] Windows artifact ready: ${{output_name}}.exe (onefile mode)"
  fi
fi

# Handle errors
if [ ! -f "/workspace/artifacts/windows_artifacts" ]; then
  if [ -f "./project/source/error_message.txt" ]; then
    windows_error=$(cat ./project/source/error_message.txt)
  else
    windows_error="Windows build output not found"
  fi
  echo "failed" > /workspace/artifacts/build_status_windows
  echo "$windows_error" > /workspace/artifacts/windows_error
fi

# Save MinGW cache for faster future builds
if [ -d /root/.cache/Nuitka/downloads ]; then
  echo "[Cloud Build] Saving MinGW cache..."
  mkdir -p /workspace/.mingw-cache
  cp -r /root/.cache/Nuitka/downloads/. /workspace/.mingw-cache/ 2>/dev/null || true
fi""",
        ],
        "waitFor": ["download-config"],
        "volumes": [{"name": "artifacts", "path": "/workspace/artifacts"}],
    }


def _generate_python_windows_upload_step(
    target_platforms: str, gcs_bucket: str, build_id: str, output_name: str
) -> Dict[str, Any]:
    """Generate Python Windows upload step."""
    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "upload-windows",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""windows_status=$(cat /workspace/artifacts/build_status_windows 2>/dev/null || echo "pending")
if [[ "$windows_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Windows upload (status: $windows_status)"
  exit 0
fi
windows_artifact=$(cat /workspace/artifacts/windows_artifacts 2>/dev/null)
if [ -z "$windows_artifact" ]; then
  exit 0
fi
echo "[Cloud Build] Uploading Windows: $windows_artifact"
gsutil cp "/workspace/artifacts/$windows_artifact" "gs://{gcs_bucket}/builds/{build_id}/windows/$windows_artifact"
""",
        ],
        "waitFor": ["build-windows"],
        "volumes": [{"name": "artifacts", "path": "/workspace/artifacts"}],
    }


def _generate_nodejs_build_step(
    target_platforms: str, output_name: str, gcs_bucket: str
) -> Dict[str, Any]:
    """Generate Node.js build step."""
    return {
        "name": "node:20-slim",
        "id": "build-nodejs",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""set -e
echo "[Cloud Build] ===== Building for Node.js ====="
echo "[Cloud Build] Build ID: BUILD_ID_PLACEHOLDER"
echo "[Cloud Build] Output name: {output_name}"

# Install Python for the runner script
apt-get update -qq && apt-get install -y -qq python3 > /dev/null 2>&1

# Install pkg globally
npm install -g @yao-pkg/pkg --quiet

cd "./project/source"

# Debug: Show directory contents
echo "[Cloud Build] Directory contents:"
ls -la
echo ""

# Debug: Show config
echo "[Cloud Build] Config:"
cat /workspace/config.json
echo ""

# Run the Node.js build runner
if [ -f ".github/scripts/cloud_runner_nodejs.py" ]; then
  echo "[Cloud Build] Running cloud_runner_nodejs.py..."
  python3 .github/scripts/cloud_runner_nodejs.py --config "$(cat /workspace/config.json)" --source "$(pwd)" 2>&1 || {{
    exit_code=$?
    echo "[Cloud Build] Runner failed with exit code: $exit_code"
    echo "[Cloud Build] Attempting direct pkg fallback..."
    
    if [ -f "package.json" ]; then
      echo "[Cloud Build] Using existing package.json"
      sed -i 's/"echo \\([^"]*\\)\\([""]\\)/"echo \\\\\"\\1\\\\\"\\2/g' package.json || true
      sed -i 's/"npm \\([^"]*\\)\\([""]\\)/"npm \\\\\"\\1\\\\\"\\2/g' package.json || true
    else
      entry_file=$(ls *.js 2>/dev/null | head -1 || echo "index.js")
      echo "[Cloud Build] Creating package.json with main: $entry_file"
      echo '{{"name": "{output_name}", "version": "1.0.0", "main": "$entry_file", "private": true}}' > package.json
    fi
    
    echo "[Cloud Build] package.json content:"
    cat package.json
    
    mkdir -p /workspace/artifacts
    npx @yao-pkg/pkg . --target node20-win-x64 --output "/workspace/artifacts/{output_name}.exe" --compress GZip 2>&1 || true
  }}
else
  echo "[Cloud Build] cloud_runner_nodejs.py not found, using fallback"
  if [ ! -f "package.json" ]; then
    entry_file=$(ls *.js 2>/dev/null | head 1 || echo "index.js")
    echo '{{"name": "{output_name}", "version": "1.0.0", "main": "$entry_file", "private": true}}' > package.json
  else
    sed -i 's/"echo \\([^"]*\\)\\([""]\\)/"echo \\\\\"\\1\\\\\"\\2/g' package.json || true
    sed -i 's/"npm \\([^"]*\\)\\([""]\\)/"npm \\\\\"\\1\\\\\"\\2/g' package.json || true
  fi
  echo "[Cloud Build] package.json content:"
  cat package.json
  npm install --quiet 2>/dev/null || true
  mkdir -p /workspace/artifacts
  npx @yao-pkg/pkg . --target node20-win-x64 --output "/workspace/artifacts/{output_name}.exe" --compress GZip
fi

# Copy artifacts to workspace
mkdir -p /workspace/artifacts

# Debug: Show artifacts directory
echo "[Cloud Build] Artifacts directory contents:"
ls -la /workspace/artifacts/ 2>/dev/null || echo "Artifacts directory empty or not found"

# Parse target platforms from config
target_platforms=$(cat /workspace/config.json | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('target_platforms', ['windows'])))" 2>/dev/null || echo "windows")
echo "[Cloud Build] Target platforms: $target_platforms"

# Find and copy Windows artifact
echo "[Cloud Build] DEBUG: Checking for Windows artifact..."
if [[ "$target_platforms" == *"windows"* ]]; then
  echo "[Cloud Build] DEBUG: Windows is in target platforms"
  if [ -f "build_output_windows/{output_name}.exe" ]; then
    cp "build_output_windows/{output_name}.exe" /workspace/artifacts/
    echo "completed" > /workspace/artifacts/build_status_windows
    echo "{output_name}.exe" > /workspace/artifacts/windows_artifacts
    echo "[Cloud Build] Found Windows artifact in build_output_windows"
  elif [ -f "/workspace/artifacts/{output_name}.exe" ]; then
    echo "completed" > /workspace/artifacts/build_status_windows
    echo "{output_name}.exe" > /workspace/artifacts/windows_artifacts
    echo "[Cloud Build] Found Windows artifact in /workspace/artifacts"
  else
    found_exe=$(find . -name "*.exe" -type f 2>/dev/null | head -1)
    if [ -n "$found_exe" ]; then
      cp "$found_exe" /workspace/artifacts/
      echo "completed" > /workspace/artifacts/build_status_windows
      echo "$(basename $found_exe)" > /workspace/artifacts/windows_artifacts
      echo "[Cloud Build] Found Windows artifact via search: $found_exe"
    else
      echo "failed" > /workspace/artifacts/build_status_windows
      echo "Node.js Windows build output not found" > /workspace/artifacts/windows_error
      echo "[Cloud Build] ERROR: No Windows exe file found!"
    fi
  fi
else
  echo "skipped" > /workspace/artifacts/build_status_windows
  echo "[Cloud Build] Windows build skipped"
fi

# Find and copy Linux artifact
if [[ "$target_platforms" == *"linux"* ]]; then
  if [ -f "build_output_linux/{output_name}" ]; then
    cp "build_output_linux/{output_name}" /workspace/artifacts/
    chmod +x "/workspace/artifacts/{output_name}"
    echo "completed" > /workspace/artifacts/build_status_linux
    echo "{output_name}" > /workspace/artifacts/linux_artifacts
    echo "[Cloud Build] Found Linux artifact"
  else
    found_linux=$(find ./build_output_linux -type f -executable 2>/dev/null | head -1)
    if [ -n "$found_linux" ]; then
      cp "$found_linux" /workspace/artifacts/
      chmod +x "/workspace/artifacts/$(basename $found_linux)"
      echo "completed" > /workspace/artifacts/build_status_linux
      echo "$(basename $found_linux)" > /workspace/artifacts/linux_artifacts
      echo "[Cloud Build] Found Linux artifact via search"
    else
      echo "failed" > /workspace/artifacts/build_status_linux
      echo "Node.js Linux build output not found" > /workspace/artifacts/linux_error
    fi
  fi
else
  echo "skipped" > /workspace/artifacts/build_status_linux
fi

echo "[Cloud Build] Node.js build step complete""".replace(
                "BUILD_ID_PLACEHOLDER", "${{BUILD_ID}}"
            ),
        ],
        "waitFor": ["download-config"],
        "volumes": [{"name": "artifacts", "path": "/workspace/artifacts"}],
    }


def _generate_nodejs_windows_upload_step(
    target_platforms: str, gcs_bucket: str, build_id: str
) -> Dict[str, Any]:
    """Generate Node.js Windows upload step."""
    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "upload-nodejs-windows",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""windows_status=$(cat /workspace/artifacts/build_status_windows 2>/dev/null || echo "pending")
if [[ "$windows_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Node.js Windows upload (status: $windows_status)"
  exit 0
fi
windows_artifact=$(cat /workspace/artifacts/windows_artifacts 2>/dev/null)
if [ -z "$windows_artifact" ]; then
  exit 0
fi
echo "[Cloud Build] Uploading Node.js Windows artifact: $windows_artifact"
gsutil cp "/workspace/artifacts/$windows_artifact" "gs://{gcs_bucket}/builds/{build_id}/windows/$windows_artifact"
""",
        ],
        "waitFor": ["build-nodejs"],
        "volumes": [{"name": "artifacts", "path": "/workspace/artifacts"}],
    }


def _generate_nodejs_linux_upload_step(
    target_platforms: str, gcs_bucket: str, build_id: str
) -> Dict[str, Any]:
    """Generate Node.js Linux upload step."""
    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "upload-nodejs-linux",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""linux_status=$(cat /workspace/artifacts/build_status_linux 2>/dev/null || echo "pending")
if [[ "$linux_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Node.js Linux upload (status: $linux_status)"
  exit 0
fi
linux_artifact=$(cat /workspace/artifacts/linux_artifacts 2>/dev/null)
if [ -z "$linux_artifact" ]; then
  exit 0
fi
echo "[Cloud Build] Uploading Node.js Linux artifact: $linux_artifact"
gsutil cp "/workspace/artifacts/$linux_artifact" "gs://{gcs_bucket}/builds/{build_id}/linux/$linux_artifact"
""",
        ],
        "waitFor": ["build-nodejs"],
        "volumes": [{"name": "artifacts", "path": "/workspace/artifacts"}],
    }


def _generate_save_cache_step(gcs_bucket: str) -> Dict[str, Any]:
    """Generate cache save step."""
    return {
        "name": "gcr.io/cloud-builders/gsutil",
        "id": "save-cache",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""set +e
echo "[Cloud Build] Saving cache..."

# Save pip cache
if [ -d /root/.cache/pip ]; then
  pip_cache_size=$(du -s /root/.cache/pip 2>/dev/null | cut -f1)
  if [ "$pip_cache_size" -gt 1000 ]; then
    tar -czf /tmp/pip-cache.tar.gz -C /root/.cache/pip . 2>/dev/null
    gsutil cp /tmp/pip-cache.tar.gz "gs://{gcs_bucket}/cache/pip-cache-default.tar.gz"
    echo "[Cloud Build] Saved pip cache ($pip_cache_size KB)"
  fi
fi

# Save ccache
if [ -d /workspace/.ccache ]; then
  ccache_size=$(du -s /workspace/.ccache 2>/dev/null | cut -f1)
  if [ "$ccache_size" -gt 1000 ]; then
    tar -czf /tmp/ccache.tar.gz -C /workspace/.ccache . 2>/dev/null
    gsutil cp /tmp/ccache.tar.gz "gs://{gcs_bucket}/cache/ccache-default.tar.gz"
    echo "[Cloud Build] Saved ccache ($ccache_size KB)"
  fi
fi

# Save MinGW cache (for Windows cross-compilation)
if [ -d /workspace/.mingw-cache ]; then
  mingw_cache_size=$(du -s /workspace/.mingw-cache 2>/dev/null | cut -f1)
  if [ "$mingw_cache_size" -gt 10000 ] && [ "$mingw_cache_size" -lt 600000 ]; then
    tar -czf /tmp/mingw-cache.tar.gz -C /workspace/.mingw-cache . 2>/dev/null
    gsutil cp /tmp/mingw-cache.tar.gz "gs://{gcs_bucket}/cache/mingw-cache-default.tar.gz"
    echo "[Cloud Build] Saved MinGW cache ($mingw_cache_size KB)"
  else
    echo "[Cloud Build] Skipping MinGW cache save (size: $mingw_cache_size KB)"
  fi
fi

# Save Nuitka cache (only essentials, max 100MB)
if [ -d "$HOME/.cache/Nuitka" ]; then
  nuitka_cache_size=$(du -s $HOME/.cache/Nuitka 2>/dev/null | cut -f1)
  if [ -n "$nuitka_cache_size" ] && [ "$nuitka_cache_size" -lt 102400 ]; then
    echo "[Cloud Build] Saving Nuitka cache ($nuitka_cache_size KB)..."
    tar -czf /tmp/nuitka-cache.tar.gz -C $HOME/.cache/Nuitka . 2>/dev/null
    gsutil cp /tmp/nuitka-cache.tar.gz "gs://{gcs_bucket}/cache/nuitka-cache-default.tar.gz"
  else
    echo "[Cloud Build] Skipping Nuitka cache save (size: $nuitka_cache_size KB, limit: 100MB)"
  fi
fi

echo "[Cloud Build] Cache save complete"
""",
        ],
        "waitFor": [
            "upload-linux",
            "upload-windows",
            "upload-nodejs-windows",
            "upload-nodejs-linux",
        ],
    }


def _generate_webhook_step(
    callback_url: str, callback_secret: str, build_id: str, gcs_bucket: str
) -> Dict[str, Any]:
    """Generate webhook callback step."""
    return {
        "name": "gcr.io/cloud-builders/curl",
        "id": "webhook-callback",
        "entrypoint": "bash",
        "args": [
            "-c",
            f"""set +e
echo "============================================"
echo "[Cloud Build] Preparing webhook callback..."
echo "============================================"

# Debug: show artifacts directory contents
echo "[Cloud Build] DEBUG: Artifacts directory contents:"
ls -la /workspace/artifacts/ 2>/dev/null || echo "Artifacts dir not found"

# Download config for language detection
gsutil cp "gs://{gcs_bucket}/builds/{build_id}/config.json" /workspace/config.json 2>/dev/null || echo "Config not found"

# Read status files
linux_status=$(cat /workspace/artifacts/build_status_linux 2>/dev/null || echo "pending")
windows_status=$(cat /workspace/artifacts/build_status_windows 2>/dev/null || echo "pending")
windows_artifact=$(cat /workspace/artifacts/windows_artifacts 2>/dev/null || echo "")
linux_artifact=$(cat /workspace/artifacts/linux_artifacts 2>/dev/null || echo "")

echo "[Cloud Build] DEBUG: linux_status=$linux_status, windows_status=$windows_status"
echo "[Cloud Build] DEBUG: windows_artifact=$windows_artifact, linux_artifact=$linux_artifact"

# Determine language from config
build_language=$(cat /workspace/config.json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('language', ''))" 2>/dev/null || echo "")
echo "[Cloud Build] DEBUG: build_language=$build_language"

# For Node.js builds, also check Node.js status files
if [[ "$build_language" == "nodejs" ]]; then
  nodejs_windows_status=$(cat /workspace/artifacts/build_status_windows 2>/dev/null || echo "pending")
  nodejs_linux_status=$(cat /workspace/artifacts/build_status_linux 2>/dev/null || echo "pending")
  echo "[Cloud Build] DEBUG: nodejs_windows_status=$nodejs_windows_status, nodejs_linux_status=$nodejs_linux_status"
  if [[ "$nodejs_windows_status" != "pending" ]]; then
    windows_status=$nodejs_windows_status
  fi
  if [[ "$nodejs_linux_status" != "pending" ]]; then
    linux_status=$nodejs_linux_status
  fi
fi

# If we have an artifact but status is wrong, fix it
if [[ -n "$windows_artifact" && "$windows_status" == "skipped" ]]; then
  echo "[Cloud Build] DEBUG: Fixing windows_status (had artifact but status was skipped)"
  windows_status="completed"
fi
if [[ -n "$linux_artifact" && "$linux_status" == "skipped" ]]; then
  echo "[Cloud Build] DEBUG: Fixing linux_status (had artifact but status was skipped)"
  linux_status="completed"
fi

linux_error=$(cat /workspace/artifacts/linux_error 2>/dev/null || echo "")
windows_error=$(cat /workspace/artifacts/windows_error 2>/dev/null || echo "")

echo "[Cloud Build] Linux: $linux_status, artifact: $linux_artifact"
echo "[Cloud Build] Windows: $windows_status, artifact: $windows_artifact"

all_skipped=true
any_completed=false
if [[ "$linux_status" != "skipped" ]]; then all_skipped=false; fi
if [[ "$windows_status" != "skipped" ]]; then all_skipped=false; fi
if [[ "$linux_status" == "completed" || "$windows_status" == "completed" ]]; then any_completed=true; fi

if [[ "$any_completed" == "true" ]]; then
  overall_status="completed"
elif [[ "$all_skipped" == "true" ]]; then
  overall_status="cancelled"
elif [[ "$linux_status" == "failed" || "$windows_status" == "failed" ]]; then
  overall_status="failed"
else
  overall_status="failed"
fi

echo "[Cloud Build] Overall: $overall_status"

linux_download_key=""
windows_download_key=""
filename=""

if [[ "$linux_status" == "completed" && -n "$linux_artifact" ]]; then
  linux_download_key="builds/{build_id}/linux/$linux_artifact"
  filename="$linux_artifact"
fi

if [[ "$windows_status" == "completed" && -n "$windows_artifact" ]]; then
  windows_download_key="builds/{build_id}/windows/$windows_artifact"
  if [[ -z "$filename" ]]; then
    filename="$windows_artifact"
  fi
fi

error_msg=""
if [[ "$overall_status" == "failed" ]]; then
  if [[ -n "$linux_error" ]]; then error_msg="Linux: $linux_error; "; fi
  if [[ -n "$windows_error" ]]; then error_msg="${{error_msg}}Windows: $windows_error"; fi
  if [[ -z "$error_msg" ]]; then error_msg="Build failed"; fi
fi

error_msg_escaped=$(echo "$error_msg" | sed 's/"/\\"/g' | tr '\\n' ' ')

# BUILD_ID is the actual GCP Cloud Build ID
payload='{{"build_id":"{build_id}","cloud_build_id":"'$BUILD_ID'","status":"'$overall_status'","linux_status":"'$linux_status'","windows_status":"'$windows_status'","linux_download_key":"'$linux_download_key'","windows_download_key":"'$windows_download_key'","filename":"'$filename'","error":"'$error_msg_escaped'","timestamp":'$(date +%s)'}}'

if [ -n "{callback_secret}" ]; then
  sig=$(echo -n "$payload" | openssl dgst -sha256 -hmac "{callback_secret}" | awk '{{print $2}}')
else
  sig=""
fi

echo "[Cloud Build] Sending webhook to: {callback_url}"
echo "[Cloud Build] Payload: $payload"

max_retries=2
retry_delay=2
for i in $(seq 1 $max_retries); do
  echo "[Cloud Build] Attempt $i/$max_retries..."
  
  if [ -n "$sig" ]; then
    response=$(curl -s -w "\\n%{{http_code}}" -X POST "{callback_url}" \\
      -H "Content-Type: application/json" \\
      -H "X-Signature: $sig" \\
      -d "$payload" --connect-timeout 5 --max-time 10 2>&1)
  else
    response=$(curl -s -w "\\n%{{http_code}}" -X POST "{callback_url}" \\
      -H "Content-Type: application/json" \\
      -d "$payload" --connect-timeout 5 --max-time 10 2>&1)
  fi
  
  http_code=$(echo "$response" | tail -1)
  echo "[Cloud Build] Response: HTTP $http_code"
  
  if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
    echo "[Cloud Build] Success (HTTP $http_code)"
    break
  else
    echo "[Cloud Build] Failed (HTTP $http_code)"
    if [[ $i -lt $max_retries ]]; then
      echo "[Cloud Build] Retrying in ${{retry_delay}}s..."
      sleep $retry_delay
      retry_delay=$((retry_delay + 2))
    fi
  fi
done

echo "[Cloud Build] Webhook completed""",
        ],
        "waitFor": ["save-cache"],
        "volumes": [{"name": "artifacts", "path": "/workspace/artifacts"}],
    }
