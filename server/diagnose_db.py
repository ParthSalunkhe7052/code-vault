"""
Diagnostic script to check database pool health.
Run this while the server is running to see pool status.
"""
import asyncio
import asyncpg
from config import DATABASE_URL


async def diagnose():
    print("=== Database Connection Diagnostic ===\n")

    # Validate DATABASE_URL exists
    if not DATABASE_URL:
        print("   ERROR: DATABASE_URL is not configured")
        print("   Set DATABASE_URL in your .env file")
        return

    pool = None
    try:
        # Test 1: Direct connection
        print("1. Testing direct connection...")
        conn = await asyncpg.connect(DATABASE_URL, timeout=10)
        await conn.close()
        print("   SUCCESS: Direct connection works")

        # Test 2: Pool
        print("\n2. Testing pool creation...")
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=3,
            timeout=10,
            command_timeout=30
        )
        print("   SUCCESS: Pool created")

        # Test 3: Acquire
        print("\n3. Testing pool acquire...")
        conn = await pool.acquire(timeout=5)
        print("   SUCCESS: Connection acquired")

        # Test 4: Query
        print("\n4. Testing simple query...")
        result = await conn.fetchval("SELECT 1")
        print(f"   SUCCESS: Query returned {result}")

        await pool.release(conn)
        print("\n5. Connection released")

        print("\n=== All checks passed! ===")

    except asyncio.TimeoutError:
        print("   ERROR: Timeout while acquiring connection")
    except Exception as e:
        print(f"   ERROR: {e}")
    finally:
        if pool:
            await pool.close()
            print("6. Pool closed")


if __name__ == "__main__":
    asyncio.run(diagnose())
