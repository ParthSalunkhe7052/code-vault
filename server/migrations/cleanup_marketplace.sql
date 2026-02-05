-- Migration: Cleanup Marketplace & Whop Integration
-- Description: Removes unused columns and tables from the marketplace era.

-- 1. Remove Marketplace columns from projects table
ALTER TABLE projects DROP COLUMN IF EXISTS is_public;
ALTER TABLE projects DROP COLUMN IF EXISTS price_cents;
ALTER TABLE projects DROP COLUMN IF EXISTS currency;
ALTER TABLE projects DROP COLUMN IF EXISTS store_slug;

-- 2. Drop Whop Integration tables
DROP TABLE IF EXISTS whop_integrations;
DROP TABLE IF EXISTS whop_purchases;

-- 3. Cleanup User columns (if any legacy seller columns exist)
-- (Checking schema, didn't see explicit seller columns in users, but safe to verify)
