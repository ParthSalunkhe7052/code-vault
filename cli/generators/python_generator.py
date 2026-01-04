from templates.python_tpl import PYTHON_WRAPPER_TEMPLATE

def get_python_wrapper(license_key: str, server_url: str, lease_enabled: bool = False) -> str:
    """Get Python license wrapper code.

    Args:
        license_key: The license key to embed
        server_url: The server URL for validation
        lease_enabled: Whether offline lease mode is enabled (default: False)

    Returns:
        The wrapper code with placeholders replaced.
    """
    code = PYTHON_WRAPPER_TEMPLATE.replace("{license_key}", license_key)
    code = code.replace("{server_url}", server_url)
    code = code.replace("{lease_enabled}", "True" if lease_enabled else "False")
    return code
