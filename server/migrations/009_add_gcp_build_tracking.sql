-- Migration: Add GCP Build Tracking and Performance Metrics
-- Purpose: Add new columns for Cloud Build optimization and track performance

-- Add new columns for GCP build tracking
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS gcp_build_id TEXT;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS build_type TEXT DEFAULT 'cloud_build';
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS build_duration INTEGER DEFAULT 0;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS queue_wait_time INTEGER DEFAULT 0;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS error_type TEXT;

-- Create index for GCP build lookups
CREATE INDEX IF NOT EXISTS idx_cloud_builds_gcp_id ON cloud_builds(gcp_build_id);

-- Create index for build type queries
CREATE INDEX IF NOT EXISTS idx_cloud_builds_type ON cloud_builds(build_type);

-- Add comments explaining the change
COMMENT ON COLUMN cloud_builds.github_run_id IS 'DEPRECATED: Use gcp_build_id for Cloud Build. Kept for backward compatibility.';
COMMENT ON COLUMN cloud_builds.gcp_build_id IS 'Google Cloud Build job ID - used for build status tracking and logs';
COMMENT ON COLUMN cloud_builds.build_type IS 'Type of build system used: cloud_build, github_actions (deprecated)';
COMMENT ON COLUMN cloud_builds.build_duration IS 'Total build time in seconds (from start to completion)';
COMMENT ON COLUMN cloud_builds.queue_wait_time IS 'Time spent waiting in queue before build started';
COMMENT ON COLUMN cloud_builds.error_type IS 'Categorized error type: timeout, connection, syntax_error, dependency_error, etc.';

-- Migrate existing data: populate gcp_build_id from github_run_id where appropriate
UPDATE cloud_builds 
SET gcp_build_id = github_run_id,
    build_type = 'cloud_build'
WHERE github_run_id IS NOT NULL 
  AND github_run_id LIKE '________-____-____-____-____________'
  AND gcp_build_id IS NULL;
