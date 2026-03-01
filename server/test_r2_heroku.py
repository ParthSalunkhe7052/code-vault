import asyncio
import os
import sys

# Add the server directory to the sys path so we can import from it
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage_service import storage_service

async def test_r2():
    print(f"R2 Enabled: {storage_service.is_cloud_enabled()}")
    if not storage_service.is_cloud_enabled():
        return
    
    # Check if a known file exists
    test_key = "builds/test-build/source.zip"
    exists = await storage_service.file_exists(test_key)
    print(f"File {test_key} exists: {exists}")
    
    # Create a test zip and upload it directly
    zip_data = b'PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    key = "builds/test-persistence/source.zip"
    
    storage_service.client.put_object(
        Bucket=storage_service.bucket,
        Key=key,
        Body=zip_data
    )
    print(f"Uploaded to {key}")
    
    exists_now = await storage_service.file_exists(key)
    print(f"File {key} exists after upload: {exists_now}")

if __name__ == "__main__":
    asyncio.run(test_r2())
