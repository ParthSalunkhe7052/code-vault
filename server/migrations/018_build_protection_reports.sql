-- Migration: Create build_protection_reports table
-- Stores protection reports generated after each build

CREATE TABLE IF NOT EXISTS build_protection_reports (
    id SERIAL PRIMARY KEY,
    build_id TEXT NOT NULL,
    project_id TEXT,
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Protection Layer Information
    protection_level TEXT NOT NULL, -- 'basic', 'standard', 'advanced', 'enterprise'
    protection_layers JSONB NOT NULL DEFAULT '[]', -- Array of applied protection features
    
    -- Security Metrics
    estimated_reversal_difficulty TEXT NOT NULL, -- 'easy', 'moderate', 'hard', 'very_hard'
    obfuscation_enabled BOOLEAN DEFAULT FALSE,
    ed25519_signatures BOOLEAN DEFAULT FALSE,
    binary_hash_verification BOOLEAN DEFAULT FALSE,
    hwid_binding_enabled BOOLEAN DEFAULT FALSE,
    offline_lease_enabled BOOLEAN DEFAULT FALSE,
    heartbeat_enabled BOOLEAN DEFAULT FALSE,
    
    -- License Information
    license_type TEXT NOT NULL, -- 'fixed', 'generic', 'demo', 'floating'
    license_tier TEXT NOT NULL, -- 'free', 'pro', 'business', 'enterprise'
    
    -- Report Content (JSON for flexibility)
    report_data JSONB NOT NULL DEFAULT '{}',
    
    -- PDF Export URL (if generated)
    pdf_url TEXT
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_build_reports_build_id ON build_protection_reports(build_id);
CREATE INDEX IF NOT EXISTS idx_build_reports_project_id ON build_protection_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_build_reports_user_id ON build_protection_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_build_reports_created_at ON build_protection_reports(created_at DESC);

-- Comment explaining table purpose
COMMENT ON TABLE build_protection_reports IS 
    'Stores protection reports for each build showing security layers applied and estimated reversal difficulty.';
