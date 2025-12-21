"""
License Dialog Template for Python Applications
This gets injected into Python apps for GUI-based license activation

Features:
- Beautiful tkinter GUI (not ugly default)
- Input field for license key
- Loading spinner during validation
- Success/Error messages
- Saves license to license.key file
"""

# This is a TEMPLATE - placeholders will be replaced at compile time:
# {{API_URL}} - License validation API endpoint
# {{APP_NAME}} - Application name for display

LICENSE_DIALOG_TEMPLATE = r'''
import os
import sys
import json
import hashlib
import platform
import threading
import urllib.request
import urllib.error
from pathlib import Path

# Try to import tkinter
try:
    import tkinter as tk
    from tkinter import ttk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


# Configuration (injected at compile time)
API_URL = "{{API_URL}}"
APP_NAME = "{{APP_NAME}}"


def get_exe_dir():
    """Get the directory where the executable is located"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def get_license_key_path():
    """Get the path to the license.key file"""
    return get_exe_dir() / "license.key"


def get_hwid():
    """Generate a hardware ID for this machine"""
    try:
        info = f"{platform.node()}|{platform.system()}|{platform.machine()}|{platform.processor()}"
        return hashlib.sha256(info.encode()).hexdigest()
    except Exception:
        return "unknown-hwid"


def validate_license_with_server(license_key: str) -> dict:
    """
    Validate license key with the server
    
    Returns:
        dict with keys: success (bool), message (str)
    """
    try:
        import random
        import time
        
        hwid = get_hwid()
        nonce = hashlib.sha256(str(random.random()).encode()).hexdigest()[:32]
        timestamp = int(time.time())
        
        data = json.dumps({
            "license_key": license_key,
            "hwid": hwid,
            "nonce": nonce,
            "timestamp": timestamp,
            "machine_name": platform.node()
        }).encode('utf-8')
        
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get("status") == "valid":
                return {"success": True, "message": "License activated successfully!"}
            else:
                return {"success": False, "message": result.get("message", "Invalid license key")}
                
    except urllib.error.URLError as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Validation error: {str(e)}"}


def save_license(license_key: str):
    """Save license key to file"""
    try:
        license_path = get_license_key_path()
        license_path.write_text(license_key, encoding='utf-8')
        return True
    except Exception:
        return False


def load_saved_license() -> str:
    """Load previously saved license key"""
    try:
        license_path = get_license_key_path()
        if license_path.exists():
            return license_path.read_text(encoding='utf-8').strip()
    except Exception:
        pass
    return None


def delete_saved_license():
    """Delete the saved license file"""
    try:
        license_path = get_license_key_path()
        if license_path.exists():
            license_path.unlink()
    except Exception:
        pass


class LicenseDialog:
    """Modern license activation dialog using tkinter"""
    
    def __init__(self):
        self.result = None
        self.validating = False
        
    def show(self) -> str:
        """
        Show the license dialog and return the validated license key
        Returns None if cancelled or validation fails
        """
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - License Activation")
        self.root.geometry("450x320")
        self.root.resizable(False, False)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.root.winfo_screenheight() // 2) - (320 // 2)
        self.root.geometry(f"+{x}+{y}")
        
        # Style
        self.root.configure(bg="#1a1a2e")
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), 
                       foreground="#e94560", background="#1a1a2e")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), 
                       foreground="#aaaaaa", background="#1a1a2e")
        style.configure("Status.TLabel", font=("Segoe UI", 9), 
                       foreground="#888888", background="#1a1a2e")
        style.configure("TButton", font=("Segoe UI", 11), padding=10)
        style.configure("TEntry", font=("Consolas", 12), padding=8)
        
        # Main frame
        main_frame = tk.Frame(self.root, bg="#1a1a2e", padx=30, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔐 License Activation", 
                               style="Title.TLabel")
        title_label.pack(pady=(0, 5))
        
        # Subtitle
        subtitle_label = ttk.Label(main_frame, 
                                  text=f"Enter your license key to activate {APP_NAME}",
                                  style="Subtitle.TLabel")
        subtitle_label.pack(pady=(0, 25))
        
        # License key entry frame
        entry_frame = tk.Frame(main_frame, bg="#16213e", padx=3, pady=3)
        entry_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.license_entry = tk.Entry(entry_frame, font=("Consolas", 12), 
                                      bg="#0f0f23", fg="#ffffff",
                                      insertbackground="#e94560",
                                      relief=tk.FLAT, width=40)
        self.license_entry.pack(fill=tk.X, padx=2, pady=2, ipady=8)
        self.license_entry.focus_set()
        
        # Bind Enter key
        self.license_entry.bind("<Return>", lambda e: self.activate())
        
        # Activate button
        self.activate_btn = tk.Button(main_frame, text="✓ Activate License",
                                     font=("Segoe UI", 11, "bold"),
                                     bg="#e94560", fg="white",
                                     activebackground="#c73e54",
                                     activeforeground="white",
                                     relief=tk.FLAT, cursor="hand2",
                                     command=self.activate)
        self.activate_btn.pack(fill=tk.X, pady=(10, 15), ipady=8)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="", style="Status.TLabel")
        self.status_label.pack(pady=(5, 0))
        
        # Progress bar (hidden initially)
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Run dialog
        self.root.mainloop()
        
        return self.result
    
    def set_status(self, message: str, color: str = "#888888"):
        """Update status label"""
        self.status_label.configure(text=message, foreground=color)
        self.root.update()
    
    def activate(self):
        """Handle activation button click"""
        if self.validating:
            return
        
        license_key = self.license_entry.get().strip()
        
        if not license_key:
            self.set_status("⚠️ Please enter a license key", "#ffaa00")
            return
        
        self.validating = True
        self.activate_btn.configure(state=tk.DISABLED, text="Validating...")
        self.set_status("🔄 Connecting to license server...", "#4a90d9")
        self.progress.pack(fill=tk.X, pady=(10, 0))
        self.progress.start(10)
        
        # Run validation in background thread
        def validate():
            result = validate_license_with_server(license_key)
            self.root.after(0, lambda: self.on_validation_complete(result, license_key))
        
        thread = threading.Thread(target=validate, daemon=True)
        thread.start()
    
    def on_validation_complete(self, result: dict, license_key: str):
        """Handle validation result"""
        self.progress.stop()
        self.progress.pack_forget()
        self.validating = False
        
        if result["success"]:
            # Save license and close
            save_license(license_key)
            self.set_status("✅ " + result["message"], "#00cc66")
            self.result = license_key
            self.root.after(1500, self.root.destroy)
        else:
            self.set_status("❌ " + result["message"], "#e94560")
            self.activate_btn.configure(state=tk.NORMAL, text="✓ Activate License")
    
    def on_close(self):
        """Handle window close"""
        if not self.validating:
            self.result = None
            self.root.destroy()


def console_license_prompt() -> str:
    """Fallback console-based license prompt"""
    print("\n" + "=" * 50)
    print(f"  {APP_NAME} - LICENSE ACTIVATION")
    print("=" * 50)
    print("\nPlease enter your license key:")
    
    try:
        license_key = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nActivation cancelled.")
        sys.exit(1)
    
    if not license_key:
        print("No license key provided. Exiting.")
        sys.exit(1)
    
    print("\nValidating license...")
    result = validate_license_with_server(license_key)
    
    if result["success"]:
        save_license(license_key)
        print(f"✓ {result['message']}")
        return license_key
    else:
        print(f"✗ {result['message']}")
        delete_saved_license()
        sys.exit(1)


def get_license() -> str:
    """
    Main entry point for license validation
    
    First checks for saved license, then prompts if needed.
    Uses GUI if available, falls back to console.
    
    Returns:
        Validated license key
    
    Exits:
        If license validation fails or is cancelled
    """
    # Check for saved license
    saved_license = load_saved_license()
    if saved_license:
        print(f"[{APP_NAME}] Found saved license. Validating...")
        result = validate_license_with_server(saved_license)
        if result["success"]:
            print(f"[{APP_NAME}] License valid. Starting application...")
            return saved_license
        else:
            print(f"[{APP_NAME}] Saved license invalid: {result['message']}")
            delete_saved_license()
    
    # Need to prompt for license
    if HAS_TKINTER:
        try:
            dialog = LicenseDialog()
            license_key = dialog.show()
            if license_key:
                return license_key
            else:
                print(f"[{APP_NAME}] License activation cancelled.")
                sys.exit(1)
        except Exception as e:
            print(f"[{APP_NAME}] GUI error: {e}. Falling back to console.")
            return console_license_prompt()
    else:
        return console_license_prompt()


# Export for use in wrapped applications
__all__ = ['get_license', 'validate_license_with_server', 'save_license', 'load_saved_license']
'''


def get_license_dialog_code(api_url: str, app_name: str) -> str:
    """
    Get the license dialog code with placeholders replaced
    
    Args:
        api_url: The license validation API endpoint
        app_name: The application name for display
    
    Returns:
        Python code ready to be injected into the application
    """
    return LICENSE_DIALOG_TEMPLATE.replace(
        "{{API_URL}}", api_url
    ).replace(
        "{{APP_NAME}}", app_name
    )
