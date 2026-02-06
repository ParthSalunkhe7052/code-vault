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


# =====================================================
# CodeVault Branding Splash - Free Tier
# This splash is removed for Pro/Enterprise users
# =====================================================
BRANDING_SPLASH_CODE = '''
# =====================================================
# CodeVault Branding - Free Tier
# This splash is removed for Pro/Enterprise users
# =====================================================
def _show_codevault_splash():
    """Show CodeVault branding splash for free tier."""
    try:
        import tkinter as tk
        import threading
        
        def show_splash():
            root = tk.Tk()
            root.overrideredirect(True)  # No window decorations
            root.attributes('-topmost', True)
            
            # Center on screen
            width, height = 350, 120
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            root.geometry(f"{width}x{height}+{x}+{y}")
            
            # Styling
            root.configure(bg='#1a1a2e')
            
            # Frame
            frame = tk.Frame(root, bg='#1a1a2e', padx=20, pady=15)
            frame.pack(fill='both', expand=True)
            
            # Shield icon (unicode) + Text
            title = tk.Label(
                frame, 
                text="\U0001F6E1 Protected by CodeVault",
                font=('Segoe UI', 14, 'bold'),
                fg='#00d4aa',
                bg='#1a1a2e'
            )
            title.pack(pady=(5, 5))
            
            subtitle = tk.Label(
                frame,
                text="License-Protected Application",
                font=('Segoe UI', 10),
                fg='#888888',
                bg='#1a1a2e'
            )
            subtitle.pack()
            
            link = tk.Label(
                frame,
                text="codevault.app",
                font=('Segoe UI', 9, 'underline'),
                fg='#6c5ce7',
                bg='#1a1a2e',
                cursor='hand2'
            )
            link.pack(pady=(5, 0))
            
            # Auto-close after 3 seconds
            root.after(3000, root.destroy)
            
            # Click anywhere to close
            root.bind('<Button-1>', lambda e: root.destroy())
            
            root.mainloop()
        
        # Run in separate thread to not block
        splash_thread = threading.Thread(target=show_splash, daemon=True)
        splash_thread.start()
        
        # Small delay to show splash
        import time
        time.sleep(0.5)
        
    except ImportError:
        # Tkinter not available - show console fallback
        print("")
        print("  \033[36m\033[1m\U0001F6E1 Protected by CodeVault\033[0m")
        print("  \033[90mLicense-Protected Application\033[0m")
        print("  \033[35mhttps://codevault.app\033[0m")
        print("")
    except Exception:
        # Silently fail for other errors
        pass

# Show splash on import
_show_codevault_splash()
'''


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


def get_python_wrapper(license_key: str, server_url: str, secret_key: str = "dev-secret-key", lease_enabled: bool = False, show_branding: bool = True) -> str:
    """Get Python license wrapper code.

    Args:
        license_key: The license key to embed (must be alphanumeric with hyphens)
        server_url: The server URL for validation (must be valid http/https URL)
        secret_key: The signing secret for the project (default: dev-secret-key)
        lease_enabled: Whether offline lease mode is enabled (default: False)
        show_branding: Whether to show CodeVault branding splash (default: True for free tier)

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
    safe_secret_key = escape_for_python_string(secret_key)

    # Build wrapper with optional branding
    wrapper_parts = []
    
    # Add branding splash if free tier (show_branding=True)
    if show_branding:
        wrapper_parts.append(BRANDING_SPLASH_CODE)
    
    # Now safe to replace in template
    code = PYTHON_WRAPPER_TEMPLATE.replace("{license_key}", safe_license_key)
    code = code.replace("{server_url}", safe_server_url)
    code = code.replace("{secret_key}", safe_secret_key)
    code = code.replace("{lease_enabled}", "True" if lease_enabled else "False")
    
    wrapper_parts.append(code)
    
    return "\n".join(wrapper_parts)
