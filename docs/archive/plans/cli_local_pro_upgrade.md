# 🚀 CodeVault CLI Upgrade Plan: "Local Pro"

> **Date:** December 28, 2025  
> **Status:** Ready for Builder  
> **Priority:** P0 - Critical (Must fix before selling)

---

## 1. Executive Summary

The CLI (`lw_compiler.py`) is the core build tool. It currently lacks two **critical "Pro" features**:
1. **JavaScript Obfuscation** - Code exists on server, but not in CLI.
2. **Build Reporting** - Dashboard never sees CLI build history.

This plan ports these features to the CLI and cleans up dead server code.

**CURRENT STATUS:**
- Phase 0: Critical Fixes ✅ (Restored `nodejs_compiler.py`)
- Phase 1: CLI Obfuscation 🚧 (PENDING)
- Phase 2: Build Reporting 🔴 (PENDING)
- Phase 3: Cleanup 🔴 (PENDING)

---

## 2. Prerequisites Checklist

- [ ] Verify `npx` is available on dev machine (`npx --version`)
- [ ] Verify `javascript-obfuscator` can be run via npx (`npx javascript-obfuscator --version`)
- [ ] Backup current `cli/lw_compiler.py` before modifications

---

## 3. Phase 1: Add Obfuscation to CLI

### 3.1 New Function: `run_obfuscation()`

**File:** `cli/lw_compiler.py`  
**Location:** After `run_pkg()` function (around line 880)

```python
def run_obfuscation(project_dir: Path, config: dict) -> bool:
    """Run JavaScript obfuscation using javascript-obfuscator.
    
    Returns True if obfuscation succeeded or was skipped gracefully.
    """
    # Check if obfuscation is enabled in config
    obfuscate = config.get("compiler_options", {}).get("obfuscate", False)
    if not obfuscate:
        print("   ⏭️ Obfuscation disabled in config")
        return True
    
    # Check if npx is available
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    
    try:
        # Test npx availability
        result = subprocess.run([npx_cmd, "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            color_print("⚠️ npx not found. Skipping obfuscation.", Colors.YELLOW)
            return True  # Continue build without obfuscation
    except (FileNotFoundError, subprocess.TimeoutExpired):
        color_print("⚠️ npx not available. Skipping obfuscation.", Colors.YELLOW)
        return True
    
    print("🔒 Obfuscating JavaScript code...")
    
    cmd = [
        npx_cmd,
        "-y",  # Auto-confirm installation
        "javascript-obfuscator@4",
        str(project_dir),
        "--output", str(project_dir),
        "--ignore-require-imports", "true",
        "--compact", "true",
        "--control-flow-flattening", "true",
        "--string-array", "true",
        "--string-array-encoding", "rc4",
        "--exclude", "**/node_modules/**",
        "--exclude", "node_modules/**",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode != 0:
            color_print(f"⚠️ Obfuscation warning: {result.stderr[:200]}", Colors.YELLOW)
            print("   Continuing build without obfuscation...")
            return True
        
        color_print("✅ Obfuscation completed", Colors.GREEN)
        return True
        
    except subprocess.TimeoutExpired:
        color_print("⚠️ Obfuscation timed out. Skipping.", Colors.YELLOW)
        return True
    except Exception as e:
        color_print(f"⚠️ Obfuscation error: {e}. Skipping.", Colors.YELLOW)
        return True
```

### 3.2 Integrate into Build Pipeline

**File:** `cli/lw_compiler.py`  
**Function:** `run_pkg()` (around line 876)

**Change:** Add obfuscation call **before** `pkg` bundling:

```diff
+    # Run obfuscation if enabled (BEFORE pkg bundles the code)
+    if config.get("language") == "nodejs":
+        run_obfuscation(pkg_cwd, config)
+    
     cmd = [
         npx_cmd,
         "-y",
         "pkg@5.8.1",
```

---

## 4. Phase 2: Add Build Reporting

### 4.1 New Server Endpoint

**File:** `server/main.py`  
**Location:** After CLI endpoints section (around line 1077)

```python
class BuildReportRequest(BaseModel):
    project_id: str
    status: str  # "success" | "failed"
    duration_seconds: int
    output_name: Optional[str] = None
    logs: Optional[str] = None

@app.post("/api/v1/builds/report")
async def report_build(
    data: BuildReportRequest,
    user: dict = Depends(get_current_user),
):
    """CLI reports build completion to server for history tracking."""
    conn = await get_db()
    try:
        # Verify project ownership
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            data.project_id, user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Insert into compile_jobs for history
        job_id = secrets.token_hex(16)
        now = utc_now()
        
        await conn.execute(
            """
            INSERT INTO compile_jobs 
                (id, project_id, status, progress, output_filename, logs, created_at, completed_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            job_id, data.project_id, data.status, 100,
            data.output_name, json.dumps([data.logs or ""]),
            now, now,
        )
        
        return {"job_id": job_id, "status": "recorded"}
    finally:
        await release_db(conn)
```

