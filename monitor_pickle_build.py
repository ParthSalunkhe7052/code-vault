
import json
import time
from cloud_build_cli_wrapper import CloudBuildClient

def monitor():
    try:
        with open("last_test_build.json", "r") as f:
            data = json.load(f)
            build_id = data["build_id"]
    except Exception as e:
        print(f"Error loading build info: {e}")
        return

    client = CloudBuildClient(project_id="cloudbuild-486309")
    
    print(f"Monitoring build: {build_id}")
    
    while True:
        try:
            status = client.get_build_status(build_id)
            print(f"[{time.strftime('%H:%M:%S')}] Status: {status['status']}")
            
            if status['status'] in ['SUCCESS', 'FAILURE', 'CANCELLED', 'EXPIRED']:
                print(f"Build finished with status: {status['status']}")
                break
                
            time.sleep(10)
        except Exception as e:
            print(f"Error checking status: {e}")
            break

if __name__ == "__main__":
    monitor()
