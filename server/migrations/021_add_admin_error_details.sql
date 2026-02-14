-- Migration: Add admin_error_details column to cloud_builds
-- Date: 2026-02-14
-- Feature: Admin debugging for cloud build failures

-- =============================================================================
-- Add admin_error_details column for detailed error tracking
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cloud_builds' AND column_name = 'admin_error_details'
    ) THEN
        ALTER TABLE cloud_builds ADD COLUMN admin_error_details TEXT;
    END IF;
END $$;

-- =============================================================================
-- Migration complete
-- =============================================================================
