// Compiler commands for Nuitka integration with real-time progress
// Uses tokio::process for non-blocking async execution
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tauri::Emitter;
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader};

#[derive(Debug, Deserialize)]
pub struct StartCompileRequest {
    pub project_path: String,
    pub entry_file: String,
    pub output_name: Option<String>,
    pub output_dir: Option<String>,
    pub license_key: Option<String>,
    pub server_url: Option<String>,  // License server URL
    pub onefile: Option<bool>,
    pub console: Option<bool>,
    pub icon_path: Option<String>,
    // Enhanced compilation options
    pub include_packages: Option<Vec<String>>,     // Python packages to include
    pub exclude_packages: Option<Vec<String>>,     // Python packages to exclude
    pub include_data_dirs: Option<Vec<String>>,    // Data directories to bundle
    pub include_data_files: Option<Vec<String>>,   // Individual files to bundle
    pub env_values: Option<std::collections::HashMap<String, String>>, // .env values to bake in
    pub install_requirements: Option<bool>,        // Auto-install deps before compile
    pub requirements_path: Option<String>,         // Path to requirements.txt
    pub build_frontend: Option<bool>,              // Build frontend before compile
    pub frontend_dir: Option<String>,              // Frontend directory (e.g., "frontend")
    pub create_launcher: Option<bool>,             // Create launcher batch file
    // Bundle requirements.txt for first-run installation
    pub bundle_requirements: Option<bool>,         // Bundle requirements.txt with output
    // Separate frontend handling  
    pub split_frontend: Option<bool>,              // Create separate frontend package instead of bundling
    // Demo mode configuration
    pub demo_mode: Option<bool>,                   // Enable demo/trial mode
    pub demo_duration_minutes: Option<u32>,        // Demo duration in minutes (30, 60, 120, etc.)
}

/// Progress event sent to frontend during compilation
#[derive(Clone, Serialize)]
pub struct CompilationProgress {
    pub job_id: String,
    pub progress: u32,
    pub message: String,
    pub stage: String,
}

/// Result of compilation
#[derive(Clone, Serialize)]
pub struct CompilationResult {
    pub job_id: String,
    pub success: bool,
    pub output_path: Option<String>,
    pub error_message: Option<String>,
}

/// Project structure scan result
#[derive(Clone, Serialize, Debug)]
pub struct ProjectStructure {
    pub packages: Vec<String>,
    pub data_dirs: Vec<String>,
    pub entry_candidates: Vec<String>,
    pub has_requirements: bool,
    pub requirements_packages: Vec<String>,
    pub has_env: bool,
    pub env_keys: Vec<String>,
    pub has_frontend: bool,
    pub frontend_framework: Option<String>,
}

/// Frontend framework detection result
#[derive(Clone, Serialize, Debug)]
pub struct FrontendInfo {
    pub framework: String,
    pub path: String,
    pub has_dist: bool,
    pub build_command: String,
}

/// Detect all Python packages in a project directory
fn detect_python_packages(project_path: &std::path::Path) -> Vec<String> {
    let mut packages = Vec::new();
    
    fn scan_dir(dir: &std::path::Path, base: &std::path::Path, packages: &mut Vec<String>) {
        if let Ok(entries) = std::fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let init_file = path.join("__init__.py");
                    if init_file.exists() {
                        // This is a Python package
                        if let Ok(rel_path) = path.strip_prefix(base) {
                            let package_name = rel_path
                                .to_string_lossy()
                                .replace("\\", ".")
                                .replace("/", ".");
                            if !package_name.starts_with("__") && !package_name.starts_with(".") {
                                packages.push(package_name);
                            }
                        }
                        // Recursively scan sub-packages
                        scan_dir(&path, base, packages);
                    }
                }
            }
        }
    }
    
    scan_dir(project_path, project_path, &mut packages);
    packages
}

/// Detect data directories (non-Python folders with data files)
fn detect_data_directories(project_path: &std::path::Path) -> Vec<String> {
    let mut data_dirs = Vec::new();
    let common_data_names = ["config", "templates", "static", "assets", "data", "resources", "public", "views"];
    
    if let Ok(entries) = std::fs::read_dir(project_path) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let dir_name = path.file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("");
                
                // Skip hidden dirs, Python cache, and venv
                if dir_name.starts_with(".") || dir_name.starts_with("__") || 
                   dir_name == "venv" || dir_name == ".venv" || dir_name == "node_modules" {
                    continue;
                }
                
                // Check if it's a common data directory
                let is_common_data = common_data_names.iter().any(|n| dir_name.eq_ignore_ascii_case(n));
                
                // Or it's a directory without __init__.py (not a Python package)
                let init_file = path.join("__init__.py");
                let is_data_dir = !init_file.exists();
                
                if is_common_data || is_data_dir {
                    // Verify it has actual files
                    if let Ok(sub_entries) = std::fs::read_dir(&path) {
                        let has_files = sub_entries
                            .flatten()
                            .any(|e| e.path().is_file());
                        if has_files {
                            data_dirs.push(dir_name.to_string());
                        }
                    }
                }
            }
        }
    }
    
    data_dirs
}

/// Detect entry file candidates (Python/JavaScript files with entry patterns)
fn detect_entry_candidates(project_path: &std::path::Path) -> Vec<String> {
    let mut candidates = Vec::new();
    let py_common = ["main.py", "app.py", "run.py", "server.py", "__main__.py"];
    let js_common = ["index.js", "main.js", "app.js", "server.js", "start.js"];
    
    if let Ok(entries) = std::fs::read_dir(project_path) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    // Python files
                    if name.ends_with(".py") {
                        if py_common.contains(&name) {
                            candidates.insert(0, name.to_string());
                        } else if let Ok(content) = std::fs::read_to_string(&path) {
                            if content.contains("if __name__") && content.contains("__main__") {
                                candidates.push(name.to_string());
                            }
                        }
                    }
                    // JavaScript/TypeScript files
                    else if name.ends_with(".js") || name.ends_with(".mjs") || name.ends_with(".ts") {
                        if js_common.contains(&name) {
                            candidates.insert(0, name.to_string());
                        } else {
                            candidates.push(name.to_string());
                        }
                    }
                }
            }
        }
    }
    
    candidates
}

/// Parse requirements.txt file
fn parse_requirements_file(project_path: &std::path::Path) -> Vec<String> {
    let req_path = project_path.join("requirements.txt");
    if let Ok(content) = std::fs::read_to_string(&req_path) {
        content
            .lines()
            .filter(|line| !line.trim().is_empty() && !line.trim().starts_with('#'))
            .map(|line| {
                // Extract package name (before any version specifier)
                line.split(&['=', '<', '>', '!', '['][..])
                    .next()
                    .unwrap_or(line)
                    .trim()
                    .to_string()
            })
            .filter(|name| !name.is_empty())
            .collect()
    } else {
        Vec::new()
    }
}

/// Parse .env file to get keys
fn parse_env_file(project_path: &std::path::Path) -> std::collections::HashMap<String, String> {
    let env_path = project_path.join(".env");
    let mut env_map = std::collections::HashMap::new();
    
    if let Ok(content) = std::fs::read_to_string(&env_path) {
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            if let Some((key, value)) = line.split_once('=') {
                let key = key.trim().to_string();
                let value = value.trim().trim_matches('"').trim_matches('\'').to_string();
                env_map.insert(key, value);
            }
        }
    }
    
    env_map
}

/// Detect frontend framework
fn detect_frontend_framework(project_path: &std::path::Path) -> Option<FrontendInfo> {
    let package_json_path = project_path.join("package.json");
    if !package_json_path.exists() {
        // Check for frontend subdirectory
        let frontend_path = project_path.join("frontend").join("package.json");
        if frontend_path.exists() {
            return detect_frontend_in_dir(&project_path.join("frontend"));
        }
        return None;
    }
    
    detect_frontend_in_dir(project_path)
}

fn detect_frontend_in_dir(dir: &std::path::Path) -> Option<FrontendInfo> {
    let package_json_path = dir.join("package.json");
    if let Ok(content) = std::fs::read_to_string(&package_json_path) {
        if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
            let deps = json.get("dependencies")
                .and_then(|d| d.as_object())
                .map(|o| o.keys().cloned().collect::<Vec<_>>())
                .unwrap_or_default();
            
            let dev_deps = json.get("devDependencies")
                .and_then(|d| d.as_object())
                .map(|o| o.keys().cloned().collect::<Vec<_>>())
                .unwrap_or_default();
            
            let all_deps: Vec<_> = deps.iter().chain(dev_deps.iter()).collect();
            
            let (framework, build_cmd) = if all_deps.iter().any(|d| d.contains("react")) {
                ("react", "npm run build")
            } else if all_deps.iter().any(|d| d.contains("vue")) {
                ("vue", "npm run build")
            } else if all_deps.iter().any(|d| d.contains("@angular")) {
                ("angular", "ng build")
            } else if all_deps.iter().any(|d| d.as_str() == "next") {
                ("next", "npm run build")
            } else if all_deps.iter().any(|d| d.as_str() == "vite") {
                ("vite", "npm run build")
            } else {
                return None;
            };
            
            let dist_path = dir.join("dist");
            let has_dist = dist_path.exists();
            
            return Some(FrontendInfo {
                framework: framework.to_string(),
                path: dir.to_string_lossy().to_string(),
                has_dist,
                build_command: build_cmd.to_string(),
            });
        }
    }
    None
}

