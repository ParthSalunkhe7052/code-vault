# Google Cloud Build Migration Guide

## Overview

This document explains how the Google Cloud Build configuration works and how to migrate from GitHub Actions to Google Cloud Build for production builds in CodeVault.

**Last Updated:** February 4, 2026  
**Status:** Ready for Migration  
**Current Build System:** GitHub Actions (`.github/workflows/cloud-compile.yml`)  
**Target Build System:** Google Cloud Build (`cloudbuild.yaml`)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Files](#key-files)
3. [How It Works](#how-it-works)
4. [Migration Steps](#migration-steps)
5. [Configuration Details](#configuration-details)
6. [Cost Analysis](#cost-analysis)
7. [Rollback Plan](#rollback-plan)
8. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

### Current Architecture (GitHub Actions)

```
User Request → Backend API → GitHub Actions Workflow Dispatch → cloud_runner.py → Build Artifacts → GCS/Webhook
```

**Issues:**
- Rate limits on GitHub API
- Complex authentication with GitHub tokens
- Limited to GitHub's infrastructure
- Less control over build environment

### Target Architecture (Google Cloud Build)

```
User Request → Backend API → Cloud Build API → cloudbuild.yaml → cloud_runner.py → Build Artifacts → GCS → Webhook
```

**Benefits:**
- No GitHub rate limits
- Direct GCP integration
- Better cost control
- More powerful build machines
- Easier secret management via Secret Manager

---

## Key Files

### 1. `cloudbuild.yaml`
**Location:** Root of repository  
**Purpose:** Defines the build pipeline for Google Cloud Build  
**Key Features:**
- Multi-platform builds (Linux, Windows, macOS)
- Parallel build execution
- Automatic artifact upload to GCS
- Webhook callbacks on completion

### 2. `setup_cloud_build.py`
**Location:** Root of repository  
**Purpose:** One-time setup script to configure Google Cloud Build  
**What It Does:**
- Enables required GCP APIs
- Creates GCS bucket for artifacts
- Sets up Secret Manager secrets
- Configures IAM permissions
- Connects GitHub repository

### 3. `cloud_build_integration.py`
**Location:** Root of repository  
**Purpose:** Python client library for triggering Cloud Build from backend  
**Usage:**
```python
from cloud_build_integration import CloudBuildClient

cloud_build = CloudBuildClient(project_id="cloudbuild-486309")
result = cloud_build.trigger_build({
    "build_id": "build-123",
    "project_id": "user-project-abc",
    "language": "python",
    "target_platforms": "windows,linux",
    "source_url": "https://presigned-url.com/source.zip",
    "config": {
        "entry_file": "main.py",
        "output_name": "my-app"
    },
    "callback_url": "https://api.codevault.com/webhook/complete"
})
```

### 4. `CLOUD_BUILD_SETUP.md`
**Location:** Root of repository  
**Purpose:** Quick start guide for setting up Google Cloud Build  
**Target Audience:** Developers setting up Cloud Build for the first time

### 5. `QUICK_START.md`
**Location:** Root of repository  
**Purpose:** Condensed setup instructions for experienced users

### 6. `.github/scripts/cloud_runner.py`
**Location:** `.github/scripts/`  
**Purpose:** Core build execution logic (used by both GitHub Actions and Cloud Build)  
**Note:** This file remains unchanged - it's platform-agnostic

---

## How It Works

### Build Pipeline Flow

#### Step 1: Download Source
```yaml
- name: 'gcr.io/cloud-builders/curl'
  args: ['-L', '-o', 'source.zip', '${_SOURCE_URL}']
```
- Downloads user's source code from presigned URL
- URL is provided by backend API

#### Step 2: Extract and Normalize Source
```yaml
- name: 'ubuntu'
  entrypoint: 'bash'
```
- Extracts ZIP file
- Normalizes directory structure (handles various ZIP formats)
- Ensures source code is in `./project/source/`

#### Step 3: Build for Linux (Native)
```yaml
- name: 'python:3.11-slim'
  entrypoint: 'bash'
```
- Runs natively on Linux
- Installs Nuitka and dependencies
- Executes `cloud_runner.py`
- Packages output as `.tar.gz`

#### Step 4: Build for Windows (Wine)
```yaml
- name: 'docker.io/tobix/pywine:3.11'
  entrypoint: 'bash'
```
- Uses Wine to run Windows Python
- Compiles to `.exe` using Nuitka
- Packages output as `.zip`

#### Step 5: Build for macOS (Cross-compilation)
```yaml
- name: 'gcr.io/cloud-builders/docker'
  entrypoint: 'bash'
```
- **Currently Skipped:** macOS cross-compilation is complex
- **Recommendation:** Keep GitHub Actions for macOS or use dedicated Mac builders
- Placeholder for future osxcross implementation

#### Step 6: Upload to Google Cloud Storage
```yaml
- name: 'gcr.io/cloud-builders/gsutil'
```
- Uploads all artifacts to `gs://codevault-builds/builds/${BUILD_ID}/`
- Organized by platform: `linux/`, `windows/`, `macos/`

#### Step 7: Send Webhook Callback
```yaml
- name: 'gcr.io/cloud-builders/curl'
  secretEnv: ['CALLBACK_SECRET']
```
- Sends completion webhook to backend
- Includes artifact URLs and build status
- Signed with HMAC for security

---

## Migration Steps

### Phase 1: Setup (Week 1)

**Goal:** Get Google Cloud Build working in parallel with GitHub Actions

1. **Run Setup Script**
   ```bash
   cd "C:\Users\parth\OneDrive\Desktop\Code Vault"
   python setup_cloud_build.py
   ```

2. **Update Backend on Digital Ocean**
   - Install dependencies: `pip install google-cloud-build google-auth`
   - Set up authentication: `gcloud auth application-default login`
   - Import `cloud_build_integration.py`

3. **Test with Sample Build**
   - Trigger a test build via Cloud Build API
   - Verify artifacts upload to GCS
   - Confirm webhook callback works

### Phase 2: Parallel Running (Week 2)

**Goal:** Route 10-20% of builds to Cloud Build

1. **Implement Traffic Splitting**
   ```python
   # In your backend build route
   if random.random() < 0.10:  # 10% to Cloud Build
       result = cloud_build.trigger_build(...)
   else:
       result = github_actions.trigger_workflow(...)
   ```

2. **Monitor Metrics**
   - Compare build times
   - Track failure rates
   - Monitor costs

3. **Fix Issues**
   - Adjust timeout settings if needed
   - Fix any platform-specific bugs
   - Optimize build caching

### Phase 3: Gradual Increase (Week 3)

**Goal:** Route 50% of builds to Cloud Build

1. **Increase Traffic**
   ```python
   if random.random() < 0.50:  # 50% to Cloud Build
       result = cloud_build.trigger_build(...)
   ```

2. **Performance Analysis**
   - Compare total costs
   - Analyze build reliability
   - Gather user feedback

### Phase 4: Full Migration (Week 4)

**Goal:** Route 100% of builds to Cloud Build

1. **Switch to 100% Cloud Build**
   ```python
   # Remove GitHub Actions code
   result = cloud_build.trigger_build(...)
   ```

2. **Archive GitHub Actions Workflow**
   - Move `.github/workflows/cloud-compile.yml` to `.github/workflows/archive/`
   - Keep file for reference (don't delete)

3. **Update Documentation**
   - Update README.md
   - Update deployment docs
   - Update API documentation

---

## Configuration Details

### Build Parameters (Substitution Variables)

All builds accept these parameters via the Cloud Build API:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `_BUILD_ID` | Unique build identifier | `build-abc123` |
| `_PROJECT_ID` | User's project ID | `user-project-xyz` |
| `_LANGUAGE` | Programming language | `python`, `nodejs` |
| `_TARGET_PLATFORMS` | Comma-separated platforms | `windows,linux,macos` |
| `_SOURCE_URL` | Presigned URL to source ZIP | `https://s3.amazonaws.com/...` |
| `_CONFIG_JSON` | JSON build configuration | `{"entry_file": "main.py"}` |
| `_CALLBACK_URL` | Webhook endpoint | `https://api.codevault.com/webhook` |
| `_ENTRY_FILE` | Entry point file | `main.py`, `index.js` |
| `_OUTPUT_NAME` | Output executable name | `my-app` |
| `_PLAN_TIER` | User's pricing plan | `free`, `pro`, `enterprise` |

### Secret Manager Configuration

Secrets are stored in Google Secret Manager:

1. **`callback-webhook-secret`**
   - Used for HMAC signing of webhooks
   - Matches the secret in your backend `.env`
   - Set during `setup_cloud_build.py`

### GCS Bucket Structure

```
gs://codevault-builds/
└── builds/
    └── {build_id}/
        ├── linux/
        │   └── {output_name}-linux.tar.gz
        ├── windows/
        │   └── {output_name}-windows.zip
        └── macos/
            └── {output_name}-macos.zip
```

### Build Machine Configuration

- **Machine Type:** `E2_HIGHCPU_8` (8 vCPUs, 8 GB RAM)
- **Timeout:** 3600 seconds (60 minutes)
- **Logging:** Cloud Logging only
- **Region:** Automatic (closest to project location)

---

## Cost Analysis

### Current Costs (GitHub Actions)

- **Free tier:** 2,000 minutes/month
- **Overage:** $0.008/minute
- **Typical usage:** ~10,000 minutes/month
- **Monthly cost:** ~$64/month

### Projected Costs (Google Cloud Build)

#### Cloud Build Pricing
- **Free tier:** 120 build-minutes/day (3,600 minutes/month)
- **Overage:** $0.003/build-minute
- **E2_HIGHCPU_8 multiplier:** 8x (so 1 real minute = 8 build-minutes)
- **Typical 60-min build:** 60 × 8 = 480 build-minutes
- **Cost per build after free tier:** 480 × $0.003 = $1.44

#### Cloud Storage Pricing
- **Storage:** $0.020/GB/month
- **Bandwidth (egress):** $0.12/GB (first 1 GB free)
- **Typical artifact:** 50 MB
- **100 builds/month:** 5 GB storage = $0.10/month

#### Total Estimated Monthly Cost
- Assuming 200 builds/month:
  - First 7.5 builds (3,600 build-minutes ÷ 480): **FREE**
  - Remaining 192.5 builds: 192.5 × $1.44 = **$277.20**
  - Storage: **$0.10**
  - **Total: ~$277.30/month**

**Note:** This is higher than GitHub Actions. Consider:
- Optimizing build times (reduce from 60 to 30 minutes)
- Using prebuilt Docker images
- Implementing build caching
- Using lower machine types for simple builds

---

## Rollback Plan

If you need to revert to GitHub Actions:

### Immediate Rollback (1 hour)

1. **Re-enable GitHub Actions Workflow**
   ```bash
   mv .github/workflows/archive/cloud-compile.yml .github/workflows/
   ```

2. **Update Backend Code**
   ```python
   # Switch back to GitHub Actions API
   result = github_actions.trigger_workflow(...)
   ```

3. **Deploy Backend**
   - Push changes to production
   - Builds resume using GitHub Actions

### Long-term Rollback (if Cloud Build fails)

- Cloud Build infrastructure remains available
- No cleanup needed
- Can retry migration later

---

## Future Enhancements

### Near-term (1-3 months)

1. **Implement Build Caching**
   - Cache Python packages between builds
   - Use ccache for C compilation
   - Expected: 30-50% faster builds

2. **Custom Docker Images**
   - Pre-install Nuitka and dependencies
   - Reduce build time by 5-10 minutes
   - Store in Google Container Registry

3. **macOS Support**
   - Set up osxcross for macOS cross-compilation
   - Or integrate with dedicated Mac cloud builders
   - Complete feature parity with GitHub Actions

### Long-term (3-6 months)

1. **Multi-region Builds**
   - Build in region closest to user
   - Reduce latency and bandwidth costs

2. **Advanced Build Options**
   - Custom optimization levels
   - Debug vs. release builds
   - Code obfuscation options

3. **Build Analytics Dashboard**
   - Track build success rates
   - Monitor build times by platform
   - Cost tracking and optimization suggestions

---

## Backend Integration Code Changes

### Current Code (GitHub Actions)

```python
# server/routes/cloud_build_routes.py (old)
import requests

def trigger_github_build(build_data):
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/cloud-compile.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "ref": "main",
        "inputs": {
            "build_id": build_data["build_id"],
            "project_id": build_data["project_id"],
            "language": build_data["language"],
            # ... other params
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
```

### New Code (Google Cloud Build)

```python
# server/routes/cloud_build_routes.py (new)
from cloud_build_integration import CloudBuildClient

# Initialize once (at module level)
cloud_build_client = CloudBuildClient(project_id="cloudbuild-486309")

def trigger_cloud_build(build_data):
    result = cloud_build_client.trigger_build({
        "build_id": build_data["build_id"],
        "project_id": build_data["project_id"],
        "language": build_data["language"],
        "target_platforms": build_data.get("platforms", "windows,linux"),
        "source_url": build_data["source_url"],
        "config": build_data["config"],
        "callback_url": f"{API_BASE_URL}/api/builds/webhook/complete"
    })
    
    return {
        "build_id": result["build_id"],
        "cloud_build_id": result["cloud_build_id"],
        "logs_url": result["logs_url"],
        "status": "queued"
    }
```

### Authentication Setup on Digital Ocean

```bash
# One-time setup on Digital Ocean server
gcloud auth application-default login

# Or use service account (recommended for production)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

---

## Troubleshooting

### Build Fails with "Source not found"

**Cause:** Presigned URL is invalid or expired  
**Solution:** Ensure presigned URLs have at least 1-hour expiration

### Build Times Out

**Cause:** Build exceeds 60-minute timeout  
**Solution:** 
- Increase timeout in `cloudbuild.yaml`
- Optimize build (enable fast_build mode)
- Use build caching

### Webhook Not Received

**Cause:** Backend endpoint unreachable or HMAC validation fails  
**Solution:**
- Check backend logs
- Verify callback URL is accessible from GCP
- Ensure secret matches between Secret Manager and backend

### Artifacts Not Uploading

**Cause:** GCS bucket permissions issue  
**Solution:**
- Run `setup_cloud_build.py` to fix IAM permissions
- Verify bucket name in `cloudbuild.yaml`

---

## Support & Resources

- **Google Cloud Build Docs:** https://cloud.google.com/build/docs
- **Cloud Build Pricing:** https://cloud.google.com/build/pricing
- **Python Client Library:** https://cloud.google.com/python/docs/reference/cloudbuild/latest
- **CodeVault Slack:** #cloud-build-migration

---

## Changelog

- **2026-02-04:** Initial documentation created
- **2026-01-29:** Marketplace features reverted, returning to licensing SaaS
- **2026-02-03:** Google Cloud Build configuration added

---

## Next Steps

1. Review this document thoroughly
2. Run `setup_cloud_build.py` to configure GCP
3. Test with a sample build
4. Begin Phase 1 migration (parallel running)
5. Monitor and optimize

For questions, contact the development team or refer to `CLOUD_BUILD_SETUP.md` for setup instructions.
