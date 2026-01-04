"""
Configuration management for License Wrapper CLI.
Handles loading/saving config and API settings.
"""

import os
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
DEFAULT_API_BASE = "http://localhost:8000/api/v1"


def load_config() -> dict:
    """Load saved configuration."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(config: dict):
    """Save configuration to file."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_base() -> str:
    """Get API base URL from config or environment."""
    config = load_config()
    return config.get("api_url", os.getenv("LW_API_URL", DEFAULT_API_BASE))


def get_headers() -> dict:
    """Get request headers with API key."""
    config = load_config()
    api_key = config.get("api_key")
    if not api_key:
        return None
    return {"Authorization": f"Bearer {api_key}"}


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return get_headers() is not None


def clear_config():
    """Clear saved configuration (logout)."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
