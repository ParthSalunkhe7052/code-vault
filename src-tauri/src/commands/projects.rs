// Project management commands
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Project {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub local_path: Option<String>,
    pub entry_file: Option<String>,
    pub cloud_synced: bool,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Deserialize)]
pub struct CreateProjectRequest {
    pub name: String,
    pub description: Option<String>,
    pub local_path: Option<String>,
}

/// Create a new local project
#[tauri::command]
pub async fn create_project(request: CreateProjectRequest) -> Result<Project, String> {
    let id = uuid::Uuid::new_v4().to_string();
    let now = chrono::Utc::now().to_rfc3339();
    
    let project = Project {
        id: id.clone(),
        name: request.name,
        description: request.description,
        local_path: request.local_path,
        entry_file: None,
        cloud_synced: false,
        created_at: now.clone(),
        updated_at: now,
    };
    
    // TODO: Save to SQLite database
    // For now, just return the project
    
    Ok(project)
}

/// List all local projects
#[tauri::command]
pub async fn list_projects() -> Result<Vec<Project>, String> {
    // TODO: Read from SQLite database
    Ok(vec![])
}

/// Get a single project by ID
#[tauri::command]
pub async fn get_project(id: String) -> Result<Option<Project>, String> {
    // TODO: Read from SQLite database
    let _ = id;
    Ok(None)
}

/// Delete a project
#[tauri::command]
pub async fn delete_project(id: String) -> Result<bool, String> {
    // TODO: Delete from SQLite database
    let _ = id;
    Ok(true)
}

/// Set the entry file for a project
#[tauri::command]
pub async fn set_project_entry(project_id: String, entry_file: String) -> Result<bool, String> {
    // TODO: Update in SQLite database
    let _ = (project_id, entry_file);
    Ok(true)
}
