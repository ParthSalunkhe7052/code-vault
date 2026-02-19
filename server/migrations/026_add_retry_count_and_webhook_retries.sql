-- Migration: Add retry_count column and webhook_retries table
-- Date: 2026-02-19
-- Description: Fix missing database columns and tables

-- Add retry_count column to cloud_builds table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cloud_builds' AND column_name = 'retry_count'
    ) THEN
        ALTER TABLE cloud_builds ADD COLUMN retry_count INTEGER DEFAULT 0;
        ALTER TABLE cloud_builds ALTER COLUMN retry_count SET DEFAULT 0;
    END IF;
END $$;

-- Create webhook_retries table if it doesn't exist
CREATE TABLE IF NOT EXISTS webhook_retries (
    id VARCHAR(32) PRIMARY KEY,
    webhook_id VARCHAR(32) NOT NULL,
    event VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    next_retry_at TIMESTAMP NOT NULL,
    last_error TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(webhook_id, event, payload)
);

-- Create indexes for webhook_retries
CREATE INDEX IF NOT EXISTS idx_webhook_retries_status ON webhook_retries(status);
CREATE INDEX IF NOT EXISTS idx_webhook_retries_next_retry ON webhook_retries(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_webhook_retries_webhook ON webhook_retries(webhook_id);
