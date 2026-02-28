-- Migration 030: Add updated_at to cloud_builds
-- Description: Adds the missing updated_at column to track build updates

-- Add updated_at column to cloud_builds table
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Update existing rows to have updated_at match created_at
UPDATE cloud_builds SET updated_at = created_at WHERE updated_at IS NULL;

-- Migration complete
