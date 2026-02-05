# Cloud Build End-to-End Testing Guide

## Overview
This guide will walk you through testing the Cloud Build migration with a realistic Discord bot project.

---

## Prerequisites Checklist

### 1. ngrok Setup
- [ ] ngrok is installed: `C:\Users\parth\AppData\Local\Microsoft\WindowsApps\ngrok.exe`
- [ ] Start ngrok: `ngrok http 8000`
- [ ] Note the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)
- [ ] Update `.env` if ngrok URL changed:
  ```
  PUBLIC_API_URL=https://your-ngrok-url.ngrok-free.app
  ```

### 2. Backend Server
- [x] All Cloud Build code changes applied
- [x] Dependencies installed (google-cloud-build, google-auth, etc.)
- [x] gcloud authentication active (parth.ajit7052@gmail.com)
- [ ] Backend ready to start

### 3. Test Files Created
- [x] `test_bot_main.py` - Discord moderation bot (315 lines)
- [x] `test_bot_requirements.txt` - Bot dependencies

---

## Step-by-Step Testing

### Phase 1: Start Services

#### 1.1 Start ngrok (Terminal 1)
```bash
ngrok http 8000
```

**Expected Output:**
```
Forwarding https://abc123.ngrok-free.app -> http://localhost:8000
```

**Action**: Copy the HTTPS URL and verify it matches `PUBLIC_API_URL` in `.env`

---

#### 1.2 Start Backend Server (Terminal 2)
```bash
cd server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
[Config] Loaded environment from: ...
[Storage] Connected to Cloudflare R2: license-builds
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Checkpoint**: Visit http://localhost:8000/docs to verify API is running

---

### Phase 2: Create Test Project

#### 2.1 Open Frontend
Navigate to: `http://localhost:5173`

If frontend not running:
```bash
# Terminal 3
cd frontend
npm run dev
```

---

#### 2.2 Login/Register
- Login with: `parth.ajit7052@gmail.com`
- Or create a test account

---

#### 2.3 Create Project
1. Click "New Project" or "Create Project"
2. Fill in details:
   - **Name**: Discord Moderation Bot
   - **Language**: Python
   - **Entry File**: test_bot_main.py

---

#### 2.4 Upload Bot Files
Upload these files to the project:
- `test_bot_main.py` (from Code Vault root)
- `test_bot_requirements.txt` → rename to `requirements.txt`

**File Paths:**
```
C:\Users\parth\OneDrive\Desktop\Code Vault\test_bot_main.py
C:\Users\parth\OneDrive\Desktop\Code Vault\test_bot_requirements.txt
```

---

### Phase 3: Trigger Cloud Build

#### 3.1 Configure Build Settings
1. Go to Project Settings or Build Configuration
2. Set:
   - **Output Name**: discord_bot
   - **Target Platforms**: 
     - [x] Windows
     - [x] Linux
     - [ ] macOS (optional - costs more)
   - **Compatibility Mode**: Off (for testing)

---

#### 3.2 Trigger Build
1. Click "Build" or "Compile" button
2. **Watch for**:
   - Build ID generated (e.g., `bld_a1b2c3d4`)
   - Status changes: `pending` → `queued` → `running`

---

#### 3.3 Monitor Backend Logs (Terminal 2)
**Expected Log Sequence:**
```
[CloudBuild] Triggering Cloud Build for bld_xxx
[CloudBuild] Successfully triggered build bld_xxx -> GCP Build abc-def-123
[CloudBuild] Webhook received: bld_xxx - windows - completed
[CloudBuild] Webhook received: bld_xxx - linux - completed
```

**Red Flags (Should NOT see):**
```
❌ GitHub API Error
❌ GITHUB_TOKEN and GITHUB_REPO must be configured
❌ Failed to trigger build
```

---

#### 3.4 Monitor GCP Console
Open: https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309

**What to look for:**
- New build with status "QUEUED" or "WORKING"
- Build ID matches backend logs
- Build steps executing:
  1. Download source from R2
  2. Install dependencies
  3. Compile with Nuitka
  4. Inject license wrapper
  5. Upload to GCS
  6. Send webhook

**Estimated Duration**: 3-5 minutes per platform

---

### Phase 4: Verify Webhooks

#### 4.1 Check ngrok Dashboard (Terminal 1)
Visit: `http://127.0.0.1:4040`

**Expected Requests:**
```
POST /api/v1/cloud-build/webhook
  Status: 200 OK
  Body: {"build_id": "bld_xxx", "platform": "windows", "status": "completed", ...}

POST /api/v1/cloud-build/webhook
  Status: 200 OK
  Body: {"build_id": "bld_xxx", "platform": "linux", "status": "completed", ...}
```

**Red Flags:**
```
❌ 401 Unauthorized (signature mismatch)
❌ 404 Not Found (webhook URL wrong)
❌ 500 Internal Server Error (database error)
```

---

