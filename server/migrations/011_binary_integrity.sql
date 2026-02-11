-- Migration 011: Binary Integrity Checking
-- Stores SHA-256 hashes of compiled binaries to detect tampering.
-- During validation, clients can optionally send their binary_hash;
-- the server checks it against registered hashes.

CREATE TABLE IF NOT EXISTS binary_hashes (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) REFERENCES projects(id) ON DELETE CASCADE,
    binary_hash VARCHAR(128) NOT NULL,
    binary_size BIGINT,
    platform VARCHAR(20),
    build_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_binary_hashes_project ON binary_hashes(project_id);
CREATE INDEX IF NOT EXISTS idx_binary_hashes_hash ON binary_hashes(binary_hash);
