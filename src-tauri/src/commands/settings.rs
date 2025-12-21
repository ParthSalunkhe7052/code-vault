// Application settings commands
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize)]
pub struct AppSettings {
    pub theme: String,
    pub api_url: String,
    pub nuitka_path: String,
    pub python_path: Option<String>,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            theme: "dark".to_string(),
            api_url: "https://codevault.parth7.me/api/v1".to_string(),
            nuitka_path: String::new(),
            python_path: None,
        }
    }
}

/// Get all application settings
#[tauri::command]
pub async fn get_settings() -> Result<AppSettings, String> {
    // TODO: Read from SQLite database
    Ok(AppSettings::default())
}

/// Update a single setting
#[tauri::command]
pub async fn update_setting(key: String, value: String) -> Result<bool, String> {
    // TODO: Update in SQLite database
    let _ = (key, value);
    Ok(true)
}

/// Update multiple settings at once
#[tauri::command]
pub async fn update_settings(settings: HashMap<String, String>) -> Result<bool, String> {
    // TODO: Update in SQLite database
    let _ = settings;
    Ok(true)
}

/// Get the Nuitka installation path
#[tauri::command]
pub async fn get_nuitka_path() -> Result<Option<String>, String> {
    // Check common locations
    let possible_paths = vec![
        "nuitka",
        "python -m nuitka",
    ];
    
    // TODO: Actually check if Nuitka is installed
    for path in possible_paths {
        // For now just return the first one
        return Ok(Some(path.to_string()));
    }
    
    Ok(None)
}

/// Set the Python/Nuitka path
#[tauri::command]
pub async fn set_compiler_path(path: String) -> Result<bool, String> {
    // TODO: Validate path and save to settings
    let _ = path;
    Ok(true)
}
