"""HWID generation utilities for CodeVault."""

import hashlib
import platform
import re
import uuid
from typing import List


def generate_hwid() -> str:
    """
    Generate multi-factor hardware ID for license validation.

    Uses MAC address, disk serial, CPU ID, and motherboard serial.
    Gracefully falls back if any factor fails.

    Returns:
        32-character hex string HWID
    """
    components: List[str] = []

    try:
        mac = ":".join(re.findall("..", "%012x" % uuid.getnode()))
        components.append(f"mac:{mac}")
    except Exception:
        pass

    if platform.system() == "Windows":
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

        try:
            import subprocess

            result = subprocess.run(
                ["wmic", "baseboard", "get", "serialnumber"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                mb_serial = lines[1].strip()
                if mb_serial and mb_serial != "SerialNumber":
                    components.append(f"mb:{mb_serial}")
        except Exception:
            pass

    try:
        cpu_id = platform.processor()
        if cpu_id:
            components.append(f"cpu:{cpu_id[:32]}")
    except Exception:
        pass

    if components:
        return hashlib.sha256("|".join(components).encode()).hexdigest()[:32]

    try:
        info = f"{platform.node()}|{platform.system()}|{platform.machine()}"
        return hashlib.sha256(info.encode()).hexdigest()[:32]
    except Exception:
        return "unknown-hwid"
