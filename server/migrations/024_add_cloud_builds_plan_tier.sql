-- Migration 024: Add plan_tier column to cloud_builds
-- Tracks the user's subscription tier when the build was created

-- Add plan_tier column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cloud_builds' AND column_name = 'plan_tier'
    ) THEN
        ALTER TABLE cloud_builds ADD COLUMN plan_tier VARCHAR(20) DEFAULT 'pro';
    END IF;
END $$;

-- Create index for tier-based queries
CREATE INDEX IF NOT EXISTS idx_cloud_builds_plan_tier ON cloud_builds(plan_tier);

-- Update existing rows to infer tier from user plan
-- Set default to 'pro' for existing builds
UPDATE cloud_builds SET plan_tier = 'pro' WHERE plan_tier IS NULL;

-- Add comment explaining the column
COMMENT ON COLUMN cloud_builds.plan_tier IS 'User subscription tier at time of build (free, pro, business)';
