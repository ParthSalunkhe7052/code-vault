# Inspection Report: Security & Feature Enhancements

**Date:** 2025-12-28  
**Inspector:** Inspector Agent  
**Scope:** Builder's implementation of Offline Leases, Version Intelligence, 200MB Limits, White-Labeling

---

## 🚨 Critical Issues (Must Fix Immediately)

### 1. [SECURITY] JWT Signature NOT Verified - Offline Lease Forgery Possible

**Files:** `cli/wrappers.py` - Lines 136-175 (Python) and Lines 689-722 (Node.js)

**Problem:** Both `_lw_verify_offline_lease()` functions decode the JWT payload but **never verify the cryptographic signature**. An attacker can:
1. Create their own fake JWT with any expiry date and HWID
2. Base64-encode a fake payload
3. Replace the `.offline_lease` file
4. Run the application offline indefinitely without a valid license

**Evidence (Python wrapper):**
```python
# Line 155-165 - Only decodes, never verifies signature
parts = token.split(".")
if len(parts) != 3:
    return False
payload_b64 = parts[1]
# ... decodes payload ...
payload = _lw_json.loads(_lw_base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
# ❌ MISSING: No signature verification!
```

**Fix Required:**
- **Option A (Recommended):** Embed the JWT secret into the compiled wrapper and verify using HMAC-SHA256
- **Option B:** Use a different approach - store a server-signed hash that includes a machine-specific secret

---

### 2. [SECURITY] Legacy Node.js Wrapper Not Updated

**File:** `cli/wrappers.py` - `get_nodejs_wrapper()` function (lines 378-585)

**Problem:** The "legacy" wrapper still has the **original offline hole vulnerability**:
```javascript
// Line 544-548 in the legacy wrapper still has:
req.on('error', (e) => {
    console.error(`⚠️ Connection error: ${e.message}`);
    console.log("[License Wrapper] Running in offline mode...");
    resolve(true);  // ❌ STILL ALLOWS OFFLINE BYPASS!
});
```

**Fix Required:** Either:
- Update the legacy wrapper with offline lease support, OR
- Remove it entirely if unused

---

## ⚠️ Warnings (Fix Before Release)

### 3. [Code Quality] Linting Violations in `wrappers.py`

Multiple whitespace and line length issues:
- 30+ blank lines containing whitespace (W293)
- Multiple lines >88 characters (E501)
- Trailing whitespace (W291)

**Fix:** Run `ruff format cli/wrappers.py`

---

### 4. [Plan Deviation] `lw_compiler.py` Does Not Fetch User Tier

**Implementation Plan stated:**
> "Fetch user's tier from server when building; Pass `show_splash=False` if tier is 'enterprise'"

**Actual Implementation:**
```python
# lw_compiler.py lines 695-698 and 717-720
show_splash = config.get("show_splash", True)  # Defaults to True
```

The compiler never fetches the user's tier from the server - it just uses a config value that defaults to `True`. Enterprise users won't get white-labeling automatically.

**Fix Required:** Either:
- Fetch tier from server during build, OR
- Require server to include `show_splash` in compile-config response

---

### 5. [Missing Feature] No Test Added for Offline Lease

**Implementation Plan stated:**
> "Add test `test_validation_returns_offline_lease` in test_api_endpoints.py"

**Actual:** No new tests were added for the offline lease functionality.

---

## ✅ Passed Checks

| Check | Status |
|-------|--------|
| `config.py` - OFFLINE_LEASE_DAYS added | ✅ |
| `models.py` - offline_lease fields added | ✅ |
| `utils.py` - `create_offline_lease()` with proper JWT signing | ✅ |
| `license_routes.py` - generates offline lease on success | ✅ |
| `license_routes.py` - all 5 INSERTs updated with client_version | ✅ |
| `analytics_routes.py` - version-stats endpoint correct | ✅ |
| `storage_service.py` - MAX_ZIP_SIZE = 200MB | ✅ |
| SQL migration script created | ✅ |
| Syntax checks pass | ✅ |
| Existing tests pass (2/2, 11 skipped) | ✅ |

---

## 📋 Fix Plan for Doctor Agent

### Priority 1: CRITICAL - Fix JWT Signature Verification

**Python Wrapper** - Add HMAC verification in `_lw_verify_offline_lease()`:
```python
import hmac as _lw_hmac

# Embed a verification secret (derived from server secret)
_LW_LEASE_SECRET = "{lease_verification_key}"  # Injected at build time

def _lw_verify_offline_lease(hwid):
    # ... existing code to read file and check expiry ...
    
    # Verify signature
    parts = token.split(".")
    if len(parts) != 3:
        return False
    
    header_payload = parts[0] + "." + parts[1]
    expected_sig = _lw_base64.urlsafe_b64encode(
        _lw_hmac.new(_LW_LEASE_SECRET.encode(), header_payload.encode(), 'sha256').digest()
    ).rstrip(b'=').decode()
    
    if parts[2] != expected_sig:
        print("[License Wrapper] Invalid lease signature")
        return False
    
    # ... rest of verification ...
```

**Node.js Wrapper** - Same fix using `crypto.createHmac()`:
```javascript
const _LW_LEASE_SECRET = "{lease_verification_key}";

function _lw_verifyOfflineLease(hwid) {
    // ... existing code ...
    
    const parts = token.split('.');
    if (parts.length !== 3) return false;
    
    const headerPayload = parts[0] + '.' + parts[1];
    const expectedSig = _lw_crypto
        .createHmac('sha256', _LW_LEASE_SECRET)
        .update(headerPayload)
        .digest('base64url');
    
    if (parts[2] !== expectedSig) {
        console.log('[License Wrapper] Invalid lease signature');
        return false;
    }
    // ... rest of verification ...
}
```

**Server-side** - Add verification key to compile-config response.

### Priority 2: Remove/Fix Legacy Wrapper

Either delete `get_nodejs_wrapper()` or apply the same offline lease fix.

### Priority 3: Linting

```bash
cd CodeVaultV1
ruff format cli/wrappers.py
```

### Priority 4: Add Test

Add test for `/api/v1/license/validate` response including `offline_lease` field.