/// Install requirements using pip
async fn install_requirements(
    project_path: &std::path::Path,
    requirements_path: &str,
    window: &tauri::Window,
    job_id: &str,
) -> Result<(), String> {
    let req_full_path = project_path.join(requirements_path);
    
    if !req_full_path.exists() {
        return Err(format!("Requirements file not found: {}", req_full_path.display()));
    }
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.to_string(),
        progress: 5,
        message: "Installing dependencies from requirements.txt...".to_string(),
        stage: "installing".to_string(),
    }).ok();
    
    let output = Command::new("pip")
        .args(["install", "-r", requirements_path])
        .current_dir(project_path)
        .output()
        .await
        .map_err(|e| format!("Failed to run pip install: {}", e))?;
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("pip install failed: {}", stderr));
    }
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.to_string(),
        progress: 10,
        message: "Dependencies installed successfully".to_string(),
        stage: "installed".to_string(),
    }).ok();
    
    Ok(())
}

/// Build frontend project
async fn build_frontend_project(
    frontend_path: &std::path::Path,
    window: &tauri::Window,
    job_id: &str,
) -> Result<String, String> {
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.to_string(),
        progress: 15,
        message: "Building frontend project...".to_string(),
        stage: "building-frontend".to_string(),
    }).ok();
    
    // Run npm install first
    let npm_install = Command::new("npm")
        .args(["install"])
        .current_dir(frontend_path)
        .output()
        .await
        .map_err(|e| format!("Failed to run npm install: {}", e))?;
    
    if !npm_install.status.success() {
        let stderr = String::from_utf8_lossy(&npm_install.stderr);
        return Err(format!("npm install failed: {}", stderr));
    }
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.to_string(),
        progress: 20,
        message: "Building frontend (npm run build)...".to_string(),
        stage: "building-frontend".to_string(),
    }).ok();
    
    // Run npm build
    let npm_build = Command::new("npm")
        .args(["run", "build"])
        .current_dir(frontend_path)
        .output()
        .await
        .map_err(|e| format!("Failed to run npm build: {}", e))?;
    
    if !npm_build.status.success() {
        let stderr = String::from_utf8_lossy(&npm_build.stderr);
        return Err(format!("npm build failed: {}", stderr));
    }
    
    // Return dist path
    let dist_path = frontend_path.join("dist");
    if !dist_path.exists() {
        // Try build folder (for Next.js, Create React App)
        let build_path = frontend_path.join("build");
        if build_path.exists() {
            return Ok(build_path.to_string_lossy().to_string());
        }
        return Err("Build folder (dist/ or build/) not found after npm build".to_string());
    }
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.to_string(),
        progress: 25,
        message: "Frontend built successfully".to_string(),
        stage: "frontend-ready".to_string(),
    }).ok();
    
    Ok(dist_path.to_string_lossy().to_string())
}

