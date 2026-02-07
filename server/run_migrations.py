"""
Database migration runner for CodeVault.
Run this script to apply pending migrations.
"""

import asyncio
import os
import glob
from database import get_db, init_database

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


async def run_migrations():
    """Run all pending migrations."""
    # Initialize database first
    await init_database()
    conn = await get_db()

    # Get list of migration files sorted by name
    migration_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))

    print(f"Found {len(migration_files)} migration files")

    for migration_file in migration_files:
        filename = os.path.basename(migration_file)
        print(f"\nChecking migration: {filename}")

        try:
            with open(migration_file, "r") as f:
                sql = f.read()

            # Execute the migration (using IF NOT EXISTS / ADD COLUMN IF NOT EXISTS for safety)
            await conn.execute(sql)
            print(f"  OK: {filename}")
        except Exception as e:
            print(f"  ERROR in {filename}: {e}")

    await conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
