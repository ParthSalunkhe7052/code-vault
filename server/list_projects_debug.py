import asyncio
import os
from database import get_db, release_db, init_db

async def list_projects():
    # Load env vars if needed or ensure they are present
    from config import DATABASE_URL
    await init_db(DATABASE_URL)
    
    conn = await get_db()
    try:
        projects = await conn.fetch('SELECT id, name FROM projects LIMIT 5')
        for p in projects:
            print(f"ID: {p['id']} | Name: {p['name']}")
    finally:
        await release_db(conn)

if __name__ == "__main__":
    asyncio.run(list_projects())
