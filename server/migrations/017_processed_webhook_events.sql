-- Migration: Create processed_webhook_events table for idempotency
-- This table tracks processed webhook events to prevent duplicate processing

CREATE TABLE IF NOT EXISTS processed_webhook_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for efficient querying by event type
CREATE INDEX IF NOT EXISTS idx_processed_webhook_events_type 
ON processed_webhook_events(event_type);

-- Create index for cleanup of old records
CREATE INDEX IF NOT EXISTS idx_processed_webhook_events_time 
ON processed_webhook_events(processed_at);

-- Add comment explaining table purpose
COMMENT ON TABLE processed_webhook_events IS 
    'Tracks processed Polar webhook events for idempotency. Events are deduplicated by event_id.';
