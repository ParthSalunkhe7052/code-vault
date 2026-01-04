from templates.nodejs_tpl import NODEJS_WRAPPER_LEGACY, NODEJS_WRAPPER_PREFIX, NODEJS_WRAPPER_SUFFIX

def get_nodejs_wrapper(license_key: str, server_url: str, target_filename: str, lease_enabled: bool = False) -> str:
    """Get Node.js license wrapper code (legacy - uses require, not pkg-compatible)."""
    # Escaping for f-string content (though we are using string replacement now)
    target_file = target_filename.replace("'", "\\'")

    # In the original code, this was an f-string:
    # wrapper_code = f'''...'''
    # It had {target_file} at the end.
    # We moved it to a template variable NODEJS_WRAPPER_LEGACY.
    # It contains placeholders like "{license_key}" and "{server_url}" and "{target_file}".

    code = NODEJS_WRAPPER_LEGACY.replace("{license_key}", license_key)
    code = code.replace("{server_url}", server_url)
    code = code.replace("{target_file}", target_file)

    return code


def get_nodejs_wrapper_inline(license_key: str, server_url: str, lease_enabled: bool = False) -> tuple[str, str]:
    """
    Get Node.js license wrapper as prefix/suffix to wrap original code.

    Args:
        license_key: The license key to embed
        server_url: The server URL for validation
        lease_enabled: Whether offline lease mode is enabled (default: False)

    Returns (prefix, suffix) tuple.
    """
    # PREFIX contains {license_key}, {server_url}, and {lease_enabled}
    prefix = NODEJS_WRAPPER_PREFIX.replace("{license_key}", license_key)
    prefix = prefix.replace("{server_url}", server_url)
    prefix = prefix.replace("{lease_enabled}", "true" if lease_enabled else "false")

    # SUFFIX is static
    suffix = NODEJS_WRAPPER_SUFFIX

    return prefix, suffix
