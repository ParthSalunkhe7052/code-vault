// Project file downloader for remote projects
// Downloads project files from the CodeVault server for local compilation

use serde::Serialize;
use std::path::PathBuf;
use tauri::Emitter;
use tokio::io::AsyncWriteExt;
use reqwest::Client;

/// Download progress event
#[derive(Clone, Serialize)]
pub struct DownloadProgress {
    pub project_id: String,
    pub progress: u32,
    pub message: String,
    pub stage: String,
}

/// Download result
#[derive(Clone, Serialize)]
pub struct DownloadResult {
    pub project_id: String,
    pub success: bool,
    pub extracted_path: Option<String>,
    pub error_message: Option<String>,
}

/// Download project files from server for local compilation
#[tauri::command]
pub async fn download_project_for_compilation(
    window: tauri::Window,
    project_id: String,
    server_url: String,
    auth_token: String,
    target_dir: Option<String>,
) -> Result<String, String> {
    // Emit start event
    window.emit("download-progress", DownloadProgress {
        project_id: project_id.clone(),
        progress: 0,
        message: "Starting download...".to_string(),
        stage: "init".to_string(),
    }).ok();
    
    // Determine target directory
    let target_path = if let Some(dir) = target_dir {
        PathBuf::from(dir)
    } else {
        // Use temp directory with project ID
        let temp_dir = std::env::temp_dir().join("license_wrapper_projects").join(&project_id);
        temp_dir
    };
    
    // Create target directory if it doesn't exist
    if !target_path.exists() {
        std::fs::create_dir_all(&target_path)
            .map_err(|e| format!("Failed to create target directory: {}", e))?;
    }
    
    window.emit("download-progress", DownloadProgress {
        project_id: project_id.clone(),
        progress: 10,
        message: "Connecting to server...".to_string(),
        stage: "connecting".to_string(),
    }).ok();
    
    // Build download URL
    let download_url = format!("{}/api/v1/projects/{}/download-source", server_url, project_id);
    
    // Create HTTP client
    let client = Client::new();
    
    // Make request
    let response = client
        .get(&download_url)
        .header("Authorization", format!("Bearer {}", auth_token))
        .send()
        .await
        .map_err(|e| format!("Failed to connect to server: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("Server returned error: {}", response.status()));
    }
    
    window.emit("download-progress", DownloadProgress {
        project_id: project_id.clone(),
        progress: 20,
        message: "Downloading project files...".to_string(),
        stage: "downloading".to_string(),
    }).ok();
    
    // Get content length for progress tracking
    let _content_length = response.content_length().unwrap_or(0);
    
    // Download to temporary zip file
    let zip_path = target_path.join("project_source.zip");
    let mut file = tokio::fs::File::create(&zip_path)
        .await
        .map_err(|e| format!("Failed to create temp file: {}", e))?;
    
    // Stream the download
    let bytes = response.bytes()
        .await
        .map_err(|e| format!("Failed to download file: {}", e))?;
    
    file.write_all(&bytes)
        .await
        .map_err(|e| format!("Failed to write file: {}", e))?;
    
    window.emit("download-progress", DownloadProgress {
        project_id: project_id.clone(),
        progress: 60,
        message: format!("Downloaded {} bytes", bytes.len()),
        stage: "downloaded".to_string(),
    }).ok();
    
    // Extract zip file
    window.emit("download-progress", DownloadProgress {
        project_id: project_id.clone(),
        progress: 70,
        message: "Extracting files...".to_string(),
        stage: "extracting".to_string(),
    }).ok();
    
    // Use std::fs for zip extraction (blocking, but wrapped in spawn_blocking)
    let zip_path_clone = zip_path.clone();
    let target_path_clone = target_path.clone();
    
    tokio::task::spawn_blocking(move || {
        let file = std::fs::File::open(&zip_path_clone)
            .map_err(|e| format!("Failed to open zip file: {}", e))?;
        
        let mut archive = zip::ZipArchive::new(file)
            .map_err(|e| format!("Failed to read zip archive: {}", e))?;
        
        for i in 0..archive.len() {
            let mut file = archive.by_index(i)
                .map_err(|e| format!("Failed to read file from archive: {}", e))?;
            
            let outpath = match file.enclosed_name() {
                Some(path) => target_path_clone.join(path),
                None => continue,
            };
            
            if file.name().ends_with('/') {
                std::fs::create_dir_all(&outpath).ok();
            } else {
                if let Some(p) = outpath.parent() {
                    if !p.exists() {
                        std::fs::create_dir_all(p).ok();
                    }
                }
                let mut outfile = std::fs::File::create(&outpath)
                    .map_err(|e| format!("Failed to create file: {}", e))?;
                std::io::copy(&mut file, &mut outfile)
                    .map_err(|e| format!("Failed to extract file: {}", e))?;
            }
        }
        
        Ok::<(), String>(())
    })
    .await
    .map_err(|e| format!("Extraction task failed: {}", e))?
    .map_err(|e| e)?;
    
    // Clean up zip file
    tokio::fs::remove_file(&zip_path).await.ok();
    
    window.emit("download-progress", DownloadProgress {
        project_id: project_id.clone(),
        progress: 100,
        message: "Project files ready".to_string(),
        stage: "complete".to_string(),
    }).ok();
    
    window.emit("download-result", DownloadResult {
        project_id: project_id.clone(),
        success: true,
        extracted_path: Some(target_path.to_string_lossy().to_string()),
        error_message: None,
    }).ok();
    
    Ok(target_path.to_string_lossy().to_string())
}

/// Check if project files are already downloaded
#[tauri::command]
pub async fn check_project_downloaded(project_id: String) -> Result<Option<String>, String> {
    let temp_dir = std::env::temp_dir()
        .join("license_wrapper_projects")
        .join(&project_id);
    
    if temp_dir.exists() {
        // Check if it has any files
        if let Ok(mut entries) = std::fs::read_dir(&temp_dir) {
            if entries.next().is_some() {
                return Ok(Some(temp_dir.to_string_lossy().to_string()));
            }
        }
    }
    
    Ok(None)
}

/// Clean up downloaded project files
#[tauri::command]
pub async fn cleanup_downloaded_project(project_id: String) -> Result<(), String> {
    let temp_dir = std::env::temp_dir()
        .join("license_wrapper_projects")
        .join(&project_id);
    
    if temp_dir.exists() {
        std::fs::remove_dir_all(&temp_dir)
            .map_err(|e| format!("Failed to clean up: {}", e))?;
    }
    
    Ok(())
}

/// Download project and prepare for compilation (combined workflow)
/// Returns the path where files were extracted, ready for compilation
#[tauri::command]
pub async fn download_and_prepare_for_compile(
    window: tauri::Window,
    project_id: String,
    server_url: String,
    auth_token: String,
    target_dir: Option<String>,
) -> Result<String, String> {
    // First download the project
    let extracted_path = download_project_for_compilation(
        window.clone(),
        project_id.clone(),
        server_url,
        auth_token,
        target_dir,
    ).await?;
    
    // Emit ready event
    window.emit("download-progress", DownloadProgress {
        project_id: project_id.clone(),
        progress: 100,
        message: format!("Project ready for compilation at: {}", extracted_path),
        stage: "ready-for-compile".to_string(),
    }).ok();
    
    Ok(extracted_path)
}

/// Get the default download directory for a project
#[tauri::command]
pub async fn get_project_download_path(project_id: String) -> Result<String, String> {
    let temp_dir = std::env::temp_dir()
        .join("license_wrapper_projects")
        .join(&project_id);
    
    Ok(temp_dir.to_string_lossy().to_string())
}