#### 4.2 Verify Database Updated
**Frontend UI should show:**
- Build status: `completed`
- Progress: 100%
- Artifacts list:
  - ✅ Windows - discord_bot.zip
  - ✅ Linux - discord_bot.zip

---

### Phase 5: Download & Test Artifacts

#### 5.1 Download Artifacts
1. Click download button for each platform
2. **Expected**: Browser downloads ZIP file from GCS signed URL

**URL should look like:**
```
https://storage.googleapis.com/codevault-builds/builds/bld_xxx/windows/discord_bot.zip?...
```

**Not like (old R2 URL):**
```
❌ https://...r2.cloudflarestorage.com/...
```

---

#### 5.2 Extract and Verify
```bash
# Extract Windows build
unzip discord_bot_windows.zip

# Check contents
dir discord_bot_windows/
```

**Expected Files:**
```
discord_bot.exe          # Main executable
LICENSE_WRAPPER.txt      # License info (if applicable)
README.txt               # Usage instructions
```

---

#### 5.3 Test License Wrapping
If license was applied, the executable should:
1. Check for license key on startup
2. Validate via CodeVault API
3. Run the bot if valid
4. Show error if invalid/missing

**Test Commands:**
```bash
# Without license (should fail gracefully)
./discord_bot.exe

# With license
set LICENSE_KEY=your-key-here
./discord_bot.exe
```

---

### Phase 6: Test Cancel Build

#### 6.1 Trigger Another Build
Start a new build with same project

---

#### 6.2 Cancel Mid-Build
1. Click "Cancel Build" button while status is "running"
2. **Watch for**:
   - Status changes to "cancelling" → "cancelled"
   - Backend logs: `[CloudBuild] Successfully cancelled GCP Build xxx`
   - GCP Console: Build status changes to "CANCELLED"

---

### Phase 7: Validate Cost & Performance

#### 7.1 Check GCP Billing
Visit: https://console.cloud.google.com/billing?project=cloudbuild-486309

**Monitor**:
- Build minutes used today
- Cost per build
- Quota remaining

---

#### 7.2 Performance Metrics
Record:
- Time to queue: _____ seconds
- Time to complete: _____ minutes
- Artifact size: _____ MB

**Compare to GitHub Actions** (if historical data available)

---

## Success Criteria

### ✅ All Tests Passed
- [ ] Backend starts without errors
- [ ] Cloud Build triggered via CLI wrapper (not GitHub API)
- [ ] GCP Build ID stored in database
- [ ] Build completes successfully
- [ ] Webhooks received (3 per-platform callbacks)
- [ ] Artifacts downloadable from GCS
- [ ] License wrapping applied correctly
- [ ] Cancel build works
- [ ] No GitHub Actions references in logs

---

## Troubleshooting

### Issue: Webhook 401 Unauthorized
**Cause**: Signature mismatch  
**Solution**:
```bash
# Check secret matches
gcloud secrets versions access latest --secret="callback-webhook-secret" --project=cloudbuild-486309

# Compare with .env
cat server/.env | grep BUILD_CALLBACK_SECRET
```

---

### Issue: Download URL 403 Forbidden
**Cause**: GCS signed URL expired or permissions issue  
**Solution**:
- Check `generate_gcs_signed_url()` function logs
- Verify gcloud auth: `gcloud auth list`
- Check GCS bucket permissions

---

### Issue: Build Timeout
**Cause**: Cloud Build took longer than 20 minutes  
**Solution**:
- Check `cloudbuild.yaml` timeout setting
- Review build logs for stuck steps
- Consider enabling fast build mode

---

### Issue: Import Error in Cloud Build
**Cause**: Missing dependencies in requirements.txt  
**Solution**:
- Add all bot dependencies to `requirements.txt`
- Example: `discord.py`, `python-dotenv`

---

## Rollback Plan

If Cloud Build fails completely:
```bash
# Revert to GitHub Actions
git checkout archive/github-actions

# Restart backend
cd server
uvicorn main:app --reload
```

---

## Post-Testing Cleanup

### Optional: Delete Test Builds
```bash
# Via frontend: Click "Delete Build" on test builds

# Or via GCS:
gsutil ls gs://codevault-builds/builds/
gsutil rm -r gs://codevault-builds/builds/bld_test_*
```

---

## Next Steps After Successful Test

1. **Document Results**: Note build times, costs, any issues
2. **Update Documentation**: Add Cloud Build info to user docs
3. **Monitor Production**: Watch first few real user builds
4. **Cost Analysis**: Compare GitHub Actions vs Cloud Build costs
5. **Optimize**: Tune `cloudbuild.yaml` for faster builds

---

## Support

**GCP Console**: https://console.cloud.google.com/cloud-build/builds?project=cloudbuild-486309  
**Backend Logs**: Terminal 2  
**Webhook Logs**: http://127.0.0.1:4040  
**Build Logs**: GCP Console > Build Details

---

**Last Updated**: Feb 4, 2026  
**Tester**: Parth Salunkhe  
**Status**: Ready for Testing ✅