/// Generate launcher batch file for full-stack applications
/// Creates a comprehensive launcher that starts backend and frontend, opens browser, and handles shutdown
fn generate_launcher_batch(
    output_dir: &std::path::Path,
    backend_exe: &str,
    frontend_dist: Option<&str>,
    output_name: &str,
) -> Result<String, String> {
    let batch_content = if let Some(frontend) = frontend_dist {
        // Full-stack launcher with frontend server
        format!(r#"@echo off
setlocal enabledelayedexpansion
title {output_name} - Application Launcher
color 0B

echo.
echo =====================================================
echo     {output_name} - Full-Stack Application
echo =====================================================
echo.

:: Check if required ports are available
netstat -an | find "8000" >nul 2>&1
if %errorlevel%==0 (
    echo [WARNING] Port 8000 may be in use. Backend might fail to start.
)

netstat -an | find "3000" >nul 2>&1
if %errorlevel%==0 (
    echo [WARNING] Port 3000 may be in use. Frontend might fail to start.
)

:: Store current directory
set "SCRIPT_DIR=%~dp0"

:: Start backend server in background
echo [1/4] Starting backend server...
start /B "Backend" "%SCRIPT_DIR%{backend_exe}"

:: Wait for backend to initialize
echo [2/4] Waiting for backend to initialize...
timeout /t 4 /nobreak > nul

:: Check if backend is running
tasklist /FI "IMAGENAME eq {backend_exe}" 2>nul | find /I "{backend_exe}" >nul
if errorlevel 1 (
    echo [ERROR] Backend failed to start!
    echo         Check the console output for errors.
    pause
    exit /b 1
)

echo       [OK] Backend server started on http://localhost:8000

:: Start frontend server
echo [3/4] Starting frontend server...
cd /d "{frontend}"
start /B "Frontend" npx serve -s . -l 3000 -n

:: Wait for frontend to initialize
timeout /t 3 /nobreak > nul

:: Open browser
echo [4/4] Opening browser...
start "" "http://localhost:3000"

echo.
echo =====================================================
echo   {output_name} is now running!
echo =====================================================
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
echo   Press any key to STOP the application...
echo =====================================================
echo.

pause > nul

echo.
echo Stopping application...

:: Kill processes gracefully
taskkill /IM "{backend_exe}" /F 2>nul
taskkill /IM node.exe /F 2>nul

echo.
echo Application stopped. Goodbye!
timeout /t 2 /nobreak > nul
"#, output_name = output_name, backend_exe = backend_exe, frontend = frontend)
    } else {
        // Simple launcher for backend-only applications
        format!(r#"@echo off
setlocal
title {output_name}
color 0B

echo.
echo =====================================================
echo     {output_name} - Starting Application
echo =====================================================
echo.

:: Store current directory
set "SCRIPT_DIR=%~dp0"

echo Starting {output_name}...
"%SCRIPT_DIR%{backend_exe}"

:: If we get here, the app has exited
echo.
echo Application has stopped.
pause
"#, output_name = output_name, backend_exe = backend_exe)
    };
    
    let batch_path = output_dir.join(format!("{}_launcher.bat", output_name));
    std::fs::write(&batch_path, batch_content)
        .map_err(|e| format!("Failed to create launcher: {}", e))?;
    
    Ok(batch_path.to_string_lossy().to_string())
}

/// Copy a directory recursively to a destination
fn copy_dir_recursive(src: &std::path::Path, dst: &std::path::Path) -> Result<(), String> {
    if !src.exists() {
        return Err(format!("Source directory does not exist: {}", src.display()));
    }
    
    // Create destination directory
    std::fs::create_dir_all(dst)
        .map_err(|e| format!("Failed to create directory {}: {}", dst.display(), e))?;
    
    // Iterate through source directory
    for entry in std::fs::read_dir(src)
        .map_err(|e| format!("Failed to read directory {}: {}", src.display(), e))?
    {
        let entry = entry.map_err(|e| format!("Failed to read entry: {}", e))?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        
        if src_path.is_dir() {
            // Recursively copy subdirectory
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            // Copy file
            std::fs::copy(&src_path, &dst_path)
                .map_err(|e| format!("Failed to copy {} to {}: {}", src_path.display(), dst_path.display(), e))?;
        }
    }
    
    Ok(())
}


/// Inject environment variables into the entry file
fn inject_env_values(
    project_path: &std::path::Path,
    entry_file: &str,
    env_values: &std::collections::HashMap<String, String>,
) -> Result<(), String> {
    if env_values.is_empty() {
        return Ok(());
    }
    
    let entry_path = project_path.join(entry_file);
    let content = std::fs::read_to_string(&entry_path)
        .map_err(|e| format!("Failed to read entry file: {}", e))?;
    
    // Generate env injection code
    let mut env_code = String::from("# ============ BAKED ENVIRONMENT VARIABLES ============\nimport os as _env_os\n");
    for (key, value) in env_values {
        // Escape quotes in value
        let escaped_value = value.replace("\\", "\\\\").replace("\"", "\\\"");
        env_code.push_str(&format!("_env_os.environ.setdefault(\"{}\", \"{}\")\n", key, escaped_value));
    }
    env_code.push_str("# ============ END BAKED ENVIRONMENT ============\n\n");
    
    // Prepend to file
    let new_content = format!("{}{}", env_code, content);
    std::fs::write(&entry_path, new_content)
        .map_err(|e| format!("Failed to write env values: {}", e))?;
    
    Ok(())
}

/// Inject first-run dependency installer code into entry file
/// This allows bundling requirements.txt and having deps install on first run
fn inject_first_run_deps_installer(
    project_path: &std::path::Path,
    entry_file: &str,
) -> Result<(), String> {
    let entry_path = project_path.join(entry_file);
    let content = std::fs::read_to_string(&entry_path)
        .map_err(|e| format!("Failed to read entry file: {}", e))?;
    
    // Check if already injected
    if content.contains("AUTO-DEPENDENCY INSTALLER") {
        return Ok(());
    }
    
    // Generate first-run dependency installer code
    let installer_code = r#"# ============ AUTO-DEPENDENCY INSTALLER ============
import subprocess as _dep_subprocess
import sys as _dep_sys
import os as _dep_os
from pathlib import Path as _dep_Path

def _lw_install_deps():
    """Install dependencies from requirements.txt on first run."""
    try:
        # Find requirements.txt relative to executable or script
        if getattr(_dep_sys, 'frozen', False):
            # Running as compiled exe
            base_dir = _dep_Path(_dep_sys.executable).parent
        else:
            # Running as script
            base_dir = _dep_Path(__file__).parent
        
        req_file = base_dir / 'requirements.txt'
        marker_file = base_dir / '.deps_installed'
        
        if req_file.exists() and not marker_file.exists():
            print("[Setup] First run detected. Installing dependencies...")
            print(f"[Setup] Reading requirements from: {req_file}")
            
            # Install using pip
            result = _dep_subprocess.run(
                [_dep_sys.executable, '-m', 'pip', 'install', '-r', str(req_file)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Create marker file to skip next time
                marker_file.write_text('1')
                print("[Setup] Dependencies installed successfully!")
            else:
                print(f"[Setup] Warning: pip install had issues: {result.stderr}")
    except Exception as e:
        print(f"[Setup] Warning: Could not install dependencies: {e}")

_lw_install_deps()
# ============ END AUTO-DEPENDENCY INSTALLER ============

"#;
    
    // Prepend to file
    let new_content = format!("{}{}", installer_code, content);
    std::fs::write(&entry_path, new_content)
        .map_err(|e| format!("Failed to write deps installer: {}", e))?;
    
    Ok(())
}

fn inject_license_wrapper(
    project_path: &std::path::Path,
    entry_file: &str,
    license_key: &str,
    server_url: &str,
    demo_mode: bool,
    demo_duration_minutes: u32,
) -> Result<(), String> {
    let entry_path = project_path.join(entry_file);
    
    if !entry_path.exists() {
        return Err(format!("Entry file not found: {}", entry_path.display()));
    }
    
    // Read original content
    let original_content = std::fs::read_to_string(&entry_path)
        .map_err(|e| format!("Failed to read entry file: {}", e))?;
    
    // Create backup - flatten path separators for nested entry files (e.g. src/main.js -> _backup_src_main.js)
    let backup_filename = format!("_backup_{}", entry_file.replace("/", "_").replace("\\", "_"));
    let backup_path = project_path.join(&backup_filename);
    
    // Ensure backup directory exists (in case we still have nested paths)
    if let Some(parent) = backup_path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create backup directory: {}", e))?;
    }
    
    std::fs::write(&backup_path, &original_content)
        .map_err(|e| format!("Failed to create backup: {}", e))?;

    
    // License wrapper code with grace period security
    let wrapper_code = format!(r##"# ============ LICENSE WRAPPER - DO NOT REMOVE ============
import sys as _lw_sys
import os as _lw_os
import hashlib as _lw_hash
import json as _lw_json
import time as _lw_time
import platform as _lw_platform
from pathlib import Path as _lw_Path

# Grace period: 24 hours (in seconds)
_LW_GRACE_PERIOD = 24 * 60 * 60

def _lw_get_hwid():
    """Generate hardware ID."""
    try:
        info = f"{{_lw_platform.node()}}|{{_lw_platform.machine()}}|{{_lw_platform.processor()}}"
        return _lw_hash.sha256(info.encode()).hexdigest()[:32]
    except:
        return "unknown-hwid"

def _lw_get_cache_path():
    """Get path to license cache file."""
    appdata = _lw_os.getenv('LOCALAPPDATA', _lw_os.path.expanduser('~'))
    cache_dir = _lw_Path(appdata) / '.license_wrapper'
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / f"license_{{_lw_hash.md5('{license_key}'.encode()).hexdigest()[:8]}}.json"

def _lw_load_cache():
    """Load cached license info."""
    try:
        cache_path = _lw_get_cache_path()
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                return _lw_json.load(f)
    except:
        pass
    return None

def _lw_save_cache(valid: bool):
    """Save license validation result to cache."""
    try:
        cache_path = _lw_get_cache_path()
        with open(cache_path, 'w') as f:
            _lw_json.dump({{
                'license_key': '{license_key}',
                'last_validated': int(_lw_time.time()),
                'valid': valid,
                'hwid': _lw_get_hwid()
            }}, f)
    except:
        pass

def _lw_check_grace_period():
    """Check if we're within the offline grace period."""
    cache = _lw_load_cache()
    if cache and cache.get('valid'):
        last_validated = cache.get('last_validated', 0)
        elapsed = int(_lw_time.time()) - last_validated
        if elapsed < _LW_GRACE_PERIOD:
            remaining = (_LW_GRACE_PERIOD - elapsed) // 3600
            print(f"[Offline Mode] Using cached validation ({{remaining}}h remaining)")
            return True
        else:
            print("[!] Offline grace period expired. Please connect to the internet.")
            return False
    return False

def _lw_validate():
    """Validate license with server."""
    LICENSE_KEY = "{license_key}"
    SERVER_URL = "{server_url}"
    
    # Skip validation for DEMO mode
    if LICENSE_KEY == "DEMO" or LICENSE_KEY == "":
        print("[License Wrapper] Running in DEMO mode")
        return True
    
    try:
        import urllib.request
        import urllib.error
        
        hwid = _lw_get_hwid()
        nonce = _lw_hash.sha256(str(_lw_time.time()).encode()).hexdigest()[:32]
        
        payload = _lw_json.dumps({{
            "license_key": LICENSE_KEY,
            "hwid": hwid,
            "machine_name": _lw_platform.node(),
            "nonce": nonce,
            "timestamp": int(_lw_time.time())
        }}).encode('utf-8')
        
        req = urllib.request.Request(
            SERVER_URL + "/api/v1/license/validate",
            data=payload,
            headers={{"Content-Type": "application/json"}}
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = _lw_json.loads(resp.read().decode('utf-8'))
            
            if result.get("status") == "valid":
                print("[OK] License validated successfully")
                _lw_save_cache(True)  # Cache successful validation
                return True
            else:
                msg = result.get("message", "License invalid")
                print(f"[ERROR] License error: {{msg}}")
                _lw_save_cache(False)  # Clear cache on revoke
                input("Press Enter to exit...")
                _lw_sys.exit(1)
                
    except urllib.error.URLError as e:
        print(f"[!] Could not reach license server: {{e.reason}}")
        # Check grace period - only allow if we have a recent valid cache
        if _lw_check_grace_period():
            return True
        else:
            print("[ERROR] Cannot verify license. Please ensure the license server is reachable.")
            input("Press Enter to exit...")
            _lw_sys.exit(1)
    except Exception as e:
        print(f"[!] License validation error: {{e}}")
        input("Press Enter to exit...")
        _lw_sys.exit(1)

# Validate on startup
_lw_validate()
# ============ END LICENSE WRAPPER ============

"##, license_key = license_key, server_url = server_url);
    
    // Generate demo mode code if enabled
    let demo_code = if demo_mode && demo_duration_minutes > 0 {
        format!(r##"
# ============ DEMO MODE - TIME LIMITED ============
import time as _demo_time
import json as _demo_json
from pathlib import Path as _demo_Path

def _lw_check_demo():
    '''Check if demo period has expired.'''
    DEMO_DURATION_SECONDS = {} * 60  # {} minutes
    
    # Get demo marker file path
    appdata = _lw_os.getenv('LOCALAPPDATA', _lw_os.path.expanduser('~'))
    demo_dir = _demo_Path(appdata) / '.license_wrapper'
    demo_dir.mkdir(exist_ok=True)
    demo_file = demo_dir / 'demo_started.json'
    
    try:
        if demo_file.exists():
            with open(demo_file, 'r') as f:
                data = _demo_json.load(f)
                start_time = data.get('start_time', 0)
        else:
            # First run - create marker
            start_time = int(_demo_time.time())
            with open(demo_file, 'w') as f:
                _demo_json.dump({{'start_time': start_time}}, f)
            print(f"[DEMO] Trial started. You have {{DEMO_DURATION_SECONDS // 60}} minutes to evaluate.")
        
        elapsed = int(_demo_time.time()) - start_time
        remaining = DEMO_DURATION_SECONDS - elapsed
        
        if remaining <= 0:
            print("[DEMO EXPIRED] Your trial period has ended.")
            print("[DEMO EXPIRED] Please purchase a license to continue using this software.")
            input("Press Enter to exit...")
            _lw_sys.exit(1)
        else:
            remaining_mins = remaining // 60
            print(f"[DEMO] Trial mode: {{remaining_mins}} minutes remaining")
            return True
            
    except Exception as e:
        print(f"[DEMO] Error checking demo status: {{e}}")
        return True  # Allow on error

_lw_check_demo()
# ============ END DEMO MODE ============

"##, demo_duration_minutes, demo_duration_minutes)
    } else {
        String::new()
    };
    
    // Write wrapped content
    let wrapped_content = format!("{}{}{}", wrapper_code, demo_code, original_content);
    std::fs::write(&entry_path, wrapped_content)
        .map_err(|e| format!("Failed to write wrapped file: {}", e))?;
    
    println!("Injected license wrapper into: {}", entry_file);
    Ok(())
}

/// Restore original entry file from backup
fn restore_original_file(
    project_path: &std::path::Path,
    entry_file: &str,
) {
    // Use same flattened path format as inject_license_wrapper
    let backup_filename = format!("_backup_{}", entry_file.replace("/", "_").replace("\\", "_"));
    let backup_path = project_path.join(&backup_filename);
    let entry_path = project_path.join(entry_file);
    
    if backup_path.exists() {
        if let Err(e) = std::fs::copy(&backup_path, &entry_path) {
            eprintln!("Warning: Failed to restore original file: {}", e);
        }
        if let Err(e) = std::fs::remove_file(&backup_path) {
            eprintln!("Warning: Failed to remove backup file: {}", e);
        }
        println!("Restored original entry file: {}", entry_file);
    }
}


/// Start a Nuitka compilation job (non-blocking)
#[tauri::command]
pub async fn run_nuitka_compilation(
    window: tauri::Window,
    request: StartCompileRequest,
) -> Result<String, String> {
    let job_id = uuid::Uuid::new_v4().to_string();
    let job_id_clone = job_id.clone();
    
    // Emit start event
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 0,
        message: "Starting compilation...".to_string(),
        stage: "init".to_string(),
    }).ok();

    // Debug: Print the project path we received
    println!("Recieved project_path: '{}'", request.project_path);
    
    // Clean up path - remove surrounding quotes if present (common issue on Windows)
    let project_path_str = request.project_path.trim_matches('"').trim_matches('\'');
    let project_path = std::path::Path::new(project_path_str);
    
    if !project_path.exists() {
        let error_msg = format!("Project path does not exist: {}", project_path.display());
        window.emit("compilation-result", CompilationResult {
            job_id: job_id.clone(),
            success: false,
            output_path: None,
            error_message: Some(error_msg.clone()),
        }).ok();
        return Err(error_msg);
    }
    
    // Detect language from entry file extension
    let entry_file_lower = request.entry_file.to_lowercase();
    let is_nodejs = entry_file_lower.ends_with(".js") 
        || entry_file_lower.ends_with(".ts")
        || entry_file_lower.ends_with(".mjs")
        || entry_file_lower.ends_with(".cjs");
    
    if is_nodejs {
        let error_msg = format!(
            "❌ Node.js Desktop Compilation Not Yet Supported\n\n\
            Entry file '{}' appears to be JavaScript/TypeScript.\n\n\
            The desktop app currently only supports Python compilation.\n\
            For Node.js projects, please use the web interface:\n\
            1. Go to http://localhost:3000 in your browser\n\
            2. Upload your Node.js project\n\
            3. Configure and compile\n\n\
            Desktop Node.js support coming soon!",
            request.entry_file
        );
        
        window.emit("compilation-result", CompilationResult {
            job_id: job_id.clone(),
            success: false,
            output_path: None,
            error_message: Some(error_msg.clone()),
        }).ok();
        
        return Err(error_msg);
    }
    
    // Store entry file for restoration later
    let entry_file_for_restore = request.entry_file.clone();
    let project_path_for_restore = project_path.to_path_buf();
    
    // Inject license wrapper if license key is provided
    let license_key = request.license_key.clone().unwrap_or_else(|| "DEMO".to_string());
    let server_url = request.server_url.clone().unwrap_or_else(|| "http://localhost:8000".to_string());
    let demo_mode = request.demo_mode.unwrap_or(false);
    let demo_duration = request.demo_duration_minutes.unwrap_or(60);
    
    if !license_key.is_empty() {
        let mode_desc = if demo_mode {
            format!("DEMO mode, {} min limit", demo_duration)
        } else if license_key == "DEMO" {
            "DEMO mode".to_string()
        } else {
            "protected".to_string()
        };
        
        window.emit("compilation-progress", CompilationProgress {
            job_id: job_id.clone(),
            progress: 3,
            message: format!("Injecting license wrapper ({})", mode_desc),
            stage: "injecting".to_string(),
        }).ok();
        
        if let Err(e) = inject_license_wrapper(project_path, &request.entry_file, &license_key, &server_url, demo_mode, demo_duration) {
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(e.clone()),
            }).ok();
            return Err(e);
        }
    }
    
    // Install dependencies if requested
    if request.install_requirements.unwrap_or(false) {
        let req_path = request.requirements_path.as_deref().unwrap_or("requirements.txt");
        if project_path.join(req_path).exists() {
            if let Err(e) = install_requirements(project_path, req_path, &window, &job_id).await {
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: false,
                    output_path: None,
                    error_message: Some(e.clone()),
                }).ok();
                return Err(e);
            }
        }
    }
    
    // Inject environment values if provided (bake into binary)
    if let Some(ref env_vals) = request.env_values {
        if !env_vals.is_empty() {
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: 4,
                message: format!("Baking {} environment values into binary", env_vals.len()),
                stage: "injecting-env".to_string(),
            }).ok();
            
            if let Err(e) = inject_env_values(project_path, &request.entry_file, env_vals) {
                // Restore original file and return error
                restore_original_file(&project_path_for_restore, &entry_file_for_restore);
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: false,
                    output_path: None,
                    error_message: Some(e.clone()),
                }).ok();
                return Err(e);
            }
        }
    }
    
    // Bundle requirements.txt with first-run installer if requested
    if request.bundle_requirements.unwrap_or(false) {
        let req_path = request.requirements_path.as_deref().unwrap_or("requirements.txt");
        if project_path.join(req_path).exists() {
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: 5,
                message: "Adding first-run dependency installer...".to_string(),
                stage: "injecting-deps".to_string(),
            }).ok();
            
            if let Err(e) = inject_first_run_deps_installer(project_path, &request.entry_file) {
                // Restore original file and return error
                restore_original_file(&project_path_for_restore, &entry_file_for_restore);
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: false,
                    output_path: None,
                    error_message: Some(e.clone()),
                }).ok();
                return Err(e);
            }
        }
    }
    
    // Build frontend if requested
    let mut frontend_dist_path: Option<String> = None;
    if request.build_frontend.unwrap_or(false) {
        if let Some(ref frontend_dir) = request.frontend_dir {
            let frontend_path = project_path.join(frontend_dir);
            if frontend_path.exists() {
                match build_frontend_project(&frontend_path, &window, &job_id).await {
                    Ok(dist_path) => {
                        frontend_dist_path = Some(dist_path);
                    }
                    Err(e) => {
                        // Restore original file and return error
                        restore_original_file(&project_path_for_restore, &entry_file_for_restore);
                        window.emit("compilation-result", CompilationResult {
                            job_id: job_id.clone(),
                            success: false,
                            output_path: None,
                            error_message: Some(e.clone()),
                        }).ok();
                        return Err(e);
                    }
                }
            }
        } else {
            // Auto-detect frontend directory
            if let Some(frontend_info) = detect_frontend_framework(project_path) {
                let frontend_path = std::path::Path::new(&frontend_info.path);
                match build_frontend_project(frontend_path, &window, &job_id).await {
                    Ok(dist_path) => {
                        frontend_dist_path = Some(dist_path);
                    }
                    Err(e) => {
                        // Log warning but continue with backend-only compilation
                        window.emit("compilation-progress", CompilationProgress {
                            job_id: job_id.clone(),
                            progress: 25,
                            message: format!("Frontend build failed (continuing with backend): {}", e),
                            stage: "warning".to_string(),
                        }).ok();
                    }
                }
            }
        }
    }
    
    // Build Nuitka command arguments
    let mut args = vec![
        "-m".to_string(),
        "nuitka".to_string(),
        "--standalone".to_string(),
        "--remove-output".to_string(), // Clean up build folders after compilation
    ];
    
    // Add onefile option
    if request.onefile.unwrap_or(true) {
        args.push("--onefile".to_string());
    }
    
    // Add console/windows mode
    if !request.console.unwrap_or(false) {
        args.push("--windows-console-mode=disable".to_string());
    }
    
    // Add output name
    let output_name = request.output_name.clone().unwrap_or_else(|| {
        request.entry_file.replace(".py", "")
    });
    args.push(format!("--output-filename={}.exe", output_name));
    
    // Add icon if provided
    if let Some(ref icon) = request.icon_path {
        args.push(format!("--windows-icon-from-ico={}", icon));
    }
    
    // Add output directory if specified
    if let Some(ref out_dir) = request.output_dir {
        // Handle output directory path (might also have quotes)
        let out_dir_clean = out_dir.trim_matches('"').trim_matches('\'');
        args.push(format!("--output-dir={}", out_dir_clean));
    }
    
    // Add include-package arguments for detected or specified packages
    let packages = if let Some(ref pkgs) = request.include_packages {
        pkgs.clone()
    } else {
        // Auto-detect Python packages
        detect_python_packages(project_path)
    };
    
    for package in &packages {
        args.push(format!("--include-package={}", package));
    }
    
    if !packages.is_empty() {
        window.emit("compilation-progress", CompilationProgress {
            job_id: job_id.clone(),
            progress: 6,
            message: format!("Including {} Python packages", packages.len()),
            stage: "preparing".to_string(),
        }).ok();
    }
    
    // Add exclude-package arguments for packages to exclude (reduces binary size)
    if let Some(ref exclude_pkgs) = request.exclude_packages {
        for package in exclude_pkgs {
            // Use nofollow-import-to to prevent importing these packages
            args.push(format!("--nofollow-import-to={}", package));
        }
        
        if !exclude_pkgs.is_empty() {
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: 6,
                message: format!("Excluding {} packages: {}", exclude_pkgs.len(), exclude_pkgs.join(", ")),
                stage: "preparing".to_string(),
            }).ok();
        }
    }
    
    // Add include-data-dir arguments for data directories
    let data_dirs = if let Some(ref dirs) = request.include_data_dirs {
        dirs.clone()
    } else {
        // Auto-detect data directories
        detect_data_directories(project_path)
    };
    
    for dir in &data_dirs {
        args.push(format!("--include-data-dir={}={}", dir, dir));
    }
    
    if !data_dirs.is_empty() {
        window.emit("compilation-progress", CompilationProgress {
            job_id: job_id.clone(),
            progress: 7,
            message: format!("Including {} data directories: {}", data_dirs.len(), data_dirs.join(", ")),
            stage: "preparing".to_string(),
        }).ok();
    }
    
    // Add include-data-files for individual files
    if let Some(ref files) = request.include_data_files {
        for file in files {
            args.push(format!("--include-data-files={}={}", file, file));
        }
    }
    
    // Bundle requirements.txt if requested
    if request.bundle_requirements.unwrap_or(false) {
        let req_path = request.requirements_path.as_deref().unwrap_or("requirements.txt");
        if project_path.join(req_path).exists() {
            args.push(format!("--include-data-files={}=requirements.txt", req_path));
            
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: 8,
                message: "Bundling requirements.txt for first-run installation".to_string(),
                stage: "preparing".to_string(),
            }).ok();
        }
    }
    
    // Include frontend dist if built AND we're NOT in split mode
    // In split mode, we copy the frontend folder separately after compilation
    let split_frontend_mode = request.split_frontend.unwrap_or(false);
    
    if let Some(ref dist_path) = frontend_dist_path {
        if split_frontend_mode {
            // In split mode, we'll copy frontend to output folder after compilation
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: 8,
                message: "Frontend will be packaged separately".to_string(),
                stage: "preparing".to_string(),
            }).ok();
        } else {
            // Bundle frontend as static files inside the exe
            args.push(format!("--include-data-dir={}=static", dist_path));
            
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: 8,
                message: "Bundling frontend as static files in executable".to_string(),
                stage: "preparing".to_string(),
            }).ok();
        }
    }
    
    // Add the entry file
    args.push(request.entry_file.clone());

    println!("Executing command: python {:?}", args);
    println!("Working directory: {:?}", project_path);
    
    // Emit preparing event
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 5,
        message: format!("Running Nuitka on {}...", request.entry_file),
        stage: "compiling".to_string(),
    }).ok();
    
    // Spawn Nuitka process using tokio (non-blocking)
    let mut child = Command::new("python")
        .args(&args)
        .current_dir(project_path)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| {
            // Enhanced error message
            let error_msg = format!("Failed to start Nuitka in '{}': {}. Make sure Python and Nuitka are installed.", project_path.display(), e);
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(error_msg.clone()),
            }).ok();
            println!("Error spawning process: {}", error_msg);
            error_msg
        })?;
    
    // Read stderr asynchronously (Nuitka outputs progress to stderr)
    if let Some(stderr) = child.stderr.take() {
        let reader = BufReader::new(stderr);
        let mut lines = reader.lines();
        let mut progress: u32 = 10;
        
        while let Ok(Some(line_text)) = lines.next_line().await {
            // Parse Nuitka output for progress
            let stage = if line_text.contains("Nuitka:INFO:") {
                progress = (progress + 2).min(90);
                "processing"
            } else if line_text.contains("Nuitka:WARNING:") {
                "warning"
            } else if line_text.contains("Nuitka:ERROR:") {
                "error"
            } else {
                progress = (progress + 1).min(90);
                "compiling"
            };
            
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress,
                message: line_text,
                stage: stage.to_string(),
            }).ok();
        }
    }
    
    // Wait for process to complete (async)
    let result = match child.wait().await {
        Ok(status) => {
            if status.success() {
                // Build output path using PathBuf for cross-platform compatibility
                // Use cleaned output_dir if specified, otherwise use cleaned project_path
                let base_path_clean = request.output_dir.as_ref()
                    .map(|s| s.trim_matches('"').trim_matches('\''))
                    .unwrap_or(project_path_str);
                
                let output_path = PathBuf::from(base_path_clean)
                    .join(format!("{}.exe", output_name))
                    .to_string_lossy()
                    .to_string();
                
                // In split frontend mode, copy frontend dist to output directory
                let mut copied_frontend_path: Option<String> = None;
                if split_frontend_mode {
                    if let Some(ref dist_path) = frontend_dist_path {
                        let frontend_dest = PathBuf::from(base_path_clean).join("frontend");
                        
                        window.emit("compilation-progress", CompilationProgress {
                            job_id: job_id.clone(),
                            progress: 95,
                            message: "Copying frontend folder to output directory...".to_string(),
                            stage: "packaging".to_string(),
                        }).ok();
                        
                        match copy_dir_recursive(std::path::Path::new(dist_path), &frontend_dest) {
                            Ok(_) => {
                                window.emit("compilation-progress", CompilationProgress {
                                    job_id: job_id.clone(),
                                    progress: 97,
                                    message: format!("Frontend copied to: {}", frontend_dest.display()),
                                    stage: "packaging".to_string(),
                                }).ok();
                                copied_frontend_path = Some(frontend_dest.to_string_lossy().to_string());
                            }
                            Err(e) => {
                                window.emit("compilation-progress", CompilationProgress {
                                    job_id: job_id.clone(),
                                    progress: 97,
                                    message: format!("Warning: Failed to copy frontend: {}", e),
                                    stage: "warning".to_string(),
                                }).ok();
                            }
                        }
                    }
                }
                
                // Create launcher batch file if requested or if frontend was built
                // In split mode, use the copied frontend path for the launcher
                let launcher_frontend_path = if split_frontend_mode {
                    copied_frontend_path.as_deref()
                } else {
                    frontend_dist_path.as_deref()
                };
                
                let launcher_path = if request.create_launcher.unwrap_or(false) || frontend_dist_path.is_some() {
                    let output_dir_path = PathBuf::from(base_path_clean);
                    let backend_exe_name = format!("{}.exe", output_name);
                    
                    match generate_launcher_batch(
                        &output_dir_path,
                        &backend_exe_name,
                        launcher_frontend_path,
                        &output_name,
                    ) {
                        Ok(launcher) => {
                            window.emit("compilation-progress", CompilationProgress {
                                job_id: job_id.clone(),
                                progress: 98,
                                message: format!("Created launcher: {}", launcher),
                                stage: "finalizing".to_string(),
                            }).ok();
                            Some(launcher)
                        }
                        Err(e) => {
                            println!("Warning: Failed to create launcher: {}", e);
                            None
                        }
                    }
                } else {
                    None
                };
                
                // Use launcher path as output if it exists, otherwise use exe path
                let final_output = launcher_path.unwrap_or(output_path);
                
                window.emit("compilation-progress", CompilationProgress {
                    job_id: job_id.clone(),
                    progress: 100,
                    message: "Compilation completed successfully!".to_string(),
                    stage: "complete".to_string(),
                }).ok();
                
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: true,
                    output_path: Some(final_output),
                    error_message: None,
                }).ok();
                
                Ok(job_id_clone)
            } else {
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: false,
                    output_path: None,
                    error_message: Some("Compilation failed".to_string()),
                }).ok();
                
                Err("Compilation failed".to_string())
            }
        }
        Err(e) => {
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(e.to_string()),
            }).ok();
            
            Err(e.to_string())
        }
    };
    
    // Always restore the original entry file after compilation
    restore_original_file(&project_path_for_restore, &entry_file_for_restore);
    
    result
}

