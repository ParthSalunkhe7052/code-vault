# === CodeVault License Protection ===
# This wrapper is injected at the top of the user's Python entry file.
# Placeholders: __LICENSE_KEY__, __API_URL__
import os as _cv_os
import sys as _cv_sys
import hashlib as _cv_hashlib
import platform as _cv_platform
import json as _cv_json
import time as _cv_time
from urllib.request import Request as _cv_Request, urlopen as _cv_urlopen
from urllib.error import URLError as _cv_URLError
import base64 as _cv_base64

# Configuration - replaced at build time
_CV_LICENSE_KEY = "__LICENSE_KEY__"
_CV_API_URL = "__API_URL__"

# Lease configuration
_CV_LEASE_DURATION = 24 * 60 * 60  # 24 hours
_CV_CLOCK_DRIFT_MAX = 60 * 60  # 1 hour max drift

def _cv_show_error(title, message, details=None):
    """Show error with GUI if available, otherwise terminal."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        full_msg = message
        if details:
            full_msg += "\n\nDetails: " + str(details)
        messagebox.showerror(title, full_msg)
        root.destroy()
        _cv_sys.exit(1)
    except Exception:
        print("\n" + "=" * 60)
        print("  " + title)
        print("=" * 60)
        print("\n" + message)
        if details:
            print("\nDetails: " + str(details))
        print("\n" + "=" * 60)
        try:
            input("\nPress Enter to exit...")
        except Exception:
            pass
        _cv_sys.exit(1)

def _cv_check_gui_available():
    """Check if tkinter GUI is available."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False

