import json
import os
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account

# Load credentials from .env
with open(".env", "r") as f:
    env_vars = {}
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_vars[k] = v

project_id = env_vars.get("GCP_PROJECT_ID")
sa_json = env_vars.get("GCP_SERVICE_ACCOUNT_JSON")

if not project_id or not sa_json:
    print("Missing GCP credentials in .env")
    exit(1)

# Initialize client
credentials = service_account.Credentials.from_service_account_info(
    json.loads(sa_json),
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
client = cloudbuild_v1.CloudBuildClient(credentials=credentials)

# List recent builds
parent = f"projects/{project_id}/locations/global"
request = cloudbuild_v1.ListBuildsRequest(parent=parent, page_size=5)
response = client.list_builds(request=request)

for build in response.builds:
    print(f"\n--- Build: {build.id} ---")
    print(f"Status: {build.status.name}")
    print(f"Log URL: {build.log_url}")
    # Also grab the source URL from steps if possible
    for step in build.steps:
        if step.id == "download-source":
            print(f"Step download-source args: {step.args}")