/// Check if Nuitka is installed
#[tauri::command]
pub async fn check_nuitka_installed() -> Result<bool, String> {
    let output = Command::new("python")
        .args(["-m", "nuitka", "--version"])
        .output()
        .await;
    
    match output {
        Ok(result) => Ok(result.status.success()),
        Err(_) => Ok(false),
    }
}

/// Get Nuitka version
#[tauri::command]
pub async fn get_nuitka_version() -> Result<String, String> {
    let output = Command::new("python")
        .args(["-m", "nuitka", "--version"])
        .output()
        .await
        .map_err(|e| e.to_string())?;
    
    if output.status.success() {
        let version = String::from_utf8_lossy(&output.stdout);
        Ok(version.trim().to_string())
    } else {
        Err("Nuitka not found".to_string())
    }
}

/// Open the compiled output folder
#[tauri::command]
pub async fn open_output_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    Ok(())
}

/// Check if a file exists at the given path
#[tauri::command]
pub async fn check_file_exists(project_path: String, entry_file: String) -> Result<bool, String> {
    let path = std::path::Path::new(&project_path).join(&entry_file);
    Ok(path.exists())
}

/// Scan project structure to detect packages, data dirs, requirements, etc.
#[tauri::command]
pub async fn scan_project_structure(project_path: String) -> Result<ProjectStructure, String> {
    let path = std::path::Path::new(&project_path);
    
    if !path.exists() {
        return Err(format!("Project path does not exist: {}", project_path));
    }
    
    let packages = detect_python_packages(path);
    let data_dirs = detect_data_directories(path);
    let entry_candidates = detect_entry_candidates(path);
    
    let req_path = path.join("requirements.txt");
    let has_requirements = req_path.exists();
    let requirements_packages = if has_requirements {
        parse_requirements_file(path)
    } else {
        Vec::new()
    };
    
    let env_path = path.join(".env");
    let has_env = env_path.exists();
    let env_values = parse_env_file(path);
    let env_keys: Vec<String> = env_values.keys().cloned().collect();
    
    let frontend_info = detect_frontend_framework(path);
    let has_frontend = frontend_info.is_some();
    let frontend_framework = frontend_info.map(|f| f.framework);
    
    Ok(ProjectStructure {
        packages,
        data_dirs,
        entry_candidates,
        has_requirements,
        requirements_packages,
        has_env,
        env_keys,
        has_frontend,
        frontend_framework,
    })
}

