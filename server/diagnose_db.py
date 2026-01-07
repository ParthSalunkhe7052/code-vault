"""
Diagnostic script to check database pool health.
Run this while the server is running to see pool status.
"""
import asyncio
import asyncpg
from config import DATABASE_URL

async def diagnose():
    print("=== Database Connection Diagnostic ===\n")

    print(f"1. Testing direct connection...")
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=10)
        print("   SUCCESS: Direct connection works")
        await conn.close()
    except Exception as e:
        print(f"   ERROR: {e}")
        return

    print(f"\n2. Testing pool creation...")
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=3,
            timeout=10,
            command_timeout=30
        )
        print("   SUCCESS: Pool created")

        print(f"\n3. Testing pool acquire...")
        conn = await pool.acquire(timeout=5)
        print("   SUCCESS: Connection acquired from pool")

        print(f"\n4. Testing simple query...")
        result = await conn.fetchval("SELECT 1")
        print(f"   SUCCESS: Query returned {result}")

        await pool.release(conn)
        print("\n5. Connection released")

        await pool.close()
        print("6. Pool closed")

        print("\n=== All checks passed! ===")

    except asyncio.TimeoutError:
        print("   ERROR: Timeout while acquiring connection from pool")
        print("   This suggests the pool is exhausted or deadlocked")
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
