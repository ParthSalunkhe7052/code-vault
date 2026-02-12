-- Migration 012: Heartbeat & HWID Heuristics
-- Adds columns for periodic heartbeat tracking and HWID fraud detection.

-- 1. Add heartbeat columns to hardware_bindings
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMP;
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS heartbeat_count INTEGER DEFAULT 0;

-- 2. Add flagging columns for suspicious HWIDs (SEC3)
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS is_flagged BOOLEAN DEFAULT FALSE;
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS flagged_reason TEXT;
ALTER TABLE hardware_bindings ADD COLUMN IF NOT EXISTS flagged_at TIMESTAMP;

-- 3. Add heartbeat configuration to projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS heartbeat_interval_seconds INTEGER DEFAULT 300; -- Default 5 mins
ALTER TABLE projects ADD COLUMN IF NOT EXISTS heartbeat_grace_period_seconds INTEGER DEFAULT 60;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_hb_last_heartbeat ON hardware_bindings(last_heartbeat_at);
CREATE INDEX IF NOT EXISTS idx_hb_flagged ON hardware_bindings(is_flagged);
