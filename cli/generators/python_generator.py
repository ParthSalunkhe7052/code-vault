"""Python license wrapper generator using unified template."""

from typing import Optional

from templates.unified_license_wrapper import (
    get_license_wrapper as _get_unified_wrapper,
)
from validators import (
    validate_license_key as _validate_license_key,
    validate_server_url as _validate_server_url,
    ValidationError,
)


# Backward compatibility alias - needed for tests
class WrapperGenerationError(ValidationError):
    """Legacy alias for ValidationError - used by external code."""

    pass


def validate_license_key(license_key: str) -> str:
    """Validate license key, raising WrapperGenerationError for tests."""
    try:
        return _validate_license_key(license_key)
    except ValidationError as e:
        raise WrapperGenerationError(str(e))


def validate_server_url(server_url: str) -> str:
    """Validate server URL, raising WrapperGenerationError for tests."""
    try:
        return _validate_server_url(server_url)
    except ValidationError as e:
        raise WrapperGenerationError(str(e))


def get_python_wrapper(
    license_key: str,
    server_url: str,
    secret_key: Optional[str] = None,
    lease_enabled: bool = True,
    show_branding: bool = True,
    public_key: str = "",
    binary_hash: str = "skip",
    heartbeat_interval: int = 300,
    app_name: str = "Protected Application",
    brand_name: str = "CodeVault",
    brand_url: str = "https://codevault.dev",
    brand_primary_color: str = "#6366f1",
) -> str:
    """
    Get Python license wrapper code using unified template.

    Args:
        license_key: The license key to embed (must be alphanumeric with hyphens)
        server_url: The server URL for validation (must be valid http/https URL)
        secret_key: DEPRECATED - ignored, kept only for backward compatibility
        lease_enabled: Whether offline lease mode is enabled (default: True)
        show_branding: Whether to show CodeVault branding (default: True for free tier)
        public_key: Ed25519 public key PEM for signature verification
        binary_hash: SHA-256 hash of binary for integrity checking (default: "skip")
        heartbeat_interval: Interval in seconds for background heartbeat (default: 300)
        app_name: Application name for UI dialogs (default: "Protected Application")
        brand_name: Custom brand name for white-labeling (Business/Enterprise only)
        brand_url: Custom brand URL for white-labeling
        brand_primary_color: Custom primary color hex for white-labeling

    Returns:
        Complete wrapper code ready to be prepended to user code.

    Raises:
        WrapperGenerationError: If license_key or server_url fail validation
    """
    validated_license_key = validate_license_key(license_key)
    validated_server_url = validate_server_url(server_url)

    return _get_unified_wrapper(
        license_key=validated_license_key,
        server_url=validated_server_url,
        lease_enabled=lease_enabled,
        public_key=public_key,
        binary_hash=binary_hash,
        heartbeat_interval=heartbeat_interval,
        app_name=app_name,
        show_branding=show_branding,
        brand_name=brand_name,
        brand_url=brand_url,
        brand_primary_color=brand_primary_color,
    )
