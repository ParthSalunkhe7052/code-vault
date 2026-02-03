# QUICK SETUP GUIDE - Google Cloud Build for CodeVault

## Your Credentials (Keep this safe!)

```
HMAC/Webhook Secret: cv_build_secret_72b2b66ab650
GitHub Repo: ParthSalunkhe7052/code-vault
Google Project: cloudbuild-486309
```

**Note:** Keep your GitHub token secure - never commit it to Git!

## Step-by-Step Instructions

### 1. Install Google Cloud SDK (In Progress)
- The installer should be open now
- Click "Next" through all prompts
- ✅ Check "Run 'gcloud init'" at the end
- Click "Finish"

### 2. After Installation - Run This Command

Open a NEW PowerShell/Terminal window and run:

```powershell
cd "C:\Users\parth\OneDrive\Desktop\Code Vault"
python setup_cloud_build.py
```

### 3. When Script Asks for Secrets

**Question:** "Enter your webhook secret (HMAC key):"
**Answer:** `cv_build_secret_72b2b66ab650`

### 4. GitHub Connection

The script will open a browser asking you to:
- Connect your GitHub account
- Select repository: ParthSalunkhe7052/code-vault
- Click "Connect"

### 5. Done! 🎉

The script will:
- Create GCS bucket: codevault-builds
- Store your webhook secret securely
- Configure all permissions
- Push cloudbuild.yaml to GitHub

---

## After Setup - Update Your Backend

Replace this GitHub Actions code:
```python
# OLD - GitHub Actions
url = f"https://api.github.com/repos/{REPO}/actions/workflows/cloud-compile.yml/dispatches"
headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
response = requests.post(url, json=payload, headers=headers)
```

With this Cloud Build code:
```python
# NEW - Google Cloud Build
from cloud_build_integration import CloudBuildClient

cloud_build = CloudBuildClient(project_id="cloudbuild-486309")
result = cloud_build.trigger_build({
    "build_id": "build-123",
    "project_id": "user-project-abc",
    "language": "python",
    "target_platforms": "windows,linux",
    "source_url": "https://your-presigned-url/source.zip",
    "config": {
        "entry_file": "main.py",
        "output_name": "my-app"
    },
    "callback_url": "https://your-api.com/webhook/complete"
})
```

---

## Troubleshooting

**"gcloud: command not found" after installation**
- Close and reopen your terminal
- Or add to PATH manually:
  - C:\Users\[YOUR_USERNAME]\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin

**Script fails with authentication error**
- Run: `gcloud auth login`
- Run: `gcloud auth application-default login`

**GitHub connection fails**
- Make sure you're logged into GitHub in your browser
- Make sure you have admin access to the repository

---

## Next Command to Run

```powershell
# After gcloud installation completes:
cd "C:\Users\parth\OneDrive\Desktop\Code Vault"
python setup_cloud_build.py
```

That's it! The script handles everything else automatically.
