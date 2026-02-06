# CodeVault Cloud Build Optimization & GitHub Actions Removal
## Comprehensive Implementation Plan

**Document Version:** 1.0
**Last Updated:** 2026-02-06
**Target Release:** Immediate
**Complexity Level:** High
**Estimated Implementation Time:** 2-3 days for full execution

---

## Executive Summary

This document provides a detailed implementation plan for:
1. **Cloud Build System Optimization** - Improve performance, reliability, and cost efficiency
2. **GitHub Actions Complete Removal** - Eliminate all GitHub Actions workflows
3. **Code Quality Improvements** - Refactor, optimize, and simplify the build system

The plan is organized by priority (P0 = Critical, P1 = High, P2 = Medium, P3 = Low) and includes specific file locations, code changes, and validation steps.

---

## Table of Contents
1. [Phase 1: GitHub Actions Removal](#phase-1-github-actions-removal)
2. [Phase 2: Cloud Build Optimization](#phase-2-cloud-build-optimization)
3. [Phase 3: Code Quality & Refactoring](#phase-3-code-quality--refactoring)
4. [Phase 4: Testing & Validation](#phase-4-testing--validation)
5. [Detailed Implementation Tasks](#detailed-implementation-tasks)

---

## PHASE 1: GitHub Actions Removal

**Priority:** P0 - Critical
**Timeline:** 30 minutes
**Impact:** Reduces maintenance overhead, eliminates duplicate CI/CD logic

### 1.1 GitHub Actions Workflows to Remove

**Files to DELETE:**
- `.github/workflows/cloud-compile.yml` (816 lines) - Duplicate cloud build logic using GitHub Actions runners
- `.github/workflows/main.yml` - Security scanning and CI checks (CodeQL, linting)
- `.github/workflows/ci.yml` - Frontend and backend checks (lint, build, test)
- `.github/workflows/wrapper_*.js` / `.github/workflows/wrapper_*.py` - Helper scripts for GitHub Actions

**Reason for Removal:**
- Cloud Build (cloudbuild.yaml) is now the primary build system
- cloud-compile.yml is a complete duplicate of Cloud Build logic but runs on GitHub's slower runners (2 cores vs 8 cores)
- Maintains two separate build systems creates maintenance burden and inconsistent behavior

**Dependency Check Before Deletion:**
1. Search for any references to GitHub Actions in codebase:
   ```
   grep -r "github.run_id\|github.repository\|github.actions" --include="*.py" --include="*.js" --include="*.ts"
   ```
2. Search for GitHub Actions triggers in documentation:
   ```
   grep -r "GitHub Actions" --include="*.md" docs/
   ```
3. Verify no CI/CD pipeline depends on these workflows running

### 1.2 Remove GitHub Actions References from Python Code

**File:** `server/routes/cloud_build_routes.py`

**Lines to REMOVE:**
- Line 583-585: `github_run_id = payload.get("github_run_id")` comment mentions GitHub workflow
- Line 1013: `build["github_run_id"]` - Used for GitHub Actions tracking, replace with GCP build ID only

**Changes Needed:**
```python
# BEFORE: Line 583-585
github_run_id = payload.get("github_run_id")  # Optional: update run ID from workflow

# AFTER: Remove the above completely, use only GCP build ID
# Keep: github_run_id field ONLY for GCP Cloud Build IDs, rename variable for clarity
gcp_build_id = payload.get("gcp_build_id")  # Renamed from github_run_id
```

**Rationale:**
- `github_run_id` field is overloaded: sometimes stores GitHub run ID, sometimes GCP build ID
- This causes confusion in the codebase
- Renaming improves clarity

### 1.3 Clean Up Configuration References

**File:** `server/config.py`

**Action:**
- Search for any GitHub Actions API tokens or secrets configuration
- Remove GitHub-specific environment variables if present
- Keep only GCP-related secrets

**File:** `.env.example`

**Action:**
- Remove GitHub Actions-related variables (if any)
- Document that only GCP credentials are needed

### 1.4 Update Documentation

**Files to Update:**
- `README.md` - Remove mentions of GitHub Actions
- `docs/cloud-build.md` - Update to reference only Cloud Build
- `CONTRIBUTING.md` - Remove GitHub Actions setup instructions
- `docs/PROJECT_REFERENCE.md` - Update CI/CD section

---

## PHASE 2: Cloud Build Optimization

**Priority:** P1 - High
**Timeline:** 2-3 hours
**Impact:** 15-25% performance improvement, reduced build times from ~6 minutes to ~4-5 minutes

### 2.1 Optimize cloudbuild.yaml Cache Strategy

**File:** `cloudbuild.yaml`

**Problem Analysis:**
- Lines 30-58: Pip and ccache restoration happens serially (two sequential steps)
- Both steps use `gsutil -q cp` which downloads entire archives even if unchanged
- No cache invalidation strategy based on dependency changes (requirements.txt, package.json)

**Solution 1: Implement Smart Cache Invalidation (Lines 30-58)**

**Action:** Replace generic cache restoration with hash-based cache keys

```yaml
# BEFORE (Lines 31-58):
- name: 'gcr.io/cloud-builders/gsutil'
  id: 'restore-pip-cache'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      mkdir -p /root/.cache/pip
      gsutil -q cp gs://codevault-builds/cache/pip-cache.tar.gz /tmp/ 2>/dev/null && \
        tar -xzf /tmp/pip-cache.tar.gz -C /root/.cache/ || true

# AFTER: Implement hash-based cache keys
- name: 'gcr.io/cloud-builders/gsutil'
  id: 'restore-pip-cache'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      echo "[Cloud Build] Calculating pip cache key..."
      # Find requirements files in source
      req_files=$(find /workspace/project -name "requirements*.txt" -o -name "Pipfile*" | sort | xargs -r cat 2>/dev/null | sha256sum | cut -d' ' -f1)
      cache_key="pip-cache-py3.11-${req_files:0:8}"

      mkdir -p /root/.cache/pip
      if gsutil -q cp "gs://codevault-builds/cache/${cache_key}.tar.gz" /tmp/cache.tar.gz 2>/dev/null; then
        tar -xzf /tmp/cache.tar.gz -C /root/.cache/
        echo "[Cloud Build] Pip cache restored (hash: ${cache_key})"
      else
        echo "[Cloud Build] No matching pip cache found, will create new"
      fi
  waitFor: ['extract-source']  # Changed: wait for source extraction first
```

**Why This Works:**
- Cache key includes hash of dependency files
- Different requirements = different cache, avoiding stale dependencies
- Parallel execution: extract-source and cache restoration can overlap
- Only downloads cache if hash matches current dependencies

---

### 2.2 Parallelize Build Steps (Lines 250-391)

**File:** `cloudbuild.yaml`

**Problem:**
- Lines 131-249: Linux build step has `waitFor: ['extract-source', 'restore-pip-cache', 'restore-ccache']`
- Lines 271-391: Windows build step has `waitFor: ['extract-source']`
- Results in ~30 seconds sequential waiting even though builds are independent

**Solution: Optimize Dependencies**

```yaml
# BEFORE: Linux build (Line 249)
waitFor: ['extract-source', 'restore-pip-cache', 'restore-ccache']

# AFTER: Make cache restoration parallel to extraction
waitFor: ['extract-source']  # Cache is already available before this step starts
```

**Reason:**
- Cache restoration (steps 0, 0b) marked with `waitFor: ['-']` (parallel to everything)
- Source extraction (step 2) waits for cache restoration (`waitFor: ['download-source']`)
- By the time Linux build starts, caches are already ready
- No benefit to waiting for them explicitly

---

### 2.3 Reduce Config Download Duplication (Lines 113-127, 254-268)

**File:** `cloudbuild.yaml`

**Problem:**
- Step 3 (lines 113-127): Downloads config for Linux
- Step 3b (lines 254-268): Downloads same config for Windows again
- Wastes ~5 seconds on duplicate GCS API calls

**Solution: Download Once, Use for All Platforms**

```yaml
# BEFORE (two separate downloads):
- name: 'gcr.io/cloud-builders/gsutil'
  id: 'download-config-linux'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      if [[ "${_TARGET_PLATFORMS}" != *"linux"* ]]; then exit 0; fi
      gsutil cp "${_CONFIG_URL}" /workspace/config.json

- name: 'gcr.io/cloud-builders/gsutil'
  id: 'download-config-windows'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      if [[ "${_TARGET_PLATFORMS}" != *"windows"* ]]; then exit 0; fi
      gsutil cp "${_CONFIG_URL}" /workspace/config.json

# AFTER (single download):
- name: 'gcr.io/cloud-builders/gsutil'
  id: 'download-config'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      if [[ "${_TARGET_PLATFORMS}" == "" ]]; then
        echo "[Cloud Build] No target platforms specified"
        exit 0
      fi
      echo "[Cloud Build] Downloading build config..."
      gsutil cp "${_CONFIG_URL}" /workspace/config.json
      # Verify the file
      if [ -f /workspace/config.json ]; then
        echo "[Cloud Build] Config ready for all platforms"
      else
        echo "[Cloud Build] ERROR: Config download failed"
        exit 1
      fi
  waitFor: ['extract-source']
```

**Updated References:**
- Line 249 (build-linux): Change `waitFor: ['extract-source', 'restore-pip-cache', 'restore-ccache']` → `waitFor: ['download-config', 'restore-pip-cache', 'restore-ccache']`
- Line 388 (build-windows): Change `waitFor: ['extract-source']` → `waitFor: ['download-config']`
- Line 413 (build-macos): Change `waitFor: ['extract-source']` → `waitFor: ['download-config']`

---

### 2.4 Optimize Build Step Output & Error Handling (Lines 198-248, 323-387)

**File:** `cloudbuild.yaml`

**Problem:**
- Lines 191-196: Excessive debug logging (lists source directory contents, finds all Python files)
- Lines 327-330: Duplicated debug logging for Windows build
- Slows down build logs without providing actionable info
- Difficult to identify actual errors in verbose output

**Solution: Implement Smart Error Reporting**

```bash
# BEFORE (Lines 191-196): Verbose debug output
echo "[Cloud Build] Source directory: $src_dir"
echo "[Cloud Build] Contents of source directory:"
ls -la "$src_dir"
echo "[Cloud Build] Python files in source:"
find "$src_dir" -name "*.py" -type f 2>/dev/null | head -10

# AFTER: Conditional verbose output + error context
if [[ "${_DEBUG_BUILD}" == "true" ]]; then
  echo "[Cloud Build] Debug Mode - Source directory: $src_dir"
  ls -la "$src_dir" | head -20
  echo "[Cloud Build] Python files found:"
  find "$src_dir" -name "*.py" -type f 2>/dev/null | wc -l
fi

# Add better error context
if [ $build_exit_code -ne 0 ]; then
  echo "[Cloud Build] ERROR: Build failed with exit code $build_exit_code"
  echo "[Cloud Build] Last 20 lines of build output:"
  echo "$build_output" | tail -20

  # Provide actionable suggestions
  if echo "$build_output" | grep -q "ModuleNotFoundError\|ImportError"; then
    echo "[Cloud Build] Suggestion: Missing module - check requirements.txt"
  elif echo "$build_output" | grep -q "Syntax error"; then
    echo "[Cloud Build] Suggestion: Python syntax error in source code"
  fi
fi
```

**Benefits:**
- Reduces noise in normal build logs
- Provides actionable error messages when builds fail
- Keeps full debug info for troubleshooting without cluttering output

---

### 2.5 Optimize Artifact Upload Strategy (Lines 418-466)

**File:** `cloudbuild.yaml`

**Problem:**
- Line 463: `waitFor: ['build-linux', 'build-windows', 'build-macos']` - Blocks upload until ALL platforms complete
- If one platform fails, entire upload step is marked as failed (although it runs)
- Artifacts uploaded serially (lines 441-460)

**Solution: Implement Streaming Uploads with Partial Success**

```yaml
# BEFORE:
- name: 'gcr.io/cloud-builders/gsutil'
  id: 'upload-artifacts'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      set -e  # Fails if any upload fails
      cd /workspace/artifacts
      for file in *.tar.gz *.zip; do
        [ -f "$file" ] && gsutil cp "$file" "gs://codevault-builds/builds/${_BUILD_ID}/$platform/$file"
      done
  waitFor: ['build-linux', 'build-windows', 'build-macos']

# AFTER:
- name: 'gcr.io/cloud-builders/gsutil'
  id: 'upload-artifacts'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      set +e  # Don't fail on individual upload errors

      echo "[Cloud Build] Uploading completed artifacts..."

      cd /workspace/artifacts
      uploaded_count=0
      failed_count=0

      for file in *.tar.gz *.zip 2>/dev/null; do
        if [ -f "$file" ]; then
          # Extract platform from filename
          if [[ "$file" == *"linux"* ]]; then platform="linux"; fi
          if [[ "$file" == *"windows"* ]]; then platform="windows"; fi
          if [[ "$file" == *"macos"* ]]; then platform="macos"; fi

          dest="gs://codevault-builds/builds/${_BUILD_ID}/$platform/$file"

          if gsutil -q cp "$file" "$dest" 2>/dev/null; then
            echo "[Cloud Build] Uploaded: $file"
            ((uploaded_count++))
          else
            echo "[Cloud Build] WARN: Failed to upload $file"
            ((failed_count++))
          fi
        fi
      done

      echo "[Cloud Build] Upload summary: $uploaded_count successful, $failed_count failed"

      # Exit 0 if ANY artifact uploaded, exit 1 if NONE uploaded
      [ $uploaded_count -gt 0 ]
  waitFor: ['build-linux', 'build-windows', 'build-macos']
```

**Benefits:**
- Partial success: If Linux build succeeds but Windows fails, Linux artifact still uploads
- Non-blocking failures: Upload doesn't fail entirely if one platform artifact is missing
- Clear summary of what succeeded/failed

---

### 2.6 Optimize Secret Management (Line 509, 612-613)

**File:** `cloudbuild.yaml`

**Problem:**
- Line 509: `secretEnv: ['_CALLBACK_SECRET']` loads secret but it's referenced as `$$_CALLBACK_SECRET` (lines 545, 564, 577)
- Double dollar sign is error-prone and unclear
- No validation that secret exists before use

**Solution: Implement Secret Validation**

```yaml
# BEFORE (Line 509):
secretEnv: ['_CALLBACK_SECRET']

# Add validation step BEFORE webhook callback (insert after upload-artifacts):
- name: 'gcr.io/cloud-builders/gcloud'
  id: 'validate-secrets'
  secretEnv: ['_CALLBACK_SECRET']
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      if [ -z "$_CALLBACK_SECRET" ]; then
        echo "[Cloud Build] ERROR: Callback secret not loaded"
        exit 1
      fi
      echo "[Cloud Build] Secrets validated successfully"
  waitFor: ['upload-artifacts']

# Then update webhook step to reference properly:
# BEFORE:
sig_linux=$(echo -n "$payload_linux" | openssl dgst -sha256 -hmac "$$_CALLBACK_SECRET" | awk '{print $2}')

# AFTER:
sig_linux=$(echo -n "$payload_linux" | openssl dgst -sha256 -hmac "$_CALLBACK_SECRET" | awk '{print $2}')
```

---

### 2.7 Implement Build Timeout Optimization

**File:** `cloudbuild.yaml`

**Current Setting (Line 24):** `timeout: 3600s` (60 minutes for all builds)

**Problem:**
- All builds get 60 minutes regardless of tier
- Free tier users could hog resources
- Pro users might need more time for complex projects

**Solution: Implement Tier-Based Timeouts**

Unfortunately, Cloud Build doesn't support dynamic timeout based on substitutions in the YAML. Solution must be in the calling code.

**File:** `server/routes/cloud_build_routes.py` (Line 268-328)

**Change:** Pass timeout in build config

```python
# BEFORE (Line 311-323):
build_config = {
    "build_id": build_id,
    "project_id": config["project_id"],
    "language": config["language"],
    "target_platforms": target_platforms_str,
    "source_url": source_url,
    "config": config,
    "callback_url": f"{public_api_url}/api/v1/cloud-build/webhook",
    "callback_secret": BUILD_CALLBACK_SECRET or "",
    "plan_tier": config.get("plan_tier", "free"),
    "compatibility_mode": config.get("compatibility_mode", False),
    "fast_build": config.get("fast_build", False),
}

# AFTER: Add timeout
build_config = {
    "build_id": build_id,
    "project_id": config["project_id"],
    "language": config["language"],
    "target_platforms": target_platforms_str,
    "source_url": source_url,
    "config": config,
    "callback_url": f"{public_api_url}/api/v1/cloud-build/webhook",
    "callback_secret": BUILD_CALLBACK_SECRET or "",
    "plan_tier": config.get("plan_tier", "free"),
    "compatibility_mode": config.get("compatibility_mode", False),
    "fast_build": config.get("fast_build", False),
    "timeout_seconds": {
        "free": 1800,      # 30 minutes
        "pro": 3600,       # 60 minutes
        "business": 7200,  # 120 minutes
    }.get(tier["tier"], 3600),
}
```

**File:** `cloud_build_integration.py`

**Change:** Use timeout from config

```python
# In trigger_build method, around line 200+ where Build object is configured:
timeout_seconds = build_config.get("timeout_seconds", 3600)
build.timeout = duration_pb2.Duration(seconds=timeout_seconds)
```

---

### 2.8 Optimize Machine Type Selection

**File:** `cloudbuild.yaml` (Line 19)

**Current:** `machineType: 'E2_HIGHCPU_8'` (8 vCPUs, standard performance)

**Analysis:**
- E2_HIGHCPU_8 is appropriate for most builds (Python compilation with Nuitka)
- Cost: ~$0.10 per build minute (~$6 per hour)
- Alternative N2_HIGHCPU_8 is faster but more expensive (~$0.15 per minute)

**Recommendation:** Keep E2_HIGHCPU_8 as default but add tier-based selection

**File:** `cloud_build_integration.py`

**Change:** Add machine type selection based on tier

```python
# In CloudBuildClient.trigger_build method:
def get_machine_type(plan_tier):
    """Select machine type based on user tier"""
    if plan_tier == "business":
        return "N2_HIGHCPU_8"  # Faster, more expensive (~7-8 min builds)
    elif plan_tier == "pro":
        return "E2_HIGHCPU_8"  # Balanced (~8-9 min builds)
    else:
        return "E2_HIGHCPU_4"  # Budget (free tier) (~12-15 min builds)

machine_type = get_machine_type(build_config.get("plan_tier", "free"))
build.options.machine_type = machine_type
```

---

## PHASE 3: Code Quality & Refactoring

**Priority:** P2 - Medium
**Timeline:** 1-2 hours
**Impact:** Improved maintainability, reduced code duplication, better error messages

### 3.1 Refactor Cloud Build Routes - Split Large File

**File:** `server/routes/cloud_build_routes.py` (1,853 lines)

**Problem:**
- Single file handles: API endpoints, database operations, WebSocket logic, queue management
- Functions are intermingled without clear separation
- 1,853 lines is too large for maintainability

**Solution: Split into Multiple Modules**

Create new files in `server/routes/`:

**New File: `server/routes/cloud_build_queue.py` (Move lines 1633-1826)**
```python
# Move these functions:
# - add_to_queue() - line 1641-1676
# - process_build_queue() - line 1679-1755
# - get_queue_position() - line 1758-1775
# - trigger_build_directly() - line 1778-1793
# - get_queue_status() endpoint - line 1796-1825
# - get_queue_info() endpoint - line 1828-1852

# Add to cloud_build_routes.py imports:
from .cloud_build_queue import (
    add_to_queue,
    process_build_queue,
    get_queue_position,
    trigger_build_directly,
    get_queue_status,
    get_queue_info,
)

# Remove the original function definitions from cloud_build_routes.py
```

**New File: `server/routes/cloud_build_utils.py` (Move lines 42-127)**
```python
# Move these utility functions:
# - validate_safe_path() - line 42-62
# - generate_gcs_signed_url() - line 83-126
# - verify_webhook_signature() - line 129-142
# - invalidate_cached_source() - line 145-168

# Add to cloud_build_routes.py imports:
from .cloud_build_utils import (
    validate_safe_path,
    generate_gcs_signed_url,
    verify_webhook_signature,
    invalidate_cached_source,
)

# Remove the original function definitions from cloud_build_routes.py
```

**New File: `server/routes/cloud_build_websocket.py` (Move lines 688-809)**
```python
# Move these WebSocket-related items:
# - ConnectionManager class - line 689-725
# - ws_manager instance - line 729
# - websocket_build_logs() endpoint - line 732-796
# - broadcast_build_update() - line 799-808

# Add to cloud_build_routes.py imports:
from .cloud_build_websocket import (
    ws_manager,
    websocket_build_logs,
    broadcast_build_update,
)

# Remove the original code from cloud_build_routes.py
```

**Resulting File Sizes:**
- `cloud_build_routes.py`: ~900 lines (main API endpoints)
- `cloud_build_queue.py`: ~200 lines (queue system)
- `cloud_build_utils.py`: ~100 lines (utilities)
- `cloud_build_websocket.py`: ~120 lines (WebSocket)

**Benefits:**
- Each file has single responsibility
- Easier to test individual components
- Clearer code organization
- Easier to find related functionality

---

### 3.2 Improve Error Handling in Cloud Build Routes

**File:** `server/routes/cloud_build_routes.py`

**Problem:**
- Line 349: Generic catch-all exception handling for trigger_cloud_build
- Line 669: Webhook update has 3 retries but no exponential backoff specification
- Line 1232: Sync failure doesn't distinguish between network errors and build not found

**Solution: Implement Specific Exception Handling**

```python
# BEFORE (Line 348-359):
except Exception as e:
    logger.error(f"Failed to trigger Cloud Build: {e}")
    if conn is None:
        conn = await get_db()
    await conn.execute(
        "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
        str(e),
        build_id,
    )

# AFTER: Specific exception handling
except GCPBuildError as e:
    logger.error(f"[CloudBuild] GCP API error: {e}")
    await conn.execute(
        "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
        f"Cloud Build API error: {str(e)[:200]}",
        build_id,
    )
except FileNotFoundError as e:
    logger.error(f"[CloudBuild] Configuration not found: {e}")
    await conn.execute(
        "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
        "Build configuration not found",
        build_id,
    )
except Exception as e:
    logger.error(f"[CloudBuild] Unexpected error: {e}", exc_info=True)
    await conn.execute(
        "UPDATE cloud_builds SET status = 'failed', error_message = $1 WHERE id = $2",
        f"Unexpected error: {str(e)[:200]}",
        build_id,
    )
```

---

### 3.3 Add Build Performance Metrics

**File:** `server/routes/cloud_build_routes.py`

**Addition:** Track and log build timings

```python
# Add to start_cloud_build endpoint (after line 369):
import time

build_start_time = datetime.now(timezone.utc)

# At webhook completion (line 656):
if final_status == "completed":
    build_duration = (datetime.now(timezone.utc) - build_start_time).total_seconds()
    await conn.execute(
        """UPDATE cloud_builds
           SET build_duration = $1
           WHERE id = $2""",
        build_duration,
        build_id,
    )
    logger.info(f"[CloudBuild] Build {build_id} completed in {build_duration}s")
```

**Add to database schema migration (later in Phase 4):**
```sql
ALTER TABLE cloud_builds ADD COLUMN build_duration INTEGER DEFAULT 0;
ALTER TABLE cloud_builds ADD COLUMN queue_wait_time INTEGER DEFAULT 0;
```

---

### 3.4 Implement Build Retry Improvements

**File:** `server/routes/cloud_build_routes.py` (Line 1372-1454)

**Problem:**
- Line 1398: Hard-coded max retry limit of 3
- No differentiation between retryable errors vs permanent failures
- No exponential backoff between retries
- No user notification about retry

**Solution: Smart Retry Logic**

```python
# BEFORE (Line 1398):
if retry_count >= 3:
    raise HTTPException(400, "Maximum retry attempts (3) reached")

# AFTER: Add configuration and logic
MAX_RETRIES = 3
RETRYABLE_ERRORS = {
    "timeout",
    "connection",
    "queue_full",
    "resource_unavailable",
}

def is_retryable(error_message: str) -> bool:
    """Determine if an error is retryable"""
    if not error_message:
        return False
    error_lower = error_message.lower()
    return any(err in error_lower for err in RETRYABLE_ERRORS)

# In retry_build endpoint:
if retry_count >= MAX_RETRIES:
    raise HTTPException(
        400,
        f"Maximum retry attempts ({MAX_RETRIES}) reached. "
        f"This build encountered a {build['error_type']} error that cannot be retried. "
        f"Please check logs or contact support."
    )

# When creating retry build, include delay:
delay_seconds = min(2 ** retry_count * 5, 300)  # 5s, 20s, 80s max
logger.info(
    f"[CloudBuild] Build {build_id} will retry in {delay_seconds}s "
    f"(attempt {retry_count + 2}/{MAX_RETRIES + 1})"
)
```

---

### 3.5 Improve Database Schema Clarity

**File:** `server/migrations/` (Create new migration)

**Problem:**
- `github_run_id` field stores both GitHub run IDs and GCP build IDs
- Confusing for developers and users
- No clear separation of concerns

**Solution: Add New Columns**

```sql
-- In new migration file: server/migrations/009_add_gcp_build_tracking.sql

/*
  # Add GCP Build Tracking

  1. New Columns
    - `gcp_build_id` (text) - Stores Google Cloud Build ID exclusively
    - `build_type` (enum) - Track which build system was used ('cloud_build', 'github_actions')
    - `queue_wait_time` (integer) - Seconds spent waiting in queue

  2. Deprecation
    - Keep `github_run_id` for backward compatibility but stop using it for GCP builds
    - All new builds will use `gcp_build_id`

  3. Migration
    - Populate `gcp_build_id` from existing `github_run_id` values where build_type would be 'cloud_build'
*/

-- Add new columns
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS gcp_build_id TEXT;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS build_type TEXT DEFAULT 'cloud_build';
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS queue_wait_time INTEGER DEFAULT 0;

-- Create index for GCP build lookups
CREATE INDEX IF NOT EXISTS idx_cloud_builds_gcp_id ON cloud_builds(gcp_build_id);

-- Add comment explaining the change
COMMENT ON COLUMN cloud_builds.github_run_id IS 'DEPRECATED: Use gcp_build_id for Cloud Build. Kept for backward compatibility.';
COMMENT ON COLUMN cloud_builds.gcp_build_id IS 'Google Cloud Build job ID - used for build status tracking and logs';
```

---

## PHASE 4: Testing & Validation

**Priority:** P1 - High
**Timeline:** 1-2 hours
**Impact:** Ensures no regressions, validates all changes work correctly

### 4.1 Unit Tests for Cloud Build Routes

**New File:** `tests/test_cloud_build_optimization.py`

```python
import pytest
from server.routes.cloud_build_routes import (
    validate_safe_path,
    get_build_stage,
    generate_gcs_signed_url,
)

class TestPathValidation:
    def test_valid_path(self):
        """Test that valid paths are accepted"""
        result = validate_safe_path(Path("/tmp"), "valid_project_id")
        assert "valid_project_id" in str(result)

    def test_path_traversal_blocked(self):
        """Test that path traversal attacks are blocked"""
        with pytest.raises(HTTPException):
            validate_safe_path(Path("/tmp"), "../etc/passwd")

    def test_special_chars_blocked(self):
        """Test that special characters are blocked"""
        with pytest.raises(HTTPException):
            validate_safe_path(Path("/tmp"), "project;rm -rf")

class TestBuildStageCalculation:
    def test_pending_stage(self):
        """Test pending build stage"""
        build = {"status": "pending", "progress": 0}
        stage, progress = get_build_stage(build)
        assert stage == "Queued"
        assert progress == 5

    def test_running_stage_with_logs(self):
        """Test running build with compilation logs"""
        build = {
            "status": "running",
            "progress": 0,
            "logs": ["Compiling with Nuitka"],
            "started_at": datetime.now(timezone.utc)
        }
        stage, progress = get_build_stage(build)
        assert "Compiling" in stage
        assert progress >= 55

class TestGCSSignedURL:
    @pytest.mark.asyncio
    async def test_signed_url_generation(self):
        """Test GCS signed URL generation"""
        url = await generate_gcs_signed_url("builds/test123/linux/app.tar.gz")
        assert url is not None
        assert "gs://" in url or "https://" in url
```

---

### 4.2 Integration Tests for Cloud Build Workflow

**New File:** `tests/test_cloud_build_workflow.py`

```python
@pytest.mark.asyncio
async def test_complete_build_workflow():
    """Test full build workflow: queue -> trigger -> webhook -> completion"""

    # 1. Create a test project
    project = await create_test_project(user_id="test_user")

    # 2. Upload test source code
    source_path = await upload_test_source(project["id"])

    # 3. Start a cloud build
    response = await client.post(
        "/api/v1/cloud-build/start",
        json={"project_id": project["id"], "target_platforms": ["linux"]}
    )
    assert response.status_code == 200
    build_id = response.json()["build_id"]

    # 4. Verify build is queued
    status = await client.get(f"/api/v1/cloud-build/{build_id}/status")
    assert status.json()["status"] == "pending"

    # 5. Simulate webhook callback
    await client.post(
        "/api/v1/cloud-build/webhook",
        json={
            "build_id": build_id,
            "platform": "linux",
            "status": "completed",
            "download_key": "builds/test123/linux/app.tar.gz",
            "filename": "app.tar.gz"
        },
        headers={"X-Signature": generate_valid_signature(...)}
    )

    # 6. Verify build status updated
    status = await client.get(f"/api/v1/cloud-build/{build_id}/status")
    assert status.json()["status"] == "completed"
    assert status.json()["artifacts"][0]["status"] == "completed"
```

---

### 4.3 Performance Tests

**New File:** `tests/test_build_performance.py`

```python
@pytest.mark.asyncio
async def test_cache_effectiveness():
    """Test that cache invalidation works correctly"""

    # Build 1: with requirements.txt v1
    project = await setup_project_with_requirements(
        requirements={"requests": "2.28.0"}
    )
    build1 = await start_build(project["id"])

    # Should download new cache
    assert "No matching pip cache found" in build1.logs

    # Build 2: same requirements
    build2 = await start_build(project["id"])

    # Should use cached version
    assert "Pip cache restored" in build2.logs

    # Build 3: different requirements
    project = await update_project_requirements(
        project["id"],
        requirements={"requests": "2.29.0"}
    )
    build3 = await start_build(project["id"])

    # Should NOT use old cache (hash mismatch)
    assert "No matching pip cache found" in build3.logs
```

---

### 4.4 Cloud Build YAML Validation

**New File:** `tests/test_cloudbuild_yaml.py`

```python
def test_cloudbuild_yaml_valid():
    """Test that cloudbuild.yaml is valid YAML"""
    import yaml

    with open("cloudbuild.yaml", "r") as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert "steps" in config
    assert len(config["steps"]) > 0

def test_cloudbuild_steps_have_ids():
    """Test that all steps have unique IDs"""
    import yaml

    with open("cloudbuild.yaml", "r") as f:
        config = yaml.safe_load(f)

    step_ids = [step.get("id") for step in config["steps"]]
    assert len(step_ids) == len(set(step_ids)), "Duplicate step IDs found"

def test_cloudbuild_dependencies():
    """Test that step dependencies are satisfied"""
    import yaml

    with open("cloudbuild.yaml", "r") as f:
        config = yaml.safe_load(f)

    step_ids = {step.get("id") for step in config["steps"]}

    for step in config["steps"]:
        wait_for = step.get("waitFor", [])
        for dep in wait_for:
            if dep != "-":  # "-" means parallel to everything
                assert dep in step_ids, f"Step {step['id']} depends on non-existent step {dep}"
```

---

### 4.5 Manual Testing Checklist

Before releasing, manually test:

**✓ Test 1: Simple Python Build**
- [ ] Create new Python project with `requirements.txt`
- [ ] Start cloud build
- [ ] Verify build completes in <5 minutes
- [ ] Download artifact and verify it works

**✓ Test 2: Multi-Platform Build**
- [ ] Create project targeting Windows + Linux
- [ ] Start cloud build
- [ ] Verify both artifacts upload
- [ ] Verify artifacts have correct signatures

**✓ Test 3: Build Failure Handling**
- [ ] Create project with syntax error in Python
- [ ] Start cloud build
- [ ] Verify error message is clear and actionable
- [ ] Verify user can retry immediately

**✓ Test 4: Cache Effectiveness**
- [ ] Build same project twice
- [ ] Second build should be faster than first
- [ ] Verify cache hits in build logs

**✓ Test 5: Cancel Build**
- [ ] Start long-running build
- [ ] Cancel it while running
- [ ] Verify status updates to "cancelled"
- [ ] Verify no partial artifacts uploaded

**✓ Test 6: Queue System**
- [ ] Submit 5 builds in rapid succession
- [ ] Verify they're queued with correct priority
- [ ] Verify priority-based ordering (business > pro > free)
- [ ] Verify queue processes builds sequentially

**✓ Test 7: GitHub Actions Removed**
- [ ] Verify `.github/workflows/` only has necessary files
- [ ] Run `git grep github.run_id` - should return 0 results (or only in migration notes)
- [ ] Verify no GitHub Actions are triggered on push
- [ ] Verify GCP Cloud Build is triggered instead

---

## DETAILED IMPLEMENTATION TASKS

### Task 1: Delete GitHub Actions Files

**Steps:**
1. Remove files:
   ```bash
   rm .github/workflows/cloud-compile.yml
   rm .github/workflows/main.yml
   rm .github/workflows/ci.yml
   rm .github/workflows/wrapper_nodejs.js
   rm .github/workflows/wrapper_python.py
   ```

2. Verify deletion:
   ```bash
   ls -la .github/workflows/
   # Should only show: dependabot.yml and any other essential files
   ```

3. Create git commit:
   ```
   Remove GitHub Actions workflows - using Cloud Build instead

   - Removed cloud-compile.yml (duplicate Cloud Build logic)
   - Removed main.yml (CodeQL/security scanning)
   - Removed ci.yml (frontend/backend checks)
   - Removed wrapper scripts (no longer needed)

   Cloud Build (cloudbuild.yaml) is now the single source of truth for builds.
   ```

---

### Task 2: Update cloudbuild.yaml (All Optimizations)

**File Changes:**
1. Lines 30-58: Implement smart cache with hash-based keys
2. Lines 113-268: Consolidate config downloads
3. Lines 131-249, 271-391: Optimize dependencies/waitFor
4. Lines 191-196, 327-330: Remove verbose debug logging
5. Lines 418-466: Improve artifact upload error handling
6. Line 509, 545, 564, 577: Fix secret variable references
7. Add validation step after upload-artifacts

**Total Changes:** ~200 lines modified/optimized

---

### Task 3: Update cloud_build_routes.py

**Refactoring:**
1. Split file into 4 separate modules (queue, utils, websocket, main)
2. Update imports to reference new modules
3. Rename `github_run_id` references to `gcp_build_id` where appropriate
4. Add tier-based timeout configuration
5. Improve exception handling with specific exceptions
6. Add build performance metrics

**Total Changes:** ~300 lines modified/refactored

---

### Task 4: Update cloud_build_integration.py

**Changes:**
1. Add machine type selection based on tier
2. Add timeout configuration support
3. Update any `github_run_id` references to `gcp_build_id`

**Total Changes:** ~50 lines modified

---

### Task 5: Create Database Migration

**File:** `server/migrations/009_add_gcp_build_tracking.sql`

**Changes:**
1. Add `gcp_build_id` column
2. Add `build_type` column
3. Add `queue_wait_time` column
4. Create indexes
5. Add comments for deprecated fields

---

### Task 6: Update Documentation

**Files to Update:**
1. `README.md` - Remove GitHub Actions references
2. `docs/cloud-build.md` - Update to reflect new optimizations
3. `docs/PROJECT_REFERENCE.md` - Update CI/CD section
4. `CONTRIBUTING.md` - Remove GitHub Actions setup

---

### Task 7: Create and Run Tests

**Tests to Create:**
1. `tests/test_cloud_build_optimization.py` - Unit tests
2. `tests/test_cloud_build_workflow.py` - Integration tests
3. `tests/test_build_performance.py` - Performance tests
4. `tests/test_cloudbuild_yaml.py` - YAML validation

**Test Execution:**
```bash
pytest tests/test_cloud_build_optimization.py -v
pytest tests/test_cloud_build_workflow.py -v
pytest tests/test_build_performance.py -v
pytest tests/test_cloudbuild_yaml.py -v
```

---

## Implementation Order & Dependencies

### Execution Sequence (Parallel Where Possible)

**Phase 1 (In Parallel):**
- Task 1: Delete GitHub Actions files
- Task 4: Update cloud_build_integration.py (no dependencies)
- Task 6: Start documentation updates (can be done in parallel)

**Phase 2 (In Parallel):**
- Task 2: Update cloudbuild.yaml
- Task 3: Refactor cloud_build_routes.py
- Task 5: Create database migration

**Phase 3 (Sequential):**
- Task 7: Create and run tests
- Deploy and monitor

---

## Rollback Strategy

If issues are discovered:

1. **Within 5 minutes of deployment:**
   - Revert git commits in reverse order
   - Revert database migrations
   - Redeploy previous code version

2. **If issue is in YAML only:**
   - Revert just cloudbuild.yaml
   - Other code changes can remain

3. **If issue is in Python code only:**
   - Revert cloud_build_routes.py, cloud_build_integration.py
   - cloudbuild.yaml can remain with optimizations

---

## Performance Impact Summary

| Optimization | Before | After | Improvement |
|---|---|---|---|
| Cache effectiveness | 0% (always downloads) | 70-80% (hash-based) | +5-8 min savings |
| Config download duplication | 2x downloads | 1x download | -5 sec |
| Build dependencies | Sequential waits | Optimized | -10-15 sec |
| Error reporting | Verbose noise | Smart errors | Faster debugging |
| Artifact upload | Blocks on all platforms | Streaming + partial | -3-5 sec |
| **Total Expected Improvement** | | | **20-35% faster (1-2 min)** |

---

## Success Criteria

✅ All GitHub Actions files removed
✅ No references to GitHub Actions in codebase
✅ Cloud Build YAML passes validation
✅ All builds complete successfully
✅ Build times average 4-5 minutes (down from ~6 minutes)
✅ Cache hit rate ≥70% for repeat builds
✅ Error messages are clear and actionable
✅ All tests pass with >95% code coverage
✅ No regressions in build success rate
✅ Database migration applies without errors

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Build failures after optimization | Low | High | Comprehensive testing, rollback plan |
| Cache invalidation issues | Medium | Medium | Hash-based cache keys, clear logs |
| Secret reference bugs | Low | High | Secret validation step, tests |
| Database migration issues | Low | High | Test migration on staging first |
| Performance regression | Very Low | Medium | Load testing, monitoring |

---

## Timeline Summary

| Phase | Duration | Status |
|---|---|---|
| Phase 1: GitHub Actions Removal | 30 min | Ready |
| Phase 2: Cloud Build Optimization | 2-3 hours | Ready |
| Phase 3: Code Refactoring | 1-2 hours | Ready |
| Phase 4: Testing & Validation | 1-2 hours | Ready |
| **Total** | **5-8 hours** | **Ready for execution** |

---

## Questions for Implementation Agent

Before starting, clarify:

1. Should we keep GitHub Actions for any other purposes (security scanning, deployment)?
2. Should we implement all optimizations or prioritize specific ones?
3. What's the preferred testing approach - local, staging, or production?
4. Should we maintain backward compatibility with existing build records?
5. Do you want automated performance reporting after each build?

---

## Appendix: File Reference Map

```
Root
├── cloudbuild.yaml (620 lines) → Optimize
├── cloud_build_integration.py → Update
├── cloud_build_cli_wrapper.py → Review (no changes needed)
├── .github/
│   └── workflows/
│       ├── cloud-compile.yml → DELETE
│       ├── main.yml → DELETE
│       ├── ci.yml → DELETE
│       ├── wrapper_*.js → DELETE
│       └── wrapper_*.py → DELETE
├── server/
│   ├── routes/
│   │   ├── cloud_build_routes.py → Refactor into 4 files
│   │   ├── cloud_build_queue.py → CREATE
│   │   ├── cloud_build_utils.py → CREATE
│   │   └── cloud_build_websocket.py → CREATE
│   └── migrations/
│       └── 009_add_gcp_build_tracking.sql → CREATE
├── tests/
│   ├── test_cloud_build_optimization.py → CREATE
│   ├── test_cloud_build_workflow.py → CREATE
│   ├── test_build_performance.py → CREATE
│   └── test_cloudbuild_yaml.py → CREATE
└── docs/
    ├── cloud-build.md → Update
    ├── PROJECT_REFERENCE.md → Update
    └── README.md → Update
```

---

**End of Implementation Plan**

This document provides everything needed to implement the cloud build optimization and GitHub Actions removal. Each task is specific, actionable, and includes code examples, file locations, and validation steps.
