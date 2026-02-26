"""
Centralized validation functions for CodeVault CLI.

This module provides shared validation logic to prevent code duplication
and ensure consistent input validation across the CLI.
"""

import re
import json
from urllib.parse import urlparse
from typing import Any


class ValidationError(Exception):
    """Raised when validation fails due to invalid input."""
    pass


class SecurityError(Exception):
    """Raised when security violations are detected."""
    pass


# Dangerous path patterns that could indicate traversal attempts
DANGEROUS_PATTERNS = [
    '..',           # Parent directory traversal
    '//',           # Double slashes
    '\\\\',         # Double backslashes
    '\x00',         # Null byte injection
    '%2e',          # URL-encoded dot
    '%2f',          # URL-encoded forward slash
    '%5c',          # URL-encoded backslash
    '%00',          # URL-encoded null
]


def validate_license_key(license_key: str) -> str:
    """Validate and sanitize license key to prevent code injection.

    License keys must be alphanumeric with hyphens only (e.g., LIC-XXXX-XXXX-XXXX-XXXX).

    Args:
        license_key: The license key to validate

    Returns:
        The validated license key (stripped of whitespace)

    Raises:
        ValidationError: If license key format is invalid
    """
    if not license_key:
        raise ValidationError("License key cannot be empty")

    license_key = license_key.strip()
    
    if not license_key:
        raise ValidationError("License key cannot be empty")

    # Allow only alphanumeric characters, hyphens, and underscores
    # This prevents code injection via special characters like quotes
    if not re.match(r'^[A-Za-z0-9\-_]+$', license_key):
        raise ValidationError(
            "Invalid license key format. Only alphanumeric characters, "
            "hyphens, and underscores are allowed."
        )

    # Reasonable length limits
    if len(license_key) < 3 or len(license_key) > 100:
        raise ValidationError(
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
        ValidationError: If URL format is invalid or contains embedded credentials
    """
    if not server_url:
        raise ValidationError("Server URL cannot be empty")

    server_url = server_url.strip()

    # Parse and validate URL structure
    try:
        parsed = urlparse(server_url)
    except Exception:
        raise ValidationError("Invalid URL format")

    # Must be http or https
    if parsed.scheme not in ('http', 'https'):
        raise ValidationError(
            "Server URL must use http:// or https:// protocol"
        )

    # Must have a valid hostname
    if not parsed.netloc:
        raise ValidationError("Server URL must have a valid hostname")

    # CRITICAL: Reject URLs with embedded credentials
    if parsed.username or parsed.password:
        raise ValidationError(
            "Server URL must not contain embedded credentials (username/password)"
        )

    # Block dangerous characters that could escape string context
    dangerous_chars = ["'", '"', '`', '\\', '\n', '\r', '\t', '\0']
    for char in dangerous_chars:
        if char in server_url:
            raise ValidationError(
                f"Server URL contains invalid character: {repr(char)}"
            )

    # Reasonable length limit
    if len(server_url) > 500:
        raise ValidationError("Server URL is too long (max 500 characters)")

    return server_url


def validate_target_filename(filename: str) -> str:
    """Validate and sanitize target filename to prevent path traversal and injection.

    Args:
        filename: The target filename to validate

    Returns:
        The validated filename

    Raises:
        ValidationError: If filename is invalid
    """
    if not filename:
        raise ValidationError("Target filename cannot be empty")

    filename = filename.strip()

    # Block path traversal
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        raise ValidationError("Invalid filename: path traversal not allowed")

    # Block dangerous characters for JavaScript string context
    dangerous_chars = ["'", '"', '`', '\\', '\n', '\r', '\t', '\0', '$', '{', '}']
    for char in dangerous_chars:
        if char in filename:
            raise ValidationError(
                f"Filename contains invalid character: {repr(char)}"
            )

    # Only allow safe filename characters
    if not re.match(r'^[A-Za-z0-9._\-]+$', filename):
        raise ValidationError(
            "Filename can only contain alphanumeric characters, dots, hyphens, and underscores"
        )

    # Reasonable length limit
    if len(filename) > 255:
        raise ValidationError("Filename is too long (max 255 characters)")

    return filename


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


def validate_output_name(output_name: str) -> str:
    """Validate and sanitize output name to prevent path traversal in output files.

    Args:
        output_name: The desired output filename (without extension)

    Returns:
        Validated and sanitized output name

    Raises:
        ValidationError: If the output name is invalid after sanitization
    """
    if not output_name:
        raise ValidationError("Output name cannot be empty")

    # Strip common path separators first
    output_name = output_name.replace('/', '').replace('\\', '')

    # Check for dangerous patterns
    output_lower = output_name.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in output_lower:
            raise ValidationError(f"Invalid output name: contains forbidden pattern '{pattern}'")

    # Auto-sanitize: replace spaces with underscores
    original_name = output_name
    output_name = output_name.replace(' ', '_')

    # Replace multiple consecutive underscores with single underscore
    output_name = re.sub(r'_+', '_', output_name)

    # Remove leading/trailing underscores and dots
    output_name = output_name.strip('_.') or 'output'

    # Validate against allowed pattern (alphanumeric, underscores, hyphens, dots)
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,99}$', output_name):
        raise ValidationError(
            f"Invalid output name '{original_name}' (sanitized to '{output_name}'): "
            "must be alphanumeric with underscores, hyphens, or dots only "
            "(max 100 chars, must start with alphanumeric)"
        )

    return output_name


def validate_include_package(package_name: str) -> str:
    """Validate Nuitka include-package names to prevent command injection.

    Args:
        package_name: The package name from config

    Returns:
        Validated package name

    Raises:
        ValidationError: If the package name is invalid
    """
    if not package_name:
        return ""

    # Skip __pycache__
    if package_name == "__pycache__":
        return ""

    # Convert path separators to dots for module names
    module_name = package_name.replace("/", ".").replace("\\", ".")

    # Validate: only alphanumeric, dots, underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.]*$', module_name):
        raise ValidationError(
            f"Invalid package name '{package_name}': contains invalid characters"
        )

    # Prevent double dots (path traversal attempt)
    if '..' in module_name:
        raise ValidationError(
            f"Invalid package name '{package_name}': contains '..' sequence"
        )

    return module_name


def validate_boolean(value: Any, field_name: str = "value") -> bool:
    """Validate and convert a value to boolean.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        Boolean representation of the value

    Raises:
        ValidationError: If the value cannot be converted to boolean
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ('true', '1', 'yes', 'on'):
            return True
        elif lower_value in ('false', '0', 'no', 'off'):
            return False
        else:
            raise ValidationError(
                f"{field_name} must be a valid boolean string "
                f"(true/false/yes/no/1/0/on/off), got '{value}'"
            )

    if isinstance(value, int):
        if value == 0:
            return False
        elif value == 1:
            return True
        else:
            raise ValidationError(
                f"{field_name} must be 0 or 1 for numeric boolean, got {value}"
            )

    if isinstance(value, float):
        if value == 0.0:
            return False
        elif value == 1.0:
            return True
        else:
            raise ValidationError(
                f"{field_name} must be 0.0 or 1.0 for float boolean, got {value}"
            )

    raise ValidationError(f"{field_name} must be a boolean or convertible to boolean")


def validate_string_not_empty(value: Any, field_name: str = "value") -> str:
    """Validate that a value is a non-empty string.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        The validated string (stripped)

    Raises:
        ValidationError: If the value is not a non-empty string
    """
    if not value:
        raise ValidationError(f"{field_name} cannot be empty")

    value = str(value).strip()

    if not value:
        raise ValidationError(f"{field_name} cannot be empty after trimming")

    return value
