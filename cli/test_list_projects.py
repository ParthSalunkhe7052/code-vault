"""Quick script to list projects and find Nautika Complex."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli_config import get_api_base, get_headers
import requests

headers = get_headers()
api_url = get_api_base()

print(f"API URL: {api_url}")
print(f"Auth: {'Yes' if headers else 'No'}")
print()

resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    projects = resp.json()
    print(f"Found {len(projects)} projects:\n")
    for i, p in enumerate(projects):
        settings = p.get("settings", {})
        if isinstance(settings, str):
            import json
            try:
                settings = json.loads(settings) if settings else {}
            except:
                settings = {}

        entry_file = settings.get("entry_file", "N/A")
        language = settings.get("language", "N/A")
        print(f"  {i+1}. {p.get('name', '?')}")
        print(f"     ID: {p.get('id', '?')}")
        print(f"     Entry: {entry_file} | Lang: {language}")
        print(f"     Has uploads: {p.get('has_uploads', False)}")
        print()
else:
    print(f"Error: {resp.text}")
