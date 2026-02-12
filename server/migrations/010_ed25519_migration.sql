-- Migration 010: Ed25519 Asymmetric Signing
-- Adds signing_algorithm column and ensures Ed25519 key columns exist.
-- Legacy HMAC projects will be auto-migrated via admin endpoint.

-- Add signing_algorithm column to track which signing method each project uses
ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_algorithm VARCHAR(10) DEFAULT 'hmac';

-- Ensure Ed25519 key columns exist (may already exist from earlier manual migration)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_private_key TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_public_key TEXT;

-- Backfill: mark projects that already have Ed25519 keys
UPDATE projects
SET signing_algorithm = 'ed25519'
WHERE signing_private_key IS NOT NULL
  AND signing_public_key IS NOT NULL
  AND signing_algorithm = 'hmac';
