// Tauri API Bridge - Detects environment and routes to appropriate backend
// In Tauri: Uses invoke() to call Rust commands
// In Browser: Falls back to HTTP API calls

// Check if running inside Tauri
export const isTauri = () => {
    return typeof window !== 'undefined' && window.__TAURI__ !== undefined;
};

// Dynamic import for Tauri API (only works in Tauri context)
let invoke = null;
if (isTauri()) {
    import('@tauri-apps/api/core').then(module => {
        invoke = module.invoke;
    });
}

// Helper to call Tauri command or fallback to HTTP
const callCommand = async (command, args = {}, httpFallback = null) => {
    if (isTauri() && invoke) {
        try {
            return await invoke(command, args);
        } catch (error) {
            console.error(`Tauri command ${command} failed:`, error);
            throw error;
        }
    } else if (httpFallback) {
        return await httpFallback();
    } else {
        throw new Error(`Command ${command} not available in browser mode`);
    }
};

// ============================================
// Project Commands (Local Tauri-only)
// ============================================

export const tauriProjects = {
    create: (name, description, localPath) =>
        callCommand('create_project', {
            request: { name, description, local_path: localPath }
        }),

    list: () => callCommand('list_projects'),

    get: (id) => callCommand('get_project', { id }),

    delete: (id) => callCommand('delete_project', { id }),

    setEntry: (projectId, entryFile) =>
        callCommand('set_project_entry', { projectId, entryFile }),
};

// ============================================
// Settings Commands (Local Tauri-only)
// ============================================

export const tauriSettings = {
    get: () => callCommand('get_settings'),

    update: (key, value) =>
        callCommand('update_setting', { key, value }),

    updateAll: (settings) =>
        callCommand('update_settings', { settings }),

    getNuitkaPath: () => callCommand('get_nuitka_path'),

    setCompilerPath: (path) =>
        callCommand('set_compiler_path', { path }),
};

// ============================================
// Compiler Commands (Local Tauri-only)
// ============================================

export const tauriCompiler = {
    // Check if Nuitka is installed
    checkInstalled: () => callCommand('check_nuitka_installed'),

    // Get Nuitka version
    getVersion: () => callCommand('get_nuitka_version'),

    // Run Nuitka compilation with progress events
    compile: (projectPath, entryFile, outputName, options = {}) =>
        callCommand('run_nuitka_compilation', {
            request: {
                project_path: projectPath,
                entry_file: entryFile,
                output_name: outputName,
                license_key: options.licenseKey || null,
                onefile: options.onefile !== false,
                console: options.console || false,
                icon_path: options.iconPath || null,
            }
        }),

    // Open output folder
    openOutput: (path) => callCommand('open_output_folder', { path }),
};

// ============================================
// Utility Functions
// ============================================

export const tauriUtils = {
    // Check if we're in desktop mode
    isDesktop: isTauri,

    // Open a folder in file explorer
    openFolder: async (path) => {
        if (isTauri()) {
            return callCommand('open_output_folder', { path });
        } else {
            console.warn('openFolder only works in desktop mode');
        }
    },
};

export default {
    isTauri,
    projects: tauriProjects,
    settings: tauriSettings,
    compiler: tauriCompiler,
    utils: tauriUtils,
};
