# Code Vault Production Implementation Plan (AI-Ready)

This plan outlines the technical steps required to finalize the production deployment of Code Vault.

## Phase 1: Build System Correction (High Priority)

### 1.1 Update Cloud Build Config Path
The `CloudBuildClient` currently points to a legacy YAML file.
- **File:** `server/routes/cloud_build_routes.py` (Wait, actually it's in the client scripts)
- **Files:** `scripts/cloud_build_integration.py` and `scripts/cloud_build_cli_wrapper.py`
- **Action:** Change `cloudbuild_path` to point to the root `cloudbuild.yaml`.
- **Logic:** 
  ```python
  # From:
  cloudbuild_path = os.path.join(os.path.dirname(__file__), "cloudbuild.yaml")
  # To:
  cloudbuild_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloudbuild.yaml")
  ```

### 1.2 Update Root cloudbuild.yaml Substitutions
Remove hardcoded legacy URLs.
- **File:** `cloudbuild.yaml` (Root)
- **Action:** Update `_CALLBACK_URL` default to be empty or a generic placeholder, ensuring the server-passed value always takes precedence.

## Phase 2: Configuration & Environment Sync

### 2.1 Standardize Environment Variable Checks
- **File:** `server/config.py`
- **Action:** Ensure `ENVIRONMENT="production"` triggers strict checks for `POLAR_WEBHOOK_SECRET` and `BUILD_CALLBACK_SECRET`.

### 2.2 Landing Page Rewrite
Ensure the landing page handles direct navigations correctly on Vercel.
- **File:** `landing-page/vercel.json`
- **Action:** Add `rewrites` array similar to `frontend/vercel.json` if routing is introduced.

## Phase 3: Performance & Cleanup

### 3.1 Optimize Landing Page Build
- **File:** `landing-page/vite.config.ts`
- **Action:** Add minification and console stripping for production.
- **Logic:**
  ```typescript
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
      },
    },
  }
  ```

### 3.2 Dependency Version Alignment (Optional/Staging)
- **Action:** Plan a migration for `frontend` to React 19 to match the `landing-page`.

## Phase 4: Verification

### 4.1 Webhook Connectivity Test
- **Action:** Use a mock payload to verify `api/v1/polar/webhook` and `api/v1/cloud-build/webhook` signature verification logic with the production secrets.

### 4.2 Database SSL Verification
- **Action:** Confirm `DATABASE_URL` from Heroku includes `sslmode=require` and that `server/database.py` successfully initializes the `asyncpg` pool with the provided SSL context.

## Success Criteria
- [ ] `scripts/cloud_build_integration.py` uses the root `cloudbuild.yaml`.
- [ ] `cloudbuild.yaml` successfully sends a callback to the production domain.
- [ ] Polar webhooks are verified with `POLAR_WEBHOOK_SECRET`.
- [ ] All production environment variables are documented and validated.
