"""
Database connection pool and initialization for PostgreSQL.
"""

from typing import Optional
from contextlib import asynccontextmanager
import uuid

import asyncpg
from fastapi import HTTPException

from config import DATABASE_URL, ADMIN_EMAIL

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


async def get_db():
    """Get database connection from pool."""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return await db_pool.acquire()


async def release_db(conn):
    """Release connection back to pool."""
    if db_pool and conn:
        await db_pool.release(conn)


async def init_database():
    """Initialize PostgreSQL database with all tables and indexes."""
    global db_pool
    
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    
    conn = await db_pool.acquire()
    try:
        # Create tables
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
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                settings JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
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
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS validation_logs (
                id SERIAL PRIMARY KEY,
                license_id TEXT REFERENCES licenses(id) ON DELETE SET NULL,
                license_key TEXT,
                hwid TEXT,
                ip_address TEXT,
                result TEXT NOT NULL,
                response_time_ms INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS project_files (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT,
                file_size INTEGER,
                is_cloud BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS compile_jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                output_path TEXT,
                output_filename TEXT,
                is_cloud BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                logs JSONB DEFAULT '[]',
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
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
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id TEXT PRIMARY KEY,
                webhook_id TEXT NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                payload JSONB,
                response_status INTEGER,
                response_body TEXT,
                delivery_time_ms INTEGER,
                success BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS hwid_reset_logs (
                id TEXT PRIMARY KEY,
                license_id TEXT NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
                reset_by_user_id TEXT NOT NULL,
                bindings_removed INTEGER DEFAULT 0,
                reason TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Analytics events table for tracking usage
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                project_id TEXT,
                metadata JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_logs_created ON validation_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_created ON analytics_events(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_user ON analytics_events(user_id)")
        
        # Migrations for existing databases
        # Add role column if it doesn't exist
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            print("[Migration] Added 'role' column to users table")
        except Exception:
            pass  # Column already exists
        
        # Grant admin role to configured email (from env var)
        if ADMIN_EMAIL:
            await conn.execute("""
                UPDATE users SET role = 'admin' WHERE email = $1
            """, ADMIN_EMAIL)
        
        # =============================================================================
        # Stripe/Subscription Tables (Phase 1)
        # =============================================================================
        
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
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS license_purchases (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                license_id TEXT REFERENCES licenses(id) ON DELETE SET NULL,
                stripe_payment_intent_id TEXT,
                stripe_checkout_session_id TEXT,
                buyer_email TEXT NOT NULL,
                buyer_name TEXT,
                amount_cents INTEGER NOT NULL,
                currency TEXT DEFAULT 'usd',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Create indexes for subscription tables
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_license_purchases_project ON license_purchases(project_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_license_purchases_session ON license_purchases(stripe_checkout_session_id)")
        
        # Migrations for marketplace columns on projects table
        migration_columns = [
            ("projects", "is_public", "BOOLEAN DEFAULT FALSE"),
            ("projects", "price_cents", "INTEGER DEFAULT 0"),
            ("projects", "currency", "TEXT DEFAULT 'usd'"),
            ("projects", "store_slug", "TEXT UNIQUE"),
        ]
        
        for table, column, column_type in migration_columns:
            try:
                await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                print(f"[Migration] Added '{column}' column to {table} table")
            except Exception:
                pass  # Column already exists
        
        # Set up admin user with enterprise subscription if ADMIN_EMAIL is configured
        if ADMIN_EMAIL:
            admin_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", ADMIN_EMAIL
            )
            if admin_user:
                admin_id = admin_user['id']
                # Update user plan to enterprise 
                await conn.execute("""
                    UPDATE users SET plan = 'enterprise', role = 'admin' WHERE id = $1
                """, admin_id)
                
                # Check if subscription exists
                existing_sub = await conn.fetchrow(
                    "SELECT id FROM subscriptions WHERE user_id = $1", admin_id
                )
                
                if not existing_sub:
                    # Create enterprise subscription for admin
                    sub_id = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO subscriptions (id, user_id, plan_tier, status)
                        VALUES ($1, $2, 'enterprise', 'active')
                    """, sub_id, admin_id)
                    print(f"[Migration] Created enterprise subscription for admin: {ADMIN_EMAIL}")
                else:
                    # Update existing subscription to enterprise
                    await conn.execute("""
                        UPDATE subscriptions SET plan_tier = 'enterprise', status = 'active'
                        WHERE user_id = $1
                    """, admin_id)
        print(f"[Migration] Updated subscription to enterprise for admin: {ADMIN_EMAIL}")

        # =============================================================================
        # Migration 005: Tier Sync Improvements (Phase 1 Fix)
        # =============================================================================
        try:
            await conn.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS sync_source VARCHAR(20) DEFAULT 'stripe_webhook'")
            print("[Migration] Added 'sync_source' column to subscriptions table")
        except Exception:
            pass

        # Create index
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)")
        
        # =============================================================================
        # Migration: Node.js Support (Phase 2)
        # =============================================================================
        try:
            await conn.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS language VARCHAR(20) DEFAULT 'python'")
            print("[Migration] Added 'language' column to projects table")
        except Exception:
            pass

        try:
            await conn.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS compiler_options JSONB DEFAULT '{}'")
            print("[Migration] Added 'compiler_options' column to projects table")
        except Exception:
            pass
        
        # =============================================================================
        # Migration: Mission Control Live Map (Geolocation)
        # =============================================================================
        geo_columns = [
            ("validation_logs", "city", "VARCHAR(100)"),
            ("validation_logs", "country", "VARCHAR(100)"),
            ("validation_logs", "latitude", "DOUBLE PRECISION"),
            ("validation_logs", "longitude", "DOUBLE PRECISION"),
        ]
        
        for table, column, column_type in geo_columns:
            try:
                await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type}")
                print(f"[Migration] Added '{column}' column to {table} table")
            except Exception:
                pass
        
        # Create index for geo queries
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_logs_geo ON validation_logs(latitude, longitude) WHERE latitude IS NOT NULL")
        
        # Sync users.plan with subscriptions.plan_tier (Critical Fix)
        # Only update if they are different
        await conn.execute("""
            UPDATE users u
            SET plan = sub_query.plan_tier
            FROM (
                SELECT DISTINCT ON (user_id) user_id, plan_tier
                FROM subscriptions
                ORDER BY user_id, created_at DESC
            ) AS sub_query
            WHERE u.id = sub_query.user_id AND u.plan != sub_query.plan_tier
        """)
        print("[Migration] Synced users.plan with subscriptions.plan_tier")

        print(f"[✓] Database initialized (PostgreSQL)")

    finally:
        await db_pool.release(conn)


async def close_database():
    """Close database pool."""
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for database initialization."""
    await init_database()
    yield
    await close_database()
