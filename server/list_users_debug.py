import asyncio
from database import get_db, init_database

async def list_users():
    await init_database()
    conn = await get_db()
    try:
        users = await conn.fetch("SELECT id, email FROM users")
        for u in users:
            print(f"ID: {u['id']} | Email: {u['email']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(list_users())