class _CV_LicenseDialog:
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
            self.root.geometry("+" + str(int(x)) + "+" + str(int(y)))
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
        title_label = self.ttk.Label(main_frame, text="License Activation",
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
        self.activate_btn = self.tk.Button(main_frame, text="Activate License",
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
        if not self.root: 
            return
        try:
            self.status_label.configure(text=message, foreground=color)
            self.root.update()
        except Exception:
            pass

    def activate(self):
        if self.validating: 
            return
        try:
            license_key = self.license_entry.get().strip()
            if not license_key:
                self.set_status("Please enter a license key", "#ffaa00")
                return

            self.validating = True
            self.activate_btn.configure(state=self.tk.DISABLED, text="Validating...")
            self.set_status("Connecting to server...", "#4a90d9")

            # Close dialog and return key for validation by caller
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

def _cv_get_hwid():
    """Generate hardware ID for license validation."""
    try:
        info = _cv_platform.node() + "|" + _cv_platform.system() + "|" + _cv_platform.machine() + "|" + _cv_platform.processor()
        return _cv_hashlib.sha256(info.encode()).hexdigest()
    except Exception:
        return "unknown-hwid"

def _cv_get_license_key_path():
    """Get path to license.key file next to the executable."""
    try:
        if getattr(_cv_sys, 'frozen', False):
            exe_dir = _cv_os.path.dirname(_cv_sys.executable)
        else:
            exe_dir = _cv_os.path.dirname(_cv_os.path.abspath(__file__))
        
        key_path = _cv_os.path.join(exe_dir, "license.key")
        
        try:
            test_file = _cv_os.path.join(exe_dir, ".cv_write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            _cv_os.remove(test_file)
            return key_path
        except Exception:
            home_dir = _cv_os.path.expanduser("~")
            app_data_dir = _cv_os.path.join(home_dir, ".codevault")
            try:
                _cv_os.makedirs(app_data_dir, exist_ok=True)
            except Exception:
                pass
            return _cv_os.path.join(app_data_dir, "license.key")
            
    except Exception:
        home_dir = _cv_os.path.expanduser("~")
        return _cv_os.path.join(home_dir, "license.key")

def _cv_get_lease_path():
    """Get path to license.lease file."""
    try:
        key_path = _cv_get_license_key_path()
        lease_dir = _cv_os.path.dirname(key_path)
        return _cv_os.path.join(lease_dir, "license.lease")
    except Exception:
        home_dir = _cv_os.path.expanduser("~")
        return _cv_os.path.join(home_dir, "license.lease")

def _cv_get_machine_secret():
    """Generate a machine-specific secret for encryption."""
    try:
        info = _cv_platform.node() + "|" + _cv_platform.machine() + "|" + _cv_platform.processor() + "|CV_SALT_2026"
        return _cv_hashlib.sha256(info.encode()).digest()
    except Exception:
        return _cv_hashlib.sha256(b"fallback_secret").digest()

def _cv_xor_encrypt(data, key):
    """XOR encryption (fallback)."""
    result = bytearray()
    key_bytes = key if isinstance(key, bytes) else key.encode()
    for i, b in enumerate(data):
        result.append(b ^ key_bytes[i % len(key_bytes)])
    return bytes(result)

def _cv_encrypt_lease(lease_data):
    """Encrypt lease with AES-256-GCM (or XOR fallback)."""
    try:
        secret = _cv_get_machine_secret()
        data_json = _cv_json.dumps(lease_data).encode('utf-8')

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import secrets as _secrets
            nonce = _secrets.token_bytes(12)
            aesgcm = AESGCM(secret)
            ciphertext = aesgcm.encrypt(nonce, data_json, None)
            return _cv_base64.b64encode(b"AES:" + nonce + ciphertext).decode()
        except ImportError:
            encrypted = _cv_xor_encrypt(data_json, secret)
            return _cv_base64.b64encode(b"XOR:" + encrypted).decode()
    except Exception:
        return None

def _cv_decrypt_lease(encrypted_data):
    """Decrypt lease (supports both AES and XOR)."""
    try:
        secret = _cv_get_machine_secret()
        raw = _cv_base64.b64decode(encrypted_data)

        if raw.startswith(b"AES:"):
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                nonce = raw[4:16]
                ciphertext = raw[16:]
                aesgcm = AESGCM(secret)
                data_json = aesgcm.decrypt(nonce, ciphertext, None)
                return _cv_json.loads(data_json.decode('utf-8'))
            except Exception:
                return None
        elif raw.startswith(b"XOR:"):
            encrypted = raw[4:]
            data_json = _cv_xor_encrypt(encrypted, secret)
            return _cv_json.loads(data_json.decode('utf-8'))
        else:
            return None
    except Exception:
        return None

def _cv_create_lease(license_key, hwid, server_time, duration=_CV_LEASE_DURATION):
    """Create a new lease token."""
    return {
        "license_key_hash": _cv_hashlib.sha256(license_key.encode()).hexdigest(),
        "hwid": hwid,
        "expires_at": server_time + duration,
        "server_time": server_time,
        "validated_at": int(_cv_time.time())
    }

def _cv_save_lease(lease_data):
    """Save encrypted lease to file."""
    try:
        lease_path = _cv_get_lease_path()
        encrypted = _cv_encrypt_lease(lease_data)
        if encrypted:
            import tempfile
            lease_dir = _cv_os.path.dirname(lease_path)
            fd, temp_path = tempfile.mkstemp(dir=lease_dir, prefix='.tmp_', text=True)
            try:
                with _cv_os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(encrypted)
                _cv_os.replace(temp_path, lease_path)
            except Exception:
                try:
                    _cv_os.unlink(temp_path)
                except Exception:
                    pass
                raise
            print("[CodeVault] Lease saved (24h offline access)")
            return True
    except Exception:
        pass
    return False

def _cv_load_lease():
    """Load and decrypt lease from file."""
    try:
        lease_path = _cv_get_lease_path()
        if _cv_os.path.exists(lease_path):
            with open(lease_path, 'r', encoding='utf-8') as f:
                return _cv_decrypt_lease(f.read().strip())
    except Exception:
        pass
    return None

def _cv_validate_lease(license_key, hwid):
    """Validate an existing lease."""
    lease = _cv_load_lease()
    if not lease:
        return False, "No lease found"

    if lease.get("hwid") != hwid:
        return False, "HWID mismatch"

    key_hash = _cv_hashlib.sha256(license_key.encode()).hexdigest()
    if lease.get("license_key_hash") != key_hash:
        return False, "License mismatch"

    if int(_cv_time.time()) > lease.get("expires_at", 0):
        return False, "Lease expired"

    remaining = lease.get("expires_at", 0) - int(_cv_time.time())
    hours = remaining // 3600
    mins = (remaining % 3600) // 60
    print("[CodeVault] Offline lease valid (" + str(hours) + "h " + str(mins) + "m remaining)")
    return True, "Valid"

def _cv_validate_license(key, hwid, api_url):
    """Validate license key with the server. Returns (success, server_time)"""
    print("[CodeVault] Validating license with server...")
    timestamp = int(_cv_time.time())
    try:
        import secrets as _secrets
        nonce = _secrets.token_hex(16)
    except ImportError:
        import random
        nonce = ''.join(random.choices('0123456789abcdef', k=32))

    data = _cv_json.dumps({
        "license_key": key,
        "hwid": hwid,
        "machine_name": _cv_platform.node(),
        "timestamp": timestamp,
        "nonce": nonce
    }).encode()

    req = _cv_Request(api_url, data=data, headers={"Content-Type": "application/json"})
    try:
        with _cv_urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            result = _cv_json.loads(body)
            # FIX: Server returns "status": "valid", not "valid": true
            server_time = result.get("server_time", result.get("timestamp", timestamp))
            is_valid = result.get("status") == "valid"
            return is_valid, server_time
    except _cv_URLError as e:
        reason = getattr(e, 'reason', str(e))
        print("[CodeVault] Connection error: " + str(reason))
        return None, 0  # None = connection error (allows offline fallback)
    except Exception as e:
        print("[CodeVault] Validation error: " + type(e).__name__ + ": " + str(e))
        return False, 0

def _cv_prompt_license():
    """Prompt user for license key using GUI or console fallback."""
    if _cv_check_gui_available():
        try:
            dialog = _CV_LicenseDialog()
            key = dialog.show()
            if key:
                return key
        except Exception as e:
            print("[CodeVault] GUI prompt failed: " + str(e))

    # Fallback to console
    print("=" * 50)
    print("  License Required")
    print("=" * 50)
    try:
        return input("Enter license key: ").strip()
    except Exception:
        return None

def _cv_license_check():
    """Main license validation with offline lease support."""
    LICENSE_KEY = _CV_LICENSE_KEY
    API_URL = _CV_API_URL

    # DEMO mode - skip validation
    if LICENSE_KEY == "DEMO":
        print("[CodeVault] Running in DEMO mode")
        return True

    hwid = _cv_get_hwid()
    key_file = _cv_get_license_key_path()

    # Check if we need to prompt for license (generic build)
    if LICENSE_KEY in ("GENERIC_BUILD", "generic", "", None):
        # Try saved key first
        saved_key = None
        if _cv_os.path.exists(key_file):
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    saved_key = f.read().strip()
            except Exception:
                pass

        if saved_key:
            print("[CodeVault] Found saved license, validating...")
            success, server_time = _cv_validate_license(saved_key, hwid, API_URL)

            if success is True:
                local_time = int(_cv_time.time())
                drift = abs(local_time - server_time)
                if drift <= _CV_CLOCK_DRIFT_MAX:
                    lease = _cv_create_lease(saved_key, hwid, server_time)
                    _cv_save_lease(lease)
                print("[CodeVault] License verified!")
                return True
            elif success is None:
                print("[CodeVault] Server unreachable, checking offline lease...")
                valid, msg = _cv_validate_lease(saved_key, hwid)
                if valid:
                    print("[CodeVault] Running with offline lease")
                    return True
                else:
                    print("[CodeVault] Offline lease invalid: " + msg)
            else:
                print("[CodeVault] Saved license is invalid or expired.")
                try:
                    _cv_os.remove(key_file)
                    lease_path = _cv_get_lease_path()
                    if _cv_os.path.exists(lease_path):
                        _cv_os.remove(lease_path)
                except Exception:
                    pass

        # Prompt for new license
        key = _cv_prompt_license()
        if not key:
            _cv_show_error("NO LICENSE KEY", "No license key was provided.", "Please run the application again and enter a valid license key.")
            return False

        # Validate the entered key
        success, server_time = _cv_validate_license(key, hwid, API_URL)

        if success is True:
            try:
                key_dir = _cv_os.path.dirname(key_file)
                if key_dir and not _cv_os.path.exists(key_dir):
                    _cv_os.makedirs(key_dir, exist_ok=True)

                import tempfile
                fd, temp_path = tempfile.mkstemp(dir=key_dir, prefix='.tmp_', text=True)
                try:
                    with _cv_os.fdopen(fd, 'w', encoding='utf-8') as f:
                        f.write(key)
                    _cv_os.replace(temp_path, key_file)
                except Exception:
                    try:
                        _cv_os.unlink(temp_path)
                    except Exception:
                        pass
                    raise

                print("[CodeVault] License saved to: " + key_file)
            except Exception as e:
                print("[CodeVault] Warning: Could not save license: " + str(e))

            local_time = int(_cv_time.time())
            drift = abs(local_time - server_time)
            if drift <= _CV_CLOCK_DRIFT_MAX:
                lease = _cv_create_lease(key, hwid, server_time)
                _cv_save_lease(lease)

            print("[CodeVault] License activated!")
            return True
        elif success is None:
            _cv_show_error("OFFLINE - LICENSE REQUIRED",
                          "Cannot validate license - server unreachable.",
                          "First-time activation requires an internet connection.")
        else:
            _cv_show_error("INVALID LICENSE", "The license key was rejected.", "Please check your license key and try again.")

    else:
        # Fixed license key mode
        success, server_time = _cv_validate_license(LICENSE_KEY, hwid, API_URL)

        if success is True:
            local_time = int(_cv_time.time())
            drift = abs(local_time - server_time)
            if drift <= _CV_CLOCK_DRIFT_MAX:
                lease = _cv_create_lease(LICENSE_KEY, hwid, server_time)
                _cv_save_lease(lease)
            print("[CodeVault] License verified!")
            return True
        elif success is None:
            print("[CodeVault] Server unreachable, checking offline lease...")
            valid, msg = _cv_validate_lease(LICENSE_KEY, hwid)
            if valid:
                print("[CodeVault] Running with offline lease")
                return True
            else:
                _cv_show_error("OFFLINE - LICENSE REQUIRED",
                              "Cannot validate license offline: " + msg,
                              "Please connect to the internet to validate your license.")
        else:
            _cv_show_error("LICENSE INVALID", "The embedded license key was rejected by the server.", None)

    return False

# Run license check on startup
if not _cv_license_check():
    _cv_sys.exit(1)
# === End CodeVault License Protection ===
