"""
Migration: Add Ed25519 asymmetric signing keys to projects.

This replaces the shared HMAC signing_secret with a public/private key pair.
Only the PUBLIC key is embedded in compiled binaries — attackers can verify
signatures but cannot forge them, eliminating the "skeleton key" vulnerability.

Usage:
    python scripts/migrate_ed25519.py
"""

import asyncio
import os
import sys
import base64

# Add server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    PublicFormat,
    NoEncryption,
)


def generate_ed25519_keypair() -> tuple[str, str]:
    """Generate an Ed25519 key pair and return (private_pem, public_pem) as strings."""
    private_key = Ed25519PrivateKey.generate()
    
    private_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    ).decode("utf-8")
    
    public_pem = private_key.public_key().public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    
    return private_pem, public_pem


async def run_migration():
    """Run the Ed25519 migration."""
    import database
    from database import init_database, close_database

    print("[Migration] Initializing database...")
    await init_database()

    async with database.db_pool.acquire() as conn:
        # Step 1: Add new columns
        print("[Migration] Adding signing_private_key and signing_public_key columns...")
        
        try:
            await conn.execute(
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_private_key TEXT"
            )
            print("  - Added 'signing_private_key' column")
        except Exception as e:
            print(f"  - signing_private_key column: {e}")

        try:
            await conn.execute(
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS signing_public_key TEXT"
            )
            print("  - Added 'signing_public_key' column")
        except Exception as e:
            print(f"  - signing_public_key column: {e}")

        # Step 2: Backfill existing projects with new key pairs
        print("[Migration] Backfilling existing projects with Ed25519 key pairs...")
        
        projects = await conn.fetch(
            "SELECT id, name FROM projects WHERE signing_private_key IS NULL"
        )
        
        if not projects:
            print("  - No projects need backfilling (all have Ed25519 keys)")
        else:
            for project in projects:
                private_pem, public_pem = generate_ed25519_keypair()
                await conn.execute(
                    "UPDATE projects SET signing_private_key = $1, signing_public_key = $2 WHERE id = $3",
                    private_pem,
                    public_pem,
                    project["id"],
                )
                print(f"  - Generated Ed25519 keys for project: {project['name']} ({project['id'][:8]}...)")
            
            print(f"  - Backfilled {len(projects)} project(s)")

    print("[Migration] Ed25519 migration complete!")
    await close_database()


if __name__ == "__main__":
    asyncio.run(run_migration())
