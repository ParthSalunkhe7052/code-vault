-- Migration 015: Analytics Setup
-- Enhances validation_logs and creates views.

-- 1. Add project_id and Geo columns to validation_logs
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS project_id VARCHAR(64);
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS country VARCHAR(10);
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 7);
ALTER TABLE validation_logs ADD COLUMN IF NOT EXISTS longitude DECIMAL(10, 7);

CREATE INDEX IF NOT EXISTS idx_logs_project ON validation_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_logs_result ON validation_logs(result);

-- 2. Daily Stats View
CREATE OR REPLACE VIEW view_daily_validations AS
SELECT 
    date_trunc('day', created_at) as day,
    project_id,
    result,
    COUNT(*) as total
FROM validation_logs
GROUP BY 1, 2, 3;

-- 3. Geo Distribution View
CREATE OR REPLACE VIEW view_geo_stats AS
SELECT 
    country,
    project_id,
    COUNT(*) as total
FROM validation_logs
WHERE country IS NOT NULL
GROUP BY 1, 2;
