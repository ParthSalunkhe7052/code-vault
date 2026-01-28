# Research: Cloud Build Audit

**Date**: 2026-01-27

## 1. Executive Summary
The Cloud Build system is mostly robust but has a critical flaw in the workflow validation logic. The runner script is smarter than the workflow, leading to false positives where the workflow claims "Entry file not found" even if the runner successfully compiled the project.

## 2. Findings & Analysis

### A. Backend (`cloud_build_routes.py`)
- **Status**: Healthy.
- **Input Validation**: `output_name` sanitization is redundant but safe.
- **Security**: Path validation is standard.

### B. Runner (`cloud_runner.py`)
- **Status**: Healthy.
- **Smart Entry Point**: The runner searches for `main.py`, `app.py`, etc., if the configured file is missing. This is a "Smart Feature".
- **License Wrapper**: Clean, console-based.

### C. Workflow (`cloud-compile.yml`)
- **Status**: **BUG FOUND**.
- **The "Smart Runner vs. Dumb Workflow" Conflict**:
    - The runner (`cloud_runner.py`) finds the entry file dynamically.
    - The workflow (`cloud-compile.yml`) *independently* checks for the file existence using the *original* input path.
    - **Scenario**: User says `entry_file: main.py`. Project has `app/main.py`. Runner finds it. Runner builds successfully. Workflow checks for `project/source/main.py`, fails, and reports "Entry file not found".
- **Logic**: The `Notify completion` step checks `if [ -n "$UPLOAD_KEY" ]`. If upload succeeded, it marks as completed.
    - Wait, if build succeeds, `UPLOAD_KEY` is set.
    - If `UPLOAD_KEY` is set, the status is "completed".
    - The "Entry file not found" check is inside the `else` block (if `UPLOAD_KEY` is empty).
    - So, if the runner succeeds, `UPLOAD_KEY` is set, and the "Entry file" check is skipped.
    - **Correction**: The bug only manifests if the build *fails* for another reason (e.g., compilation error). The error message might misleadingly say "Entry file not found" if the path didn't match, masking the real compilation error.

### D. Other Issues
- **Error Propagation**: If Nuitka fails, the workflow says "Compilation failed. Check GitHub Actions logs." This is lazy. We should try to capture the last few lines of the log.

## 3. Recommendations
1.  **Trust the Runner**: If the runner fails, rely on the runner's exit code/logs, not a secondary file check.
2.  **Capture Logs**: Modify `cloud_runner.py` to write the last 50 lines of output to a file, and have the workflow read that file into the error message.
