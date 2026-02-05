# 🚀 Cloud Build Setup - Manual Steps

## ✅ What's Already Done

1. ✅ Python dependencies installed (`google-cloud-build`, `google-auth`, `google-cloud-storage`)
2. ✅ Code updated to use Cloud Build API
3. ✅ Webhook format fixed (per-platform callbacks)
4. ✅ GCS/R2 hybrid download URLs implemented
5. ✅ Landing page localhost detection fixed

---

## 🔧 Manual Steps Required (15 minutes)

### Step 1: Set Up Google Cloud Authentication (5 minutes)

**Option A - Quick Setup (Recommended for testing)**:
1. Open a **new PowerShell/Terminal window**
2. Run:
   ```powershell
   gcloud auth application-default login
   ```
3. Follow the browser prompts to authenticate
4. Grant permissions when asked

**Option B - Production Setup (Service Account)**:
1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=cloudbuild-486309
2. Find service account: `codevault-ai-agent@cloudbuild-486309.iam.gserviceaccount.com`
3. Click "Keys" → "Add Key" → "Create new key" → "JSON"
4. Download the JSON key file
5. Set environment variable:
   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\downloaded\key.json"
   ```

**Verify authentication**:
```powershell
gcloud auth application-default print-access-token
```
If you see a long token → ✅ Authentication successful!

---

### Step 2: Connect GitHub Repository (5 minutes)

**CRITICAL**: Cloud Build cannot work without this step!

1. **Open in browser**: https://console.cloud.google.com/cloud-build/triggers/connect?project=cloudbuild-486309

2. **Click "Connect Repository"**

3. **Select source**: "GitHub (Cloud Build GitHub App)"

4. **Authenticate**: 
   - Log in to GitHub if prompted
   - Grant permissions to Google Cloud Build app

5. **Select repository**:
   - Search for: `ParthSalunkhe7052/code-vault`
   - Click "Connect"

6. **Verify connection**:
   - Go to: https://console.cloud.google.com/cloud-build/repositories?project=cloudbuild-486309
   - You should see `ParthSalunkhe7052/code-vault` listed

---

### Step 3: Verify Setup (5 minutes)

Run the verification script:

```powershell
python verify_cloud_build_setup.py
```

**Expected output**:
```
Checks passed: 7/7

✅ Dependencies
✅ Authentication
✅ Cloud Build API
✅ Cloud Storage
✅ Secret Manager
✅ GitHub Connection
✅ Build Test Info

🎉 SUCCESS! All checks passed!
```

**If you see errors**:
- Authentication error → Retry Step 1
- GitHub connection error → Retry Step 2
- API errors → Contact support (rare)

---

## 🧪 Testing Cloud Build

### Test 1: Manual Build Trigger (via gcloud)

```powershell
gcloud builds submit `
  --config=cloudbuild.yaml `
  --no-source `
  --project=cloudbuild-486309 `
  --substitutions=_BUILD_ID=test-001,_PROJECT_ID=test-proj,_LANGUAGE=python,_TARGET_PLATFORMS=linux,_SOURCE_URL=https://httpbin.org/delay/1,_CONFIG_JSON_B64=e30=,_CALLBACK_URL=https://example.com/webhook,_ENTRY_FILE=main.py,_OUTPUT_NAME=test-app,_PLAN_TIER=free,_COMPATIBILITY_MODE=false,_FAST_BUILD=false
```

**Expected**:
- Build ID printed (e.g., `12345678-1234-1234-1234-123456789abc`)
- Build visible at: https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309

**If it fails**:
- "permission denied" → Check authentication (Step 1)
- "repository not found" → GitHub not connected (Step 2)
- "cloudbuild.yaml not found" → Run command from project root directory

---

### Test 2: Backend Build Trigger (via Dashboard)

1. **Start your backend**:
   ```powershell
   cd server
   uvicorn main:app --reload
   ```

2. **Access dashboard**: http://localhost:5173

3. **Create a test project**:
   - Upload a simple Python file (e.g., `print("Hello")`)
   - Click "Cloud Build"
   - Select platform: "Linux"
   - Click "Start Build"

4. **Monitor**:
   - Backend logs: Watch for "[CloudBuild] Build triggered successfully"
   - GCP Console: https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309
   - Wait for webhook callback

5. **Check download**:
   - After build completes, check "Builds" tab
   - Download button should appear
   - Click to download artifact

**Expected flow**:
```
Dashboard → Backend (trigger_cloud_build) → Google Cloud Build → 
Build runs → Uploads to GCS → Sends webhook → Backend updates DB → 
User can download
```

---

## 🔍 Troubleshooting

### Issue: "ImportError: cannot import name 'cloudbuild_v1'"

**Fix**: The import path is different
```python
# WRONG:
from google.cloud import cloudbuild_v1

