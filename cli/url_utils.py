"""
URL normalization utilities for CodeVault.

Provides consistent URL handling across CLI, server, and cloud build systems.
Ensures that URLs are properly formatted for API calls without duplication.
"""

from urllib.parse import urlparse, urlunparse


def normalize_server_url(url: str, ensure_no_api_suffix: bool = True) -> str:
    """
    Normalize server URL to a consistent format.
    
    This function ensures that URLs are properly formatted for API calls,
    preventing issues with duplicate path segments (e.g., /api/v1/api/v1).
    
    Args:
        url: The URL to normalize
        ensure_no_api_suffix: If True, strips /api/v1 or /api from the end
    
    Returns:
        Normalized URL string
    
    Examples:
        >>> normalize_server_url("https://api.codevault.app")
        "https://api.codevault.app"
        >>> normalize_server_url("https://api.codevault.app/api/v1")
        "https://api.codevault.app"
        >>> normalize_server_url("https://api.codevault.app/")
        "https://api.codevault.app"
    """
    if not url:
        return url
    
    # Parse URL
    parsed = urlparse(url)
    
    # Remove trailing slashes from path
    path = parsed.path.rstrip('/')
    
    # Remove /api/v1 or /api suffix if requested
    if ensure_no_api_suffix:
        if path.endswith('/api/v1'):
            path = path[:-7]
        elif path.endswith('/api'):
            path = path[:-4]
        # Handle case where there's just /api/v1 with no leading content
        if path == '/api/v1' or path == 'api/v1':
            path = ''
        elif path == '/api' or path == 'api':
            path = ''
    
    # Reconstruct URL
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        '',  # params
        '',  # query
        ''   # fragment
    ))
    
    return normalized


def get_api_url(server_url: str, endpoint: str = "") -> str:
    """
    Build a full API URL from a server URL.
    
    Args:
        server_url: Base server URL (will be normalized)
        endpoint: API endpoint path (will be appended with /api/v1 prefix)
    
    Returns:
        Full API URL
    
    Examples:
        >>> get_api_url("https://api.codevault.app", "license/validate")
        "https://api.codevault.app/api/v1/license/validate"
        >>> get_api_url("https://api.codevault.app/api/v1", "license/validate")
        "https://api.codevault.app/api/v1/license/validate"
    """
    # Normalize server URL (remove /api/v1 if present)
    base_url = normalize_server_url(server_url, ensure_no_api_suffix=True)
    
    # Ensure endpoint starts with /
    if endpoint and not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    
    # Build full URL
    return f"{base_url}/api/v1{endpoint}"


# Backward compatibility aliases
normalize_api_url = normalize_server_url
strip_api_suffix = lambda url: normalize_server_url(url, ensure_no_api_suffix=True)
