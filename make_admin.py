"""
Make parth.ajit7052@gmail.com admin and remove demo account
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

# Load from data/.env (same as server/config.py does)
env_file = Path(__file__).parent.parent / "data" / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()  # Fallback

DATABASE_URL = os.getenv("DATABASE_URL")

async def setup_admin():
    print("=" * 60)
    print("  Setting up Admin Account")
    print("=" * 60)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # 0. Ensure subscriptions table exists
        print("\n[0/5] Ensuring subscriptions table exists...")
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
        print("    ✅ Subscriptions table ready")
        
        # 1. Delete demo user and all related data
        print("\n[1/5] Removing demo account...")
        demo = await conn.fetchrow("SELECT id FROM users WHERE email = $1", "demo@example.com")
        if demo:
            demo_id = demo['id']
            # Delete will cascade to projects, licenses, etc.
            await conn.execute("DELETE FROM users WHERE id = $1", demo_id)
            print("    ✅ Demo account removed")
        else:
            print("    ℹ️  Demo account not found")
        
        # 2. Update your account to admin/enterprise
        print("\n[2/5] Upgrading parth.ajit7052@gmail.com to admin...")
        user = await conn.fetchrow("SELECT id, plan, role FROM users WHERE email = $1", "parth.ajit7052@gmail.com")
        if user:
            await conn.execute("""
                UPDATE users 
                SET plan = 'enterprise', 
                    role = 'admin',
                    name = 'Parth Ajit (Admin)',
                    updated_at = NOW()
                WHERE email = $1
            """, "parth.ajit7052@gmail.com")
            print("    ✅ Account upgraded to Enterprise + Admin role")
            print("    📧 Email: parth.ajit7052@gmail.com")
            print("    👤 Name: Parth Ajit (Admin)")
            print("    🏆 Plan: Enterprise")
            print("    🔐 Role: Admin")
            
            # Create or update subscription record
            existing_sub = await conn.fetchrow(
                "SELECT id FROM subscriptions WHERE user_id = $1", user['id']
            )
            if not existing_sub:
                import uuid
                sub_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO subscriptions (id, user_id, plan_tier, status)
                    VALUES ($1, $2, 'enterprise', 'active')
                """, sub_id, user['id'])
                print("    ✅ Created enterprise subscription")
            else:
                await conn.execute("""
                    UPDATE subscriptions SET plan_tier = 'enterprise', status = 'active'
                    WHERE user_id = $1
                """, user['id'])
                print("    ✅ Updated existing subscription to enterprise")
        else:
            print("    ❌ Account not found. Please register first.")

        
        # 3. Show account stats
        print("\n[3/5] Account Statistics...")
        if user:
            projects = await conn.fetchval("SELECT COUNT(*) FROM projects WHERE user_id = $1", user['id'])
            licenses = await conn.fetchval("""
                SELECT COUNT(*) FROM licenses l 
                JOIN projects p ON l.project_id = p.id 
                WHERE p.user_id = $1
            """, user['id'])
            print(f"    Projects: {projects}")
            print(f"    Licenses: {licenses}")
        
        # 4. Verify no demo accounts remain
        print("\n[4/5] Verifying cleanup...")
        demo_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE email LIKE '%demo%'")
        if demo_count == 0:
            print("    ✅ No demo accounts found")
        else:
            print(f"    ⚠️  Found {demo_count} demo-related accounts")
        
        print("\n" + "=" * 60)
        print("  ✅ Admin Setup Complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_admin())
