"""HWID generation utilities for CodeVault."""

import hashlib
import platform
import re
import uuid
from typing import List


def generate_hwid() -> str:
    """
    Generate multi-factor hardware ID for license validation.

    Uses MAC address, CPU model, and Windows disk serial.
    Gracefully falls back if any factor fails.

    Returns:
        32-character hex string HWID
    """
    components: List[str] = []

    # 1. MAC Address - Unify by picking the smallest non-zero MAC found
    try:
        if platform.system() == "Windows":
            import subprocess
            output = subprocess.check_output("ipconfig /all", text=True, timeout=5)
            all_macs = re.findall(r"Physical Address[. ]+: ([\w-]+)", output)
            # Standardize MAC format to XX:XX:XX:XX:XX:XX
            formatted_macs = [m.replace("-", ":").lower() for m in all_macs if m and m != "00-00-00-00-00-00"]
            if formatted_macs:
                components.append(f"mac:{sorted(formatted_macs)[0]}")
        else:
            # Unix fallback
            mac = ":".join(re.findall("..", "%012x" % uuid.getnode()))
            if mac and mac != "00:00:00:00:00:00":
                components.append(f"mac:{mac.lower()}")
    except Exception:
        pass

    # 2. CPU Model - Unify with Node.js using Registry on Windows
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_model, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if cpu_model:
                components.append(f"cpu:{cpu_model.strip()[:32]}")
        except Exception:
            pass
            
        # 3. Disk Serial - Continue using wmic but with silent failure
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "serialnumber"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                disk_serial = lines[1].strip()
                if disk_serial and disk_serial != "SerialNumber":
                    components.append(f"disk:{disk_serial}")
        except Exception:
            pass
    else:
        # Non-Windows fallbacks
        try:
            cpu_id = platform.processor()
            if cpu_id:
                components.append(f"cpu:{cpu_id[:32]}")
        except Exception:
            pass

    if components:
        # Join with | and hash to 32-char hex string (first 32 chars of SHA256)
        return hashlib.sha256("|".join(components).encode()).hexdigest()[:32]

    try:
        # Final fallback
        info = f"{platform.node()}|{platform.system()}|{platform.machine()}"
        return hashlib.sha256(info.encode()).hexdigest()[:32]
    except Exception:
        return "unknown-hwid"
