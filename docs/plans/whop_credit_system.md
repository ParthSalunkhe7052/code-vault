# Whop Integration & Cloud Build Credit System Plan

## Overview
This plan addresses two critical monetization features:
1.  **Whop Integration**: Allow users to sell their software on Whop.com, with CodeVault automatically generating and emailing licenses upon purchase.
2.  **Cloud Build Credits**: Enforce a "usage-based" model for the expensive Cloud Build feature (e.g., 15 credits/month for Pro), replacing the current unlimited/tier-based loose check.

## Current State Analysis
- **Billing**: Currently `polar_routes.py` handles subscriptions and direct license purchases. There is no infrastructure for 3rd party marketplaces like Whop.
- **Cloud Build**: `cloud_build_routes.py` exists but does not appear to have granular credit deduction logic, only basic tier checks via `get_user_tier_limits`.
- **Database**: The `users` table likely lacks a `build_credits` column.

## Implementation Approach
We will build a dedicated `whop_routes.py` to handle incoming webhooks from Whop. We will also modify the `users` table to track `build_credits` and update the `cloud_build` endpoint to deduct them.

---

## Phase 1: Database Schema & Models
### Overview
Add support for tracking build credits and Whop transactions.

### Changes Required:
#### 1. `CodeVaultV1/server/migrations/008_add_credits_and_whop.sql` (New)
**Goal**: Create the SQL migration.
```sql
-- Add credits to users
ALTER TABLE users ADD COLUMN build_credits INTEGER DEFAULT 0;

-- Add Whop integration table
CREATE TABLE whop_integrations (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    whop_company_id TEXT,
    whop_api_key TEXT, -- Encrypted
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add Whop purchases log
CREATE TABLE whop_purchases (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id), -- The developer
    whop_payment_id TEXT UNIQUE,
    license_id TEXT REFERENCES licenses(id),
    buyer_email TEXT,
    amount_cents INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. `CodeVaultV1/server/models.py`
**Goal**: Update Pydantic/SQLAlchemy models (if applicable, though codebase seems to use raw SQL `databases` package mostly).
**Changes**:
- Document the new fields for future reference.

### Success Criteria:
- [x] `npm run test` (or project equivalent)
- [x] `curl -X POST localhost:8000/api/v1/whop/webhook` with a valid mock payload generates a license in the DB.

---

## Phase 3: Cloud Build Credit System
### Overview
Enforce credit limits on cloud builds.

### Changes Required:
#### 1. `CodeVaultV1/server/app/core/config.py` (or `CodeVaultV1/server/config.py`)
**Goal**: Define credit costs.
```python
BUILD_COST_STANDARD = 1
BUILD_COST_FAST = 0  # Maybe free for dev? Or 0.5?
```

#### 2. `CodeVaultV1/server/routes/cloud_build_routes.py`
**Goal**: Check and deduct credits before starting build.
**Changes**:
- In `create_build`:
  1. Check `user.build_credits > 0`.
  2. If yes, proceed.
  3. **Transaction**: Deduct 1 credit AND create build job.
  4. If fail, rollback.

#### 3. `CodeVaultV1/server/routes/polar_routes.py`
**Goal**: Reset/Top-up credits on subscription renewal.
**Changes**:
- In `handle_order_paid`:
  - `UPDATE users SET build_credits = 15 WHERE id = ...` (For Pro)
  - `UPDATE users SET build_credits = 50 WHERE id = ...` (For Business)

### Success Criteria:
- [x] User with 0 credits receives 403 when trying to build.
- [x] User with 1 credit can build, and balance goes to 0.

---

## Phase 4: CLI "Whoami" Update
### Overview
Let users see their credit balance.

### Changes Required:
#### 1. `CodeVaultV1/server/routes/auth_routes.py`
**Goal**: Return `build_credits` in the `/me` endpoint.

#### 2. `CodeVaultV1/cli/commands/auth.py`
**Goal**: Print `Credits: X` in `codevault whoami`.

### Success Criteria:
- [x] `codevault whoami` prints "Build Credits: 15".

