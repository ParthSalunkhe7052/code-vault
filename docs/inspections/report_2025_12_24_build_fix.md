# Inspection Report: Build Error

**Date:** 2025-12-24
**Inspector:** Antigravity

## Issue
Build fails with `nuitka: lw-compiler: error: unrecognized arguments: --output ...`.

## Deep Scan Findings

### Structure Check
- `cli/lw_compiler.py` is the entry point for compilation.
- `server/compilers/build_orchestrator.py` invokes `lw_compiler.py` as a subprocess.

### Discrepancy
- **Implementation Mismatch**: `build_orchestrator.py` assumes `lw_compiler.py` supports:
    - Local file paths as input (instead of Project IDs).
    - `--output` flag.
    - `--api-url` flag.
    - `--demo` flags.
- **Current State**: `lw_compiler.py` only supports Project IDs and `requests`-based config fetching, and lacks these flags.

### Risk
- **Source Integrity**: If `lw_compiler.py` is forced to run on local files without safeguards, the `inject_license_wrapper` function writes directly to the entry file. This would permanently modify the user's source code with the license wrapper, which is destructive.

## Recommendations
1.  **Update CLI**: Modify `lw_compiler.py` to support "Local Mode" which operates on a temporary copy of the source.
2.  **Add Arguments**: Implement the missing flags to align with `build_orchestrator`'s usage.
