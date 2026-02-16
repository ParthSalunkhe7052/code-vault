# CodeVault Build Test Scripts

## Node.js Build Tester (`test_nodejs_build.py`)

Autonomous testing script for Node.js cloud builds.

### Prerequisites

1. **GCP Credentials**: Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable or use `--credentials` flag
2. **Python packages**: `google-cloud-storage`, `google-cloud-build`

### Setup

```powershell
# Set GCP credentials
$env:GOOGLE_APPLICATION_CREDENTIALS = "path/to/your/service-account.json"

# Install dependencies
pip install google-cloud-storage google-cloud-build
```

### Usage

```powershell
# Run all tests
python scripts/test_nodejs_build.py --all

# Run specific test
python scripts/test_nodejs_build.py --test simple_console

# Run quick tests (skip full suite)
python scripts/test_nodejs_build.py --quick

# With explicit credentials
python scripts/test_nodejs_build.py --credentials path/to/creds.json --all
```

### Test Cases

| Test | Description |
|------|-------------|
| `simple_console` | Basic console.log output |
| `fs_operations` | File system read/write/delete |
| `modules_test` | Built-in Node.js modules |
| `async_code` | Async/await operations |
| `full_suite` | Complete test suite |

### Output

```
============================================================
#  CODEVAULT NODE.JS BUILD TEST SUITE
#  Run ID: test_20260215_143052
============================================================

============================================================
TEST: Simple Console Output
============================================================

Step 1: Creating source files
[OK] Created: C:\Temp\nodejs_test_xxx\...

Step 2: Uploading to GCS
[INFO] Uploading source to gs://codevault-builds/...

Step 3: Triggering Cloud Build
[OK] Build started: xxx-xxx-xxx

Step 4: Waiting for build
  [10s] Status: WORKING
  [20s] Status: WORKING
  [30s] Status: SUCCESS

Step 5: Downloading artifact
[OK] Downloaded: test.exe (xxx bytes)

Step 6: Running EXE
[INFO] Running EXE: ...

Step 7: Validating output
  ✓ Found: 'Hello from CodeVault!'
  ✓ Found: 'Test PASSED'
  ✓ Exit code: 0

============================================================
TEST PASSED: Simple Console Output
============================================================
```

### Quick Start (Windows)

```powershell
# Just double-click run_test.bat or:
scripts\run_test.bat --quick
```
