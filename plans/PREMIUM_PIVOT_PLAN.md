# CodeVault: Premium Pivot Implementation Plan

## Overview
Pivot CodeVault from a free-for-all money pit to a sustainable "Security-First" platform.
**Goal:** Restrict "Cloud Build" to Pro users ($19/mo). Enable robust Local Build for free users via CLI.

## Current State Analysis
- **Backend:** `server/routes/cloud_build_routes.py` allows anyone to POST `/api/build`.
- **CLI:** `cli/compiler_logic.py` contains `run_nuitka` but `cli/commands/build.py` might default to cloud or require args.
- **Frontend:** UI has a generic "Build" button.
- **Billing:** No Stripe integration for "Pro" status check.

## Implementation Approach
1.  **Phase 1: The Gate (Backend):** Add `is_pro_user()` check to `cloud_build_routes.py`.
2.  **Phase 2: The CLI (Local):** Verify and polish `cli/` to ensure `codevault build --local` works seamlessly for free users.
3.  **Phase 3: The Payment (Stripe):** Implement Stripe Webhooks and User `is_pro` status in DB.
4.  **Phase 4: The Upsell (Frontend):** Update Dashboard to show "Upgrade for Cloud Build" and guide free users to CLI.

## Phase 1: The Gate (Backend Protection)
### Overview
Stop the bleeding. Prevent non-pro users from triggering Cloud Builds.

### Changes Required:
#### 1. `server/models.py`
**Changes**: Add `is_pro` boolean and `stripe_subscription_id` to `User` model.
```python
class User(db.Model):
    # ... existing fields
    is_pro = db.Column(db.Boolean, default=False)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
```

#### 2. `server/routes/cloud_build_routes.py`
**Changes**: Add decorator or check at top of `trigger_build`.
```python
@cloud_build_bp.route('/build', methods=['POST'])
@login_required
def trigger_build():
    if not current_user.is_pro:
        return jsonify({
            "error": "Premium Feature",
            "message": "Cloud Build is a Pro feature. Use the CLI for local builds.",
            "upgrade_url": "/upgrade"
        }), 403
    # ... existing logic
```

### Success Criteria:
- [ ] `pytest tests/test_cloud_build.py` (Should fail for free user).
- [ ] Manual: POST to `/api/build` returns 403.

## Phase 2: The CLI (Local Build Polish)
### Overview
Ensure free users have a working alternative so they don't rage-quit.

### Changes Required:
#### 1. `cli/commands/build.py`
**Changes**: Add explicit `--local` flag default if not Pro (or just make it the default).
```python
# Pseudo-code update
@click.command()
@click.option('--cloud', is_flag=True, help="Run build on CodeVault Cloud (Pro only)")
def build(cloud):
    if cloud:
         # Check API for pro status, else fail
         pass
    else:
         # Run run_nuitka() locally
         pass
```

### Success Criteria:
- [ ] `codevault build` runs Nuitka locally on a sample script.

## Phase 3: The Payment (Stripe Integration)
### Overview
Process payments to toggle `is_pro`.

### Changes Required:
#### 1. `server/routes/billing_routes.py` (New)
**Changes**: Create Checkout Session and Webhook handler.
- Endpoint: `/api/billing/checkout` (Creates Stripe Session)
- Endpoint: `/api/billing/webhook` (Listens for `invoice.payment_succeeded`)

### Success Criteria:
- [ ] Stripe Test Mode payment updates user `is_pro` to True in DB.

## Phase 4: The Upsell (Frontend)
### Overview
Update UI to reflect the new reality.

### Changes Required:
#### 1. `frontend/src/components/Dashboard.tsx`
**Changes**:
- If `!user.isPro`:
    - Disable "Cloud Build" button.
    - Show tooltip: "Upgrade to Pro for Cloud Build".
    - Add "Build Locally" card with CLI instructions.

### Success Criteria:
- [ ] UI shows "Locked" icon for Cloud Build on free account.

## Implementation Note
We will start with **Phase 1 & 2** immediately to stop the cost leak. Phase 3 & 4 can follow.
