-- Migration 022: License Limits and Trial Builds
-- Adds total license tracking for free tier and trial build system

-- 1. Add license tracking columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_licenses_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS legacy_tier_model BOOLEAN DEFAULT FALSE;

-- 2. Set legacy_tier_model for existing free tier users (grandfather them)
UPDATE users SET legacy_tier_model = TRUE WHERE plan = 'free' AND legacy_tier_model = FALSE;

-- 3. Create trial_builds table to track trial builds per user
CREATE TABLE IF NOT EXISTS trial_builds (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    demo_duration_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trial_builds_user ON trial_builds(user_id);
CREATE INDEX IF NOT EXISTS idx_trial_builds_created ON trial_builds(created_at);

-- 4. Create trial_build_tokens table for one-time use tokens
CREATE TABLE IF NOT EXISTS trial_build_tokens (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    demo_duration_minutes INTEGER DEFAULT 60,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trial_tokens_user ON trial_build_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_trial_tokens_expires ON trial_build_tokens(expires_at);

-- 5. Create function to count user's total licenses across all projects
CREATE OR REPLACE FUNCTION count_user_total_licenses(p_user_id VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count
    FROM licenses l
    JOIN projects p ON l.project_id = p.id
    WHERE p.user_id = p_user_id;
    
    RETURN total_count;
END;
$$ LANGUAGE plpgsql;

-- 6. Trigger to update total_licenses_used when licenses are created/deleted
CREATE OR REPLACE FUNCTION update_user_license_count()
RETURNS TRIGGER AS $$
DECLARE
    user_id_val VARCHAR(64);
BEGIN
    -- Get user_id from the project
    IF TG_OP = 'INSERT' THEN
        SELECT user_id INTO user_id_val FROM projects WHERE id = NEW.project_id;
        UPDATE users SET total_licenses_used = total_licenses_used + 1 WHERE id = user_id_val;
    ELSIF TG_OP = 'DELETE' THEN
        SELECT user_id INTO user_id_val FROM projects WHERE id = OLD.project_id;
        UPDATE users SET total_licenses_used = GREATEST(0, total_licenses_used - 1) WHERE id = user_id_val;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_update_license_count'
    ) THEN
        CREATE TRIGGER trigger_update_license_count
        AFTER INSERT OR DELETE ON licenses
        FOR EACH ROW EXECUTE FUNCTION update_user_license_count();
    END IF;
END $$;

-- 7. Backfill total_licenses_used for existing users
UPDATE users u SET total_licenses_used = (
    SELECT COUNT(*) 
    FROM licenses l 
    JOIN projects p ON l.project_id = p.id 
    WHERE p.user_id = u.id
);
