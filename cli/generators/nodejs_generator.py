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


def get_nodejs_wrapper(license_key: str, server_url: str, target_filename: str, lease_enabled: bool = False) -> str:
    """Get Node.js license wrapper code (legacy - uses require, not pkg-compatible).

    Args:
        license_key: The license key to embed (must be alphanumeric with hyphens)
        server_url: The server URL for validation (must be valid http/https URL)
        target_filename: The target file to wrap (must be safe filename)
        lease_enabled: Whether offline lease mode is enabled (default: False)

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

    # Now safe to replace in template
    code = NODEJS_WRAPPER_LEGACY.replace("{license_key}", safe_license_key)
    code = code.replace("{server_url}", safe_server_url)
    code = code.replace("{target_file}", safe_target_file)

    return code


def get_nodejs_wrapper_inline(license_key: str, server_url: str, lease_enabled: bool = False) -> tuple[str, str]:
    """
    Get Node.js license wrapper as prefix/suffix to wrap original code.

    Args:
        license_key: The license key to embed (must be alphanumeric with hyphens)
        server_url: The server URL for validation (must be valid http/https URL)
        lease_enabled: Whether offline lease mode is enabled (default: False)

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

    # PREFIX contains {license_key}, {server_url}, and {lease_enabled}
    prefix = NODEJS_WRAPPER_PREFIX.replace("{license_key}", safe_license_key)
    prefix = prefix.replace("{server_url}", safe_server_url)
    prefix = prefix.replace("{lease_enabled}", "true" if lease_enabled else "false")

    # SUFFIX is static
    suffix = NODEJS_WRAPPER_SUFFIX

    return prefix, suffix
