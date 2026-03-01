import asyncio
import os
import subprocess
from pathlib import Path
from storage_service import storage_service

async def main():
    if not storage_service.is_cloud_enabled():
        print("Cloud storage is not enabled.")
        return

    print("Cloud storage is enabled.")
    
    # Create a small dummy zip file
    dummy_zip = b'PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' # Empty zip file
    
    # Upload it
    project_id = "test-123"
    build_id = "test-build"
    key = f"builds/{build_id}/source.zip"
    
    storage_service.client.put_object(
        Bucket=storage_service.bucket,
        Key=key,
        Body=dummy_zip
    )
    print(f"Uploaded dummy zip to {key}")
    
    # Generate URL
    url = storage_service.generate_presigned_url(key, expires_in=3600)
    print(f"Generated URL: {url}")
    
    # Test curl locally
    print("\n--- Testing CURL ---")
    cmd = f'curl -L -o test_download.zip "{url}"'
    print(f"Running: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"Curl exit code: {result.returncode}")
    print(f"Curl stderr: {result.stderr}")
    
    # Check if test_download.zip is a valid zip
    print("\n--- Testing ZIP ---")
    if Path('test_download.zip').exists():
        size = Path('test_download.zip').stat().st_size
        print(f"Downloaded file size: {size} bytes")
        with open('test_download.zip', 'rb') as f:
            print(f"Content start: {f.read(10)}")
            
        import zipfile
        try:
            with zipfile.ZipFile('test_download.zip') as z:
                z.testzip()
            print("ZIP is valid!")
        except Exception as e:
            print(f"ZIP IS INVALID: {e}")
    else:
        print("test_download.zip not found!")

if __name__ == "__main__":
    asyncio.run(main())
