// Backend Manager - Handles Python backend lifecycle for desktop app
// Starts, monitors, and stops the Python backend service

use std::process::{Command, Child, Stdio};
use std::sync::Mutex;
use std::path::PathBuf;
use std::fs;
use std::time::Duration;
use std::thread;

/// Global backend process handle
static BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

/// Backend configuration
#[allow(dead_code)]
pub struct BackendConfig {
    pub port: u16,
    pub log_dir: PathBuf,
}

impl Default for BackendConfig {
    fn default() -> Self {
        Self {
            port: 8765,
            log_dir: dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("license-wrapper")
                .join("logs"),
        }
    }
}

/// Find Python executable
pub fn find_python() -> Option<PathBuf> {
    // Try common Python locations on Windows
    let candidates = vec![
        "python",
        "python3",
        "py",
    ];
    
    for candidate in candidates {
        if let Ok(output) = Command::new(candidate)
            .args(["--version"])
            .output()
        {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout);
                // Check for Python 3.12+
                if version.contains("Python 3.") {
                    return Some(PathBuf::from(candidate));
                }
            }
        }
    }
    
    None
}

/// Get the port file path
fn get_port_file() -> PathBuf {
    dirs::data_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("license-wrapper")
        .join("logs")
        .join("backend.port")
}

/// Read backend port from port file
pub fn get_backend_port() -> Option<u16> {
    let port_file = get_port_file();
    if port_file.exists() {
        if let Ok(content) = fs::read_to_string(&port_file) {
            return content.trim().parse().ok();
        }
    }
    None
}

/// Get backend URL
pub fn get_backend_url() -> String {
    let port = get_backend_port().unwrap_or(8765);
    format!("http://127.0.0.1:{}", port)
}

/// Start the backend service
pub fn start_backend(app_path: &PathBuf) -> Result<u16, String> {
    // Check if already running
    if is_backend_running() {
        if let Some(port) = get_backend_port() {
            println!("[BackendManager] Backend already running on port {}", port);
            return Ok(port);
        }
    }
    
    // Find Python
    let python = find_python().ok_or_else(|| {
        "Python not found. Please install Python 3.12+ from python.org".to_string()
    })?;
    
    println!("[BackendManager] Found Python: {:?}", python);
    
    // Find backend_service.py
    let backend_script = app_path.join("backend_service.py");
    if !backend_script.exists() {
        return Err(format!("Backend script not found: {:?}", backend_script));
    }
    
    println!("[BackendManager] Starting backend from: {:?}", backend_script);
    
    // Start the backend process
    let child = Command::new(&python)
        .arg(&backend_script)
        .arg("--auto-port")
        .current_dir(app_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;
    
    // Store the process handle
    {
        let mut process = BACKEND_PROCESS.lock().map_err(|e| e.to_string())?;
        *process = Some(child);
    }
    
    // Wait for backend to be ready (check port file)
    let mut attempts = 0;
    let max_attempts = 30; // 15 seconds total
    
    while attempts < max_attempts {
        thread::sleep(Duration::from_millis(500));
        
        if let Some(port) = get_backend_port() {
            // Verify backend is responding
            if check_backend_health_sync(port) {
                println!("[BackendManager] Backend ready on port {}", port);
                return Ok(port);
            }
        }
        
        attempts += 1;
    }
    
    Err("Backend failed to start within timeout".to_string())
}

/// Check if backend is healthy (sync version)
fn check_backend_health_sync(port: u16) -> bool {
    // Simple TCP connection check
    use std::net::TcpStream;
    
    TcpStream::connect(format!("127.0.0.1:{}", port))
        .map(|_| true)
        .unwrap_or(false)
}

/// Check if backend is running
pub fn is_backend_running() -> bool {
    let mut process = match BACKEND_PROCESS.lock() {
        Ok(p) => p,
        Err(_) => return false,
    };
    
    if let Some(ref mut child) = *process {
        match child.try_wait() {
            Ok(None) => true, // Still running
            Ok(Some(_)) => {
                // Process exited
                *process = None;
                false
            }
            Err(_) => false,
        }
    } else {
        // Check if port file exists (backend might be running from previous session)
        if let Some(port) = get_backend_port() {
            return check_backend_health_sync(port);
        }
        false
    }
}

/// Stop the backend service
pub fn stop_backend() {
    println!("[BackendManager] Stopping backend...");
    
    if let Ok(mut process) = BACKEND_PROCESS.lock() {
        if let Some(ref mut child) = *process {
            // Try graceful shutdown first
            #[cfg(target_os = "windows")]
            {
                // On Windows, use taskkill
                let _ = Command::new("taskkill")
                    .args(["/PID", &child.id().to_string(), "/T"])
                    .output();
            }
            
            #[cfg(not(target_os = "windows"))]
            {
                // On Unix, send SIGTERM
                let _ = child.kill();
            }
            
            // Wait for process to exit
            let _ = child.wait();
            *process = None;
        }
    }
    
    // Clean up port file
    let port_file = get_port_file();
    if port_file.exists() {
        let _ = fs::remove_file(port_file);
    }
    
    println!("[BackendManager] Backend stopped");
}

/// Tauri command: Check backend status
#[tauri::command]
pub fn check_backend_status() -> Result<serde_json::Value, String> {
    let running = is_backend_running();
    let port = get_backend_port();
    
    Ok(serde_json::json!({
        "running": running,
        "port": port,
        "url": get_backend_url()
    }))
}

/// Tauri command: Start backend
#[tauri::command]
pub fn start_backend_service(app_path: String) -> Result<u16, String> {
    start_backend(&PathBuf::from(app_path))
}

/// Tauri command: Stop backend
#[tauri::command]
pub fn stop_backend_service() -> Result<(), String> {
    stop_backend();
    Ok(())
}
