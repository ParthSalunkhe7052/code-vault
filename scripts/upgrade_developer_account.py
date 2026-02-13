"""
One-time script to upgrade developer account to enterprise tier.
Run with: python scripts/upgrade_developer_account.py
"""

import asyncio
import sys
import os

# Add server directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.join(os.path.dirname(script_dir), "server")
sys.path.insert(0, server_dir)

from database import init_database, get_db, release_db, close_database


DEVELOPER_EMAIL = "parth.ajit7052@gmail.com"


async def upgrade_developer():
    """Upgrade developer account to enterprise with lifetime subscription."""
    
    print(f"[*] Upgrading account: {DEVELOPER_EMAIL}")
    print("-" * 50)
    
    # Initialize database
    await init_database()
    
    conn = await get_db()
    try:
        # 1. Find user by email
        user = await conn.fetchrow(
            "SELECT id, email, role, plan FROM users WHERE email = $1",
            DEVELOPER_EMAIL
        )
        
        if not user:
            print(f"[ERROR] User not found: {DEVELOPER_EMAIL}")
            print("[TIP] Make sure you have registered an account with this email first.")
            return False
        
        user_id = user["id"]
        print(f"[OK] Found user: {user['email']}")
        print(f"     Current role: {user['role']}")
        print(f"     Current plan: {user['plan']}")
        
        # 2. Update user role to 'developer' and plan to 'enterprise'
        await conn.execute(
            """
            UPDATE users 
            SET role = 'developer', plan = 'enterprise', updated_at = NOW()
            WHERE id = $1
            """,
            user_id
        )
        print("[OK] Updated user: role='developer', plan='enterprise'")
        
        # 3. Check for existing subscription
        existing_sub = await conn.fetchrow(
            "SELECT id, plan_tier, status, current_period_end FROM subscriptions WHERE user_id = $1",
            user_id
        )
        
        if existing_sub:
            # Update existing subscription to enterprise, lifetime (no expiry)
            await conn.execute(
                """
                UPDATE subscriptions 
                SET plan_tier = 'enterprise', 
                    status = 'active',
                    current_period_end = NULL,
                    cancel_at_period_end = FALSE,
                    updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id
            )
            print("[OK] Updated subscription to enterprise (lifetime)")
        else:
            # Create new enterprise subscription
            import uuid
            sub_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO subscriptions (id, user_id, plan_tier, status, current_period_end)
                VALUES ($1, $2, 'enterprise', 'active', NULL)
                """,
                sub_id, user_id
            )
            print("[OK] Created enterprise subscription (lifetime)")
        
        # 4. Verify changes
        updated_user = await conn.fetchrow(
            "SELECT role, plan FROM users WHERE id = $1", user_id
        )
        updated_sub = await conn.fetchrow(
            "SELECT plan_tier, status, current_period_end FROM subscriptions WHERE user_id = $1", user_id
        )
        
        print("-" * 50)
        print("[SUCCESS] Account upgraded!")
        print(f"     Role: {updated_user['role']}")
        print(f"     Plan: {updated_user['plan']}")
        print(f"     Subscription: {updated_sub['plan_tier']} ({updated_sub['status']})")
        print(f"     Expiry: {'Lifetime (never expires)' if updated_sub['current_period_end'] is None else updated_sub['current_period_end']}")
        print("-" * 50)
        print("[NOTE] Restart the server and re-login to see changes in the UI.")
        
        return True
        
    finally:
        await release_db(conn)
        await close_database()


if __name__ == "__main__":
    success = asyncio.run(upgrade_developer())
    sys.exit(0 if success else 1)
