import asyncio
import asyncpg

async def test_connection():
    try:
        print("Testing database connection...")
        conn = await asyncpg.connect(
            'postgresql://neondb_owner:@ep-solitary-lab-a15xogjj-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require',
            timeout=10
        )
        print("SUCCESS: Connected successfully!")
        await conn.close()
        print("SUCCESS: Connection closed")
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")

asyncio.run(test_connection())
