import asyncio
import sys
from pathlib import Path

# Add server directory to path
# Script is in CodeVaultV1/scripts/, server is in CodeVaultV1/server/
sys.path.append(str(Path(__file__).parent.parent / "server"))

from config import (
    GITHUB_TOKEN, GITHUB_REPO, BUILD_CALLBACK_SECRET,
    R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT
)
from database import init_database, close_database, get_db, release_db

async def check_setup():
    print("=== Cloud Build Setup Verification ===\n")
    
    # 1. Check Environment Variables
    print("1. Checking Environment Variables...")
    missing = []
    if not GITHUB_TOKEN:
        missing.append("GITHUB_TOKEN")
    if not GITHUB_REPO:
        missing.append("GITHUB_REPO")
    if not BUILD_CALLBACK_SECRET:
        missing.append("BUILD_CALLBACK_SECRET")
    if not R2_ACCESS_KEY_ID:
        missing.append("R2_ACCESS_KEY_ID")
    if not R2_SECRET_ACCESS_KEY:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not R2_ENDPOINT:
        missing.append("R2_ENDPOINT")
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Please add them to your .env file.")
    else:
        print("✅ All required environment variables are set.")

    # 2. Check Database Table
    print("\n2. Checking Database Schema...")
    try:
        await init_database()
        conn = await get_db()
        try:
            row = await conn.fetchrow("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'cloud_builds'
                );
            """)
            if row and row[0]:
                print("✅ Table 'cloud_builds' exists.")
            else:
                print("❌ Table 'cloud_builds' does NOT exist.")
                print("   Restart the server to trigger auto-migration.")
        finally:
            await release_db(conn)
            await close_database()
    except Exception as e:
        print(f"❌ Database check failed: {e}")

    # 3. Check Workflow File
    print("\n3. Checking GitHub Workflow...")
    # Script is in CodeVaultV1/scripts/, workflow is in CodeVaultV1/.github/...
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "cloud-compile.yml"
    if workflow_path.exists():
        print(f"✅ Workflow file found at {workflow_path}")
        print("   ⚠️  Remember to push this file to GitHub:")
        print("      git add .github/workflows/cloud-compile.yml")
        print("      git commit -m 'Add cloud compilation workflow'")
        print("      git push")
    else:
        print("❌ Workflow file missing!")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_setup())
