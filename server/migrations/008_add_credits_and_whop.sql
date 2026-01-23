-- Add credits to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS build_credits INTEGER DEFAULT 0;

-- Add Whop integration table
CREATE TABLE IF NOT EXISTS whop_integrations (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    whop_company_id TEXT,
    whop_api_key TEXT, -- Encrypted
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add Whop purchases log
CREATE TABLE IF NOT EXISTS whop_purchases (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE, -- The developer
    whop_payment_id TEXT UNIQUE,
    license_id TEXT REFERENCES licenses(id) ON DELETE SET NULL,
    buyer_email TEXT,
    amount_cents INTEGER,
    status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
