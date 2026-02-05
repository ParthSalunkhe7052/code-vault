# MASTER EXECUTION PROTOCOL: CODE VAULT "SOLENYA" REFACTOR
**Target Audience**: AI Agent / Senior Engineer
**Objective**: Eliminate critical technical debt, secure the licensing protocol, and optimize performance.
**Directives**: Execute strictly in order. Do not skip verification steps.

---

## Phase 1: The Database Sanitation (The Purge)
**Goal**: Remove all "Marketplace" and "Whop" legacy artifacts to normalize the schema.

### Step 1.1: Backup & Clean `database.py`
**Target File**: `server/database.py`
**Instruction**:
1.  **Locate** the `init_database` function.
2.  **Delete** the following table creation blocks:
    -   `whop_integrations`
    -   `whop_purchases`
    -   `license_purchases`
3.  **Delete** the "Migration" blocks that add these columns to `projects`:
    -   `is_public`
    -   `price_cents`
    -   `currency`
    -   `store_slug`
4.  **Refactor** the `init_database` function to remove the `try...except pass` pattern. Use strictly defined `CREATE TABLE IF NOT EXISTS` statements. If a column is missing, fail fast or use a proper migration check (e.g., check `information_schema`).

### Step 1.2: Clean Data Models
**Target File**: `server/models.py`
**Instruction**:
1.  Remove `WhopIntegration`, `WhopPurchase`, and `LicensePurchase` classes.
2.  Remove `is_public`, `price`, `currency`, `store_slug` fields from `Project` models.

### Step 1.3: Verify Schema
**Verification Command**:
```bash
# Verify no "whop" strings remain in the server directory
grep -r "whop" server/ | grep -v "migration"
```

---

## Phase 2: Security Hardening (The Locks)
**Goal**: Secure the validation endpoint against concurrency attacks and spoofing.

### Step 2.1: Atomic License Validation
**Target File**: `server/routes/license_routes.py`
**Function**: `validate_license`
**Instruction**:
1.  **Replace** the select-then-insert logic for `hardware_bindings`.
2.  **Implement** a transaction with locking.
    ```python
    async with conn.transaction():
        # Lock the license row to prevent race conditions
        license_row = await conn.fetchrow(
            "SELECT id, max_machines, ... FROM licenses WHERE license_key = $1 FOR UPDATE", 
            data.license_key
        )
        # ... logic ...
        # Now check count and insert safely
        count = await conn.fetchval("SELECT COUNT(*) ...")
        if count < max_machines:
            await conn.execute("INSERT ...")
    ```

### Step 2.2: Secure Password & API Key Storage
**Target File**: `server/utils.py` & `server/routes/auth_routes.py` (if exists) or wherever `users` are created.
**Instruction**:
1.  Ensure `api_key` is **hashed** before storage, just like passwords.
2.  Update `get_current_user` to hash the incoming header key before comparing with the database.

---

## Phase 3: Async & Performance (The Speed)
**Goal**: Stop blocking the event loop.

### Step 3.1: Offload GeoIP
**Target File**: `server/routes/license_routes.py`
**Instruction**:
1.  **Remove** `run_in_threadpool(get_geo_from_ip, ...)` from the `validate_license` hot path.
2.  **Move** it to a background task using `BackgroundTasks` or simply fire-and-forget `asyncio.create_task`.
3.  **Impact**: The validation response should NOT wait for the map data.

### Step 3.2: Async File I/O
**Target File**: `server/utils.py` (or wherever file logging happens)
**Instruction**:
1.  Identify any `with open(...)` or `json.dump` to disk inside async routes.
2.  Replace with `aiofiles` or move to a threadpool if strictly necessary.

---

## Phase 4: Frontend Truth (The UI)
**Goal**: Align the UI with the Backend reality.

### Step 4.1: Dynamic Limits
**Target File**: `frontend/src/contexts/PricingContext.jsx`
**Instruction**:
1.  **Remove** the hardcoded `LIMITS` object.
2.  **Create** a new endpoint `GET /api/v1/user/limits` in the backend.
3.  **Update** `PricingProvider` to fetch these limits on load and store them in state.

### Step 4.2: Remove Optimistic Admin Override
**Target File**: `frontend/src/contexts/PricingContext.jsx`
**Instruction**:
1.  **Delete** the block: `if (user.role === 'admin') { setTier(TIERS.ENTERPRISE); ... }`.
2.  **Logic**: The admin should actually *have* an enterprise subscription in the database. The UI should just reflect the DB state.

---

## Phase 5: New Core Features (The Value)
**Goal**: Add features that justify the $29/mo price.

### Step 5.1: Variable Injection Schema
**Target File**: `server/database.py`
**Instruction**:
1.  Create table `license_variables`:
    ```sql
    CREATE TABLE IF NOT EXISTS license_variables (
        id TEXT PRIMARY KEY,
        license_id TEXT REFERENCES licenses(id),
        key TEXT NOT NULL,
        value TEXT NOT NULL, -- Encrypted?
        is_secret BOOLEAN DEFAULT FALSE
    );
    ```

### Step 5.2: Variable Injection Endpoint
**Target File**: `server/routes/license_routes.py`
**Instruction**:
1.  Update `validate_license` to fetch variables for the license.
2.  Include them in the `LicenseValidationResponse`.

---

## Verification Protocol
For each phase, the Agent must:
1.  **Apply** the changes.
2.  **Run** `pytest` (Backend) or `npm run build` (Frontend).
3.  **Verify** no regressions in existing flows.
