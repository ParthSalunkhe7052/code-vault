import asyncio
import os
import subprocess
from storage_service import storage_service

async def test_download():
    # 1. Generate key and upload some data
    build_id = "test-download-build"
    key = f"builds/{build_id}/source.zip"
    
    zip_data = b'PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    storage_service.client.put_object(
        Bucket=storage_service.bucket,
        Key=key,
        Body=zip_data
    )
    print(f"Uploaded to {key}")
    
    # 2. Generate presigned URL
    url = storage_service.generate_presigned_url(key, expires_in=3600)
    print(f"URL Length: {len(url)}")
    print(f"URL: {url}")
    
    # 3. Test with a Python HTTP client instead of curl
    import urllib.request
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = response.read()
            print(f"Python downloaded {len(data)} bytes. Starts with {data[:2]}")
    except Exception as e:
        print(f"Python download failed: {e}")
        
    # 4. Test exact curl syntax exactly as used in Cloud Build
    print("\n--- Testing curl as in Cloud Build ---")
    cmd = f'curl -sL -w "%{{http_code}}" -o download_test.zip "{url}"'
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"Curl HTTP Code Output: {process.stdout}")
    print(f"Curl STDERR: {process.stderr}")
    
    if os.path.exists("download_test.zip"):
        size = os.path.getsize("download_test.zip")
        print(f"Curl saved {size} bytes")
        if size < 500:
            with open("download_test.zip", "r") as f:
                print(f"File content: {f.read()}")

if __name__ == "__main__":
    asyncio.run(test_download())
