-- Migration 029: Add license_id to cloud_builds
-- Feature: Link cloud builds to specific licenses for hardware locking

-- Add license_id column to cloud_builds table
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS license_id VARCHAR(32) REFERENCES licenses(id) ON DELETE SET NULL;

-- Create index for faster lookups by license
CREATE INDEX IF NOT EXISTS idx_cloud_builds_license ON cloud_builds(license_id);

-- Migration complete
