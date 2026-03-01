import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv('server/.env')
async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    artifacts = await conn.fetch('SELECT platform, status, download_key, download_filename, error_message FROM cloud_build_artifacts WHERE build_id = $1', '321e1e884c2663d27b68a8442c6673e2')
    for a in artifacts:
        print('Platform=', a['platform'], 'Status=', a['status'], 'DownloadKey=', a['download_key'], 'Filename=', a['download_filename'])
    await conn.close()
asyncio.run(main())
