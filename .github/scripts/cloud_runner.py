#!/usr/bin/env python3
"""
CodeVault Cloud Build Runner
Standalone script to execute optimized Nuitka builds in CI/CD environments.
"""

import os
import sys
import shutil
import tempfile
import logging
import multiprocessing
import subprocess
import argparse
import json
import re
import time
from pathlib import Path
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [CloudRunner] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Embedded Templates
# =============================================================================

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

# Lease configuration
_CV_LEASE_DURATION = 24 * 60 * 60  # 24 hours
_CV_CLOCK_DRIFT_MAX = 60 * 60  # 1 hour max drift

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
        info = f"{_cv_platform.node()}|{_cv_platform.system()}|{_cv_platform.machine()}|{_cv_platform.processor()}"
        return _cv_hashlib.sha256(info.encode()).hexdigest()
    except Exception:
        return "unknown-hwid"

def _cv_get_license_key_path():
    """Get path to license.key file next to the executable."""
    try:
        if getattr(_cv_sys, 'frozen', False):
            # Running as compiled exe (Nuitka/PyInstaller)
            exe_dir = _cv_os.path.dirname(_cv_sys.executable)
        else:
            # Running as script
            exe_dir = _cv_os.path.dirname(_cv_os.path.abspath(__file__))
        
        # Try executable directory first
        key_path = _cv_os.path.join(exe_dir, "license.key")
        
        # Test if we can write to this location
        try:
            test_file = _cv_os.path.join(exe_dir, ".cv_write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            _cv_os.remove(test_file)
            print(f"[CodeVault] License will be saved to: {key_path}")
            return key_path
        except Exception as write_err:
            # Fall back to user's home directory if exe dir is not writable
            print(f"[CodeVault] Cannot write to exe directory: {exe_dir}")
            print(f"[CodeVault] Reason: {write_err}")
            home_dir = _cv_os.path.expanduser("~")
            app_data_dir = _cv_os.path.join(home_dir, ".codevault")
            try:
                _cv_os.makedirs(app_data_dir, exist_ok=True)
            except Exception:
                pass
            fallback_path = _cv_os.path.join(app_data_dir, "license.key")
            print(f"[CodeVault] Using fallback path: {fallback_path}")
            return fallback_path
            
    except Exception as e:
        # Final fallback
        print(f"[CodeVault] Error determining license path: {e}")
        home_dir = _cv_os.path.expanduser("~")
        return _cv_os.path.join(home_dir, "license.key")

def _cv_get_lease_path():
    """Get path to license.lease file next to the executable."""
    try:
        # Use same directory as license.key file for consistency
        key_path = _cv_get_license_key_path()
        lease_dir = _cv_os.path.dirname(key_path)
        lease_path = _cv_os.path.join(lease_dir, "license.lease")
        return lease_path
            
    except Exception as e:
        # Final fallback
        print(f"[CodeVault] Error determining lease path: {e}")
        home_dir = _cv_os.path.expanduser("~")
        return _cv_os.path.join(home_dir, "license.lease")

def _cv_get_machine_secret():
    """Generate a machine-specific secret for encryption."""
    try:
        info = f"{_cv_platform.node()}|{_cv_platform.machine()}|{_cv_platform.processor()}|CV_SALT_2026"
        return _cv_hashlib.sha256(info.encode()).digest()
    except Exception:
        return _cv_hashlib.sha256(b"fallback_secret").digest()

def _cv_xor_encrypt(data, key):
    """XOR encryption (fallback only)."""
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

        # Try AES-256-GCM first (secure)
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import secrets as _secrets
            nonce = _secrets.token_bytes(12)
            aesgcm = AESGCM(secret)
            ciphertext = aesgcm.encrypt(nonce, data_json, None)
            return _cv_base64.b64encode(b"AES:" + nonce + ciphertext).decode()
        except ImportError:
            # Fallback to XOR if cryptography not available
            encrypted = _cv_xor_encrypt(data_json, secret)
            return _cv_base64.b64encode(b"XOR:" + encrypted).decode()
    except Exception:
        return None

def _cv_decrypt_lease(encrypted_data):
    """Decrypt lease (supports both AES and XOR)."""
    try:
        secret = _cv_get_machine_secret()
        raw = _cv_base64.b64decode(encrypted_data)

        # Check encryption method
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
    """Save encrypted lease to file using atomic write."""
    try:
        lease_path = _cv_get_lease_path()
        encrypted = _cv_encrypt_lease(lease_data)
        if encrypted:
            # Atomic write: temp file + rename to prevent corruption
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
    """Validate license key with the server. Returns (success, server_time)"""
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
        "nonce": nonce
    }).encode()

    req = _cv_Request(api_url, data=data, headers={"Content-Type": "application/json"})
    try:
        with _cv_urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            result = _cv_json.loads(body)
            server_time = result.get("server_time", result.get("timestamp", timestamp))
            return result.get("status") == "valid", server_time
    except _cv_URLError as e:
        reason = getattr(e, 'reason', str(e))
        print(f"[CodeVault] Connection error: {reason}")
        return None, 0  # None = connection error (allows offline fallback)
    except Exception as e:
        print(f"[CodeVault] Validation error: {type(e).__name__}: {e}")
        return False, 0

