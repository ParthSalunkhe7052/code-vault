-- =============================================================================
-- Base Schema for CodeVault
-- Created: 2026-02-18
-- Description: Core tables required for CodeVault application
-- =============================================================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(32) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    plan VARCHAR(20) DEFAULT 'free',
    role VARCHAR(20) DEFAULT 'user',
    api_key VARCHAR(255),
    build_credits INTEGER DEFAULT 0,
    legacy_tier_model BOOLEAN DEFAULT FALSE,
    total_licenses_used INTEGER DEFAULT 0,
    stripe_customer_id VARCHAR(100),
    -- Default branding
    default_brand_name VARCHAR(100),
    default_brand_url VARCHAR(500),
    default_brand_primary_color VARCHAR(7) DEFAULT '#6366f1',
    default_brand_secondary_color VARCHAR(7) DEFAULT '#4f46e5',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- =============================================================================
-- PROJECTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    language VARCHAR(20) DEFAULT 'python',
    compiler_options JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    signing_secret VARCHAR(64),
    signing_private_key TEXT,
    signing_public_key TEXT,
    signing_algorithm VARCHAR(10) DEFAULT 'ed25519',
    -- White-label branding
    brand_name VARCHAR(100),
    brand_url VARCHAR(500),
    brand_primary_color VARCHAR(7) DEFAULT '#6366f1',
    brand_secondary_color VARCHAR(7) DEFAULT '#4f46e5',
    brand_logo_url VARCHAR(1000),
    -- Heartbeat settings
    heartbeat_interval_seconds INTEGER DEFAULT 300,
    heartbeat_grace_period_seconds INTEGER DEFAULT 60,
    hmac_deprecation_warning_shown BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);

