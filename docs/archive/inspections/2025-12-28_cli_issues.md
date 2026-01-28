# Inspection Report: CLI Issues After Obfuscation Implementation

**Date:** 2025-12-28  
**Inspector:** Antigravity (Inspector Workflow)

## 🚨 Critical Issues (Must Fix Immediately)

### 1. [UX] CLI Terminal Cannot Scroll
- **File:** [Run CLI.bat](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/Run%20CLI.bat#L4)
- **Line:** 4
- **Problem:** `mode con: cols=100 lines=35` sets a fixed 35-line buffer which prevents scrolling.
- **Impact:** Users cannot see previous output, build logs, or error messages.
- **Fix:** Remove or increase the `lines=` value to allow scrollback (e.g., `lines=9999` or remove entirely).

### 2. [Auth] Email Login Is Case-Sensitive
- **File:** [auth_routes.py](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/server/routes/auth_routes.py#L68-71)
- **Problem:** SQL query `WHERE email = $1` performs exact match, so `Parth.ajit7052@gmail.com` ≠ `parth.ajit7052@gmail.com`.
- **Impact:** Users with capital letters in their email cannot log in.
- **Fix:** Normalize emails to lowercase on both registration and login:
  ```python
  data.email.lower()
  ```

### 3. [Build] Entry File Detection Shows `main.py` for Node.js Projects
- **File:** [main.py](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/server/main.py#L1061-1062)
- **Problem:** The `build-bundle` endpoint defaults to `main.py` regardless of project language:
  ```python
  "entry_file": settings.get("entry_file", "main.py" if language == "python" else "index.js")
  ```
  But the `language` variable may be incorrect (says `python` for Node.js projects).
- **Impact:** Node.js builds fail with "Entry file not found: main.py".
- **Root Cause:** The project's `language` field is being set/stored incorrectly, OR `settings.get("entry_file")` returns `None` when it should return detected entry point.

## ⚠️ Warnings (Fix Before Release)

### 4. [Data Integrity] Email Stored Without Normalization
- **File:** [auth_routes.py](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/server/routes/auth_routes.py#L37-42)
- **Problem:** Registration stores email as-is without normalizing to lowercase.
- **Impact:** Same user could accidentally create multiple accounts with different cases.

### 5. [Logic] `compile-config` vs `build-bundle` Inconsistency
- **Files:** 
  - [main.py:get_compile_config](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/server/main.py#L891-935) - Has smart entry file detection
  - [main.py:get_build_bundle](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/server/main.py#L1061-1062) - Uses simple fallback
- **Problem:** The `compile-config` endpoint (lines 891-935) has sophisticated entry file detection that checks files, but `build-bundle` (lines 1061-1062) ignores this and uses a simple fallback.
- **Impact:** The two endpoints return different `entry_file` values for the same project.

### 6. [CLI] Project Language Reported Incorrectly
- **File:** [lw_compiler.py:cmd_build](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/cli/lw_compiler.py#L373)
- **Evidence:** Build output shows `Language: nodejs` but still tries to use `main.py`.
- **Problem:** The `compile-config` endpoint returns correct `language: nodejs` but wrong `entry_file: main.py`.

## ✅ Passed Checks

- Directory structure matches `CONTRIBUTING.md`.
- No hardcoded secrets found in production code.
- `.env.example` exists and `.env` is properly gitignored.
- Test files exist at `tests/test_api_endpoints.py` and `tests/test_structure.py`.

## 📊 Evidence Summary

```
[1/5] Fetching project configuration...
      Project: Test Obf
      Entry file: main.py         ← WRONG! Should be index.js
      Output: test_obf.exe
      Language: nodejs            ← Correct

[WARN] Entry file not found: C:\...\main.py  ← Confirms mismatch
```

## 🔮 Recommended Fix Order

1. **Fix scrolling** (quickest win, immediate UX impact)
2. **Fix email case sensitivity** (auth blocker)
3. **Fix entry file detection in `build-bundle`** (build-breaking)
4. **Normalize email on registration** (data hygiene)