def _cv_prompt_license():
    """Prompt user for license key using GUI or console fallback."""
    # Check GUI availability first
    if _cv_check_gui_available():
        try:
            dialog = _CV_LicenseDialog()
            key = dialog.show()
            if key:
                return key
        except Exception as e:
            print(f"[CodeVault] GUI prompt failed: {e}")

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
    LICENSE_KEY = "{license_key}"
    API_URL = "{server_url}"

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
            print(f"[CodeVault] Found saved license, validating...")
            success, server_time = _cv_validate_license(saved_key, hwid, API_URL)

            if success is True:
                # Online validation succeeded - create/update lease
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
                # Connection error - try offline lease
                print("[CodeVault] Server unreachable, checking offline lease...")
                valid, msg = _cv_validate_lease(saved_key, hwid)
                if valid:
                    print("[CodeVault] Running with offline lease")
                    return True
                else:
                    print(f"[CodeVault] Offline lease invalid: {msg}")
            else:
                # License rejected
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
            # Save license key to the same directory as the executable (atomic write)
            try:
                key_dir = _cv_os.path.dirname(key_file)
                if key_dir and not _cv_os.path.exists(key_dir):
                    _cv_os.makedirs(key_dir, exist_ok=True)

                # Atomic write to prevent corruption
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

            # Create lease for offline use
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
        # Fixed license key mode
        success, server_time = _cv_validate_license(LICENSE_KEY, hwid, API_URL)

        if success is True:
            # Create lease for offline use
            local_time = int(_cv_time.time())
            drift = abs(local_time - server_time)
            if drift <= _CV_CLOCK_DRIFT_MAX:
                lease = _cv_create_lease(LICENSE_KEY, hwid, server_time)
                _cv_save_lease(lease)
            print("[CodeVault] License verified!")
            return True
        elif success is None:
            # Connection error - try offline lease
            print("[CodeVault] Server unreachable, checking offline lease...")
            valid, msg = _cv_validate_lease(LICENSE_KEY, hwid)
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

