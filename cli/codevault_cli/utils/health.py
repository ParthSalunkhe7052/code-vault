import asyncio
import sys
import shutil
import subprocess
from typing import Dict, Any, Tuple, Optional

async def check_nuitka() -> Tuple[bool, str, Optional[str]]:
    """
    Check for Nuitka and a compatible C++ compiler.
    Returns: (success, version_info, error_message)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "nuitka", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
        output = stdout.decode("utf-8", errors="replace")
        
        if process.returncode == 0:
            version = output.strip().split("
")[0]
            # Check for compiler in output
            has_compiler = "gcc" in output.lower() or "msvc" in output.lower() or "clang" in output.lower()
            if not has_compiler:
                return True, version, "Nuitka installed but no C++ compiler detected. Install MinGW-w64 or MSVC."
            return True, version, None
        else:
            return False, "Not working", "Nuitka returned error code. Try: pip install --upgrade nuitka"
    except asyncio.TimeoutError:
        return False, "Timeout", "Nuitka check timed out."
    except Exception as e:
        return False, "Not found", f"Nuitka not installed. Run: {sys.executable} -m pip install nuitka"

async def check_node() -> Tuple[bool, str, Optional[str]]:
    """
    Check for Node.js and npx availability.
    Returns: (success, version_info, error_message)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "node", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
        if process.returncode == 0:
            version = stdout.decode("utf-8").strip()
            # Check for npx
            npx_path = shutil.which("npx") or shutil.which("npx.cmd")
            if not npx_path:
                return True, version, "Node.js installed but 'npx' not found. Check your PATH."
            return True, version, None
        else:
            return False, "Not working", "Node.js returned error code."
    except Exception:
        return False, "Not found", "Node.js not installed. Download from https://nodejs.org/"

async def check_auth() -> Tuple[bool, str]:
    """Check if the user is authenticated."""
    try:
        # Avoid circular imports by importing here
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        from cli_config import load_config
        config = load_config()
        if config.get("api_key"):
            return True, f"Authenticated as {config.get('email', 'Unknown')}"
        return False, "Not authenticated. Run 'codevault auth login'"
    except Exception as e:
        return False, f"Configuration error: {e}"
