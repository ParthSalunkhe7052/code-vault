"""Test build script for Nautika Complex project."""
import sys
import os

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PYTHONIOENCODING"] = "utf-8"

from cli_config import get_api_base, get_headers

PROJECT_ID = "c4744cff76a813f176718f17c6d8ca0e"
PROJECT_NAME = "Nautika Complex"

headers = get_headers()
api_url = get_api_base()

print(f"Building project: {PROJECT_NAME}")
print(f"Project ID: {PROJECT_ID}")
print(f"API URL: {api_url}")
print()

# Build configuration (same as interactive mode with fast=True)
config = {
    "project_id": PROJECT_ID,
    "project_name": PROJECT_NAME,
    "fast_build": True,
    "license_key": "GENERIC_BUILD",
    "jobs": None,
    "obfuscate": False,
    "lease": False,
    "runtime_license": True,
    "demo": False,
    "demo_duration": 60,
    "open_build": False,
    "platform": None,
    "language": None,
}

# Use simple build runner (default)
from codevault_cli.simple_build_runner import run_remote_build_simple

print("Starting remote build (simple mode, fast)...")
print("=" * 60)

success, output_path, error = run_remote_build_simple(
    project_id=PROJECT_ID,
    config=config,
    headers=headers,
    api_url=api_url,
    project_data=None,
    project_name=PROJECT_NAME,
    max_retries=1,  # Only 1 attempt for testing
)

print()
print("=" * 60)
print(f"Result: {'SUCCESS' if success else 'FAILED'}")
if output_path:
    print(f"Output: {output_path}")
if error:
    print(f"Error: {error}")
