# Inspection Report: CLI Crashes and Obfuscation Issues

**Date:** 2025-12-28  
**Inspector:** Antigravity (Inspector Workflow)

## 🚨 Critical Issues (Must Fix Immediately)

### 1. [Build] Obfuscation Not Detected Despite Being Enabled in UI

![Web UI showing obfuscation enabled](file:///C:/Users/parth/.gemini/antigravity/brain/56f22604-6366-4117-8712-6deb2ed5beb8/uploaded_image_0_1766938417455.png)

![CLI showing obfuscation disabled](file:///C:/Users/parth/.gemini/antigravity/brain/56f22604-6366-4117-8712-6deb2ed5beb8/uploaded_image_1_1766938417455.png)

- **Files:** 
  - [main.py:1105](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/server/main.py#L1105) - `build-bundle` 
  - [main.py:978](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/server/main.py#L978) - `compile-config`
- **Problem:** `build-bundle` passes raw `compiler_options` from DB without tier-gating, while `compile-config` applies tier-gating logic.
- **Evidence:** CLI shows "⏭️ Obfuscation disabled in config" even though UI shows "Enabled".
- **Root Cause:** `compile-config` has tier-gating at line 978, but `build-bundle` uses raw DB value at line 1105.

### 2. [Runtime] Compiled EXE Crashes After License Entry
- **Symptoms:** App asks for license, validates successfully, then immediately crashes.
- **Possible Causes:**
  1. The original application code has an error that only surfaces after validation
  2. The async IIFE wrapper doesn't properly catch errors
  3. Missing dependencies in the bundled executable
- **Evidence:** User reports crash happens after license is entered (validation succeeds).

### 3. [UX] Terminal Cursor Jumps Above Output
- **File:** [lw_compiler.py:431](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/cli/lw_compiler.py#L431)
- **Problem:** Using `\r` (carriage return) for progress updates leaves the cursor at the beginning of the line. When more output follows, it overwrites or creates confusion.
- **Root Cause:** `print(f"\r      Downloaded: {pct}%", end="", flush=True)` moves cursor to line start.

## ⚠️ Warnings (Fix Before Release)

### 4. [Code Quality] Duplicate `run_obfuscation` Functions
- **File:** [lw_compiler.py](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/cli/lw_compiler.py)
- **Lines:** 758-823 (first definition) and 985-1062 (second definition)
- **Problem:** Same function defined twice. Python uses the second one, but the first is dead code.
- **Impact:** Confusion, potential bugs if only one is updated.

### 5. [Data] `build-bundle` Config Merging Doesn't Include `compiler_options`
- **File:** [lw_compiler.py:452](file:///c:/Users/parth/OneDrive/Desktop/Code%20Vault/CodeVaultV1/cli/lw_compiler.py#L452)
- **Problem:** When CLI merges bundle config, it only copies `license_key`, `api_url`, `server_url`, `language` - not `compiler_options`.

## ✅ Passed Checks

- Directory structure matches `CONTRIBUTING.md`.
- No hardcoded secrets in wrapper code.
- Error handling present in wrappers for uncaught exceptions.
- HMAC signature verification implemented for offline leases.

## 📊 Evidence Summary

```
[5/5] Compiling with pkg... (this may take 2-5 minutes)
📦 Installing npm dependencies...
   ✅ Dependencies installed
   ✅ Added pkg config for ESM/CJS modules
   ⏭️ Obfuscation disabled in config    ← BUG: Should be enabled!
```

## 🔮 Recommended Fix Order

1. **Fix obfuscation tier-gating in `build-bundle`** (main issue visible to user)
2. **Delete duplicate `run_obfuscation` function** (code quality)
3. **Fix terminal cursor issue** (UX)
4. **Improve crash error messages in wrapper** (debugging)
5. **Add `compiler_options` to config merge** (completeness)
