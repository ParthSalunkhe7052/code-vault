"""
System utilities for CodeVault CLI

B29: Disk space pre-check
"""

import shutil
import sys
from pathlib import Path
from typing import Tuple


def check_disk_space(path: Path, required_mb: int = 2048) -> Tuple[bool, int]:
    """Check if there's enough disk space at the given path.

    Args:
        path: Path to check (should exist or have parent that exists)
        required_mb: Minimum required space in MB (default 2GB)

    Returns:
        Tuple of (has_enough_space, available_mb)
    """
    try:
        # Get the directory to check
        check_path = path if path.exists() else path.parent
        if not check_path.exists():
            check_path = Path.home()

        # Get disk usage
        usage = shutil.disk_usage(check_path)
        available_mb = usage.free // (1024 * 1024)

        return available_mb >= required_mb, available_mb
    except Exception as e:
        # If we can't check, assume it's ok but log the error
        print(f"Warning: Could not check disk space: {e}", file=sys.stderr)
        return True, 0


def check_build_prerequisites(project_dir: Path, config: dict) -> Tuple[bool, str]:
    """Check all prerequisites before starting a build.

    Args:
        project_dir: Project directory path
        config: Build configuration

    Returns:
        Tuple of (can_proceed, message)
    """
    language = config.get("language", "python")
    fast_build = config.get("fast_build", False)

    # Determine required space based on language and build mode
    if language == "nodejs":
        # Node.js/pkg needs less space
        required_mb = 512 if fast_build else 1024
    else:
        # Python/Nuitka needs more space, especially for onefile builds
        required_mb = 1024 if fast_build else 3072  # 1GB or 3GB

    # Check disk space in project directory
    has_space, available_mb = check_disk_space(project_dir, required_mb)

    if not has_space:
        return (
            False,
            f"Insufficient disk space: {available_mb}MB available, {required_mb}MB required",
        )

    # Additional checks could go here (memory, etc.)

    return True, f"Prerequisites OK ({available_mb}MB available)"


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"
