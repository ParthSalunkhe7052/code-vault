# Research: Cloud Build Optimization

**Date**: 2026-01-27
**Author**: Pickle Rick

## 1. Executive Summary
The significant performance gap (30m Cloud vs 15m Local) is primarily caused by **configuration differences**, not just hardware limitations. The Cloud Runner explicitly disables critical caching mechanisms (`ccache`) and enforces the slowest compilation mode (`--onefile`), while also running on limited hardware (2 vCPU).

## 2. Technical Context

### 2.1 Hardware Comparison
- **Local (estimated)**: 8+ vCPUs, SSD, Persistent Environment.
- **GitHub Actions (Windows/Linux Standard)**: 2 vCPUs, 7GB RAM.
- **Impact**: Nuitka scales linearly with cores. 2 cores = 1/4th the speed of 8 cores.

### 2.2 Configuration Analysis (`cloud_runner.py`)
- **Caching Disabled**: The script explicitly passes `--disable-ccache`.
  ```python
  # cloud_runner.py:348
  "--disable-ccache",  # Avoid ccache issues in CI
  ```
  **Consequence**: Nuitka recompiles all generated C code from scratch every run, even if the `.yml` file restores the Nuitka cache folder. The restored cache is ignored for C-compilation.

- **Forced Onefile**:
  ```python
  # cloud_runner.py:356
  "--onefile",
  ```
  **Consequence**: After compilation, Nuitka must compress the binary and dependencies into a self-extracting archive. This is CPU intensive and single-threaded.

### 2.3 Workflow Analysis (`cloud-compile.yml`)
- **Redundant Installs**:
  - Step: `Install Build Tools` (pip install nuitka...)
  - Script: `cloud_runner.py` -> `_prepare_dependencies` (pip install dependencies...)
  - While `pip` cache is restored, the *process* of checking/installing adds overhead.

## 3. Findings & Analysis

| Feature | Local (`lw_compiler.py`) | Cloud (`cloud_runner.py`) | Impact |
| :--- | :--- | :--- | :--- |
| **Caching** | Enabled (Implicit) | **Disabled** (`--disable-ccache`) | **Critical**. Recompiling C code is the slowest part. |
| **Cores** | Max 8 | Max 2 | High. 4x throughput difference. |
| **Mode** | `--fast` (Directory) or `--onefile` | `--onefile` (Always) | Medium. Compression adds ~2-5 mins. |
| **Env** | Persistent | Fresh VM | Low/Medium. Dependency install overhead. |

## 4. Technical Constraints
- **GitHub Free Tier**: Hard limit of 2 vCPUs. Cannot just "add more power" without paying.
- **Student Pack**: Provides "Pro" features (more minutes), but usually the same *runner specs* (2 vCPU) unless using larger runners (which consume minutes faster).

## 5. Recommendations (Preview)
1.  **Enable Caching**: Remove `--disable-ccache` and configure Nuitka to use the GitHub Action restored cache path.
2.  **Optimize Mode**: Allow `--fast` mode (directory output) for test builds, skipping `--onefile`.
3.  **Pre-baked Environment**: Use a Docker container with Nuitka/Dependencies pre-installed (for Linux builds).

## 6. Architecture Documentation
- **Workflow**: `cloud-compile.yml` -> `cloud_runner.py` -> `Nuitka`
- **Cache Keys**: `windows-nuitka-py3.11-v3`
