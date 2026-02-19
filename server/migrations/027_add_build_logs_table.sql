-- Migration: Add build_logs table
-- Date: 2026-02-19
-- Description: Fix missing build_logs table

-- Create build_logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS build_logs (
    id VARCHAR(32) PRIMARY KEY,
    build_id VARCHAR(32) NOT NULL,
    message TEXT NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'info',
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_build_logs_build ON build_logs(build_id);
CREATE INDEX IF NOT EXISTS idx_build_logs_timestamp ON build_logs(timestamp);
