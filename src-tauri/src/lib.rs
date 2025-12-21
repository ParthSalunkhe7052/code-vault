// CodeVault Desktop Application - Tauri Backend
// Main library that registers all commands and initializes the app

mod commands;
mod db;
mod backend_manager;

use commands::{projects, settings, compiler, downloader};

/// Initialize and run the Tauri application
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // Plugins
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        
        // Register all commands
        .invoke_handler(tauri::generate_handler![
            // Project commands
            projects::create_project,
            projects::list_projects,
            projects::get_project,
            projects::delete_project,
            projects::set_project_entry,
            
            // Settings commands
            settings::get_settings,
            settings::update_setting,
            settings::update_settings,
            settings::get_nuitka_path,
            settings::set_compiler_path,
            
            // Compiler commands
            compiler::run_nuitka_compilation,
            compiler::run_nodejs_compilation,
            compiler::check_nuitka_installed,
            compiler::get_nuitka_version,
            compiler::open_output_folder,
            compiler::check_file_exists,
            compiler::scan_project_structure,
            compiler::read_env_file_values,
            compiler::detect_frontend,
            compiler::convert_png_to_ico,
            compiler::check_python_installed,
            compiler::get_nuitka_status,
            compiler::install_nuitka,
            compiler::install_pillow,
            // Node.js commands
            compiler::check_node_installed,
            compiler::check_pkg_installed,
            compiler::install_pkg,
            compiler::check_npm_installed,
            compiler::check_obfuscator_installed,
            // Professional Installer Build System
            compiler::run_installer_build,
            // NSIS (Windows Installer) commands
            compiler::check_nsis_installed,
            
            // Backend management commands
            backend_manager::check_backend_status,
            backend_manager::start_backend_service,
            backend_manager::stop_backend_service,
            
            // Downloader commands
            downloader::download_project_for_compilation,
            downloader::check_project_downloaded,
            downloader::cleanup_downloaded_project,
            downloader::download_and_prepare_for_compile,
            downloader::get_project_download_path,
        ])
        
        // Run the app
        .run(tauri::generate_context!())
        .expect("error while running CodeVault application");
}

