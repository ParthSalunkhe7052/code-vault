-- Migration 025: Fix missing columns after Neon to Supabase migration
-- Adds all columns that were in Neon but missing in Supabase

-- =============================================================================
-- CLOUD BUILD ARTIFACTS - Missing columns
-- =============================================================================

-- Add status column
ALTER TABLE cloud_build_artifacts ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending';

-- Add download columns  
ALTER TABLE cloud_build_artifacts ADD COLUMN IF NOT EXISTS download_key VARCHAR(500);
ALTER TABLE cloud_build_artifacts ADD COLUMN IF NOT EXISTS download_filename VARCHAR(255);

-- Add error tracking
ALTER TABLE cloud_build_artifacts ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Add timing columns
ALTER TABLE cloud_build_artifacts ADD COLUMN IF NOT EXISTS started_at TIMESTAMP;
ALTER TABLE cloud_build_artifacts ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_cloud_build_artifacts_status ON cloud_build_artifacts(status);
CREATE INDEX IF NOT EXISTS idx_cloud_build_artifacts_platform ON cloud_build_artifacts(platform);

-- =============================================================================
-- CLOUD BUILDS - Missing columns
-- =============================================================================

-- Add logs column (TEXT array or JSONB for build logs)
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS logs TEXT[] DEFAULT '{}';

-- Add target_platforms if not exists
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS target_platforms JSONB DEFAULT '["windows"]';

-- Ensure all GCP build tracking columns exist
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS gcp_build_id TEXT;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS build_type TEXT DEFAULT 'cloud_build';
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS build_duration INTEGER DEFAULT 0;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS queue_wait_time INTEGER DEFAULT 0;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS error_type TEXT;
ALTER TABLE cloud_builds ADD COLUMN IF NOT EXISTS admin_error_details TEXT;

-- Create index for GCP build ID
CREATE INDEX IF NOT EXISTS idx_cloud_builds_gcp_id ON cloud_builds(gcp_build_id);

-- =============================================================================
-- PROJECTS - Missing columns
-- =============================================================================

-- Add signing algorithm columns
ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_algorithm VARCHAR(10) DEFAULT 'ed25519';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_private_key TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_public_key TEXT;

-- Add heartbeat columns
ALTER TABLE projects ADD COLUMN IF NOT EXISTS heartbeat_interval_seconds INTEGER DEFAULT 300;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS heartbeat_grace_period_seconds INTEGER DEFAULT 60;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS hmac_deprecation_warning_shown BOOLEAN DEFAULT FALSE;

-- Add white-label branding columns
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_name VARCHAR(100);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_url VARCHAR(500);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_primary_color VARCHAR(7) DEFAULT '#6366f1';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_secondary_color VARCHAR(7) DEFAULT '#4f46e5';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_logo_url VARCHAR(1000);

-- =============================================================================
-- LICENSES - Missing columns
-- =============================================================================

-- Add license type columns
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS license_type VARCHAR(20) DEFAULT 'perpetual';
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS license_mode VARCHAR(20) DEFAULT 'static';
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS max_concurrent INTEGER DEFAULT 1;

-- Add trial columns
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS subscription_id VARCHAR(100);
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMP;
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS trial_duration_days INTEGER;
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS converted_from_trial BOOLEAN DEFAULT FALSE;
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS converted_at TIMESTAMP;

-- =============================================================================
-- USERS - Missing columns
-- =============================================================================

-- Add license tracking columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_licenses_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS legacy_tier_model BOOLEAN DEFAULT FALSE;

-- Add branding default columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_url VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_primary_color VARCHAR(7) DEFAULT '#6366f1';
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_secondary_color VARCHAR(7) DEFAULT '#4f46e5';

-- Add Stripe column
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);

-- =============================================================================
-- HARDWARE BINDINGS - Missing columns
-- =============================================================================

-- Add heartbeat columns
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMP;
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS heartbeat_count INTEGER DEFAULT 0;
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS is_flagged BOOLEAN DEFAULT FALSE;
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS flagged_reason TEXT;
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS flagged_at TIMESTAMP;

-- =============================================================================
-- SUBSCRIPTIONS - Missing columns
-- =============================================================================

-- Add sync and Stripe columns
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS sync_source VARCHAR(20) DEFAULT 'manual';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_status VARCHAR(50);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS polar_subscription_id VARCHAR(100);

-- =============================================================================
-- VALIDATION LOGS - Missing columns
-- =============================================================================

-- Add geo/analytics columns
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS project_id VARCHAR(32);
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS country VARCHAR(2);
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS latitude FLOAT;
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS longitude FLOAT;

CREATE INDEX IF NOT EXISTS idx_validation_logs_project ON validation_logs(project_id);

-- =============================================================================
-- TIER LIMITS - Missing columns
-- =============================================================================

-- Add cloud build columns
ALTER TABLE tier_limits ADD COLUMN IF NOT EXISTS cloud_compilation BOOLEAN DEFAULT FALSE;
ALTER TABLE tier_limits ADD COLUMN IF NOT EXISTS cloud_builds_per_month INTEGER DEFAULT 0;

-- Update default values for existing tiers
UPDATE tier_limits SET cloud_compilation = FALSE, cloud_builds_per_month = 0 WHERE tier = 'free';
UPDATE tier_limits SET cloud_compilation = TRUE, cloud_builds_per_month = 25 WHERE tier = 'pro';
UPDATE tier_limits SET cloud_compilation = TRUE, cloud_builds_per_month = 100 WHERE tier = 'business';
UPDATE tier_limits SET cloud_compilation = TRUE, cloud_builds_per_month = -1 WHERE tier = 'enterprise';

-- =============================================================================
-- UPDATE EXISTING DATA
-- =============================================================================

-- Set default status for existing cloud_build_artifacts
UPDATE cloud_build_artifacts SET status = 'completed' WHERE status = 'pending' AND artifact_key IS NOT NULL;

-- Backfill user license counts
UPDATE users u SET total_licenses_used = (
    SELECT COUNT(*) 
    FROM licenses l 
    JOIN projects p ON l.project_id = p.id 
    WHERE p.user_id = u.id
) WHERE total_licenses_used = 0;

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================
