# ============ LICENSE WRAPPER TEMPLATE - DO NOT EDIT DIRECTLY ============
# Unified template for CodeVault license protection
# Uses $PLACEHOLDER format for string.Template substitution
# =========================================================================

UNIFIED_PYTHON_WRAPPER = r'''# ============ LICENSE WRAPPER - DO NOT REMOVE ============
import sys as _$PREFIX_sys
import os as _$PREFIX_os
import hashlib as _$PREFIX_hash
import json as _$PREFIX_json
import time as _$PREFIX_time
import platform as _$PREFIX_platform
import base64 as _$PREFIX_base64
import re as _$PREFIX_re
import hmac as _$PREFIX_hmac

# ============ CONFIGURATION PLACEHOLDERS (filled during build) ============
_$PREFIX_LICENSE_KEY = "$LICENSE_KEY"
_$PREFIX_PRODUCT_ID = "$PRODUCT_ID"
_$PREFIX_HWID_ENABLED = $HWID_ENABLED
_$PREFIX_LEASE_ENABLED = $LEASE_ENABLED
_$PREFIX_SECRET_KEY = b"$SECRET_KEY"
_$PREFIX_API_BASE = "$API_BASE"
_$PREFIX_FUNC_PREFIX = "$FUNC_PREFIX"

# Constants
_$PREFIX_LEASE_DURATION = 24 * 60 * 60  # 24 hours
_$PREFIX_CLOCK_DRIFT_MAX = 60 * 60  # 1 hour
_$PREFIX_VERSION = "2.0.0"

def _$PREFIX_show_error(title, message, details=None):
    """Show error with formatting."""
    print("\n" + "=" * 60)
    print(f"  ❌ {title}")
    print("=" * 60)
    print(f"\n{message}")
    if details:
        print(f"\nDetails: {details}")
    print("\n" + "-" * 60)
    print("TROUBLESHOOTING:")
    print("-" * 60)
    if "LICENSE INVALID" in title:
        print("• Check that license.key file exists next to executable")
        print("• Verify your license key is valid and not expired")
        print("• Contact support if you believe this is an error")
    elif "HWID MISMATCH" in title:
        print("• This license is tied to a specific machine")
        print("• Contact support to transfer license to new machine")
    elif "OFFLINE LEASE" in title:
        print("• System time may be incorrect - check system clock")
        print("• Connect to internet at least once every 24 hours")
        print("• Delete license.key to force re-validation")
    else:
        print("• Check your internet connection")
        print("• Verify firewall allows the application")
        print("• Try running as administrator")
    print("=" * 60)
    _$PREFIX_sys.exit(1)

def _$PREFIX_xor_decrypt(data, key):
    """XOR decrypt data using rotating key."""
    result = bytearray()
    key_len = len(key)
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % key_len])
    return bytes(result)

def _$PREFIX_verify_signature(data, signature, secret):
    """Verify HMAC signature."""
    try:
        expected = _$PREFIX_hmac.new(secret, data.encode(), _$PREFIX_hash.sha256).hexdigest()
        return _$PREFIX_hmac.compare_digest(signature.lower(), expected.lower())
    except Exception:
        return False

def _$PREFIX_get_hwid():
    """Generate hardware ID."""
    try:
        import uuid as _$PREFIX_uuid
        mac = ":".join(_$PREFIX_re.findall("..", "%012x" % _$PREFIX_uuid.getnode()))
        info = f"{_$PREFIX_platform.node()}|{_$PREFIX_platform.machine()}|{_$PREFIX_platform.processor()}|{mac}"
        return _$PREFIX_hash.sha256(info.encode()).hexdigest()[:32]
    except Exception as e:
        print(f"[License] Warning: Could not generate HWID: {e}")
        try:
            info = f"{_$PREFIX_platform.node()}|{_$PREFIX_platform.machine()}|{_$PREFIX_platform.processor()}"
            return _$PREFIX_hash.sha256(info.encode()).hexdigest()[:32]
        except Exception:
            return "unknown-hwid"

def _$PREFIX_get_license_key_path():
    """Get path to license.key file."""
    try:
        if getattr(_$PREFIX_sys, 'frozen', False):
            exe_dir = _$PREFIX_os.path.dirname(_$PREFIX_sys.executable)
        else:
            exe_dir = _$PREFIX_os.path.dirname(_$PREFIX_os.path.abspath(__file__))
        return _$PREFIX_os.path.join(exe_dir, "license.key")
    except Exception:
        return "license.key"

def _$PREFIX_load_license_file():
    """Load and decrypt license file."""
    try:
        key_path = _$PREFIX_get_license_key_path()
        if not _$PREFIX_os.path.exists(key_path):
            return None
        with open(key_path, 'rb') as f:
            encrypted = f.read()
        decrypted = _$PREFIX_xor_decrypt(encrypted, _$PREFIX_SECRET_KEY)
        return _$PREFIX_json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        print(f"[License] Failed to load license file: {e}")
        return None

def _$PREFIX_save_license_file(data):
    """Encrypt and save license file."""
    try:
        key_path = _$PREFIX_get_license_key_path()
        json_str = _$PREFIX_json.dumps(data)
        encrypted = _$PREFIX_xor_decrypt(json_str.encode('utf-8'), _$PREFIX_SECRET_KEY)
        with open(key_path, 'wb') as f:
            f.write(encrypted)
        return True
    except Exception as e:
        print(f"[License] Failed to save license file: {e}")
        return False

def _$PREFIX_validate_online(license_key, hwid):
    """Validate license online."""
    try:
        import urllib.request as _$PREFIX_req
        import urllib.error as _$PREFIX_err
        
        validation_data = {
            "license_key": license_key,
            "hwid": hwid,
            "product_id": _$PREFIX_PRODUCT_ID,
            "version": _$PREFIX_VERSION
        }
        
        req = _$PREFIX_req.Request(
            f"{_$PREFIX_API_BASE}/validate",
            data=_$PREFIX_json.dumps(validation_data).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with _$PREFIX_req.urlopen(req, timeout=30) as resp:
            result = _$PREFIX_json.loads(resp.read().decode('utf-8'))
            return result
    except Exception as e:
        return {"valid": False, "error": str(e)}

def _$PREFIX_validate_offline(license_data, hwid):
    """Validate license offline using lease."""
    if not _$PREFIX_LEASE_ENABLED:
        return {"valid": False, "error": "Offline validation not enabled"}
    
    if not license_data:
        return {"valid": False, "error": "No license data"}
    
    # Check license key
    if license_data.get("key") != _$PREFIX_LICENSE_KEY:
        return {"valid": False, "error": "License key mismatch"}
    
    # Check HWID if enabled
    if _$PREFIX_HWID_ENABLED:
        stored_hwid = license_data.get("hwid")
        if stored_hwid and stored_hwid != hwid:
            return {"valid": False, "error": "HWID mismatch"}
    
    # Check lease expiry
    lease_until = license_data.get("lease_until", 0)
    current_time = int(_$PREFIX_time.time())
    
    # Allow clock drift
    if current_time > lease_until + _$PREFIX_CLOCK_DRIFT_MAX:
        return {"valid": False, "error": f"Offline lease expired. Connect to internet to renew."}
    
    return {"valid": True, "offline": True}

def _$PREFIX_prompt_license_gui():
    """Prompt for license using GUI dialog."""
    try:
        if _$PREFIX_platform.system() == "Windows":
            import tkinter as _$PREFIX_tk
            from tkinter import simpledialog, messagebox
            
            root = _$PREFIX_tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            messagebox.showinfo(
                "License Required",
                "Please enter your license key to continue.\n\n"
                "Contact support@codevault.io if you need assistance."
            )
            
            license_key = simpledialog.askstring(
                "Enter License Key",
                "License Key:",
                parent=root
            )
            
            root.destroy()
            return license_key
        else:
            # Linux/Mac - use zenity or console
            try:
                import subprocess as _$PREFIX_sub
                result = _$PREFIX_sub.run(
                    ["zenity", "--entry", "--title=License Required", 
                     "--text=Enter your license key:"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
            # Fallback to console
            return input("Enter license key: ").strip()
    except Exception as e:
        print(f"[License] GUI prompt failed: {e}")
        return input("Enter license key: ").strip()

def _$PREFIX_main():
    """Main license validation flow."""
    print(f"[License] License Wrapper v{_$PREFIX_VERSION}")
    print(f"[License] Product: {_$PREFIX_PRODUCT_ID}")
    
    hwid = _$PREFIX_get_hwid()
    print(f"[License] HWID: {hwid}")
    
    # Load existing license
    license_data = _$PREFIX_load_license_file()
    
    # Try offline validation first
    if license_data:
        result = _$PREFIX_validate_offline(license_data, hwid)
        if result["valid"]:
            print("[License] ✓ Valid (offline)")
            return
    
    # Need online validation
    print("[License] Validating online...")
    
    license_key = _$PREFIX_LICENSE_KEY
    if license_key == "GENERIC_BUILD" or not license_key:
        license_key = _$PREFIX_prompt_license_gui()
    
    if not license_key:
        _$PREFIX_show_error("LICENSE REQUIRED", "No license key provided.")
    
    result = _$PREFIX_validate_online(license_key, hwid)
    
    if not result.get("valid"):
        error_msg = result.get("error", "Unknown error")
        _$PREFIX_show_error("LICENSE INVALID", f"Validation failed: {error_msg}")
    
    # Save validated license
    if _$PREFIX_LEASE_ENABLED:
        lease_until = int(_$PREFIX_time.time()) + _$PREFIX_LEASE_DURATION
        new_license_data = {
            "key": license_key,
            "hwid": hwid if _$PREFIX_HWID_ENABLED else None,
            "validated_at": int(_$PREFIX_time.time()),
            "lease_until": lease_until,
            "product_id": _$PREFIX_PRODUCT_ID
        }
        _$PREFIX_save_license_file(new_license_data)
        print(f"[License] ✓ Valid (online, lease until {_$PREFIX_time.ctime(lease_until)})")
    else:
        print("[License] ✓ Valid (online)")

# Run license check before user code
_$PREFIX_main()

# ============ USER APPLICATION CODE BELOW ============
'''
