# ============ LICENSE WRAPPER - DO NOT REMOVE ============
PYTHON_WRAPPER_TEMPLATE = r'''# ============ LICENSE WRAPPER - DO NOT REMOVE ============
import sys as _lw_sys
import os as _lw_os
import hashlib as _lw_hash
import json as _lw_json
import time as _lw_time
import platform as _lw_platform
import base64 as _lw_base64

# ============ LEASE CONFIGURATION ============
# This flag controls whether offline lease validation is enabled
_LW_LEASE_ENABLED = {lease_enabled}
_LW_LEASE_DURATION = 24 * 60 * 60  # 24 hours in seconds
_LW_CLOCK_DRIFT_MAX = 60 * 60  # 1 hour max clock drift

def _lw_show_error(title, message, details=None):
    """Show error with formatting and troubleshooting guidance."""
    print("\n" + "=" * 60)
    print(f"  ❌ {title}")
    print("=" * 60)
    print(f"\n{message}")
    if details:
        print(f"\nDetails: {details}")

    # Add context-specific troubleshooting
    print("\n" + "-" * 60)
    print("TROUBLESHOOTING:")
    print("-" * 60)
    if "LICENSE INVALID" in title:
        print("- Check your license key for typos")
        print("- Ensure the license is active and not expired")
        print("- Verify you're connected to the internet")
    elif "CONNECTION REQUIRED" in title or "OFFLINE" in title:
        print("- Check your internet connection")
        print("- Try connecting to a different network")
        print("- If offline mode is desired, contact support")
    elif "SERVER ERROR" in title:
        print("- The license server may be temporarily unavailable")
        print("- Try again in a few minutes")
        print("- Check https://status.codevault.io for server status")
    elif "VALIDATION ERROR" in title or "RESPONSE ERROR" in title:
        print("- This may be a bug in the license wrapper")
        print("- Please report this error with full details")
    else:
        print("- Please take a screenshot of this entire error")
        print("- Include information about what you were doing")
        print("- Contact support with the error details")

    print("\n" + "=" * 60)
    try:
        input("\nPress Enter to exit...")
    except Exception:
        pass
    _lw_sys.exit(1)

class LicenseDialog:
    """Modern license activation dialog using tkinter"""
    
    def __init__(self):
        try:
            import tkinter as tk
            from tkinter import ttk
            self.tk = tk
            self.ttk = ttk
            self.has_tkinter = True
        except ImportError:
            self.has_tkinter = False
            return

        self.result = None
        self.validating = False
        self.root = None
        
    def show(self):
        if not self.has_tkinter:
            return None
            
        self.root = self.tk.Tk()
        self.root.title("License Activation")
        self.root.geometry("450x320")
        self.root.resizable(False, False)
        
        # Center window
        self.root.update_idletasks()
        try:
            x = (self.root.winfo_screenwidth() // 2) - (450 // 2)
            y = (self.root.winfo_screenheight() // 2) - (320 // 2)
            self.root.geometry(f"+{int(x)}+{int(y)}")
        except Exception:
            pass
        
        # Style
        self.root.configure(bg="#1a1a2e")
        
        style = self.ttk.Style()
        style.theme_use('clam')
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), 
                       foreground="#e94560", background="#1a1a2e")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), 
                       foreground="#aaaaaa", background="#1a1a2e")
        style.configure("Status.TLabel", font=("Segoe UI", 9), 
                       foreground="#888888", background="#1a1a2e")
        
        # Main frame
        main_frame = self.tk.Frame(self.root, bg="#1a1a2e", padx=30, pady=25)
        main_frame.pack(fill=self.tk.BOTH, expand=True)
        
        # Branding
        branding_label = self.ttk.Label(main_frame, text="Protected by CodeVault",
                                  style="Status.TLabel")
        branding_label.pack(pady=(0, 10))
        
        # Title
        title_label = self.ttk.Label(main_frame, text="🔐 License Activation", 
                               style="Title.TLabel")
        title_label.pack(pady=(0, 5))
        
        # Subtitle
        subtitle_label = self.ttk.Label(main_frame, 
                                  text="Enter your license key to activate this application",
                                  style="Subtitle.TLabel")
        subtitle_label.pack(pady=(0, 25))
        
        # License key entry
        entry_frame = self.tk.Frame(main_frame, bg="#16213e", padx=3, pady=3)
        entry_frame.pack(fill=self.tk.X, pady=(0, 15))
        
        self.license_entry = self.tk.Entry(entry_frame, font=("Consolas", 12), 
                                      bg="#0f0f23", fg="#ffffff",
                                      insertbackground="#e94560",
                                      relief=self.tk.FLAT, width=40)
        self.license_entry.pack(fill=self.tk.X, padx=2, pady=2, ipady=8)
        self.license_entry.focus_set()
        
        self.license_entry.bind("<Return>", lambda e: self.activate())
        
        # Activate button
        self.activate_btn = self.tk.Button(main_frame, text="✓ Activate License",
                                     font=("Segoe UI", 11, "bold"),
                                     bg="#e94560", fg="white",
                                     activebackground="#c73e54",
                                     activeforeground="white",
                                     relief=self.tk.FLAT, cursor="hand2",
                                     command=self.activate)
        self.activate_btn.pack(fill=self.tk.X, pady=(10, 15), ipady=8)
        
        self.status_label = self.ttk.Label(main_frame, text="", style="Status.TLabel")
        self.status_label.pack(pady=(5, 0))
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_close()
            
        return self.result
        
    def set_status(self, message, color="#888888"):
        if not self.root: return
        try:
            self.status_label.configure(text=message, foreground=color)
            self.root.update()
        except Exception:
            pass
        
    def activate(self):
        if self.validating: return
        try:
            license_key = self.license_entry.get().strip()
            if not license_key:
                self.set_status("⚠️ Please enter a license key", "#ffaa00")
                return
                
            self.validating = True
            self.activate_btn.configure(state=self.tk.DISABLED, text="Validating...")
            self.set_status("🔄 Connecting to server...", "#4a90d9")
            
            # Close dialog and return key for validation by caller
            # This keeps the logic simple and synchronous in the caller
            self.result = license_key
            self.root.destroy()
        except Exception:
            self.validating = False

    def on_close(self):
        if not self.validating:
            self.result = None
            try:
                self.root.destroy()
            except Exception:
                pass

def _lw_check_gui_available():
    """Check if tkinter GUI is available."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception as e:
        print("[License Wrapper] GUI not available, using console mode")
        print(f"[License Wrapper] Reason: {e}")
        return False

def _lw_get_hwid():
    """Generate hardware ID."""
    try:
        info = f"{_lw_platform.node()}|{_lw_platform.machine()}|{_lw_platform.processor()}"
        return _lw_hash.sha256(info.encode()).hexdigest()[:32]
    except Exception as e:
        print(f"[License Wrapper] Warning: Could not generate HWID: {e}")
        return "unknown-hwid"

def _lw_get_license_key_path():
    """Get path to license.key file next to the executable."""
    try:
        if getattr(_lw_sys, 'frozen', False):
            exe_dir = _lw_os.path.dirname(_lw_sys.executable)
        else:
            exe_dir = _lw_os.path.dirname(_lw_os.path.abspath(__file__))
        return _lw_os.path.join(exe_dir, "license.key")
    except Exception as e:
        print(f"[License Wrapper] Warning: Could not get license path: {e}")
        return "license.key"

def _lw_get_lease_path():
    """Get path to license.lease file next to the executable."""
    try:
        if getattr(_lw_sys, 'frozen', False):
            exe_dir = _lw_os.path.dirname(_lw_sys.executable)
        else:
            exe_dir = _lw_os.path.dirname(_lw_os.path.abspath(__file__))
        return _lw_os.path.join(exe_dir, "license.lease")
    except Exception:
        return "license.lease"

def _lw_get_machine_secret():
    """Generate a machine-specific secret for encryption."""
    try:
        info = f"{_lw_platform.node()}|{_lw_platform.machine()}|{_lw_platform.processor()}|LW_SALT_2026"
        return _lw_hash.sha256(info.encode()).digest()
    except Exception:
        return _lw_hash.sha256(b"fallback_secret_key").digest()

def _lw_xor_encrypt(data, key):
    """Simple XOR encryption (fallback only)."""
    result = bytearray()
    key_bytes = key if isinstance(key, bytes) else key.encode()
    for i, b in enumerate(data):
        result.append(b ^ key_bytes[i % len(key_bytes)])
    return bytes(result)

def _lw_encrypt_lease(lease_data):
    """Encrypt lease data with AES-256-GCM (or XOR fallback)."""
    try:
        secret = _lw_get_machine_secret()
        data_json = _lw_json.dumps(lease_data).encode('utf-8')
        
        # Try AES-256-GCM first (secure)
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import secrets as _secrets
            nonce = _secrets.token_bytes(12)
            aesgcm = AESGCM(secret)
            ciphertext = aesgcm.encrypt(nonce, data_json, None)
            return _lw_base64.b64encode(b"AES:" + nonce + ciphertext).decode()
        except ImportError:
            # Cryptography not available - fail securely
            return None
    except Exception as e:
        print(f"[License Wrapper] Encryption error: {e}")
        return None

def _lw_decrypt_lease(encrypted_data):
    """Decrypt lease data (supports both AES and XOR)."""
    try:
        secret = _lw_get_machine_secret()
        raw = _lw_base64.b64decode(encrypted_data)
        
        # Check encryption method
        if raw.startswith(b"AES:"):
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                nonce = raw[4:16]
                ciphertext = raw[16:]
                aesgcm = AESGCM(secret)
                data_json = aesgcm.decrypt(nonce, ciphertext, None)
                return _lw_json.loads(data_json.decode('utf-8'))
            except Exception:
                return None
        else:
            return None
    except Exception as e:
        print(f"[License Wrapper] Decryption error: {e}")
        return None

def _lw_create_lease(license_key, hwid, server_time, duration=_LW_LEASE_DURATION):
    """Create a new lease token."""
    return {
        "license_key_hash": _lw_hash.sha256(license_key.encode()).hexdigest(),
        "hwid": hwid,
        "expires_at": server_time + duration,
        "server_time": server_time,
        "validated_at": int(_lw_time.time())
    }

def _lw_save_lease(lease_data):
    """Save encrypted lease to file."""
    # Only save lease if lease mode is enabled
    if not _LW_LEASE_ENABLED:
        return False
    try:
        lease_path = _lw_get_lease_path()
        encrypted = _lw_encrypt_lease(lease_data)
        if encrypted:
            with open(lease_path, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            print("[License Wrapper] Lease saved (expires in 24h)")
            return True
    except Exception as e:
        print(f"[License Wrapper] Could not save lease: {e}")
    return False

def _lw_load_lease():
    """Load and decrypt lease from file."""
    # Only load lease if lease mode is enabled
    if not _LW_LEASE_ENABLED:
        return None
    try:
        lease_path = _lw_get_lease_path()
        if _lw_os.path.exists(lease_path):
            with open(lease_path, 'r', encoding='utf-8') as f:
                encrypted = f.read().strip()
            return _lw_decrypt_lease(encrypted)
    except Exception as e:
        print(f"[License Wrapper] Could not load lease: {e}")
    return None

def _lw_validate_lease(license_key):
    """Validate an existing lease."""
    # Only validate lease if lease mode is enabled
    if not _LW_LEASE_ENABLED:
        return False, "Offline mode not enabled for this build"
    lease = _lw_load_lease()
    if not lease:
        return False, "No lease found"
    
    hwid = _lw_get_hwid()
    current_time = int(_lw_time.time())
    
    if lease.get("hwid") != hwid:
        return False, "HWID mismatch - lease invalid on this machine"
    
    key_hash = _lw_hash.sha256(license_key.encode()).hexdigest()
    if lease.get("license_key_hash") != key_hash:
        return False, "License key mismatch"
    
    expires_at = lease.get("expires_at", 0)
    if current_time > expires_at:
        return False, f"Lease expired"
    
    remaining = expires_at - current_time
    hours = remaining // 3600
    mins = (remaining % 3600) // 60
    print(f"[License Wrapper] Offline lease valid ({hours}h {mins}m remaining)")
    return True, "Lease valid"

def _lw_prompt_for_license():
    """Prompt user for license key using GUI or console fallback."""
    try:
        dialog = LicenseDialog()
        key = dialog.show()
        if key: return key
    except Exception as e:
        print(f"[License Wrapper] GUI prompt failed: {e}")
    
    # Fallback
    try:
        print("\n" + "="*50)
        print("  LICENSE KEY REQUIRED")
        print("="*50)
        license_key = input("Please enter your License Key: ").strip()
        if license_key: return license_key
        return None
    except Exception:
        return None


def _lw_load_or_prompt_license():
    """Load license from file or prompt user for it."""
    license_path = _lw_get_license_key_path()
    
    if _lw_os.path.exists(license_path):
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_key = f.read().strip()
                if license_key:
                    print(f"[License Wrapper] Loaded license from {license_path}")
                    return license_key
        except Exception as e:
            print(f"[License Wrapper] Warning: Could not read license file: {e}")
    
    print("[License Wrapper] No license key found. Please enter your license key.")
    license_key = _lw_prompt_for_license()
    
    if not license_key:
        _lw_show_error("NO LICENSE KEY", "No license key was provided.", "The application requires a valid license key to run.")
    
    try:
        with open(license_path, 'w', encoding='utf-8') as f:
            f.write(license_key)
        print(f"[License Wrapper] License key saved to {license_path}")
    except Exception as e:
        print(f"[License Wrapper] Warning: Could not save license file: {e}")
    
    return license_key

def _lw_validate():
    """Validate license with server."""
    LICENSE_KEY = "{license_key}"
    SERVER_URL = "{server_url}"

    # Check GUI availability at startup
    _lw_check_gui_available()

    if LICENSE_KEY == "DEMO":
        print("[License Wrapper] Running in DEMO mode")
        return True

    if LICENSE_KEY == "GENERIC_BUILD":
        LICENSE_KEY = _lw_load_or_prompt_license()
    
    hwid = _lw_get_hwid()
    
    try:
        import urllib.request
        import urllib.error
        
        nonce = _lw_hash.sha256(str(_lw_time.time()).encode()).hexdigest()[:32]
        
        payload = _lw_json.dumps({
            "license_key": LICENSE_KEY,
            "hwid": hwid,
            "machine_name": _lw_platform.node(),
            "nonce": nonce,
            "timestamp": int(_lw_time.time())
        }).encode('utf-8')
        
        req = urllib.request.Request(
            SERVER_URL + "/api/v1/license/validate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = _lw_json.loads(resp.read().decode('utf-8'))
            
            # CRITICAL SECURITY: Verify Signature
            server_sig = result.get("signature")
            if not server_sig:
                _lw_show_error("SECURITY ERROR", "Server response is unsigned.", "Validation failed for security reasons.")
            
            # Recompute signature locally to verify
            # Fields: status|expires_at|features|variables|client_nonce|server_nonce|timestamp|server_time
            import hmac as _lw_hmac
            
            # Consistent JSON for comparison
            features_json = _lw_json.dumps(sorted(result.get("features", [])), sort_keys=True)
            variables_json = _lw_json.dumps(result.get("variables", {}), sort_keys=True)
            
            msg = "|".join(str(v) for v in [
                result.get("status", ""),
                result.get("expires_at", "") or "",
                features_json,
                variables_json,
                result.get("client_nonce", ""),
                result.get("server_nonce", ""),
                result.get("timestamp", ""),
                result.get("server_time", "")
            ])
            
            # Using the embedded secret key
            # NOTE: In production, the compiler should inject this secret
            _LW_SECRET = "{secret_key}" 
            expected_sig = _lw_hmac.new(_LW_SECRET.encode(), msg.encode(), _lw_hash.sha256).hexdigest()
            
            if not _lw_hmac.compare_digest(server_sig, expected_sig):
                _lw_show_error("SECURITY ERROR", "Server signature mismatch.", "The response from the license server appears to be tampered with or forged.")

            if result.get("status") == "valid":
                print("✅ License validated online")
                
                # Check clock drift and create lease
                server_time = result.get("server_time", result.get("timestamp", int(_lw_time.time())))
                local_time = int(_lw_time.time())
                drift = abs(local_time - server_time)
                
                if drift > _LW_CLOCK_DRIFT_MAX:
                    print(f"[License Wrapper] ⚠️ Clock drift detected: {drift}s")
                    print("[License Wrapper] Lease not created due to clock mismatch")
                else:
                    # Create and save lease for offline use
                    lease = _lw_create_lease(LICENSE_KEY, hwid, server_time)
                    _lw_save_lease(lease)
                
                return True
            else:
                msg = result.get("message", "License invalid")
                try:
                    license_path = _lw_get_license_key_path()
                    if _lw_os.path.exists(license_path):
                        _lw_os.remove(license_path)
                        print("License file removed.")
                    lease_path = _lw_get_lease_path()
                    if _lw_os.path.exists(lease_path):
                        _lw_os.remove(lease_path)
                except Exception:
                    pass
                _lw_show_error("LICENSE INVALID", "The license key was rejected by the server.", f"Server message: {msg}")
                
    except Exception as e:
        # Connection failed
        error_msg = str(e.reason) if hasattr(e, 'reason') else str(e)
        print(f"[License Wrapper] Server unreachable: {error_msg}")

        # Only attempt offline lease validation if lease mode is enabled
        if _LW_LEASE_ENABLED:
            print("[License Wrapper] Checking offline lease...")

            # Check for existing valid lease
            lease_valid, lease_msg = _lw_validate_lease(LICENSE_KEY)

            if lease_valid:
                print("✅ Running with valid offline lease")
                return True
            else:
                print(f"[License Wrapper] Offline lease invalid: {lease_msg}")
                _lw_show_error("OFFLINE - LICENSE REQUIRED",
                              "Cannot validate license offline.",
                              f"{lease_msg}\n\nPlease connect to the internet to validate your license.")
                return False
        else:
            # Lease mode disabled - requires online validation
            _lw_show_error("CONNECTION REQUIRED",
                          "This application requires an internet connection to validate the license.",
                          "Please check your internet connection and try again.")
            return False

_lw_validate()

# Global exception handler for user code errors
def _lw_excepthook(exc_type, exc_value, exc_tb):
    """Global exception handler to catch crashes in user code."""
    import traceback as _tb
    print("\n" + "=" * 60)
    print("  APPLICATION ERROR")
    print("=" * 60)
    print(f"\nAn unexpected error occurred:\n")
    print(f"Error Type: {exc_type.__name__}")
    print(f"Error Message: {exc_value}")
    print("\n--- Traceback ---")
    _tb.print_exception(exc_type, exc_value, exc_tb)
    print("\n" + "=" * 60)
    print("Please take a screenshot of this error and report it.")
    print("=" * 60)
    try:
        input("\nPress Enter to exit...")
    except Exception:
        pass
    _lw_sys.exit(1)

_lw_sys.excepthook = _lw_excepthook
# ============ END LICENSE WRAPPER ============
'''