/// Read .env file and return key-value pairs
#[tauri::command]
pub async fn read_env_file_values(project_path: String) -> Result<std::collections::HashMap<String, String>, String> {
    let path = std::path::Path::new(&project_path);
    
    if !path.exists() {
        return Err(format!("Project path does not exist: {}", project_path));
    }
    
    Ok(parse_env_file(path))
}

/// Detect frontend framework in a project
#[tauri::command]
pub async fn detect_frontend(project_path: String) -> Result<Option<FrontendInfo>, String> {
    let path = std::path::Path::new(&project_path);
    
    if !path.exists() {
        return Err(format!("Project path does not exist: {}", project_path));
    }
    
    Ok(detect_frontend_framework(path))
}

// ============ Phase 4: PNG to ICO Conversion ============

/// Convert PNG image to ICO format for executable icons
/// Uses Python PIL for conversion (requires Pillow)
#[tauri::command]
pub async fn convert_png_to_ico(png_path: String) -> Result<String, String> {
    let png_path_obj = std::path::Path::new(&png_path);
    
    if !png_path_obj.exists() {
        return Err("PNG file not found".to_string());
    }
    
    // Output ICO path (same location, .ico extension)
    let ico_path = png_path_obj.with_extension("ico");
    
    // Use Python's PIL via subprocess for conversion
    let python_script = format!(r#"
from PIL import Image
import sys

try:
    img = Image.open(r'{}')
    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    # Save as ICO with multiple sizes
    img.save(r'{}', format='ICO', sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
    print('OK')
except Exception as e:
    print(f'ERROR: {{e}}', file=sys.stderr)
    sys.exit(1)
"#, png_path, ico_path.display());
    
    let result = Command::new("python")
        .args(["-c", &python_script])
        .output()
        .await
        .map_err(|e| format!("Failed to run Python for conversion: {}", e))?;
    
    if result.status.success() {
        Ok(ico_path.to_string_lossy().to_string())
    } else {
        let stderr = String::from_utf8_lossy(&result.stderr);
        if stderr.contains("No module named 'PIL'") {
            Err("Pillow not installed. Run: pip install Pillow".to_string())
        } else {
            Err(format!("Conversion failed: {}", stderr))
        }
    }
}

// ============ Phase 5: Prerequisites Check ============

/// Python installation status
#[derive(Clone, serde::Serialize)]
pub struct PythonStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub path: Option<String>,
}

/// Nuitka installation status
#[derive(Clone, serde::Serialize)]
pub struct NuitkaStatus {
    pub installed: bool,
    pub version: Option<String>,
}

/// Check if Python is installed and return version info
#[tauri::command]
pub async fn check_python_installed() -> Result<PythonStatus, String> {
    let output = Command::new("python")
        .args(["--version"])
        .output()
        .await;
    
    match output {
        Ok(result) if result.status.success() => {
            // Python may output version to stdout OR stderr depending on version
            let version = if !result.stdout.is_empty() {
                String::from_utf8_lossy(&result.stdout).trim().to_string()
            } else {
                String::from_utf8_lossy(&result.stderr).trim().to_string()
            };
            
            // Also get python path
            let path_output = Command::new("python")
                .args(["-c", "import sys; print(sys.executable)"])
                .output()
                .await
                .ok();
            
            let path = path_output
                .filter(|o| o.status.success())
                .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string());
            
            Ok(PythonStatus { 
                installed: true, 
                version: Some(version.replace("Python ", "")),
                path,
            })
        },
        _ => Ok(PythonStatus { installed: false, version: None, path: None })
    }
}

