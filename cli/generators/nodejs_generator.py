import re
import json
from urllib.parse import urlparse
from templates.nodejs_tpl import NODEJS_WRAPPER_LEGACY, NODEJS_WRAPPER_PREFIX, NODEJS_WRAPPER_SUFFIX


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


def validate_target_filename(filename: str) -> str:
    """Validate and sanitize target filename to prevent path traversal and injection.

    Args:
        filename: The target filename to validate

    Returns:
        The validated filename

    Raises:
        WrapperGenerationError: If filename is invalid
    """
    if not filename:
        raise WrapperGenerationError("Target filename cannot be empty")

    filename = filename.strip()

    # Block path traversal
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        raise WrapperGenerationError("Invalid filename: path traversal not allowed")

    # Block dangerous characters for JavaScript string context
    dangerous_chars = ["'", '"', '`', '\\', '\n', '\r', '\t', '\0', '$', '{', '}']
    for char in dangerous_chars:
        if char in filename:
            raise WrapperGenerationError(
                f"Filename contains invalid character: {repr(char)}"
            )

    # Only allow safe filename characters
    if not re.match(r'^[A-Za-z0-9._\-]+$', filename):
        raise WrapperGenerationError(
            "Filename can only contain alphanumeric characters, dots, hyphens, and underscores"
        )

    # Reasonable length limit
    if len(filename) > 255:
        raise WrapperGenerationError("Filename is too long (max 255 characters)")

    return filename


def escape_for_js_string(value: str) -> str:
    """Safely escape a value for embedding in a JavaScript string literal.

    Uses JSON encoding to properly escape special characters.

    Args:
        value: The string to escape

    Returns:
        Escaped string safe for JavaScript string literal
    """
    # JSON encode handles escaping of quotes, backslashes, newlines, etc.
    # We strip the surrounding quotes since we'll add our own in the template
    encoded = json.dumps(value)
    # Remove surrounding quotes from JSON encoding
    return encoded[1:-1]


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
    validated_target_file = validate_target_filename(target_filename)

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
