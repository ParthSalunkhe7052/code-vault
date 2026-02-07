-- Migration: Add cloud_builds table and tier limits for cloud compilation
-- Date: 2026-01-12
-- Feature: Cloud-Based Compilation

-- =============================================================================
-- 1. Create cloud_builds table
-- =============================================================================
CREATE TABLE IF NOT EXISTS cloud_builds (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Build configuration
    language VARCHAR(20) NOT NULL,
    entry_file VARCHAR(255) NOT NULL,
    output_name VARCHAR(255) NOT NULL,
    license_key VARCHAR(255),
    config_json JSONB NOT NULL,
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, queued, running, completed, failed, cancelled
    progress INTEGER DEFAULT 0,  -- 0-100
    
    -- Results
    download_key VARCHAR(500),  -- R2 object key
    download_filename VARCHAR(255),
    download_size BIGINT,
    error_message TEXT,
    
    -- Metadata
    github_run_id VARCHAR(50),  -- GitHub Actions run ID
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Cleanup tracking
    expires_at TIMESTAMP,  -- When download link expires
    deleted_at TIMESTAMP
);

-- =============================================================================
-- 2. Create indexes for efficient queries
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_cloud_builds_user ON cloud_builds(user_id);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_project ON cloud_builds(project_id);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_status ON cloud_builds(status);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_created ON cloud_builds(created_at DESC);

-- =============================================================================
-- 3. Add cloud_builds_per_month column to tier_limits if it doesn't exist
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tier_limits' AND column_name = 'cloud_builds_per_month'
    ) THEN
        ALTER TABLE tier_limits ADD COLUMN cloud_builds_per_month INTEGER DEFAULT 0;
    END IF;
END $$;

-- =============================================================================
-- 4. Update tier limits for cloud builds
-- =============================================================================
UPDATE tier_limits SET cloud_builds_per_month = 0 WHERE tier = 'free';
UPDATE tier_limits SET cloud_builds_per_month = 10 WHERE tier = 'pro';
UPDATE tier_limits SET cloud_builds_per_month = -1 WHERE tier = 'business';  -- unlimited

-- =============================================================================
-- 5. Add cloud_compilation boolean to tier_limits if missing
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tier_limits' AND column_name = 'cloud_compilation'
    ) THEN
        ALTER TABLE tier_limits ADD COLUMN cloud_compilation BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

UPDATE tier_limits SET cloud_compilation = FALSE WHERE tier = 'free';
UPDATE tier_limits SET cloud_compilation = TRUE WHERE tier = 'pro';
UPDATE tier_limits SET cloud_compilation = TRUE WHERE tier = 'business';

-- =============================================================================
-- Migration complete
-- =============================================================================
