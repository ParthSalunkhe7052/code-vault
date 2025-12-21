// Database schema initialization
use rusqlite::{Connection, Result};

#[allow(dead_code)]
pub fn init_schema(conn: &Connection) -> Result<()> {
    conn.execute_batch(r#"
        -- Local projects (synced from cloud or created locally)
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            local_path TEXT,
            entry_file TEXT,
            cloud_synced INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Local license cache for offline validation
        CREATE TABLE IF NOT EXISTS license_cache (
            license_key TEXT PRIMARY KEY,
            project_id TEXT,
            is_valid INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            expires_at TEXT,
            max_machines INTEGER DEFAULT 1,
            features TEXT,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_validated TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        -- Application settings
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Compilation history
        CREATE TABLE IF NOT EXISTS compile_history (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            entry_file TEXT NOT NULL,
            output_name TEXT,
            status TEXT DEFAULT 'pending',
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            output_path TEXT,
            error_message TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        -- Analytics events (local tracking before cloud sync)
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            project_id TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            synced INTEGER DEFAULT 0
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
        CREATE INDEX IF NOT EXISTS idx_license_cache_project ON license_cache(project_id);
        CREATE INDEX IF NOT EXISTS idx_compile_history_project ON compile_history(project_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_synced ON analytics_events(synced);
    "#)?;
    
    // Insert default settings if not exist
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'dark')",
        [],
    )?;
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('api_url', 'https://codevault.parth7.me/api/v1')",
        [],
    )?;
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('nuitka_path', '')",
        [],
    )?;
    
    Ok(())
}
