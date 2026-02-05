"""
CodeVault Database Migration Script
Creates tables and runs necessary schema updates.
"""

import asyncio
import os
import sys
import asyncpg
from dotenv import load_dotenv

# Add server directory to path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

async def run_migrations():
    # Try to load from server/.env if not in root
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'server', '.env'))
    load_dotenv() # Fallback to root
    database_url = os.getenv("DATABASE_URL")
    admin_email = os.getenv("ADMIN_EMAIL")

    if not database_url:
        print("❌ Error: DATABASE_URL not set in .env")
        return

    print(f"🚀 Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        print("📦 Creating tables...")
        
        # User Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                plan TEXT DEFAULT 'free',
                role TEXT DEFAULT 'user',
                api_key TEXT UNIQUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Projects Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                language TEXT DEFAULT 'python',
                compiler_options JSONB DEFAULT '{}',
                settings JSONB DEFAULT '{}',
                signing_secret TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Licenses Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                license_key TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active',
                expires_at TIMESTAMPTZ,
                max_machines INTEGER DEFAULT 1,
                features JSONB DEFAULT '[]',
                client_name TEXT,
                client_email TEXT,
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                last_validated_at TIMESTAMPTZ
            )
        """)

        # Hardware Bindings Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS hardware_bindings (
                id TEXT PRIMARY KEY,
                license_id TEXT NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
                hwid TEXT NOT NULL,
                machine_name TEXT,
                ip_address TEXT,
                first_seen_at TIMESTAMPTZ DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(license_id, hwid)
            )
        """)

        # Validation Logs Table (THE BIG ONE)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS validation_logs (
                id SERIAL PRIMARY KEY,
                license_id TEXT REFERENCES licenses(id) ON DELETE SET NULL,
                license_key TEXT,
                hwid TEXT,
                ip_address TEXT,
                result TEXT NOT NULL,
                response_time_ms INTEGER,
                city TEXT,
                country TEXT,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # License Variables Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS license_variables (
                id TEXT PRIMARY KEY,
                license_id TEXT NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                is_secret BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(license_id, key)
            )
        """)

        # Subscriptions Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT UNIQUE,
                plan_tier TEXT DEFAULT 'free',
                status TEXT DEFAULT 'active',
                current_period_start TIMESTAMPTZ,
                current_period_end TIMESTAMPTZ,
                cancel_at_period_end BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Cloud Builds Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cloud_builds (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                language VARCHAR(20) NOT NULL,
                entry_file VARCHAR(255) NOT NULL,
                output_name VARCHAR(255) NOT NULL,
                license_key VARCHAR(255),
                config_json JSONB NOT NULL,
                target_platforms JSONB DEFAULT '["windows"]',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                download_key VARCHAR(500),
                download_filename VARCHAR(255),
                download_size BIGINT,
                error_message TEXT,
                github_run_id VARCHAR(50),
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                expires_at TIMESTAMPTZ,
                deleted_at TIMESTAMPTZ
            )
        """)

        # Webhooks Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                secret TEXT,
                events JSONB DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                last_triggered_at TIMESTAMPTZ,
                failure_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Indexes
        print("🔍 Creating indexes...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_logs_created ON validation_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_license_variables_license ON license_variables(license_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_logs_geo ON validation_logs(latitude, longitude) WHERE latitude IS NOT NULL")

        # Column Migrations (Ensure existing tables have new columns)
        print("🛠️ Running column migrations...")
        try:
            await conn.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_secret TEXT")
            print("  - Added 'signing_secret' to projects")
        except Exception as e:
            print(f"  - Note: projects.signing_secret check: {e}")

        # Ensure all existing projects HAVE a signing secret
        await conn.execute("UPDATE projects SET signing_secret = md5(random()::text) WHERE signing_secret IS NULL")
        print("  - Backfilled missing signing_secrets")

        # Admin Setup
        if admin_email:
            print(f"👑 Setting up admin: {admin_email}")
            await conn.execute("UPDATE users SET role = 'admin', plan = 'enterprise' WHERE email = $1", admin_email)

        print("✅ Migrations complete!")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migrations())
