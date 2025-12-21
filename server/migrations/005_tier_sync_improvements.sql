-- Migration 005: Tier Synchronization Improvements
-- Date: 2025-12-17
-- Description: Adds sync_source tracking and fixes mismatches between users.plan and subscriptions.plan_tier

-- 1. Add sync_source column to subscriptions table
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS sync_source VARCHAR(20) DEFAULT 'stripe_webhook';

-- 2. Create index on subscriptions.user_id for faster lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);

-- 3. Backfill/Sync users.plan with subscriptions.plan_tier
-- This fixes the critical bug where users have Enterprise sub but Free plan in users table
UPDATE users u
SET plan = (
    SELECT s.plan_tier 
    FROM subscriptions s 
    WHERE s.user_id = u.id 
    ORDER BY s.created_at DESC 
    LIMIT 1
)
WHERE EXISTS (
    SELECT 1 FROM subscriptions s WHERE s.user_id = u.id
);
