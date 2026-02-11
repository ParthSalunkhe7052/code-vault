-- Migration 016: Usage-based Pricing & Stripe Integration
-- Tracks validation usage and connects to Stripe.

-- 1. Usage Counters for metered billing
CREATE TABLE IF NOT EXISTS usage_counters (
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
    metric_name VARCHAR(50) NOT NULL, -- e.g. 'validations', 'cloud_builds'
    current_value INTEGER DEFAULT 0,
    reset_at TIMESTAMP,
    PRIMARY KEY (user_id, metric_name)
);

-- 2. Stripe integration for users
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);

-- 3. Stripe integration for subscriptions
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_status VARCHAR(50);
