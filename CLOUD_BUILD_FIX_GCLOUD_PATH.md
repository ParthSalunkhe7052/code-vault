# Cloud Build Fix - gcloud Path Issue

## Problem
```
Failed to trigger Cloud Build: Cloud Build error: [WinError 2] The system cannot find the file specified
```

## Root Cause
The `subprocess.run()` calls in `cloud_build_cli_wrapper.py` were using `"gcloud"` as a string, which Windows couldn't find because:
1. gcloud is installed as `gcloud.cmd` on Windows
2. The full path is: `C:\Users\parth\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`
3. This path may not be in the subprocess environment PATH

## Fix Applied ✅

### Updated `cloud_build_cli_wrapper.py`

#### Added gcloud path detection:
```python
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
    
    return "gcloud"  # Fallback
```

#### Updated all subprocess calls:
```python
# Before (3 places):
cmd = ["gcloud", "builds", "submit", ...]
subprocess.run(cmd, ...)

# After:
cmd = [self.gcloud_cmd, "builds", "submit", ...]
subprocess.run(cmd, ..., shell=True)  # Added shell=True for Windows .cmd files
```

## Verification ✅

```bash
python -c "from cloud_build_cli_wrapper import CloudBuildClient; client = CloudBuildClient(); print(client.gcloud_cmd)"
# Output: C:\Users\parth\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.CMD

python -c "from cloud_build_cli_wrapper import CloudBuildClient; import subprocess; client = CloudBuildClient(); result = subprocess.run([client.gcloud_cmd, 'version'], capture_output=True, text=True, shell=True); print(result.stdout)"
# Output: Google Cloud SDK 555.0.0 ...
```

## Next Steps

### 1. Restart Backend Server
**In your terminal running uvicorn:**
- Press `CTRL+C` to stop
- Run again: `uvicorn main:app --reload`

**Expected output:**
```
[Config] Loaded environment from: ...
[Storage] Connected to Cloudflare R2: license-builds
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Retry Build
- Go to frontend: http://localhost:5173
- Navigate to your project
- Click "Build" again

**Expected backend logs:**
```
[CloudBuild] Using ngrok tunnel: https://dinorah-screwed-collette.ngrok-free.dev
[CloudBuild] Triggering Cloud Build for bld_xxx
[CloudBuild] Successfully triggered build bld_xxx -> GCP Build abc-def-123
```

**Should NOT see:**
```
❌ Failed to trigger Cloud Build: Cloud Build error: [WinError 2]
```

### 3. Monitor Build
Open GCP Console:
https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309

**You should see:**
- New build with status "QUEUED" or "WORKING"
- Build steps executing in real-time
- Estimated time: 3-5 minutes

### 4. Verify Webhooks
Check ngrok dashboard:
http://127.0.0.1:4040

**Expected:**
- POST requests to `/api/v1/cloud-build/webhook`
- Status: 200 OK
- One webhook per platform (Windows, Linux, etc.)

## Technical Details

### Why shell=True?
On Windows, `.cmd` files are not executables. They need to be run through `cmd.exe`, which is what `shell=True` does.

### Why shutil.which()?
`shutil.which()` searches the system PATH and returns the full path to the executable, handling Windows `.cmd` files automatically.

### Platform Detection
The code detects Windows via `sys.platform == "win32"` and adjusts behavior accordingly. On Linux/macOS, it would use the standard `gcloud` binary.

## Files Modified

- `cloud_build_cli_wrapper.py` (lines 1-47, 103-104, 147-148, 168-169)
  - Added `_find_gcloud()` method
  - Changed all `"gcloud"` → `self.gcloud_cmd`
  - Added `shell=True` to subprocess.run()

## Rollback

If issues persist:
```bash
git diff cloud_build_cli_wrapper.py
git checkout cloud_build_cli_wrapper.py  # Revert if needed
```

---

**Status**: Fixed ✅  
**Ready to Test**: Yes  
**Last Updated**: Feb 4, 2026 (after first build attempt)