-- =============================================================================
-- PROJECT FILES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS project_files (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(500),
    file_hash VARCHAR(64),
    file_size BIGINT,
    is_cloud BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_files_project ON project_files(project_id);

-- =============================================================================
-- LICENSES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS licenses (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    license_key VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    expires_at TIMESTAMP,
    max_machines INTEGER DEFAULT 1,
    features JSONB DEFAULT '[]',
    client_name VARCHAR(255),
    client_email VARCHAR(255),
    notes TEXT,
    license_type VARCHAR(20) DEFAULT 'perpetual',
    license_mode VARCHAR(20) DEFAULT 'static',
    max_concurrent INTEGER DEFAULT 1,
    subscription_id VARCHAR(100),
    trial_started_at TIMESTAMP,
    trial_duration_days INTEGER,
    converted_from_trial BOOLEAN DEFAULT FALSE,
    converted_at TIMESTAMP,
    last_validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_licenses_project ON licenses(project_id);
CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key);

-- =============================================================================
-- HARDWARE BINDINGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS hardware_bindings (
    id VARCHAR(32) PRIMARY KEY,
    license_id VARCHAR(32) NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    hwid VARCHAR(64) NOT NULL,
    machine_name VARCHAR(255),
    ip_address VARCHAR(45),
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    last_heartbeat_at TIMESTAMP,
    heartbeat_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_flagged BOOLEAN DEFAULT FALSE,
    flagged_reason TEXT,
    flagged_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hardware_bindings_license ON hardware_bindings(license_id);
CREATE INDEX IF NOT EXISTS idx_hardware_bindings_hwid ON hardware_bindings(hwid);

-- =============================================================================
-- LICENSE VARIABLES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS license_variables (
    id VARCHAR(32) PRIMARY KEY,
    license_id VARCHAR(32) NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value VARCHAR(1000),
    is_secret BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(license_id, key)
);

CREATE INDEX IF NOT EXISTS idx_license_variables_license ON license_variables(license_id);

-- =============================================================================
-- SUBSCRIPTIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_tier VARCHAR(20) DEFAULT 'free',
    status VARCHAR(20) DEFAULT 'active',
    sync_source VARCHAR(20) DEFAULT 'manual',
    stripe_subscription_id VARCHAR(100),
    stripe_status VARCHAR(50),
    polar_subscription_id VARCHAR(100),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);

-- =============================================================================
-- TIER LIMITS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS tier_limits (
    tier VARCHAR(20) PRIMARY KEY,
    max_projects INTEGER DEFAULT 1,
    max_licenses_per_project INTEGER DEFAULT 50,
    max_licenses_total INTEGER DEFAULT 50,
    can_sell_licenses BOOLEAN DEFAULT FALSE,
    cloud_compilation BOOLEAN DEFAULT FALSE,
    cloud_builds_per_month INTEGER DEFAULT 0,
    cloud_platforms JSONB DEFAULT '["windows"]',
    webhooks BOOLEAN DEFAULT FALSE,
    team_seats INTEGER DEFAULT 1,
    node_support BOOLEAN DEFAULT FALSE,
    white_label_branding BOOLEAN DEFAULT FALSE,
    analytics BOOLEAN DEFAULT FALSE,
    trial_builds_per_month INTEGER DEFAULT 5
);

-- Insert default tier limits
INSERT INTO tier_limits (tier, max_projects, max_licenses_per_project, max_licenses_total, can_sell_licenses, cloud_compilation, cloud_builds_per_month, webhooks, team_seats, node_support, white_label_branding, analytics, trial_builds_per_month)
VALUES 
    ('free', 1, 50, 50, FALSE, FALSE, 0, FALSE, 1, FALSE, FALSE, FALSE, 5),
    ('pro', -1, 500, 500, TRUE, TRUE, 25, TRUE, 1, TRUE, FALSE, TRUE, -1),
    ('business', -1, 5000, 5000, TRUE, TRUE, 100, TRUE, 10, TRUE, TRUE, TRUE, -1),
    ('enterprise', -1, -1, -1, TRUE, TRUE, -1, TRUE, -1, TRUE, TRUE, TRUE, -1)
ON CONFLICT (tier) DO NOTHING;

-- =============================================================================
-- WEBHOOKS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS webhooks (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    events JSONB DEFAULT '["license.validated", "license.created"]',
    secret VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhooks_user ON webhooks(user_id);

-- =============================================================================
-- VALIDATION LOGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS validation_logs (
    id VARCHAR(32) PRIMARY KEY,
    license_id VARCHAR(32),
    project_id VARCHAR(32),
    license_key VARCHAR(50),
    hwid VARCHAR(64),
    ip_address VARCHAR(45),
    country VARCHAR(2),
    city VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT,
    result VARCHAR(20),
    response_time_ms INTEGER,
    machine_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validation_logs_project ON validation_logs(project_id);

CREATE INDEX IF NOT EXISTS idx_validation_logs_license ON validation_logs(license_id);
CREATE INDEX IF NOT EXISTS idx_validation_logs_project ON validation_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_validation_logs_created ON validation_logs(created_at DESC);

-- =============================================================================
-- HWID RESET LOGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS hwid_reset_logs (
    id VARCHAR(32) PRIMARY KEY,
    license_id VARCHAR(32) NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    reset_by_user_id VARCHAR(32) NOT NULL REFERENCES users(id),
    bindings_removed INTEGER DEFAULT 0,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hwid_reset_logs_license ON hwid_reset_logs(license_id);

-- =============================================================================
-- CLOUD BUILDS TABLE (from migration 006)
-- =============================================================================
CREATE TABLE IF NOT EXISTS cloud_builds (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language VARCHAR(20) NOT NULL,
    entry_file VARCHAR(255) NOT NULL,
    output_name VARCHAR(255) NOT NULL,
    license_key VARCHAR(255),
    config_json JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    download_key VARCHAR(500),
    download_filename VARCHAR(255),
    download_size BIGINT,
    error_message TEXT,
    github_run_id VARCHAR(50),
    gcp_build_id TEXT,
    build_type TEXT DEFAULT 'cloud_build',
    build_duration INTEGER DEFAULT 0,
    queue_wait_time INTEGER DEFAULT 0,
    error_type TEXT,
    admin_error_details TEXT,
    logs TEXT[] DEFAULT '{}',
    target_platforms JSONB DEFAULT '["windows"]',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    deleted_at TIMESTAMP,
    plan_tier VARCHAR(20) DEFAULT 'pro'
);

CREATE INDEX IF NOT EXISTS idx_cloud_builds_user ON cloud_builds(user_id);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_project ON cloud_builds(project_id);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_status ON cloud_builds(status);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_created ON cloud_builds(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_plan_tier ON cloud_builds(plan_tier);
CREATE INDEX IF NOT EXISTS idx_cloud_builds_gcp_id ON cloud_builds(gcp_build_id);

-- =============================================================================
-- CLOUD BUILD ARTIFACTS TABLE (from migration 007)
-- =============================================================================
CREATE TABLE IF NOT EXISTS cloud_build_artifacts (
    id VARCHAR(32) PRIMARY KEY,
    build_id VARCHAR(32) NOT NULL REFERENCES cloud_builds(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    artifact_key VARCHAR(500),
    artifact_size BIGINT,
    checksum VARCHAR(64),
    download_key VARCHAR(500),
    download_filename VARCHAR(255),
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cloud_build_artifacts_build ON cloud_build_artifacts(build_id);
CREATE INDEX IF NOT EXISTS idx_cloud_build_artifacts_status ON cloud_build_artifacts(status);
CREATE INDEX IF NOT EXISTS idx_cloud_build_artifacts_platform ON cloud_build_artifacts(platform);

-- =============================================================================
-- BINARY HASHES TABLE (from migration 011)
-- =============================================================================
CREATE TABLE IF NOT EXISTS binary_hashes (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    binary_hash VARCHAR(64) NOT NULL,
    binary_size BIGINT,
    platform VARCHAR(20),
    build_id VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, binary_hash)
);

CREATE INDEX IF NOT EXISTS idx_binary_hashes_project ON binary_hashes(project_id);

-- =============================================================================
-- LICENSE SESSIONS TABLE (from migration 014 - floating licenses)
-- =============================================================================
CREATE TABLE IF NOT EXISTS license_sessions (
    id VARCHAR(32) PRIMARY KEY,
    license_id VARCHAR(32) NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    hwid VARCHAR(64) NOT NULL,
    session_token VARCHAR(64) NOT NULL,
    ip_address VARCHAR(45),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_active_at TIMESTAMP,
    released_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_license_sessions_license ON license_sessions(license_id);
CREATE INDEX IF NOT EXISTS idx_license_sessions_token ON license_sessions(session_token);

-- =============================================================================
-- WHOP INTEGRATIONS TABLE (from migration 008)
-- =============================================================================
CREATE TABLE IF NOT EXISTS whop_integrations (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    whop_user_id VARCHAR(100),
    api_key VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whop_integrations_user ON whop_integrations(user_id);

-- =============================================================================
-- WHOP PURCHASES TABLE (from migration 008)
-- =============================================================================
CREATE TABLE IF NOT EXISTS whop_purchases (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    whop_order_id VARCHAR(100),
    product_id VARCHAR(100),
    amount_cents INTEGER,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whop_purchases_user ON whop_purchases(user_id);

-- =============================================================================
-- USAGE COUNTERS TABLE (from migration 016)
-- =============================================================================
CREATE TABLE IF NOT EXISTS usage_counters (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    counter_type VARCHAR(50) NOT NULL,
    counter_value BIGINT DEFAULT 0,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, counter_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_usage_counters_user ON usage_counters(user_id);

-- =============================================================================
-- PROCESSED WEBHOOK EVENTS TABLE (from migration 017)
-- =============================================================================
CREATE TABLE IF NOT EXISTS processed_webhook_events (
    id VARCHAR(32) PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL,
    event_type VARCHAR(100),
    payload JSONB,
    processed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_webhook_events_event_id ON processed_webhook_events(event_id);

-- =============================================================================
-- BUILD PROTECTION REPORTS TABLE (from migration 018)
-- =============================================================================
CREATE TABLE IF NOT EXISTS build_protection_reports (
    id VARCHAR(32) PRIMARY KEY,
    build_id VARCHAR(32) NOT NULL REFERENCES cloud_builds(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20),
    message TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_build_protection_reports_build ON build_protection_reports(build_id);

-- =============================================================================
-- TRIAL BUILDS TABLE (from migration 022)
-- =============================================================================
CREATE TABLE IF NOT EXISTS trial_builds (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    build_id VARCHAR(32) REFERENCES cloud_builds(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending',
    platform VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trial_builds_user ON trial_builds(user_id);
CREATE INDEX IF NOT EXISTS idx_trial_builds_project ON trial_builds(project_id);

-- =============================================================================
-- TRIAL BUILD TOKENS TABLE (from migration 022)
-- =============================================================================
CREATE TABLE IF NOT EXISTS trial_build_tokens (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    used_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trial_build_tokens_user ON trial_build_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_trial_build_tokens_hash ON trial_build_tokens(token_hash);

-- =============================================================================
-- ADMIN USER SETUP
-- =============================================================================
-- This will be handled by the application based on ADMIN_EMAIL env variable

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================
