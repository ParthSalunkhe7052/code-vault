# ============ LICENSE WRAPPER TEMPLATE - DO NOT REMOVE ============
# This template is used by the server's Python compiler.
# Variables are substituted using .replace() - NOT f-strings.
# Placeholders: {license_key}, {server_url}, {public_key}, {app_name}

PYTHON_WRAPPER_TEMPLATE = r'''# === CodeVault License Protection ===
import os as _cv_os
import sys as _cv_sys
import hashlib as _cv_hashlib
import platform as _cv_platform
import json as _cv_json
import time as _cv_time
from urllib.request import Request as _cv_Request, urlopen as _cv_urlopen
from urllib.error import URLError as _cv_URLError
import base64 as _cv_base64

# Configuration
_CV_LICENSE_KEY = "{license_key}"
_CV_SERVER_URL = "{server_url}"
_CV_PUBLIC_KEY = """{public_key}"""
_CV_APP_NAME = "{app_name}"

# Lease configuration
_CV_LEASE_DURATION = 24 * 60 * 60
_CV_CLOCK_DRIFT_MAX = 60 * 60

def _cv_show_error(title, message, details=None):
    """Show error with formatting and wait for user."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print(f"\n{message}")
    if details:
        print(f"\nDetails: {details}")
    print("\n" + "=" * 60)
    print("Please take a screenshot of this error and report it.")
    print("=" * 60)
    try:
        input("\nPress Enter to exit...")
    except Exception:
        pass
    _cv_sys.exit(1)

def _cv_build_signature_message(result):
    """Build canonical message for signature verification."""
    features_json = _cv_json.dumps(sorted(result.get("features", [])), sort_keys=True)
    variables_json = _cv_json.dumps(result.get("variables", {}), sort_keys=True)
    msg = "|".join(str(v) for v in [
        result.get("status", ""),
        result.get("expires_at", "") or "",
        features_json,
        variables_json,
        result.get("client_nonce", "") or result.get("nonce", ""),
        result.get("server_nonce", ""),
        result.get("timestamp", "") or "",
        result.get("server_time", "") or ""
    ])
    return msg

def _cv_verify_signature(result):
    """Verify Ed25519 signature from server response."""
    server_sig = result.get("signature")
    if not server_sig:
        _cv_show_error("SECURITY ERROR", 
                      "Server response is unsigned.",
                      "Response missing digital signature.")
        return False
    
    if not _CV_PUBLIC_KEY or not _CV_PUBLIC_KEY.strip():
        _cv_show_error("SECURITY ERROR",
                      "No public key configured.",
                      "Cannot verify server response without a public key.")
        return False
    
    msg = _cv_build_signature_message(result)
    
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        
        pub_key = load_pem_public_key(_CV_PUBLIC_KEY.encode())
        sig_bytes = _cv_base64.b64decode(server_sig)
        pub_key.verify(sig_bytes, msg.encode())
        return True
    except Exception as e:
        _cv_show_error("SECURITY ERROR",
                      "Server signature verification failed.",
                      f"The response may be tampered. Error: {e}")
        return False

def _cv_check_gui_available():
    """Check if tkinter GUI is available."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception as e:
        print("[CodeVault] GUI not available, using console mode")
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
        self.root.title(f"{_CV_APP_NAME} - License Activation")
        self.root.geometry("450x320")
        self.root.resizable(False, False)

        self.root.update_idletasks()
        try:
            x = (self.root.winfo_screenwidth() // 2) - (450 // 2)
            y = (self.root.winfo_screenheight() // 2) - (320 // 2)
            self.root.geometry(f"+{int(x)}+{int(y)}")
        except Exception:
            pass

        self.root.configure(bg="#1a1a2e")

        style = self.ttk.Style()
        style.theme_use('clam')
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                       foreground="#e94560", background="#1a1a2e")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10),
                       foreground="#aaaaaa", background="#1a1a2e")
        style.configure("Status.TLabel", font=("Segoe UI", 9),
                       foreground="#888888", background="#1a1a2e")

        main_frame = self.tk.Frame(self.root, bg="#1a1a2e", padx=30, pady=25)
        main_frame.pack(fill=self.tk.BOTH, expand=True)

        branding_label = self.ttk.Label(main_frame, text="Protected by CodeVault",
                                  style="Status.TLabel")
        branding_label.pack(pady=(0, 10))

        title_label = self.ttk.Label(main_frame, text="License Activation",
                               style="Title.TLabel")
        title_label.pack(pady=(0, 5))

        subtitle_label = self.ttk.Label(main_frame,
                                  text="Enter your license key to activate this application",
                                  style="Subtitle.TLabel")
        subtitle_label.pack(pady=(0, 25))

        entry_frame = self.tk.Frame(main_frame, bg="#16213e", padx=3, pady=3)
        entry_frame.pack(fill=self.tk.X, pady=(0, 15))

        self.license_entry = self.tk.Entry(entry_frame, font=("Consolas", 12),
                                      bg="#0f0f23", fg="#ffffff",
                                      insertbackground="#e94560",
                                      relief=self.tk.FLAT, width=40)
        self.license_entry.pack(fill=self.tk.X, padx=2, pady=2, ipady=8)
        self.license_entry.focus_set()

        self.license_entry.bind("<Return>", lambda e: self.activate())

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
            self.on_close

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
                self.set_status("Please enter a license key", "#ffaa00")
                return

            self.validating = True
            self.activate_btn.configure(state=self.tk.DISABLED, text="Validating...")
            self.set_status("Connecting to server...", "#4a90d9")

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
    """Generate multi-factor hardware ID for license validation."""
    components = []
    
    try:
        import uuid as _cv_uuid
        import re as _cv_re
        mac = ":".join(_cv_re.findall("..", "%012x" % _cv_uuid.getnode()))
        components.append(f"mac:{mac}")
    except Exception:
        pass
    
    if _cv_platform.system() == "Windows":
        try:
            import subprocess as _cv_subprocess
            result = _cv_subprocess.run(
                ["wmic", "diskdrive", "get", "serialnumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                disk_serial = lines[1].strip()
                if disk_serial and disk_serial != "SerialNumber":
                    components.append(f"disk:{disk_serial}")
        except Exception:
            pass
        
        try:
            import subprocess as _cv_subprocess
            result = _cv_subprocess.run(
                ["wmic", "baseboard", "get", "serialnumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                mb_serial = lines[1].strip()
                if mb_serial and mb_serial != "SerialNumber":
                    components.append(f"mb:{mb_serial}")
        except Exception:
            pass
    
    try:
        cpu_id = _cv_platform.processor()
        if cpu_id:
            components.append(f"cpu:{cpu_id[:32]}")
    except Exception:
        pass
    
    if components:
        return _cv_hashlib.sha256("|".join(components).encode()).hexdigest()[:32]
    
    try:
        info = f"{_cv_platform.node()}|{_cv_platform.system()}|{_cv_platform.machine()}"
        return _cv_hashlib.sha256(info.encode()).hexdigest()[:32]
    except Exception:
        return "unknown-hwid"

def _cv_get_binary_hash():
    """Calculate SHA-256 hash of current executable for integrity checking."""
    try:
        if getattr(_cv_sys, 'frozen', False):
            path = _cv_sys.executable
        else:
            path = _cv_sys.argv[0]
        
        sha256 = _cv_hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256.update(byte_block)
        return sha256.hexdigest()
    except Exception:
        return None

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
    key_path = _cv_get_license_key_path()
    lease_dir = _cv_os.path.dirname(key_path)
    return _cv_os.path.join(lease_dir, "license.lease")

def _cv_get_machine_secret():
    """Generate a machine-and-application-specific secret for lease encryption.

    The secret is derived from a combination of:
    - Machine-observable hardware identifiers (platform node/machine/processor)
    - The Ed25519 public key embedded at compile time (_CV_PUBLIC_KEY)

    Binding the lease encryption key to _CV_PUBLIC_KEY ensures that even if an
    attacker knows the machine's hostname/CPU string, they cannot reconstruct the
    key without also knowing the application-specific public key — which varies
    per project on the CodeVault server.
    """
    try:
        app_binding = _cv_hashlib.sha256(_CV_PUBLIC_KEY.encode()).hexdigest()[:32] if _CV_PUBLIC_KEY else "no-key"
        info = f"{_cv_platform.node()}|{_cv_platform.machine()}|{_cv_platform.processor()}|{app_binding}"
        return _cv_hashlib.sha256(info.encode()).digest()
    except Exception:
        return _cv_hashlib.sha256(b"fallback_secret").digest()

def _cv_encrypt_lease(lease_data):
    """Encrypt lease with AES-256-GCM."""
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
            return None
    except Exception:
        return None

def _cv_decrypt_lease(encrypted_data):
    """Decrypt lease data (AES-256-GCM)."""
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
            except:
                try:
                    _cv_os.unlink(temp_path)
                except:
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
    print(f"[CodeVault] Offline lease valid ({hours}h {mins}m remaining)")
    return True, "Valid"

def _cv_validate_license(key, hwid, api_url):
    """Validate license key with the server. Returns (success, server_time, result)"""
    print(f"[CodeVault] Validating license with server...")
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
        "nonce": nonce,
        "binary_hash": _cv_get_binary_hash()
    }).encode()

    req = _cv_Request(api_url, data=data, headers={"Content-Type": "application/json"})
    try:
        with _cv_urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            result = _cv_json.loads(body)
            
            # Verify Ed25519 signature
            if not _cv_verify_signature(result):
                return False, 0, None
            
            # Protocol v2: Verify response freshness
            issued_at = result.get("issued_at")
            if issued_at:
                current_time = int(_cv_time.time())
                response_age = current_time - issued_at
                if response_age > 300:
                    _cv_show_error("SECURITY ERROR", "Response expired.",
                                  f"Server response is too old ({response_age}s). Possible replay attack.")
                    return False, 0, None
                if response_age < -60:
                    _cv_show_error("SECURITY ERROR", "Response from future.",
                                  "Clock skew detected. Please correct your system time.")
                    return False, 0, None
            
            # Protocol v2: Require jti for replay protection
            if not result.get("jti"):
                _cv_show_error("SECURITY ERROR", "Missing replay protection.",
                              "Server response missing jti (replay protection ID).")
                return False, 0, None
            
            server_time = result.get("server_time", result.get("timestamp", timestamp))
            return result.get("status") == "valid", server_time, result
    except _cv_URLError as e:
        reason = getattr(e, 'reason', str(e))
        print(f"[CodeVault] Connection error: {reason}")
        return None, 0, None  # None = connection error
    except Exception as e:
        print(f"[CodeVault] Validation error: {type(e).__name__}: {e}")
        return False, 0, None

def _cv_prompt_license():
    """Prompt user for license key using GUI or console fallback."""
    if _cv_check_gui_available():
        try:
            dialog = _CV_LicenseDialog()
            key = dialog.show()
            if key:
                return key
        except Exception as e:
            print(f"[CodeVault] GUI prompt failed: {e}")

    print("=" * 50)
    print("  License Required")
    print("=" * 50)
    try:
        return input("Enter license key: ").strip()
    except Exception:
        return None

def _cv_license_check():
    """Main license validation with offline lease support."""
    hwid = _cv_get_hwid()
    key_file = _cv_get_license_key_path()

    if _CV_LICENSE_KEY == "GENERIC_BUILD":
        saved_key = None
        if _cv_os.path.exists(key_file):
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    saved_key = f.read().strip()
            except Exception:
                pass

        if saved_key:
            print(f"[CodeVault] Found saved license, validating...")
            success, server_time, result = _cv_validate_license(saved_key, hwid, _CV_SERVER_URL)

            if success is True:
                local_time = int(_cv_time.time())
                drift = abs(local_time - server_time)
                if drift <= _CV_CLOCK_DRIFT_MAX:
                    lease = _cv_create_lease(saved_key, hwid, server_time)
                    _cv_save_lease(lease)
                else:
                    print(f"[CodeVault] Clock drift detected ({drift}s), lease not saved")
                print("[CodeVault] License verified!")
                return True
            elif success is None:
                print("[CodeVault] Server unreachable, checking offline lease...")
                valid, msg = _cv_validate_lease(saved_key, hwid)
                if valid:
                    print("[CodeVault] Running with offline lease")
                    return True
                else:
                    print(f"[CodeVault] Offline lease invalid: {msg}")
            else:
                print("[CodeVault] Saved license is invalid or expired.")
                try:
                    _cv_os.remove(key_file)
                    lease_path = _cv_get_lease_path()
                    if _cv_os.path.exists(lease_path):
                        _cv_os.remove(lease_path)
                except Exception:
                    pass

        key = _cv_prompt_license()
        if not key:
            _cv_show_error("NO LICENSE KEY", "No license key was provided.", "Please run the application again and enter a valid license key.")
            return False

        success, server_time, result = _cv_validate_license(key, hwid, _CV_SERVER_URL)

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
                except:
                    try:
                        _cv_os.unlink(temp_path)
                    except:
                        pass
                    raise

                print(f"[CodeVault] License saved to: {key_file}")
            except Exception as e:
                print(f"[CodeVault] Warning: Could not save license: {e}")

            local_time = int(_cv_time.time())
            drift = abs(local_time - server_time)
            if drift <= _CV_CLOCK_DRIFT_MAX:
                lease = _cv_create_lease(key, hwid, server_time)
                _cv_save_lease(lease)
            else:
                print(f"[CodeVault] Clock drift detected ({drift}s), lease not saved")

            print("[CodeVault] License activated!")
            return True
        elif success is None:
            _cv_show_error("OFFLINE - LICENSE REQUIRED",
                          "Cannot validate license - server unreachable.",
                          "First-time activation requires an internet connection.")
        else:
            _cv_show_error("INVALID LICENSE", "The license key was rejected.", "Please check your license key and try again.")

    else:
        success, server_time, result = _cv_validate_license(_CV_LICENSE_KEY, hwid, _CV_SERVER_URL)

        if success is True:
            local_time = int(_cv_time.time())
            drift = abs(local_time - server_time)
            if drift <= _CV_CLOCK_DRIFT_MAX:
                lease = _cv_create_lease(_CV_LICENSE_KEY, hwid, server_time)
                _cv_save_lease(lease)
            print("[CodeVault] License verified!")
            return True
        elif success is None:
            print("[CodeVault] Server unreachable, checking offline lease...")
            valid, msg = _cv_validate_lease(_CV_LICENSE_KEY, hwid)
            if valid:
                print("[CodeVault] Running with offline lease")
                return True
            else:
                _cv_show_error("OFFLINE - LICENSE REQUIRED",
                              f"Cannot validate license offline: {msg}",
                              "Please connect to the internet to validate your license.")
        else:
            _cv_show_error("LICENSE INVALID", "The embedded license key was rejected by the server.", None)

    return False

# Run license check on startup
_cv_license_check()
# === End CodeVault License Protection ===
'''


PYTHON_DEMO_WRAPPER = r'''# === CodeVault License Protection (Demo Mode) ===
import time as _cv_time
import sys as _cv_sys

_CV_DEMO_START = _cv_time.time()
_CV_DEMO_DURATION = 60 * 60  # 1 hour demo

print("[CodeVault] Running in DEMO mode (1 hour limit)")

def _cv_check_demo_expired():
    """Check if demo has expired."""
    elapsed = _cv_time.time() - _CV_DEMO_START
    if elapsed > _CV_DEMO_DURATION:
        print("[CodeVault] Demo period has expired!")
        try:
            input("Press Enter to exit...")
        except Exception:
            pass
        _cv_sys.exit(1)

_cv_check_demo_expired()
# === End CodeVault License Protection ===
'''