/// Get detailed Nuitka status
#[tauri::command]
pub async fn get_nuitka_status() -> Result<NuitkaStatus, String> {
    let output = Command::new("python")
        .args(["-m", "nuitka", "--version"])
        .output()
        .await;
    
    match output {
        Ok(result) if result.status.success() => {
            let version = String::from_utf8_lossy(&result.stdout)
                .lines()
                .next()
                .unwrap_or("")
                .trim()
                .to_string();
            
            Ok(NuitkaStatus { 
                installed: true, 
                version: Some(version),
            })
        },
        _ => Ok(NuitkaStatus { installed: false, version: None })
    }
}

/// Install Nuitka via pip
#[tauri::command]
pub async fn install_nuitka() -> Result<String, String> {
    // Use python -m pip to ensure we use the correct pip for the active Python
    let output = Command::new("python")
        .args(["-m", "pip", "install", "nuitka", "--upgrade"])
        .output()
        .await
        .map_err(|e| format!("Failed to run pip: {}", e))?;
    
    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        Ok(format!("Nuitka installed successfully!\n{}", stdout))
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Installation failed: {}", stderr))
    }
}

/// Install Pillow (for PNG to ICO conversion)
#[tauri::command]
pub async fn install_pillow() -> Result<String, String> {
    // Use python -m pip to ensure we use the correct pip for the active Python
    let output = Command::new("python")
        .args(["-m", "pip", "install", "Pillow", "--upgrade"])
        .output()
        .await
        .map_err(|e| format!("Failed to run pip: {}", e))?;
    
    if output.status.success() {
        Ok("Pillow installed successfully!".to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Installation failed: {}", stderr))
    }
}

// =============================================================================
// Node.js Build Prerequisites
// =============================================================================

#[derive(Clone, serde::Serialize)]
pub struct NodeStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub path: Option<String>,
}

#[derive(Clone, serde::Serialize)]
pub struct PkgStatus {
    pub installed: bool,
    pub version: Option<String>,
}

/// Check if Node.js is installed and return version info
#[tauri::command]
pub async fn check_node_installed() -> Result<NodeStatus, String> {
    let output = Command::new("node")
        .args(["--version"])
        .output()
        .await;
    
    match output {
        Ok(result) if result.status.success() => {
            let version = String::from_utf8_lossy(&result.stdout).trim().to_string();
            
            // Also get node path
            let path_output = Command::new("where")
                .args(["node"])
                .output()
                .await
                .ok();
            
            let path = path_output
                .filter(|o| o.status.success())
                .map(|o| String::from_utf8_lossy(&o.stdout).lines().next().unwrap_or("").trim().to_string());
            
            Ok(NodeStatus { 
                installed: true, 
                version: Some(version.replace("v", "")),
                path,
            })
        },
        _ => Ok(NodeStatus { installed: false, version: None, path: None })
    }
}

/// Check if pkg can be run via npx (comes with Node.js)
/// Since npx auto-downloads packages, we just verify npx is available
#[tauri::command]
pub async fn check_pkg_installed() -> Result<PkgStatus, String> {
    // First check if npx is available (comes with Node.js)
    let npx_check = Command::new("npx")
        .args(["--version"])
        .output()
        .await;
    
    match npx_check {
        Ok(result) if result.status.success() => {
            // npx is available, so pkg can be run via npx (it auto-downloads)
            // Try to get pkg version if already cached
            let pkg_version = Command::new("npx")
                .args(["pkg", "--version"])
                .output()
                .await
                .ok()
                .filter(|r| r.status.success())
                .map(|r| String::from_utf8_lossy(&r.stdout).trim().to_string());
            
            Ok(PkgStatus { 
                installed: true, 
                version: pkg_version.or(Some("via npx".to_string())),
            })
        },
        _ => {
            // npx not found - Node.js might not be properly installed
            Ok(PkgStatus { installed: false, version: None })
        }
    }
}

/// pkg is run via npx, no installation needed
/// This just returns success since npx handles downloading
#[tauri::command]
pub async fn install_pkg() -> Result<String, String> {
    // With npx, pkg doesn't need to be installed globally
    // npx will download it automatically when needed
    // Just verify npx works
    let output = Command::new("npx")
        .args(["--version"])
        .output()
        .await
        .map_err(|e| format!("Failed to run npx: {}. Make sure Node.js is installed correctly.", e))?;
    
    if output.status.success() {
        Ok("pkg is available via npx! No installation needed - npx will download it automatically when building.".to_string())
    } else {
        Err("npx not found. Please reinstall Node.js to get npx.".to_string())
    }
}

/// Check if npm is installed
#[derive(Clone, Serialize)]
pub struct NpmStatus {
    pub installed: bool,
    pub version: Option<String>,
}

#[tauri::command]
pub async fn check_npm_installed() -> Result<NpmStatus, String> {
    let result = Command::new("npm")
        .args(["--version"])
        .output()
        .await;
    
    match result {
        Ok(output) if output.status.success() => {
            let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
            Ok(NpmStatus { installed: true, version: Some(version) })
        },
        _ => Ok(NpmStatus { installed: false, version: None })
    }
}

/// Check if javascript-obfuscator is installed (optional)
#[derive(Clone, Serialize)]
pub struct ObfuscatorStatus {
    pub installed: bool,
    pub version: Option<String>,
}

#[tauri::command]
pub async fn check_obfuscator_installed() -> Result<ObfuscatorStatus, String> {
    // Check via npx
    let result = Command::new("npx")
        .args(["javascript-obfuscator", "--version"])
        .output()
        .await;
    
    match result {
        Ok(output) if output.status.success() => {
            let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
            Ok(ObfuscatorStatus { installed: true, version: Some(version) })
        },
        _ => Ok(ObfuscatorStatus { installed: false, version: None })
    }
}

