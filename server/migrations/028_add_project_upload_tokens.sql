-- Migration 028: Add project_upload_tokens table for R2 presigned URL uploads
-- Enables direct R2 uploads to bypass Heroku 30-second request timeout

CREATE TABLE IF NOT EXISTS project_upload_tokens (
    project_id VARCHAR(32) PRIMARY KEY,
    token VARCHAR(64) NOT NULL,
    r2_key VARCHAR(512) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_upload_tokens_token ON project_upload_tokens(token);
CREATE INDEX IF NOT EXISTS idx_project_upload_tokens_r2_key ON project_upload_tokens(r2_key);
