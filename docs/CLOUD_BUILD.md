# Feature: Cloud Builds
## 1. Where is the workflow created?
I have created the workflow file locally at:
`C:\Users\parth\OneDrive\Desktop\Code Vault\CodeVaultV1\.github\workflows\cloud-compile.yml`

This file is part of your source code now. **You must push this file to your GitHub repository** for the Cloud Build feature to work.

## 2. Why don't I see a new repo?
I am working on your **local file system**. I do not have permission to push code to your GitHub account directly. You need to run the following commands in your terminal to sync the changes:

```bash
cd "C:\Users\parth\OneDrive\Desktop\Code Vault\CodeVaultV1"
git add .
git commit -m "Add Cloud Build feature"
git push origin main
```

## 3. How will this compile?
Here is the step-by-step flow:
1.  **User Request:** A user clicks "Build in Cloud" on your SaaS dashboard.
2.  **API Call:** Your backend (`cloud_build_routes.py`) receives this request.
3.  **Trigger:** Your backend uses the `GITHUB_TOKEN` to send a signal to GitHub Actions (specifically the `cloud-compile.yml` workflow).
4.  **Execution:** GitHub spins up a fresh Windows virtual machine (for free, using your Student Pack).
5.  **Compilation:** This VM downloads the code, runs `nuitka`, and compiles it into an `.exe`.
6.  **Upload:** The VM uploads the result back to your R2 storage.
7.  **Notification:** The VM calls your backend's webhook to say "Done!".

## 4. Do I need to login?
*   **You (The Admin):** You just need to set the `GITHUB_TOKEN` in your `.env` file. This token acts as the "login" for the system to talk to GitHub.
*   **Your Users:** They do **not** need a GitHub account. They just log in to your SaaS as usual.

## Implementation Status
*   ✅ **Workflow:** `.github/workflows/cloud-compile.yml` created (with caching optimization).
*   ✅ **Backend:** `cloud_build_routes.py` created and fixed.
*   ✅ **Database:** Auto-migration added for `cloud_builds` table.
*   ✅ **Frontend:** `CloudBuildButton.jsx` added and integrated into the Wizard.

### Final Step for You
Run the git commands above to push the new workflow file to GitHub. Then restart your backend server.