/// Run Node.js compilation with license protection
/// Uses shell execution for Windows PATH resolution
#[tauri::command]
pub async fn run_nodejs_compilation(
    window: tauri::Window,
    request: StartCompileRequest,
) -> Result<String, String> {
    let job_id = uuid::Uuid::new_v4().to_string();
    let job_id_clone = job_id.clone();
    
    // Emit start event
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 0,
        message: "Starting Node.js compilation...".to_string(),
        stage: "init".to_string(),
    }).ok();
    
    let project_path = std::path::Path::new(&request.project_path);
    let entry_file = &request.entry_file;
    let entry_path = project_path.join(entry_file);
    
    if !entry_path.exists() {
        let error_msg = format!("Entry file not found: {}", entry_path.display());
        window.emit("compilation-result", CompilationResult {
            job_id: job_id.clone(),
            success: false,
            output_path: None,
            error_message: Some(error_msg.clone()),
        }).ok();
        return Err(error_msg);
    }
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 10,
        message: "Checking dependencies...".to_string(),
        stage: "preparing".to_string(),
    }).ok();
    
    // Check if node_modules exists, if not and package.json exists, run npm install
    let node_modules_path = project_path.join("node_modules");
    let package_json_path = project_path.join("package.json");
    
    if package_json_path.exists() && !node_modules_path.exists() {
        window.emit("compilation-progress", CompilationProgress {
            job_id: job_id.clone(),
            progress: 12,
            message: "Installing npm dependencies (npm install)...".to_string(),
            stage: "preparing".to_string(),
        }).ok();
        
        // Run npm install
        #[cfg(target_os = "windows")]
        let npm_result = Command::new("powershell")
            .args(["-NoProfile", "-Command", "npm install"])
            .current_dir(project_path)
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .output()
            .await;
        
        #[cfg(not(target_os = "windows"))]
        let npm_result = Command::new("sh")
            .args(["-c", "npm install"])
            .current_dir(project_path)
            .output()
            .await;
        
        match npm_result {
            Ok(output) if output.status.success() => {
                window.emit("compilation-progress", CompilationProgress {
                    job_id: job_id.clone(),
                    progress: 18,
                    message: "Dependencies installed successfully!".to_string(),
                    stage: "preparing".to_string(),
                }).ok();
            },
            Ok(output) => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                let error_msg = format!("npm install failed: {}", stderr);
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: false,
                    output_path: None,
                    error_message: Some(error_msg.clone()),
                }).ok();
                return Err(error_msg);
            },
            Err(e) => {
                let error_msg = format!("Failed to run npm install: {}\n\nMake sure Node.js and npm are installed.", e);
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: false,
                    output_path: None,
                    error_message: Some(error_msg.clone()),
                }).ok();
                return Err(error_msg);
            }
        }
    } else if !package_json_path.exists() {
        window.emit("compilation-progress", CompilationProgress {
            job_id: job_id.clone(),
            progress: 15,
            message: "Warning: No package.json found. Dependencies may be missing.".to_string(),
            stage: "preparing".to_string(),
        }).ok();
    } else {
        window.emit("compilation-progress", CompilationProgress {
            job_id: job_id.clone(),
            progress: 15,
            message: "Dependencies already installed.".to_string(),
            stage: "preparing".to_string(),
        }).ok();
    }
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 20,
        message: "Injecting license wrapper...".to_string(),
        stage: "preparing".to_string(),
    }).ok();
    
    // License wrapper JavaScript code - injected into the project
    let license_key = request.license_key.as_deref().unwrap_or("DEMO");
    let server_url = request.server_url.as_deref().unwrap_or("http://localhost:8000");
    let api_url = format!("{}/api/v1/license/validate", server_url);
    
    let license_wrapper_js = format!(r#"
const crypto = require('crypto');
const os = require('os');

// License Configuration
const LICENSE_KEY = '{}';
const API_URL = '{}';

function getHWID() {{
    try {{
        const cpus = os.cpus();
        const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
        const info = `${{os.hostname()}}|${{os.platform()}}|${{os.arch()}}|${{os.totalmem()}}|${{cpuModel}}`;
        return crypto.createHash('sha256').update(info).digest('hex');
    }} catch (e) {{
        return 'unknown-hwid';
    }}
}}

function validateLicense() {{
    if (LICENSE_KEY === 'DEMO') {{
        console.log('[CodeVault] Running in DEMO mode');
        return Promise.resolve(true);
    }}
    
    return new Promise((resolve, reject) => {{
        const hwid = getHWID();
        const nonce = crypto.randomBytes(16).toString('hex');
        const timestamp = Math.floor(Date.now() / 1000);
        
        let urlObj;
        try {{
            urlObj = new URL(API_URL);
        }} catch (e) {{
            console.error('[CodeVault] Invalid API URL');
            process.exit(1);
        }}

        const postData = JSON.stringify({{
            license_key: LICENSE_KEY,
            hwid: hwid,
            nonce: nonce,
            timestamp: timestamp,
            machine_name: os.hostname()
        }});
        
        const options = {{
            hostname: urlObj.hostname,
            port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
            path: urlObj.pathname,
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }}
        }};
        
        const lib = urlObj.protocol === 'http:' ? require('http') : require('https');

        const req = lib.request(options, (res) => {{
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {{
                try {{
                    if (res.statusCode !== 200) {{
                        console.error(`[CodeVault] Validation failed (HTTP ${{res.statusCode}})`);
                        process.exit(1);
                    }}
                    const response = JSON.parse(body);
                    if (response.status === 'valid') {{
                        resolve(true);
                    }} else {{
                        console.error('[CodeVault] License invalid:', response.message || 'Unknown error');
                        process.exit(1);
                    }}
                }} catch (e) {{
                    console.error('[CodeVault] Failed to parse validation response');
                    process.exit(1);
                }}
            }});
        }});
        
        req.on('error', (e) => {{
            console.error('[CodeVault] Connection error:', e.message);
            process.exit(1);
        }});
        
        req.write(postData);
        req.end();
    }});
}}

module.exports = validateLicense;
"#, license_key, api_url);

    // Create license wrapper file
    let wrapper_path = project_path.join("_cv_license_wrapper.js");
    if let Err(e) = std::fs::write(&wrapper_path, &license_wrapper_js) {
        let error_msg = format!("Failed to create license wrapper: {}", e);
        window.emit("compilation-result", CompilationResult {
            job_id: job_id.clone(),
            success: false,
            output_path: None,
            error_message: Some(error_msg.clone()),
        }).ok();
        return Err(error_msg);
    }
    
    // Create bootstrap entry file that validates license then runs main
    let bootstrap_id = uuid::Uuid::new_v4().to_string().replace("-", "")[..8].to_string();
    let bootstrap_filename = format!("_cv_bootstrap_{}.js", bootstrap_id);
    let bootstrap_path = project_path.join(&bootstrap_filename);
    
    // Handle entry file path - could be relative with subdirectories
    let entry_require_path = if entry_file.contains('/') || entry_file.contains('\\') {
        format!("./{}", entry_file.replace('\\', "/"))
    } else {
        format!("./{}", entry_file)
    };
    
    let bootstrap_content = format!(r#"
const validateLicense = require('./_cv_license_wrapper');
validateLicense().then(() => {{
    console.log('[CodeVault] License verified. Starting application...');
    require('{}');
}}).catch(err => {{
    console.error('[CodeVault] Startup error:', err);
    process.exit(1);
}});
"#, entry_require_path);

    if let Err(e) = std::fs::write(&bootstrap_path, &bootstrap_content) {
        // Cleanup wrapper on failure
        std::fs::remove_file(&wrapper_path).ok();
        let error_msg = format!("Failed to create bootstrap entry: {}", e);
        window.emit("compilation-result", CompilationResult {
            job_id: job_id.clone(),
            success: false,
            output_path: None,
            error_message: Some(error_msg.clone()),
        }).ok();
        return Err(error_msg);
    }
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 25,
        message: "License wrapper injected. Packaging with pkg...".to_string(),
        stage: "packaging".to_string(),
    }).ok();
    
    // Determine output path
    let output_name = request.output_name.clone().unwrap_or_else(|| {
        entry_path.file_stem()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_else(|| "output".to_string())
    });
    
    let output_dir = request.output_dir.clone()
        .map(PathBuf::from)
        .unwrap_or_else(|| project_path.parent().unwrap_or(project_path).join("output"));
    
    std::fs::create_dir_all(&output_dir).ok();
    
    let output_exe = output_dir.join(format!("{}.exe", output_name));
    
    // Build pkg command
    // Use PowerShell on Windows for proper quoted path handling
    // PowerShell handles paths with spaces much better than cmd
    let output_exe_str = output_exe.to_string_lossy().to_string();
    let entry_file_relative = format!(".\\{}", bootstrap_filename);
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 40,
        message: format!("Running: npx -y pkg {} --output {}", entry_file_relative, output_exe_str),
        stage: "packaging".to_string(),
    }).ok();
    
    // Run pkg via PowerShell for proper PATH resolution on Windows
    // Use spawn() instead of output() for real-time streaming
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 45,
        message: "Starting pkg (may download Node.js binaries on first run)...".to_string(),
        stage: "packaging".to_string(),
    }).ok();
    
    // Use PowerShell which handles paths with spaces properly
    #[cfg(target_os = "windows")]
    let mut child = match Command::new("powershell")
        .args([
            "-NoProfile",
            "-Command",
            &format!(
                "npx -y pkg '{}' --target node18-win-x64 --output '{}'",
                entry_file_relative,
                output_exe_str.replace('\'', "''")  // Escape single quotes
            )
        ])
        .current_dir(project_path)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
    {
        Ok(c) => c,
        Err(e) => {
            std::fs::remove_file(&wrapper_path).ok();
            std::fs::remove_file(&bootstrap_path).ok();
            let error_msg = format!("Failed to start pkg: {}\n\nMake sure Node.js is installed and npx is in your PATH.", e);
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(error_msg.clone()),
            }).ok();
            return Err(error_msg);
        }
    };
    
    #[cfg(not(target_os = "windows"))]
    let mut child = match Command::new("sh")
        .args([
            "-c",
            &format!(
                "npx -y pkg '.{}' --target node18-linux-x64 --output '{}'",
                bootstrap_filename,
                output_exe_str.replace('\'', "'\\''")  // Escape single quotes for bash
            )
        ])
        .current_dir(project_path)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
    {
        Ok(c) => c,
        Err(e) => {
            std::fs::remove_file(&wrapper_path).ok();
            std::fs::remove_file(&bootstrap_path).ok();
            let error_msg = format!("Failed to start pkg: {}\n\nMake sure Node.js is installed.", e);
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(error_msg.clone()),
            }).ok();
            return Err(error_msg);
        }
    };
    
    // Collect output while streaming progress
    let mut stdout_lines = Vec::new();
    let mut stderr_lines = Vec::new();
    let mut progress_counter = 50; // Start at 50%, increment to 90%
    
    // Read stdout in real-time
    if let Some(stdout) = child.stdout.take() {
        use tokio::io::{AsyncBufReadExt, BufReader};
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        
        while let Ok(Some(line)) = lines.next_line().await {
            stdout_lines.push(line.clone());
            
            // Emit progress with the actual log line
            progress_counter = std::cmp::min(progress_counter + 2, 90);
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: progress_counter,
                message: format!("[pkg] {}", line),
                stage: "packaging".to_string(),
            }).ok();
        }
    }
    
    // Read any remaining stderr
    if let Some(stderr) = child.stderr.take() {
        use tokio::io::{AsyncBufReadExt, BufReader};
        let reader = BufReader::new(stderr);
        let mut lines = reader.lines();
        
        while let Ok(Some(line)) = lines.next_line().await {
            stderr_lines.push(line.clone());
            
            // Emit stderr as progress too (could be warnings/errors)
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: progress_counter,
                message: format!("[pkg stderr] {}", line),
                stage: "packaging".to_string(),
            }).ok();
        }
    }
    
    // Wait for process to complete
    let status = child.wait().await;
    
    // Cleanup temp files regardless of result
    std::fs::remove_file(&wrapper_path).ok();
    std::fs::remove_file(&bootstrap_path).ok();
    
    match status {
        Ok(s) if s.success() => {
            window.emit("compilation-progress", CompilationProgress {
                job_id: job_id.clone(),
                progress: 100,
                message: "Build completed successfully!".to_string(),
                stage: "completed".to_string(),
            }).ok();
            
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: true,
                output_path: Some(output_exe.to_string_lossy().to_string()),
                error_message: None,
            }).ok();
            
            Ok(job_id_clone)
        },
        Ok(_) => {
            let stdout_str = stdout_lines.join("\n");
            let stderr_str = stderr_lines.join("\n");
            let error_msg = format!("pkg build failed:\n{}\n{}", stdout_str, stderr_str);
            
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(error_msg.clone()),
            }).ok();
            
            Err(error_msg)
        },
        Err(e) => {
            let error_msg = format!("Failed to wait for pkg: {}\n\nMake sure Node.js is installed and npx is in your PATH.", e);
            
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(error_msg.clone()),
            }).ok();
            
            Err(error_msg)
        }
    }
}

