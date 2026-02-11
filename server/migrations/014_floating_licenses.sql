-- Migration 014: Floating Licenses
-- Supports session-based concurrent licensing.

-- Add floating mode columns to licenses
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS license_mode VARCHAR(20) DEFAULT 'static'; -- 'static' or 'floating'
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS max_concurrent INTEGER DEFAULT 1;

-- Create license_sessions table for floating licenses
CREATE TABLE IF NOT EXISTS license_sessions (
    id VARCHAR(64) PRIMARY KEY,
    license_id VARCHAR(64) REFERENCES licenses(id) ON DELETE CASCADE,
    hwid VARCHAR(64) NOT NULL,
    session_token VARCHAR(128) NOT NULL,
    ip_address VARCHAR(45),
    started_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    released_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sessions_license ON license_sessions(license_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON license_sessions(is_active);

-- Constraint: valid license modes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_license_mode') THEN
        ALTER TABLE licenses ADD CONSTRAINT ck_license_mode 
        CHECK (license_mode IN ('static', 'floating'));
    END IF;
END
$$;
