import re
import json
from urllib.parse import urlparse
from templates.python_tpl import PYTHON_WRAPPER_TEMPLATE


class WrapperGenerationError(Exception):
    """Raised when wrapper generation fails due to invalid input."""
    pass


def validate_license_key(license_key: str) -> str:
    """Validate and sanitize license key to prevent code injection.

    License keys must be alphanumeric with hyphens only (e.g., LIC-XXXX-XXXX-XXXX-XXXX).

    Args:
        license_key: The license key to validate

    Returns:
        The validated license key (stripped of whitespace)

    Raises:
        WrapperGenerationError: If license key format is invalid
    """
    if not license_key:
        raise WrapperGenerationError("License key cannot be empty")

    license_key = license_key.strip()

    # Allow only alphanumeric characters, hyphens, and underscores
    # This prevents code injection via special characters like quotes
    if not re.match(r'^[A-Za-z0-9\-_]+$', license_key):
        raise WrapperGenerationError(
            "Invalid license key format. Only alphanumeric characters, "
            "hyphens, and underscores are allowed."
        )

    # Reasonable length limits
    if len(license_key) < 3 or len(license_key) > 100:
        raise WrapperGenerationError(
            "License key must be between 3 and 100 characters"
        )

    return license_key


def validate_server_url(server_url: str) -> str:
    """Validate and sanitize server URL to prevent code injection.

    Args:
        server_url: The server URL to validate

    Returns:
        The validated server URL

    Raises:
        WrapperGenerationError: If URL format is invalid
    """
    if not server_url:
        raise WrapperGenerationError("Server URL cannot be empty")

    server_url = server_url.strip()

    # Parse and validate URL structure
    try:
        parsed = urlparse(server_url)
    except Exception:
        raise WrapperGenerationError("Invalid URL format")

    # Must be http or https
    if parsed.scheme not in ('http', 'https'):
        raise WrapperGenerationError(
            "Server URL must use http:// or https:// protocol"
        )

    # Must have a valid hostname
    if not parsed.netloc:
        raise WrapperGenerationError("Server URL must have a valid hostname")

    # Block dangerous characters that could escape string context
    dangerous_chars = ["'", '"', '`', '\\', '\n', '\r', '\t', '\0']
    for char in dangerous_chars:
        if char in server_url:
            raise WrapperGenerationError(
                f"Server URL contains invalid character: {repr(char)}"
            )

    # Reasonable length limit
    if len(server_url) > 500:
        raise WrapperGenerationError("Server URL is too long (max 500 characters)")

    return server_url


def escape_for_python_string(value: str) -> str:
    """Safely escape a value for embedding in a Python string literal.

    Uses JSON encoding to properly escape special characters.

    Args:
        value: The string to escape

    Returns:
        Escaped string safe for Python string literal
    """
    # JSON encode handles escaping of quotes, backslashes, newlines, etc.
    # We strip the surrounding quotes since we'll add our own in the template
    encoded = json.dumps(value)
    # Remove surrounding quotes from JSON encoding
    return encoded[1:-1]


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