/// Request for building a professional installer
#[derive(Debug, Deserialize)]
pub struct InstallerBuildRequest {
    pub project_path: String,
    pub entry_file: String,
    pub project_name: String,
    pub project_version: Option<String>,
    pub publisher: Option<String>,
    pub language: String,  // "python" or "nodejs"
    pub license_key: Option<String>,
    pub server_url: Option<String>,
    pub license_mode: Option<String>,  // "fixed", "generic", or "demo"
    pub distribution_type: String,  // "portable" or "installer"
    pub create_desktop_shortcut: Option<bool>,
    pub create_start_menu: Option<bool>,
    pub output_dir: Option<String>,
}

/// Run professional installer build using build orchestrator API
#[tauri::command]
pub async fn run_installer_build(
    window: tauri::Window,
    request: InstallerBuildRequest,
) -> Result<String, String> {
    let job_id = uuid::Uuid::new_v4().to_string();
    
    // Emit start event
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 0,
        message: "Starting professional build...".to_string(),
        stage: "init".to_string(),
    }).ok();
    
    // Determine output directory
    let output_dir = if let Some(dir) = request.output_dir {
        dir
    } else {
        let project_path = std::path::Path::new(&request.project_path);
        project_path.join("output").to_string_lossy().to_string()
    };
    
    // Build API request payload
    let api_payload = serde_json::json!({
        "project_name": request.project_name,
        "project_version": request.project_version.unwrap_or_else(|| "1.0.0".to_string()),
        "publisher": request.publisher.unwrap_or_else(|| "Unknown Publisher".to_string()),
        "source_dir": request.project_path,
        "entry_file": request.entry_file,
        "language": request.language,
        "license_key": request.license_key.unwrap_or_else(|| "GENERIC_BUILD".to_string()),
        "api_url": request.server_url.unwrap_or_else(|| "http://localhost:8000".to_string()),
        "license_mode": request.license_mode.unwrap_or_else(|| "generic".to_string()),
        "distribution_type": request.distribution_type,
        "create_desktop_shortcut": request.create_desktop_shortcut.unwrap_or(true),
        "create_start_menu": request.create_start_menu.unwrap_or(true),
        "output_dir": output_dir
    });
    
    window.emit("compilation-progress", CompilationProgress {
        job_id: job_id.clone(),
        progress: 10,
        message: "Calling build orchestrator API...".to_string(),
        stage: "api".to_string(),
    }).ok();
    
    // Call the build API endpoint
    let client = reqwest::Client::new();
    let api_url = "http://localhost:8000/api/v1/build/installer";
    
    match client.post(api_url)
        .json(&api_payload)
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<serde_json::Value>().await {
                    Ok(result) => {
                        let success = result.get("success").and_then(|v| v.as_bool()).unwrap_or(false);
                        
                        if success {
                            let output_path = result.get("output_path")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown");
                            let output_name = result.get("output_name")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown");
                            
                            window.emit("compilation-progress", CompilationProgress {
                                job_id: job_id.clone(),
                                progress: 100,
                                message: format!("Build completed: {}", output_name),
                                stage: "completed".to_string(),
                            }).ok();
                            
                            window.emit("compilation-result", CompilationResult {
                                job_id: job_id.clone(),
                                success: true,
                                output_path: Some(output_path.to_string()),
                                error_message: None,
                            }).ok();
                            
                            Ok(job_id)
                        } else {
                            let error = result.get("error")
                                .and_then(|v| v.as_str())
                                .unwrap_or("Unknown error");
                            
                            window.emit("compilation-result", CompilationResult {
                                job_id: job_id.clone(),
                                success: false,
                                output_path: None,
                                error_message: Some(error.to_string()),
                            }).ok();
                            
                            Err(format!("Build failed: {}", error))
                        }
                    },
                    Err(e) => {
                        let error_msg = format!("Failed to parse API response: {}", e);
                        window.emit("compilation-result", CompilationResult {
                            job_id: job_id.clone(),
                            success: false,
                            output_path: None,
                            error_message: Some(error_msg.clone()),
                        }).ok();
                        Err(error_msg)
                    }
                }
            } else {
                let error_msg = format!("API returned error: {}", response.status());
                window.emit("compilation-result", CompilationResult {
                    job_id: job_id.clone(),
                    success: false,
                    output_path: None,
                    error_message: Some(error_msg.clone()),
                }).ok();
                Err(error_msg)
            }
        },
        Err(e) => {
            let error_msg = format!("Failed to call build API: {}. Is the backend running?", e);
            window.emit("compilation-result", CompilationResult {
                job_id: job_id.clone(),
                success: false,
                output_path: None,
                error_message: Some(error_msg.clone()),
            }).ok();
            Err(error_msg)
        }
    }
}

/// NSIS status structure
#[derive(Clone, Serialize, Debug)]
pub struct NsisStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub path: Option<String>,
}

/// Check if NSIS (Nullsoft Scriptable Install System) is installed
/// Used for creating professional Windows installers
#[tauri::command]
pub async fn check_nsis_installed() -> Result<NsisStatus, String> {
    // Common NSIS installation paths on Windows
    let nsis_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ];
    
    // First check common paths
    for path in &nsis_paths {
        let path_buf = std::path::PathBuf::from(path);
        if path_buf.exists() {
            // Try to get version
            let version = Command::new(path)
                .args(["/VERSION"])
                .output()
                .await
                .ok()
                .filter(|r| r.status.success())
                .map(|r| String::from_utf8_lossy(&r.stdout).trim().to_string());
            
            return Ok(NsisStatus {
                installed: true,
                version,
                path: Some(path.to_string()),
            });
        }
    }
    
    // Check if makensis is in PATH
    let which_result = Command::new("where")
        .args(["makensis"])
        .output()
        .await;
    
    match which_result {
        Ok(result) if result.status.success() => {
            let path = String::from_utf8_lossy(&result.stdout)
                .lines()
                .next()
                .map(|s| s.trim().to_string());
            
            // Try to get version
            let version = if let Some(ref p) = path {
                Command::new(p)
                    .args(["/VERSION"])
                    .output()
                    .await
                    .ok()
                    .filter(|r| r.status.success())
                    .map(|r| String::from_utf8_lossy(&r.stdout).trim().to_string())
            } else {
                None
            };
            
            Ok(NsisStatus {
                installed: true,
                version,
                path,
            })
        },
        _ => Ok(NsisStatus {
            installed: false,
            version: None,
            path: None,
        }),
    }
}
