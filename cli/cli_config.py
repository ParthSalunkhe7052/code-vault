"""
Configuration management for License Wrapper CLI.
Handles loading/saving config and API settings.

SECURITY: API keys are stored in the OS keyring (Windows Credential Manager,
macOS Keychain, or Linux Secret Service) rather than plaintext files.
"""

import os
import json
import logging
import stat
from pathlib import Path
from typing import Optional

# Keyring import with fallback
try:
    import keyring
    from keyring.errors import KeyringError
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    KeyringError = Exception  # Fallback for type hints


SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
DEFAULT_API_BASE = "http://localhost:8000/api/v1"

# Keyring service name for CodeVault CLI
KEYRING_SERVICE = "codevault-cli"
KEYRING_USERNAME = "api_token"

logger = logging.getLogger(__name__)


class SecureConfigError(Exception):
    """Error in secure configuration operations."""
    pass


def _set_restrictive_permissions(file_path: Path) -> None:
    """Set file permissions to owner-only (0600) on Unix systems."""
    try:
        if os.name != 'nt':  # Unix-like systems
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError as e:
        logger.warning(f"Could not set restrictive permissions on {file_path}: {e}")


def _get_token_from_keyring() -> Optional[str]:
    """Retrieve API token from OS keyring."""
    if not KEYRING_AVAILABLE:
        return None

    try:
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        return token
    except KeyringError as e:
        logger.warning(f"Keyring access failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected keyring error: {e}")
        return None


def _save_token_to_keyring(token: str) -> bool:
    """Save API token to OS keyring."""
    if not KEYRING_AVAILABLE:
        return False

    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        return True
    except KeyringError as e:
        logger.warning(f"Failed to save token to keyring: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error saving to keyring: {e}")
        return False


def _delete_token_from_keyring() -> bool:
    """Delete API token from OS keyring."""
    if not KEYRING_AVAILABLE:
        return False

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        return True
    except KeyringError:
        # Token may not exist, that's fine
        return True
    except Exception as e:
        logger.warning(f"Unexpected error deleting from keyring: {e}")
        return False


def _get_token_from_file() -> Optional[str]:
    """Fallback: Get token from config file (legacy/no-keyring mode)."""
    config = _load_config_file()
    return config.get("api_key")


def _load_config_file() -> dict:
    """Load non-sensitive configuration from file."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_config_file(config: dict) -> None:
    """Save non-sensitive configuration to file."""
    # Remove api_key from config before saving (it goes to keyring)
    safe_config = {k: v for k, v in config.items() if k != "api_key"}
    CONFIG_FILE.write_text(json.dumps(safe_config, indent=2))
    _set_restrictive_permissions(CONFIG_FILE)


def load_config() -> dict:
    """Load saved configuration.

    Non-sensitive settings come from config.json.
    API token comes from OS keyring (with file fallback).
    """
    config = _load_config_file()

    # Try keyring first for the token
    token = _get_token_from_keyring()

    if token:
        config["api_key"] = token
    elif "api_key" not in config:
        # Also try file fallback for legacy configs
        legacy_token = _get_token_from_file()
        if legacy_token:
            config["api_key"] = legacy_token
            # Migrate to keyring
            if _save_token_to_keyring(legacy_token):
                logger.info("Migrated API token from file to secure storage")
                # Remove from file
                _save_config_file(config)

    return config


def save_config(config: dict) -> None:
    """Save configuration.

    API token is stored in OS keyring.
    Other settings are stored in config.json.
    """
    api_key = config.get("api_key")

    if api_key:
        if KEYRING_AVAILABLE:
            if _save_token_to_keyring(api_key):
                logger.debug("API token saved to secure keyring storage")
            else:
                # Fallback to file with warning
                logger.warning(
                    "Could not save to keyring. Token will be stored in config file. "
                    "Install 'keyring' package for secure storage: pip install keyring"
                )
                _save_config_file_with_token(config)
                return
        else:
            # No keyring available - use file with restrictive permissions
            logger.warning(
                "Keyring not available. Token stored in config file. "
                "For secure storage, install: pip install keyring"
            )
            _save_config_file_with_token(config)
            return

    # Save non-sensitive config to file
    _save_config_file(config)


def _save_config_file_with_token(config: dict) -> None:
    """Fallback: Save config including token to file (insecure mode)."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    _set_restrictive_permissions(CONFIG_FILE)


def get_api_base() -> str:
    """Get API base URL from config or environment."""
    config = _load_config_file()  # Don't need token for this
    return config.get("api_url", os.getenv("LW_API_URL", DEFAULT_API_BASE))


def get_headers() -> Optional[dict]:
    """Get request headers with API key."""
    config = load_config()
    api_key = config.get("api_key")
    if not api_key:
        return None
    return {"Authorization": f"Bearer {api_key}"}


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return get_headers() is not None


def clear_config() -> None:
    """Clear saved configuration (logout).

    Removes token from keyring and deletes config file.
    """
    # Clear keyring
    _delete_token_from_keyring()

    # Clear config file
    if CONFIG_FILE.exists():
        try:
            CONFIG_FILE.unlink()
        except OSError as e:
            logger.warning(f"Could not delete config file: {e}")


def check_token_expiry() -> Optional[dict]:
    """Check if the stored token is expired.

    Returns:
        None if no token or token is valid
        dict with error info if token is expired/invalid
    """
    import base64
    import time

    config = load_config()
    token = config.get("api_key")

    if not token:
        return None

    try:
        # JWT tokens have 3 parts separated by dots
        parts = token.split(".")
        if len(parts) != 3:
            return {"error": "invalid_token", "message": "Token format is invalid"}

        # Decode the payload (middle part)
        # Add padding if needed
        payload_b64 = parts[1]
        padding_needed = (4 - len(payload_b64) % 4) % 4
        payload_b64 += "=" * padding_needed

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Check expiry
        exp = payload.get("exp")
        if exp and exp < time.time():
            return {
                "error": "token_expired",
                "message": "Your session has expired. Please log in again."
            }

        return None

    except Exception:
        # If we can't decode/check, assume it's fine and let the server validate
        return None


def get_storage_info() -> dict:
    """Get information about how credentials are stored.

    Returns:
        dict with storage method and security status
    """
    if KEYRING_AVAILABLE:
        # Try to detect the keyring backend
        try:
            backend = keyring.get_keyring().__class__.__name__
        except Exception:
            backend = "Unknown"

        return {
            "method": "keyring",
            "backend": backend,
            "secure": True,
            "message": f"Credentials stored securely using {backend}"
        }
    else:
        return {
            "method": "file",
            "backend": "config.json",
            "secure": False,
            "message": "Credentials stored in config file. Install 'keyring' for secure storage."
        }