# Check periodically (import this check into your main loop if needed)
_cv_check_demo_expired()
# === End CodeVault License Protection ===
'''

# =============================================================================
# Cloud Runner Logic
# =============================================================================

class CloudRunner:
    """Execute optimized builds with Nuitka and Turbo Mode."""
    
    def __init__(self, source_dir: Path, output_dir: Path, config: dict):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.config = config
        
    def run(self) -> Path:
        """Execute the full build pipeline."""
        logger.info(f"Starting build for: {self.config.get('project_name', 'Unknown')}")
        
        # 1. Prepare Environment
        self._prepare_dependencies()
        
        # 2. Find and validate entry file
        entry_file = self._find_entry_file(self.config.get("entry_file", "main.py"))
        
        # 3. Inject Wrapper
        self._inject_license_wrapper(entry_file)
        
        # 4. Compile
        return self._compile_nuitka(entry_file)
    
    def _find_entry_file(self, entry_file: str) -> str:
        """Find entry file with smart fallback for various directory structures."""
        # Try exact path first
        if (self.source_dir / entry_file).exists():
            logger.info(f"Found entry file: {entry_file}")
            return entry_file
        
        # Try flattened structure (e.g., "app/main.py" -> "main.py")
        flat_entry = Path(entry_file).name
        if (self.source_dir / flat_entry).exists():
            logger.warning(f"Entry file '{entry_file}' not found, using flattened: '{flat_entry}'")
            return flat_entry
        
        # Try common Python entry point names
        common_entries = ["main.py", "app.py", "__main__.py", "run.py", "start.py", "index.py"]
        for alt in common_entries:
            if (self.source_dir / alt).exists():
                logger.warning(f"Entry file '{entry_file}' not found, using alternative: '{alt}'")
                return alt
        
        # List available Python files for better error message
        py_files = list(self.source_dir.glob("*.py"))
        if py_files:
            # Use the first Python file as a last resort
            fallback = py_files[0].name
            logger.warning(f"No standard entry file found, using first Python file: '{fallback}'")
            return fallback
        
        # No Python files at all - this will fail
        all_files = [f.name for f in self.source_dir.iterdir() if f.is_file()][:10]
        raise FileNotFoundError(
            f"Entry file '{entry_file}' not found. No Python files in source root. "
            f"Files found: {all_files}"
        )

    def _prepare_dependencies(self):
        """Install dependencies with smart filtering."""
        req_file = self.source_dir / "requirements.txt"
        if req_file.exists():
            logger.info("Installing dependencies...")
            
            # Filter requirements
            content = req_file.read_text(encoding="utf-8")
            filtered_lines = []
            
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                    
                # Skip heavy C-dependant libs if not supported
                if re.search(r'^(ta-lib|TA-Lib)', line, re.IGNORECASE):
                    logger.warning("Skipping ta-lib (requires system libs)")
                    continue
                    
                filtered_lines.append(line)
            
            # Write filtered
            filtered_req = self.source_dir / "requirements_filtered.txt"
            filtered_req.write_text("\n".join(filtered_lines), encoding="utf-8")
            
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(filtered_req),
                 "--quiet", "--disable-pip-version-check", "--no-warn-script-location"],
                stdout=sys.stdout, stderr=sys.stderr
            )

    def _uses_tkinter(self) -> bool:
        """Check if project uses tkinter by scanning source files."""
        try:
            for py_file in self.source_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    # Check for tkinter imports
                    if re.search(r'^(?:import\s+tkinter|from\s+tkinter\s+import)', content, re.MULTILINE):
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _inject_license_wrapper(self, entry_file: str):
        """Inject license wrapper into entry file."""
        entry_path = self.source_dir / entry_file
        if not entry_path.exists():
            raise FileNotFoundError(f"Entry file not found: {entry_file}")
            
        logger.info("Injecting license protection...")
        original_code = entry_path.read_text(encoding="utf-8")
        
        license_key = self.config.get("license_key", "GENERIC_BUILD")
        api_url = self.config.get("api_url", "")
        
        if license_key == "demo":
            wrapper = PYTHON_DEMO_WRAPPER
        else:
            wrapper = PYTHON_WRAPPER_TEMPLATE.replace("{license_key}", license_key).replace("{server_url}", api_url)
            
        entry_path.write_text(wrapper + "\n\n" + original_code, encoding="utf-8")

    def _compile_nuitka(self, entry_file: str) -> Path:
        """Run Nuitka with Turbo Mode optimizations."""
        output_name = self.config.get("output_name") or "app"
        
        # CRITICAL FIX: Ensure output_name is never empty
        if not output_name or output_name.strip() == "":
            output_name = "app"
            logger.warning("output_name was empty, defaulting to 'app'")
        
        # Sanitize output name (remove invalid characters)
        output_name = "".join(c for c in output_name if c.isalnum() or c in "-_")
        if not output_name:
            output_name = "app"
        
        logger.info(f"Output name: {output_name}")
        
        # Platform specific output naming
        if sys.platform == "win32":
            output_exe = f"{output_name}.exe"
        elif sys.platform == "darwin":
            output_exe = f"{output_name}.app"
        else:
            output_exe = output_name
            
        cmd = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            "--onefile",
            "--remove-output",
            "--assume-yes-for-downloads",
            "--lto=no",  # Disable Link-Time Optimization (much faster builds)
            "--disable-ccache",  # Avoid ccache issues in CI
            # "--show-progress", # Disabled to reduce CI log spam
        ]
        
        # Add macOS specific flags
        if sys.platform == "darwin":
            cmd.append("--macos-create-app-bundle")
            # For app bundle, --onefile might not be compatible or needed in the same way, 
            # but Nuitka supports both. If using bundle, output is a directory.
            # However, previous workflow used both.
        
        cmd.extend([
            f"--output-filename={output_exe}",
            f"--output-dir={self.output_dir}"
        ])
        
        # Parallel jobs
        cpu_count = multiprocessing.cpu_count()
        cmd.append(f"--jobs={cpu_count}")
        logger.info(f"Using {cpu_count} CPU cores")
        
        # Turbo Mode Blacklist
        # Standard blacklist + aggressive optimizations
        blacklist = [
            "test", "unittest", "pytest", "pdb", "doctest", "trace", "pyclbr", "pstats", "profile", "cProfile",
            "imaplib", "poplib", "smtplib", "nntplib", "ftplib", "telnetlib",
            "cgi", "cgitb", "wsgiref", "http.server", "xmlrpc", "pydoc", "webbrowser", "turtle", "turtledemo",
            "idlelib", "tkinter", "curses",
            # Heavy libraries that cause Nuitka recursion issues - compiled as bytecode instead
            "sqlalchemy", "pandas", "numpy", "scipy", "PIL", "matplotlib", "certifi"
        ]
        
        compatibility_mode = self.config.get("compatibility_mode", False)
        
        if not compatibility_mode:
            logger.info("⚡ TURBO MODE ENABLED")
            turbo_exclusions = [
                "encodings.cp1006", "encodings.cp1026", "encodings.cp1125", "encodings.cp1140",
                "lzma", "bz2", "calendar", "sched"
            ]
            blacklist.extend(turbo_exclusions)
            cmd.append("--disable-plugins=anti-bloat")
        else:
            logger.info("Using Compatibility Mode (Standard optimizations)")
            cmd.append("--enable-plugin=anti-bloat")
            
        for module in blacklist:
            cmd.append(f"--nofollow-import-to={module}")
            
        # NOTE: Removed --enable-plugin=tk-inter as it significantly slows builds
        # The wrapper code has fallback for when tkinter is not available
        # Only add it if the project actually imports tkinter
        if self._uses_tkinter():
            logger.info("Project uses tkinter, enabling tk-inter plugin")
            cmd.append("--enable-plugin=tk-inter")
        else:
            logger.info("Skipping tk-inter plugin (not used by project)")
        
        # Add entry file
        cmd.append(str(self.source_dir / entry_file))
        
        logger.info("Starting Nuitka compilation...")
        logger.info(f"Entry file: {entry_file}")
        logger.info(f"Output file: {output_exe}")
        logger.info(f"Output dir: {self.output_dir}")
        
        # Log the full command for debugging
        logger.info(f"Nuitka command (first 500 chars): {' '.join(cmd)[:500]}...")
        
        subprocess.check_call(cmd, stdout=sys.stdout, stderr=sys.stderr)
        
        final_path = self.output_dir / output_exe
        if not final_path.exists():
             # Search recursive if Nuitka moved it
             found = list(self.output_dir.rglob(output_exe))
             if found:
                 final_path = found[0]
             else:
                 # Fallback for macOS: checking if it produced a binary instead of .app
                 if sys.platform == "darwin":
                     fallback = self.output_dir / output_name
                     if fallback.exists():
                         final_path = fallback
                     else:
                         raise FileNotFoundError("Output executable not found")
                 else:
                     raise FileNotFoundError("Output executable not found")
                 
        logger.info(f"Build complete: {final_path}")
        return final_path

def main():
    parser = argparse.ArgumentParser(description="CodeVault Cloud Runner")
    parser.add_argument("--config", required=True, help="JSON config string")
    parser.add_argument("--source", required=True, help="Source directory")
    args = parser.parse_args()
    
    try:
        config = json.loads(args.config)
        source_dir = Path(args.source).resolve()
        output_dir = source_dir / "build_output"
        output_dir.mkdir(exist_ok=True)
        
        runner = CloudRunner(source_dir, output_dir, config)
        exe_path = runner.run()
        
        # Output result for GH Actions (using new GITHUB_OUTPUT environment variable)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"exe_path={exe_path}\n")
        else:
            # Fallback for local testing
            print(f"::set-output name=exe_path::{exe_path}")
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
