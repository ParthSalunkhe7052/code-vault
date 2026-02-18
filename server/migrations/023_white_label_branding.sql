-- Migration 023: White Label Branding
-- Adds custom branding fields for Business/Enterprise tiers

-- 1. Add branding columns to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_name VARCHAR(100);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_url VARCHAR(500);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_primary_color VARCHAR(7) DEFAULT '#6366f1';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_secondary_color VARCHAR(7) DEFAULT '#4f46e5';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_logo_url VARCHAR(1000);

-- 2. Add branding settings to users table (for account-level defaults)
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_url VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_primary_color VARCHAR(7) DEFAULT '#6366f1';
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_brand_secondary_color VARCHAR(7) DEFAULT '#4f46e5';

-- 3. Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_projects_brand ON projects(brand_name) WHERE brand_name IS NOT NULL;

-- 4. Add constraint to ensure valid hex colors
ALTER TABLE projects DROP CONSTRAINT IF EXISTS valid_primary_color;
ALTER TABLE projects DROP CONSTRAINT IF EXISTS valid_secondary_color;
ALTER TABLE projects ADD CONSTRAINT valid_primary_color CHECK (brand_primary_color ~ '^#[0-9A-Fa-f]{6}$' OR brand_primary_color IS NULL);
ALTER TABLE projects ADD CONSTRAINT valid_secondary_color CHECK (brand_secondary_color ~ '^#[0-9A-Fa-f]{6}$' OR brand_secondary_color IS NULL);
