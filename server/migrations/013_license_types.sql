-- Migration 013: License Types (Monetization Phase)
-- Supports Perpetual, Subscription, and Trial licenses.

-- Add license_type column
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS license_type VARCHAR(20) DEFAULT 'perpetual';

-- Add subscription/trial specific columns
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS subscription_id VARCHAR(100);
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMP;
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS trial_duration_days INTEGER;

-- Conversion tracking
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS converted_from_trial BOOLEAN DEFAULT FALSE;
ALTER TABLE licenses ADD COLUMN IF NOT EXISTS converted_at TIMESTAMP;

-- Constraint: valid license types
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_license_type') THEN
        ALTER TABLE licenses ADD CONSTRAINT ck_license_type 
        CHECK (license_type IN ('perpetual', 'subscription', 'trial'));
    END IF;
END
$$;
