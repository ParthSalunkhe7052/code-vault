import re
from pathlib import Path
from typing import Dict, Any, Optional

class PathTraversalError(Exception):
    """Raised when a path traversal attack is detected."""
    pass

# Regex for valid output names: alphanumeric, underscores, hyphens, dots (no path separators)
OUTPUT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,99}$")

# Dangerous path patterns that could indicate traversal attempts
DANGEROUS_PATTERNS = [
    "..",  # Parent directory traversal
    "//",  # Double slashes
    "\\\\",  # Double backslashes
    "\x00",  # Null byte injection
    "%2e",  # URL-encoded dot
    "%2f",  # URL-encoded forward slash
    "%5c",  # URL-encoded backslash
    "%00",  # URL-encoded null
    "%c0%ae",  # UTF-8 overlong encoding attack (dot)
    "%c0%af",  # UTF-8 overlong encoding attack (slash)
]

def validate_entry_file(entry_file: str, project_dir: Path) -> Path:
    """Validate entry file path to prevent path traversal.

    Args:
        entry_file: The entry file path from config
        project_dir: The base project directory

    Returns:
        Validated absolute path to the entry file

    Raises:
        PathTraversalError: If path traversal is detected
    """
    if not entry_file:
        raise PathTraversalError("Entry file cannot be empty")

    # Normalize backslashes to forward slashes for cross-platform compatibility
    entry_file = entry_file.replace("\\", "/")

    # Check for dangerous patterns in the raw input
    entry_lower = entry_file.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in entry_lower:
            raise PathTraversalError(f"Invalid entry file path: contains forbidden pattern '{pattern}'")

    # Normalize the path
    entry_path = Path(entry_file)

    # Ensure it's not absolute (should be relative to project)
    if entry_path.is_absolute():
        raise PathTraversalError("Entry file must be a relative path, not absolute")

    # Resolve relative to project directory
    full_path = (project_dir / entry_path).resolve()
    project_resolved = project_dir.resolve()

    # Verify the resolved path is within the project directory
    try:
        full_path.relative_to(project_resolved)
    except ValueError:
        raise PathTraversalError(
            f"Path traversal detected: entry file '{entry_file}' resolves outside project directory"
        )

    return full_path

def validate_output_name(output_name: str) -> str:
    """Validate and sanitize output name to prevent path traversal in output files.

    Args:
        output_name: The desired output filename (without extension)

    Returns:
        Validated and sanitized output name

    Raises:
        PathTraversalError: If the output name is invalid after sanitization
    """
    if not output_name:
        raise PathTraversalError("Output name cannot be empty")

    # Strip common path separators first
    output_name = output_name.replace("/", "").replace("\\", "")

    # Check for dangerous patterns
    output_lower = output_name.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in output_lower:
            raise PathTraversalError(f"Invalid output name: contains forbidden pattern '{pattern}'")

    # Auto-sanitize: replace spaces with underscores
    original_name = output_name
    output_name = output_name.replace(" ", "_")

    # Replace multiple consecutive underscores with single underscore
    output_name = re.sub(r"_+", "_", output_name)

    # Remove leading/trailing underscores and dots
    output_name = output_name.strip("_.")

    # Validate against allowed pattern
    if not OUTPUT_NAME_PATTERN.match(output_name):
        raise PathTraversalError(
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
        PathTraversalError: If the package name is invalid
    """
    if not package_name:
        return ""

    # Skip __pycache__
    if package_name == "__pycache__":
        return ""

    # Convert path separators to dots for module names
    module_name = package_name.replace("/", ".").replace("\\", ".")

    # Validate: only alphanumeric, dots, underscores
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", module_name):
        raise PathTraversalError(f"Invalid package name '{package_name}': contains invalid characters")

    # Prevent double dots (path traversal attempt)
    if ".." in module_name:
        raise PathTraversalError(f"Invalid package name '{package_name}': contains '..' sequence")

    return module_name

def safe_resolve_path(base_dir: Path, relative_path: str) -> Path:
    """Safely resolve a relative path against a base directory.

    Prevents path traversal by ensuring the result stays within base_dir.

    Args:
        base_dir: The base directory (must exist)
        relative_path: The relative path to resolve

    Returns:
        The resolved absolute path

    Raises:
        PathTraversalError: If traversal is detected or path escapes base
    """
    if not base_dir.exists():
        raise PathTraversalError(f"Base directory does not exist: {base_dir}")

    base_resolved = base_dir.resolve()

    # Handle empty or current directory references
    if not relative_path or relative_path in (".", "./"):
        return base_resolved

    # Normalize backslashes to forward slashes for cross-platform compatibility
    relative_path = relative_path.replace("\\", "/")

    # Check for dangerous patterns
    path_lower = relative_path.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in path_lower:
            raise PathTraversalError(f"Invalid path: contains forbidden pattern '{pattern}'")

    # Resolve and validate
    target = (base_resolved / relative_path).resolve()

    try:
        target.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalError(f"Path traversal detected: '{relative_path}' escapes base directory")

    return target
