"""Build caching utilities for CodeVault."""

import hashlib
import time
from pathlib import Path
from typing import Optional


CACHE_LIMITS = {
    "pip": 1024 * 1024 * 500,
    "ccache": 1024 * 1024 * 1024,
    "mingw": 1024 * 1024 * 800,
    "nuitka": 1024 * 1024 * 200,
}

CACHE_TTL_DAYS = 14
CACHE_EVICTION_THRESHOLD = 0.9


def get_build_cache_key(source_dir: Path, config_str: str) -> str:
    """
    Generate cache key based on source code and configuration.

    Args:
        source_dir: Source directory
        config_str: String representation of build configuration

    Returns:
        Cache key (16 hex characters)
    """
    m = hashlib.sha256()
    m.update(config_str.encode())

    for py_file in sorted(source_dir.rglob("*.py")):
        try:
            m.update(py_file.read_bytes())
        except (OSError, PermissionError):
            pass

    pkg_json = source_dir / "package.json"
    if pkg_json.exists():
        try:
            m.update(pkg_json.read_bytes())
        except (OSError, PermissionError):
            pass

    return m.hexdigest()[:16]


def check_cache(
    cache_dir: Path, cache_key: str, ttl_days: int = CACHE_TTL_DAYS
) -> Optional[Path]:
    """
    Check if cached build exists.

    Args:
        cache_dir: Directory containing cache
        cache_key: Cache key to check
        ttl_days: Cache TTL in days

    Returns:
        Path to cached exe or None
    """
    if not cache_dir.exists():
        return None

    cached_exe = cache_dir / f"{cache_key}.exe"
    if cached_exe.exists():
        age_days = (time.time() - cached_exe.stat().st_mtime) / 86400
        if age_days < ttl_days:
            return cached_exe
    return None


def save_to_cache(cache_dir: Path, cache_key: str, exe_path: Path) -> bool:
    """
    Save build result to cache.

    Args:
        cache_dir: Cache directory
        cache_key: Cache key
        exe_path: Compiled executable

    Returns:
        True if save was successful
    """
    import shutil

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_exe = cache_dir / f"{cache_key}.exe"
        shutil.copy2(exe_path, cached_exe)
        return True
    except Exception:
        return False
