#!/usr/bin/env python3
"""Script to upgrade user to admin with enterprise tier."""

import asyncio
import os
import asyncpg

# Load from environment
DATABASE_URL = os.getenv("DATABASE_URL")

async def upgrade_user():
    """Upgrade parth.ajit7052@gmail.com to admin with enterprise tier."""
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set.")
        return

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # First check the table schema
        print("Checking users table schema...")
        columns = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
        )
        column_names = [col["column_name"] for col in columns]
        print(f"Available columns: {column_names}")

        # Build query dynamically based on available columns
        select_cols = ["id", "email", "role"]
        if "tier" in column_names:
            select_cols.append("tier")
        if "build_credits" in column_names:
            select_cols.append("build_credits")

        select_query = f"SELECT {', '.join(select_cols)} FROM users WHERE email = $1"

        # Check if user exists
        user = await conn.fetchrow(select_query, "parth.ajit7052@gmail.com")

        if not user:
            print("User not found: parth.ajit7052@gmail.com")
            return

        print(f"\nFound user: {user['email']}")
        print(f"Current role: {user['role']}")
        if "tier" in column_names:
            print(f"Current tier: {user['tier']}")

        # Build update query dynamically
        update_fields = ["role = 'admin'"]
        if "tier" in column_names:
            update_fields.append("tier = 'enterprise'")
        if "plan" in column_names:
            update_fields.append("plan = 'enterprise'")
        if "build_credits" in column_names:
            update_fields.append("build_credits = 999999")

        update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE email = $1"

        # Update user
        await conn.execute(update_query, "parth.ajit7052@gmail.com")

        # Verify update
        updated_user = await conn.fetchrow(select_query, "parth.ajit7052@gmail.com")

        print("\nUser upgraded successfully!")
        print(f"New role: {updated_user['role']}")
        if "tier" in column_names:
            print(f"New tier: {updated_user['tier']}")
        if "build_credits" in column_names:
            print(f"Build credits: {updated_user['build_credits']}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(upgrade_user())
