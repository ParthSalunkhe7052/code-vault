# Google Cloud Build Setup for CodeVault

## Quick Start Guide

This automated script will configure Google Cloud Build to replace GitHub Actions for your production builds.

### Prerequisites

1. **Google Cloud SDK (gcloud) installed**
   - Windows: Download from https://cloud.google.com/sdk/docs/install-sdk#windows
   - macOS: `brew install --cask google-cloud-sdk`
   - Linux: https://cloud.google.com/sdk/docs/install-sdk#linux

2. **Git installed** (for pushing cloudbuild.yaml)

3. **Your webhook secret** (the same HMAC secret you use in GitHub Actions)

---

## Installation Steps

### Step 1: Authenticate with Google Cloud

Open your terminal and run:

```bash
gcloud auth login
```

This will open a browser where you log in with your Google account.

### Step 2: Run the Setup Script

```bash
cd "C:\Users\parth\OneDrive\Desktop\Code Vault"
python setup_cloud_build.py
```

The script will automatically:
- ✅ Enable required Google Cloud APIs
- ✅ Create Cloud Storage bucket for build artifacts
- ✅ Set up Secret Manager secrets
- ✅ Configure IAM permissions
- ✅ Guide you through GitHub connection
- ✅ Commit and push cloudbuild.yaml
- ✅ Validate the setup

**Estimated time: 5 minutes**

---

## What Happens During Setup

1. **API Enablement** - Enables Cloud Build, Storage, and Secret Manager APIs
2. **GCS Bucket Creation** - Creates `codevault-builds` bucket for storing executables
3. **Secret Creation** - Stores your webhook secret securely in Secret Manager
4. **GitHub Connection** - Opens browser to connect your GitHub repo (OAuth)
5. **Configuration Push** - Commits `cloudbuild.yaml` to your repository
6. **Validation** - Tests that everything is working

---

## After Setup

### Update Your Backend (Digital Ocean)

Replace your GitHub Actions trigger code with Cloud Build API:

```python
from cloud_build_integration import CloudBuildClient

# Initialize once
cloud_build = CloudBuildClient(project_id="cloudbuild-486309")

# Trigger build (replaces GitHub Actions API call)
result = cloud_build.trigger_build({
    "build_id": "build-123",
    "project_id": "user-project-abc",
    "language": "python",
    "target_platforms": "windows,linux",
    "source_url": "https://your-presigned-url.com/source.zip",
    "config": {
        "entry_file": "main.py",
        "output_name": "my-app"
    },
    "callback_url": "https://your-api.com/webhook/complete"
})

print(f"Build started: {result['build_id']}")
print(f"Logs: {result['logs_url']}")
```

### Install Dependencies on Digital Ocean

```bash
pip install google-cloud-build google-auth
```

### Set Up Authentication on Digital Ocean

**Option 1: Application Default Credentials (Recommended for servers)**
```bash
gcloud auth application-default login
```

**Option 2: Service Account (if available)**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

---

## Testing Your Setup

### Manual Test in Console

1. Go to: https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309
2. Click "RUN" → "Advanced"
3. Fill in substitution variables
4. Click "RUN"

### Test from Your Backend

Use the example in `cloud_build_integration.py`:

```python
python cloud_build_integration.py
```

---

## Migration Strategy

We recommend a **phased rollout**:

1. **Week 1: Parallel Running**
   - Keep GitHub Actions active
   - Route 10% of builds to Cloud Build
   - Monitor for issues

2. **Week 2: Increase Traffic**
   - Route 50% to Cloud Build
   - Compare build times and success rates

3. **Week 3: Full Migration**
   - Route 100% to Cloud Build
   - Disable GitHub Actions workflows

4. **Week 4: Cleanup**
   - Archive `.github/workflows/cloud-compile.yml`
   - Update documentation

---

## Troubleshooting

### "gcloud: command not found"

Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install

### "Permission denied" errors

Make sure you're authenticated:
```bash
gcloud auth login
gcloud auth application-default login
```

### "Bucket already exists"

That's fine! The script will use the existing bucket.

### GitHub connection fails

Make sure you:
1. Are logged into GitHub in your browser
2. Have admin access to the `ParthSalunkhe7052/code-vault` repository
3. Authorized the Cloud Build GitHub App

### Builds fail with "source not found"

Check that:
1. The presigned URL is accessible
2. The source.zip file is properly formatted
3. The `_SOURCE_URL` substitution variable is correct

---

## Important Files

- `cloudbuild.yaml` - Build configuration (committed to repo)
- `setup_cloud_build.py` - This setup script
- `cloud_build_integration.py` - Backend integration code
- `.github/scripts/cloud_runner.py` - Build execution script (unchanged)

---

## Cost Estimates

**Cloud Build Pricing:**
- First 120 build-minutes/day: **FREE**
- After that: $0.003/build-minute
- Typical 60-min build: ~$0.18 (only after free tier)

**Cloud Storage Pricing:**
- First 5GB: **FREE**
- After that: $0.020/GB/month

**Estimated monthly cost:** $5-20 (depending on build volume)

---

## Security Best Practices

✅ **DO:**
- Use Secret Manager for sensitive data
- Rotate webhook secrets regularly
- Use IAM roles (not service account keys)
- Enable Cloud Build logs for auditing

❌ **DON'T:**
- Commit secrets to Git
- Share service account keys
- Make GCS buckets publicly readable
- Disable Cloud Build logging

---

## Support

- **Cloud Build Docs:** https://cloud.google.com/build/docs
- **Cloud Storage Docs:** https://cloud.google.com/storage/docs
- **IAM Docs:** https://cloud.google.com/iam/docs

---

## Rollback Plan

If you need to rollback to GitHub Actions:

1. Re-enable `.github/workflows/cloud-compile.yml`
2. Update backend to use GitHub Actions API
3. Builds will continue working immediately

The Cloud Build setup remains available for future use.

---

**Ready? Run the setup script now:**

```bash
python setup_cloud_build.py
```