# CORRECT:
from google.cloud.devtools import cloudbuild_v1
```

This is already fixed in `cloud_build_integration.py` ✅

---

### Issue: "DefaultCredentialsError: Your default credentials were not found"

**Fix**: Run authentication again
```powershell
gcloud auth application-default login
```

Or set service account key:
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\key.json"
```

---

### Issue: "Repository not connected" or "404 Not Found"

**Fix**: GitHub repo not connected to Cloud Build
- Retry Step 2 above
- Make sure you selected the correct repository
- Check https://console.cloud.google.com/cloud-build/repositories?project=cloudbuild-486309

---

### Issue: Webhook not received / Build status not updating

**Possible causes**:
1. **Callback URL not accessible**: 
   - In development, use ngrok: `ngrok http 8000`
   - Update `PUBLIC_API_URL` in `.env`: `PUBLIC_API_URL=https://your-ngrok-url.ngrok.io`

2. **Webhook signature mismatch**:
   - Check `BUILD_CALLBACK_SECRET` matches in both:
     - `.env` file
     - Google Secret Manager

3. **Firewall blocking**:
   - Allow inbound connections from GCP IP ranges
   - Or use ngrok for testing

---

### Issue: Artifact download fails / URL returns 403

**Possible causes**:
1. **GCS permissions**: Service account needs `roles/storage.objectAdmin`
2. **Signed URL expired**: URLs valid for 1 hour only
3. **File in R2 instead of GCS**: Old GitHub Actions builds

**Fix**: The `generate_gcs_signed_url()` function handles both GCS and R2 automatically ✅

---

## 📊 Monitoring

### View Build Logs
https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309

### View Artifacts in GCS
```powershell
gsutil ls gs://codevault-builds/builds/
```

### Check Webhook Secret
```powershell
gcloud secrets versions access latest --secret=callback-webhook-secret --project=cloudbuild-486309
```

### View Service Account Permissions
```powershell
gcloud projects get-iam-policy cloudbuild-486309 `
  --flatten="bindings[].members" `
  --filter="bindings.members:*@cloudbuild.gserviceaccount.com"
```

---

## 🎯 Quick Reference

### Important URLs
- **GCP Console**: https://console.cloud.google.com/?project=cloudbuild-486309
- **Cloud Build**: https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309
- **GCS Bucket**: https://console.cloud.google.com/storage/browser/codevault-builds?project=cloudbuild-486309
- **Triggers**: https://console.cloud.google.com/cloud-build/triggers?project=cloudbuild-486309
- **Secrets**: https://console.cloud.google.com/security/secret-manager?project=cloudbuild-486309

### Key Files Modified
- ✅ `server/requirements.txt` - Added GCP dependencies
- ✅ `cloud_build_integration.py` - Cloud Build API client
- ✅ `server/routes/cloud_build_routes.py` - Updated to use Cloud Build
- ✅ `cloudbuild.yaml` - Per-platform webhooks
- ✅ `landing-page/components/*.tsx` - Auto-detect localhost

### Environment Variables Needed
```bash
# Backend .env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json  # Optional if using gcloud auth
PUBLIC_API_URL=http://localhost:8000  # Or ngrok URL for testing
BUILD_CALLBACK_SECRET=your-webhook-secret  # Must match Secret Manager
```

---

## ✅ Success Checklist

Before going live, verify:

- [ ] Step 1 completed (authentication works)
- [ ] Step 2 completed (GitHub repo connected)
- [ ] Step 3 passed (verification script shows all green)
- [ ] Test 1 passed (manual build via gcloud works)
- [ ] Test 2 passed (backend trigger works)
- [ ] Webhook received (check backend logs)
- [ ] Artifact downloadable (signed URL works)
- [ ] Landing page localhost links work

---

## 🆘 Need Help?

If you're stuck after following these steps:

1. Run verification script: `python verify_cloud_build_setup.py`
2. Check the output and error messages
3. Review the troubleshooting section above
4. Check GCP Console logs: https://console.cloud.google.com/logs/query?project=cloudbuild-486309

---

**Next**: Once all checks pass, your Cloud Build integration is fully functional! 🎉
