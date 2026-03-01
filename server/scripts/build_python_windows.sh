set -e
if [[ "{target_platforms}" != *"windows"* ]]; then
  echo "[Cloud Build] Skipping Windows build"
  echo "skipped" > /workspace/build_status_windows
  exit 0
fi

echo "[Cloud Build] ===== Building for Windows ====="
export NUITKA_CACHE_DIR=/workspace/.nuitka-cache
mkdir -p $NUITKA_CACHE_DIR

# Restore MinGW cache (avoids re-downloading ~300MB toolchain each build)
if [ -d /workspace/.mingw-cache ]; then
  echo "[Cloud Build] Restoring MinGW cache..."
  mkdir -p /root/.cache/Nuitka/downloads
  cp -r /workspace/.mingw-cache/. /root/.cache/Nuitka/downloads/ 2>/dev/null || true
  echo "[Cloud Build] MinGW cache restored"
fi

wine python -m pip install --quiet --disable-pip-version-check nuitka==2.4.8 ordered-set zstandard requests cryptography pefile

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

echo "[Cloud Build] Running cloud_runner.py for Windows build..."
set +e
output=$(wine python "./project/source/.github/scripts/cloud_runner.py" --config "$decoded_config" --source "$(winepath -w $(realpath ./project/source))" 2>&1)
runner_exit_code=$?
set -e

echo "$output"

if [ $runner_exit_code -ne 0 ]; then
  echo "[Cloud Build] ERROR: cloud_runner.py exited with code $runner_exit_code"
  error_snippet=$(echo "$output" | grep -v "wine:" | grep -v "fixme:" | tail -n 5)
  echo "Build Failed: $error_snippet" > ./project/source/error_message.txt
fi

windows_artifacts=""
windows_status="failed"
windows_error=""

# Check for standalone output - look for ANY .dist folder (Nuitka names it after entry file, not output name)
# e.g., main.py -> main.dist, not {output_name}.dist
dist_dir=$(find ./project/source/build_output_windows_wine -type d -name "*.dist" 2>/dev/null | head -1)

if [ -n "$dist_dir" ] && [ -d "$dist_dir" ]; then
  dist_name=$(basename "$dist_dir")
  echo "[Cloud Build] Found standalone .dist folder: $dist_dir (name: $dist_name)"
  # List contents for debugging
  echo "[Cloud Build] .dist folder contents:"
  ls -la "$dist_dir/" 2>/dev/null || true
  
  # Zip the entire .dist folder with all dependencies (including python311.dll)
  # Use Python zipfile (more reliable than apt-get install zip)
  parent_dir=$(dirname "$dist_dir")
  cd "$parent_dir"
  if command -v zip &> /dev/null; then
    zip -r -q "/workspace/{output_name}.zip" "$dist_name" -x "*.pyc" -x "__pycache__/*"
  else
    wine python -c "
import zipfile, os
dn, on = '$dist_name', '{output_name}'
zf = zipfile.ZipFile(f'Z:\\workspace\\{on}.zip', 'w', zipfile.ZIP_DEFLATED)
for r, ds, fs in os.walk(dn):
  ds[:] = [d for d in ds if d != '__pycache__']
  for f in fs:
    if f.endswith('.pyc'): continue
    zf.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), '.'))
zf.close()
"
  fi
  cd /workspace

  if [ -f "/workspace/{output_name}.zip" ]; then
    archive_size=$(ls -lh "/workspace/{output_name}.zip" | awk '{{print $5}}')
    echo "[Cloud Build] Archive size: $archive_size"
    windows_artifacts="{output_name}.zip"
    windows_status="completed"
    echo "[Cloud Build] Windows artifact ready: $windows_artifacts (standalone folder with dependencies)"
  else
    windows_error="Failed to create zip from .dist folder"
  fi
else
  # Fallback: Check for onefile mode (single EXE)
  echo "[Cloud Build] No .dist folder found, checking for onefile EXE..."
  found_exe=""
  
  if [ -f "./project/source/build_output_windows_wine/{output_name}.exe" ]; then
    found_exe="./project/source/build_output_windows_wine/{output_name}.exe"
    echo "[Cloud Build] Found onefile EXE: $found_exe"
  else
    found_exe=$(find ./project/source/build_output_windows_wine -type f -name "*.exe" 2>/dev/null | head -1)
    if [ -n "$found_exe" ]; then
      echo "[Cloud Build] Found EXE: $found_exe"
    fi
  fi

  if [ -n "$found_exe" ] && [ -f "$found_exe" ]; then
    exe_size=$(ls -lh "$found_exe" | awk '{{print $5}}')
    echo "[Cloud Build] EXE size: $exe_size"
    cp "$found_exe" "/workspace/{output_name}.exe"
    if [ -f "/workspace/{output_name}.exe" ]; then
      windows_artifacts="{output_name}.exe"
      windows_status="completed"
      echo "[Cloud Build] Windows artifact ready: $windows_artifacts (self-contained onefile EXE)"
    else
      windows_error="Failed to copy EXE to artifacts"
    fi
  else
    if [ -f "./project/source/error_message.txt" ]; then
      windows_error=$(cat ./project/source/error_message.txt)
    else
      windows_error="Windows EXE not found in build output"
    fi
  fi
fi

echo "$windows_status" > /workspace/build_status_windows
echo "$windows_artifacts" > /workspace/windows_artifacts
echo "$windows_error" > /workspace/windows_error

# Save MinGW cache for faster future Windows builds (10MB < size < 600MB)
if [ -d /root/.cache/Nuitka/downloads ]; then
  mingw_cache_size=$(du -s /root/.cache/Nuitka/downloads 2>/dev/null | cut -f1)
  if [ -n "$mingw_cache_size" ] && [ "$mingw_cache_size" -gt 10000 ] && [ "$mingw_cache_size" -lt 600000 ]; then
    echo "[Cloud Build] Saving MinGW cache ($mingw_cache_size KB)..."
    mkdir -p /workspace/.mingw-cache
    cp -r /root/.cache/Nuitka/downloads/. /workspace/.mingw-cache/ 2>/dev/null || true
    echo "[Cloud Build] MinGW cache staged"
  else
    echo "[Cloud Build] Skipping MinGW cache (size: $mingw_cache_size KB, limit: 600MB)"
  fi
fi
