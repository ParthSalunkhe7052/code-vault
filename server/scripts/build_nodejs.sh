set -e
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
python3 .github/scripts/cloud_runner_nodejs.py --config "$(cat /workspace/config.json)" --source "$(pwd)" 2>&1
runner_exit_code=$?

if [ $runner_exit_code -ne 0 ]; then
  echo "[Cloud Build] ERROR: cloud_runner_nodejs.py failed with exit code $runner_exit_code"
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
target_plats=$(cat /workspace/config.json | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('target_platforms', ['windows'])))" 2>/dev/null || echo "windows")
echo "[Cloud Build] Target platforms: $target_plats"

# Windows artifact - strict: only accept expected output file
if [[ "$target_plats" == *"windows"* ]]; then
  if [ -f "build_output_windows/{output_name}.exe" ]; then
    exe_size=$(stat -c%s "build_output_windows/{output_name}.exe" 2>/dev/null || echo "0")
    echo "[Cloud Build] Found Windows exe: build_output_windows/{output_name}.exe ($exe_size bytes)"
    if [ "$exe_size" -lt 10000 ]; then
      echo "[Cloud Build] WARNING: EXE seems too small, may be corrupted"
      echo "failed" > /workspace/build_status_windows
      echo "Windows EXE file is too small ($exe_size bytes) - likely corrupted" > /workspace/windows_error
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
if [[ "$target_plats" == *"linux"* ]]; then
  if [ -f "build_output_linux/{output_name}" ]; then
    linux_size=$(stat -c%s "build_output_linux/{output_name}" 2>/dev/null || echo "0")
    echo "[Cloud Build] Found Linux binary: build_output_linux/{output_name} ($linux_size bytes)"
    if [ "$linux_size" -lt 10000 ]; then
      echo "[Cloud Build] WARNING: Binary seems too small, may be corrupted"
      echo "failed" > /workspace/build_status_linux
      echo "Linux binary file is too small ($linux_size bytes) - likely corrupted" > /workspace/linux_error
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
