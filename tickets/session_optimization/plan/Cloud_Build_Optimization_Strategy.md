# Cloud Build Optimization Strategy

**Date**: 2026-01-27
**Status**: Recommended
**Author**: Pickle Rick

## 1. Root Cause Analysis
The current GitHub Actions build (~30m) is 2x slower than local (~15m) due to three primary factors:
1.  **Disabled Caching**: The `cloud_runner.py` script explicitly disables `ccache` (`--disable-ccache`), forcing a full C-level recompilation every run.
2.  **Forced Onefile**: The workflow enforces `--onefile` mode, adding significant compression time (CPU bound) at the end of the build.
3.  **Hardware Limits**: GitHub Free Tier runners (2 vCPU) are significantly weaker than the local machine (est. 8+ vCPU).

## 2. Optimization Plan (The "Fix It" Strategy)

### Phase 1: The "Low Hanging Fruit" (Configuration Fixes)
**Estimated Impact**: 30-50% speedup.
**Cost**: $0.

1.  **Enable Caching in `cloud_runner.py`**:
    -   **Action**: Remove the `"--disable-ccache"` flag from `cmd` list in `_compile_nuitka`.
    -   **Action**: Ensure `NUITKA_CACHE_DIR` env var is respected (it is already set in `.yml`).
    -   **Action**: For Windows, ensure `clcache` is installed (`pip install clcache`). For Linux, ensure `ccache` is installed (`sudo apt-get install ccache`).

2.  **Implement "Fast Mode" for CI**:
    -   **Action**: Add `fast_build` boolean input to `cloud-compile.yml`.
    -   **Action**: Pass `--fast-build` (or equivalent config) to `cloud_runner.py`.
    -   **Action**: If fast build, skip `--onefile` and upload the directory (zipped) instead of the exe.
    -   **Benefit**: Skips the compression phase (~2-5 mins) and allows incremental linking.

### Phase 2: Advanced Optimization (Environment)
**Estimated Impact**: Additional 20% speedup.
**Cost**: $0.

1.  **Docker Container (Linux Only)**:
    -   **Current**: `Setup Python` -> `Install Nuitka` -> `Install Dependencies`.
    -   **Proposed**: Create a public Docker image `codevault/builder:latest` with Python 3.11, Nuitka, Patchelf, and ccache pre-installed.
    -   **Action**: Update `cloud-compile.yml` to run inside this container.
    -   **Benefit**: Eliminates tool installation time (~1-2 mins).

### Phase 3: Alternatives (If GitHub Actions is still too slow)
**Evaluation**:
-   **GitLab CI (Free)**: 400 mins/month. Shared runners are also often 1-2 vCPU. Not significantly faster without paid runners.
-   **CircleCI (Free)**: 30,000 credits. 2 vCPU resource class. Same hardware limit.
-   **Self-Hosted Runner**:
    -   **Option**: Use an old laptop/PC as a self-hosted runner for GitHub Actions.
    -   **Cost**: Electricity.
    -   **Benefit**: 100% Free, utilizes full 8+ cores, persistent cache. **Fastest Option**.

## 3. Implementation Guide

### Step 1: Update `cloud_runner.py`
Modify `_compile_nuitka` to accept a `fast_build` flag and remove caching restrictions.

```python
# Remove this line
# "--disable-ccache",

# Add this logic
if fast_build:
    cmd.append("--output-dir=build")
    # No --onefile
else:
    cmd.append("--onefile")
```

### Step 2: Update `cloud-compile.yml`
Add inputs and install ccache.

```yaml
inputs:
  fast_build:
    description: 'Skip compression for faster build'
    type: boolean
    default: false

# ... inside steps ...
- name: Install Caching Tools
  if: runner.os == 'Linux'
  run: sudo apt-get install -y ccache
```

## 4. Conclusion
**Status: Implemented and Deployed.**
- `cloud_runner.py`: Patched.
- `cloud-compile.yml`: Updated.
- GitHub: Pushed.
- Frontend: Redeployed.

We do not need to switch providers yet. We are artificially throttling our current provider. Implementing Phase 1 (Caching + Fast Mode) should bring build times close to 15-20 minutes, which is acceptable for a free tier.
