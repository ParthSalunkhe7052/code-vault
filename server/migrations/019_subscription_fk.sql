-- Migration 019: Subscription Foreign Key Constraints
-- Add foreign key constraint on subscriptions.user_id and unique constraint

-- Add foreign key constraint with cascade delete
ALTER TABLE subscriptions 
ADD CONSTRAINT fk_subscriptions_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Add unique constraint to prevent duplicate subscriptions per user
ALTER TABLE subscriptions 
ADD CONSTRAINT unique_user_subscription UNIQUE (user_id);
