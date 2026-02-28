set -e
if [[ "{target_platforms}" != *"linux"* ]]; then
  echo "[Cloud Build] Skipping Linux build"
  echo "skipped" > /workspace/build_status_linux
  exit 0
fi

echo "[Cloud Build] ===== Building for Linux ====="
# Skip pip install if Nuitka 2.4.8 is already pre-installed in the builder image
python3 -c "import nuitka; v=nuitka.__version__; assert v=='2.4.8', 'version mismatch: '+v" 2>/dev/null || 
  pip install --quiet --disable-pip-version-check nuitka==2.4.8 ordered-set zstandard requests cryptography

if [ ! -f "./project/source/.github/scripts/cloud_runner.py" ]; then
  echo "cloud_runner.py not found" > ./project/source/error_message.txt
  echo "failed" > /workspace/build_status_linux
  exit 0
fi

decoded_config=$(cat /workspace/config.json)
export NUITKA_JOBS=6
export NUITKA_CACHE_DIR=/workspace/.nuitka-cache
# Point ccache at the restored workspace directory so Nuitka's C compilation is cached
export CCACHE_DIR=/workspace/.ccache
export CCACHE_COMPRESS=1
mkdir -p $NUITKA_CACHE_DIR

if [ -d /workspace/.nuitka-cache ]; then
  mkdir -p $HOME/.cache/Nuitka
  cp -r /workspace/.nuitka-cache/. $HOME/.cache/Nuitka/ 2>/dev/null || true
fi

python3 "./project/source/.github/scripts/cloud_runner.py" --config "$decoded_config" --source "./project/source" || true

cd "./project/source"

linux_artifacts=""
linux_status="failed"
linux_error=""

# Check for standalone output - look for ANY .dist folder (Nuitka names it after entry file, not output name)
# e.g., main.py -> main.dist, not {output_name}.dist
dist_dir=$(find ./project/source/build_output_linux -type d -name "*.dist" 2>/dev/null | head -1)

if [ -n "$dist_dir" ] && [ -d "$dist_dir" ]; then
  dist_name=$(basename "$dist_dir")
  echo "[Cloud Build] Found standalone .dist folder: $dist_dir (name: $dist_name)"
  
  # Zip the entire .dist folder with all dependencies (including python dlls)
  parent_dir=$(dirname "$dist_dir")
  cd "$parent_dir"
  tar -czf "/workspace/{output_name}.tar.gz" "$dist_name"
  cd /workspace
  
  if [ -f "/workspace/{output_name}.tar.gz" ]; then
    linux_artifacts="{output_name}.tar.gz"
    linux_status="completed"
    echo "[Cloud Build] Linux artifact ready: $linux_artifacts (standalone folder with dependencies)"
  else
    linux_error="Failed to create tar.gz from .dist folder"
  fi
elif [ -d "build_output_linux" ]; then
  # Fallback: Check for onefile mode (single binary)
  found_binary=$(find build_output_linux -type f -name "{output_name}" 2>/dev/null | head -1)
  if [ -n "$found_binary" ]; then
    cp "$found_binary" ./
  fi
  
  if [ -f "{output_name}" ]; then
    chmod +x "{output_name}"
    tar -czf "/workspace/{output_name}.tar.gz" "{output_name}"
    linux_artifacts="{output_name}.tar.gz"
    linux_status="completed"
    echo "[Cloud Build] Linux artifact ready: $linux_artifacts (onefile binary)"
  else
    if [ -f "error_message.txt" ]; then
      linux_error=$(cat error_message.txt)
    else
      linux_error="Linux build output '{output_name}' not found"
    fi
  fi
else
  if [ -f "error_message.txt" ]; then
    linux_error=$(cat error_message.txt)
  else
    linux_error="Linux build output directory not found"
  fi
fi

echo "$linux_status" > /workspace/build_status_linux
echo "$linux_artifacts" > /workspace/linux_artifacts
echo "$linux_error" > /workspace/linux_error

if [ -d "$HOME/.cache/Nuitka" ]; then
  mkdir -p /workspace/.nuitka-cache
  cp -r $HOME/.cache/Nuitka/. /workspace/.nuitka-cache/ 2>/dev/null || true
fi
