// Database module for CodeVault local SQLite storage
pub mod schema;

use rusqlite::{Connection, Result};
use std::path::PathBuf;
use std::sync::Mutex;
use std::fs;

/// Get the path to the local database
#[allow(dead_code)]
pub fn get_db_path() -> PathBuf {
    let app_data = dirs::data_local_dir().expect("Could not find app data directory");
    let codevault_dir = app_data.join("CodeVault");
    fs::create_dir_all(&codevault_dir).ok();
    codevault_dir.join("codevault.db")
}

/// Database connection wrapper - thread-safe
#[allow(dead_code)]
pub struct Database {
    conn: Mutex<Connection>,
}

#[allow(dead_code)]
impl Database {
    /// Create a new database connection
    pub fn new() -> Result<Self> {
        let db_path = get_db_path();
        let conn = Connection::open(db_path)?;
        
        // Initialize schema
        schema::init_schema(&conn)?;
        
        Ok(Database {
            conn: Mutex::new(conn),
        })
    }
    
    /// Get a reference to the connection for queries
    pub fn connection(&self) -> std::sync::MutexGuard<'_, Connection> {
        self.conn.lock().expect("Failed to acquire database lock")
    }
}

impl Default for Database {
    fn default() -> Self {
        Self::new().expect("Failed to initialize database")
    }
}
