"""Node.js license wrapper generator using centralized validators."""

from templates.nodejs_tpl import NODEJS_WRAPPER_LEGACY, NODEJS_WRAPPER_PREFIX, NODEJS_WRAPPER_SUFFIX
from validators import (
    validate_license_key as _validate_license_key,
    validate_server_url as _validate_server_url,
    validate_target_filename as _validate_target_filename,
    escape_for_js_string,
    ValidationError
)


# Backward compatibility alias - needed for tests
class WrapperGenerationError(ValidationError):
    """Legacy alias for ValidationError - used by external code."""
    pass


# =====================================================
# CodeVault Branding - Free Tier (Node.js Console Banner)
# This branding is removed for Pro/Enterprise users
# =====================================================
NODEJS_BRANDING_CODE = '''
// =====================================================
// CodeVault Branding - Free Tier
// This branding is removed for Pro/Enterprise users
// =====================================================
(function showCodeVaultBranding() {
    // Console branding with colors
    console.log('');
    console.log('\\x1b[36m\\x1b[1m  \\u{1F6E1} Protected by CodeVault\\x1b[0m');
    console.log('\\x1b[90m  License-Protected Application\\x1b[0m');
    console.log('\\x1b[35m  https://codevault.app\\x1b[0m');
    console.log('');
})();
'''


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


def get_nodejs_wrapper(license_key: str, server_url: str, target_filename: str, lease_enabled: bool = False, show_branding: bool = True) -> str:
    """Get Node.js license wrapper code (legacy - uses require, not pkg-compatible).

    Args:
        license_key: The license key to embed (must be alphanumeric with hyphens)
        server_url: The server URL for validation (must be valid http/https URL)
        target_filename: The target file to wrap (must be safe filename)
        lease_enabled: Whether offline lease mode is enabled (default: False)
        show_branding: Whether to show CodeVault branding (default: True for free tier)

    Returns:
        The wrapper code with placeholders replaced.

    Raises:
        WrapperGenerationError: If inputs fail validation
    """
    # Validate all inputs BEFORE embedding in code
    validated_license_key = validate_license_key(license_key)
    validated_server_url = validate_server_url(server_url)
    validated_target_file = _validate_target_filename(target_filename)

    # Escape for safe embedding in JavaScript string literals
    safe_license_key = escape_for_js_string(validated_license_key)
    safe_server_url = escape_for_js_string(validated_server_url)
    safe_target_file = escape_for_js_string(validated_target_file)

    # Build wrapper parts
    wrapper_parts = []
    
    # Add branding if free tier
    if show_branding:
        wrapper_parts.append(NODEJS_BRANDING_CODE)
    
    # Now safe to replace in template
    code = NODEJS_WRAPPER_LEGACY.replace("{license_key}", safe_license_key)
    code = code.replace("{server_url}", safe_server_url)
    code = code.replace("{target_file}", safe_target_file)
    
    wrapper_parts.append(code)

    return "\n".join(wrapper_parts)


def get_nodejs_wrapper_inline(license_key: str, server_url: str, lease_enabled: bool = False, show_branding: bool = True, public_key: str = "", heartbeat_interval: int = 300) -> tuple[str, str]:
    """
    Get Node.js license wrapper as prefix/suffix to wrap original code.

    Args:
        license_key: The license key to embed (must be alphanumeric with hyphens)
        server_url: The server URL for validation (must be valid http/https URL)
        lease_enabled: Whether offline lease mode is enabled (default: False)
        show_branding: Whether to show CodeVault branding (default: True for free tier)
        public_key: Ed25519 public key PEM for signature verification (preferred)
        heartbeat_interval: Interval in seconds for background heartbeat (default: 300)

    Returns:
        (prefix, suffix) tuple with validated and escaped values.

    Raises:
        WrapperGenerationError: If inputs fail validation
    """
    # Validate all inputs BEFORE embedding in code
    validated_license_key = validate_license_key(license_key)
    validated_server_url = validate_server_url(server_url)

    # Escape for safe embedding in JavaScript string literals
    safe_license_key = escape_for_js_string(validated_license_key)
    safe_server_url = escape_for_js_string(validated_server_url)

    # Build prefix with optional branding
    prefix_parts = []

    # Add branding if free tier
    if show_branding:
        prefix_parts.append(NODEJS_BRANDING_CODE)

    # PREFIX contains {license_key}, {server_url}, {lease_enabled}, and {public_key}
    prefix = NODEJS_WRAPPER_PREFIX.replace("{license_key}", safe_license_key)
    prefix = prefix.replace("{server_url}", safe_server_url)
    prefix = prefix.replace("{lease_enabled}", "true" if lease_enabled else "false")
    prefix = prefix.replace("{heartbeat_interval}", str(heartbeat_interval * 1000)) # JS uses ms
    # Embed Ed25519 public key for signature verification
    prefix = prefix.replace("{public_key}", public_key if public_key else "")

    prefix_parts.append(prefix)

    # SUFFIX is static
    suffix = NODEJS_WRAPPER_SUFFIX

    return "\n".join(prefix_parts), suffix
