-- Migration: Cloud Build Platforms & Artifacts
-- Adds support for multi-platform builds and artifacts tracking

-- Add target_platforms to cloud_builds
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS target_platforms JSONB DEFAULT '["windows"]';

-- Create cloud_build_artifacts table
CREATE TABLE IF NOT EXISTS cloud_build_artifacts (
    id VARCHAR(32) PRIMARY KEY,
    build_id VARCHAR(32) NOT NULL REFERENCES cloud_builds(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL, -- windows, macos, linux
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Results
    download_key VARCHAR(500),
    download_filename VARCHAR(255),
    file_size BIGINT,
    
    -- Metadata
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_build_artifacts_build ON cloud_build_artifacts(build_id);
CREATE INDEX IF NOT EXISTS idx_build_artifacts_platform ON cloud_build_artifacts(platform);