### 4.2 CLI Report Function

**File:** `cli/lw_compiler.py`  
**Location:** After `run_obfuscation()` function

```python
def report_build_to_server(
    project_id: str,
    status: str,
    duration: int,
    output_name: str = None,
    logs: str = None
):
    """Report build completion to server for dashboard history."""
    headers = get_headers()
    api_url = get_api_base()
    
    if not headers:
        return  # Not logged in, skip silently
    
    try:
        resp = requests.post(
            f"{api_url}/builds/report",
            headers=headers,
            json={
                "project_id": project_id,
                "status": status,
                "duration_seconds": duration,
                "output_name": output_name,
                "logs": logs,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            color_print("📤 Build reported to dashboard", Colors.DIM)
    except Exception:
        pass  # Silently fail - reporting is optional
```

### 4.3 Call Report at End of Build

**File:** `cli/lw_compiler.py`  
**Function:** `cmd_build()` (around line 503)

**Change:** Track duration and report at completion:

```diff
+    build_start_time = time.time()
     success = run_compiler(source_dir, config)
 
     if success:
         copy_output(source_dir, config, effective_license, args.output)
         color_print("\n✅ Build complete!", Colors.GREEN)
+        
+        # Report to server
+        duration = int(time.time() - build_start_time)
+        report_build_to_server(
+            project_id=project_id,
+            status="success",
+            duration=duration,
+            output_name=config.get("output_name"),
+        )
     else:
         color_print("\n❌ Compilation failed.", Colors.RED)
+        
+        duration = int(time.time() - build_start_time)
+        report_build_to_server(
+            project_id=project_id,
+            status="failed",
+            duration=duration,
+        )
```

---

## 5. Phase 3: Cleanup Dead Code

### 5.1 Files to DELETE

| Path | Reason |
|:-----|:-------|
| `src-tauri/` (entire folder) | Legacy desktop app, replaced by Web+CLI |
| `server/compilers/nodejs_compiler.py` | Logic moved to CLI |
| `server/compilers/build_orchestrator.py` | No longer used |
| `server/compilers/templates/` | Only used by server compilers |

### 5.2 Code to REMOVE from `server/main.py`

- [ ] Remove `compile_jobs_cache` dictionary (line ~60)
- [ ] Remove `@app.post("/api/v1/build/installer/start")` endpoint
- [ ] Remove `_run_installer_build_job()` async function
- [ ] Remove `@app.get("/api/v1/build/installer/{job_id}/status")` endpoint
- [ ] Remove `@app.delete("/api/v1/build/installer/{job_id}/cancel")` endpoint
- [ ] Keep `@app.post("/api/v1/compile/start")` - refactor to show "Use CLI" message instead

---

## 6. Verification Checklist

### 6.1 Obfuscation Test
- [ ] Create a simple Node.js project with `.js` files
- [ ] Run `lw-compiler build <project_id>` with obfuscation enabled
- [ ] Open the generated `.exe` with a hex editor or unpack it
- [ ] Verify the JS code inside is obfuscated (garbled variable names)

### 6.2 Build Reporting Test
- [ ] Run `lw-compiler build <project_id>`
- [ ] Open Dashboard → Recent Activity
- [ ] Verify "Build completed (success)" appears within 5 seconds

### 6.3 Regression Test
- [ ] Python project builds still work (Nuitka)
- [ ] License validation still works in compiled .exe
- [ ] Dashboard shows all existing features

---

## 7. Rollback Plan

If any phase fails:
1. **Phase 1 (Obfuscation):** Remove the new function. CLI still works, just without obfuscation.
2. **Phase 2 (Reporting):** Remove endpoint and CLI call. Dashboard just won't show CLI builds.
3. **Phase 3 (Cleanup):** Don't delete. Keep dead code until P1/P2 are stable.

---

## 8. Next Steps (Post-Implementation)

1. [ ] Update `docs/reality-check/reality_check_report.md` with new "Implemented" status
2. [ ] Update `docs/PROJECT_DOCUMENTATION.md` CLI section with obfuscation flags
3. [ ] Consider adding `--obfuscate` CLI flag for explicit control
