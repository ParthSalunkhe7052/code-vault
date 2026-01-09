"""Python license wrapper generator using centralized validators."""

from templates.python_tpl import PYTHON_WRAPPER_TEMPLATE
from validators import (
    validate_license_key as _validate_license_key,
    validate_server_url as _validate_server_url,
    escape_for_python_string,
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


def get_python_wrapper(license_key: str, server_url: str, lease_enabled: bool = False) -> str:
    """Get Python license wrapper code.

    Args:
        license_key: The license key to embed (must be alphanumeric with hyphens)
        server_url: The server URL for validation (must be valid http/https URL)
        lease_enabled: Whether offline lease mode is enabled (default: False)

    Returns:
        The wrapper code with placeholders replaced.

    Raises:
        WrapperGenerationError: If license_key or server_url fail validation
    """
    # Validate inputs BEFORE embedding in code
    validated_license_key = validate_license_key(license_key)
    validated_server_url = validate_server_url(server_url)

    # Escape for safe embedding in Python string literals
    safe_license_key = escape_for_python_string(validated_license_key)
    safe_server_url = escape_for_python_string(validated_server_url)

    # Now safe to replace in template
    code = PYTHON_WRAPPER_TEMPLATE.replace("{license_key}", safe_license_key)
    code = code.replace("{server_url}", safe_server_url)
    code = code.replace("{lease_enabled}", "True" if lease_enabled else "False")
    return code
