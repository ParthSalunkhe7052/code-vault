"""
Python Compiler for CodeVault.
Compiles Python projects with license protection using Nuitka.

This module mirrors NodeJSCompiler and provides:
- Runtime license validation (not embedded keys)
- Proper exe output for NSIS builder integration
- Support for generic, demo, and fixed license modes
"""

import asyncio
import os
import shutil
import sys
import tempfile
import logging
import multiprocessing
from pathlib import Path
from typing import Optional, Callable
import re

logger = logging.getLogger(__name__)


class PythonCompiler:
    """
    Compiles Python projects using Nuitka with runtime license validation.

    Flow:
    1. Copy source to temp directory
    2. Inject license wrapper (runtime prompt, NOT embedded)
    3. Run Nuitka to create standalone exe
    4. Return exe path for NSIS builder

    This mirrors the NodeJSCompiler approach for consistency.
    """

    async def log(self, message: str, callback: Optional[Callable] = None):
        """Log message and call callback if provided"""
        logger.info(f"[PythonCompiler] {message}")
        print(f"[PythonCompiler] {message}", flush=True)
        if callback:
            await callback(message)

    async def compile(
        self,
        source_dir: Path,
        entry_file: str,
        output_dir: Path,
        output_name: str,
        license_key: str,
        api_url: str,
        options: dict,
        log_callback: Optional[Callable] = None,
    ) -> Path:
        """
        Compile Python project with license protection.

        Args:
            source_dir: Path to project source directory
            entry_file: Relative path to entry file (e.g., "main.py")
            output_dir: Directory for final output
            output_name: Base name for output exe
            license_key: License key (or "GENERIC_BUILD" for runtime prompt)
            api_url: License validation API URL
            options: Additional compiler options
            log_callback: Async callback for log messages

        Returns:
            Path to compiled executable
        """
        # Step 1: Create temp build directory
        build_dir = Path(tempfile.mkdtemp(prefix="cv_python_"))
        await self.log(f"Build directory: {build_dir}", log_callback)

        try:
            # Step 2: Copy source files
            await self.log("Copying source files...", log_callback)
            src_copy = build_dir / "src"

            # Copy while ignoring common unnecessary files
            shutil.copytree(
                source_dir,
                src_copy,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    ".git",
                    "*.pyc",
                    ".venv",
                    "venv",
                    ".env",
                    "node_modules",
                    "*.egg-info",
                    ".mypy_cache",
                    ".pytest_cache",
                ),
            )

            # Step 3: Inject license wrapper
            await self.log("Injecting license protection...", log_callback)
            entry_path = src_copy / entry_file

            if not entry_path.exists():
                raise FileNotFoundError(f"Entry file not found: {entry_file}")

            self._inject_license_wrapper(entry_path, license_key, api_url)

            # Step 4: Run Nuitka
            await self.log("Running Nuitka compilation...", log_callback)
            exe_path = await self._run_nuitka(
                src_copy, entry_file, output_dir, output_name, options, log_callback
            )

            await self.log(f"✓ Compilation complete: {exe_path.name}", log_callback)
            return exe_path

        except Exception as e:
            await self.log(f"✗ Compilation failed: {e}", log_callback)
            raise
        finally:
            # Cleanup
            try:
                shutil.rmtree(build_dir, ignore_errors=True)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup build dir: {cleanup_error}")

    def _inject_license_wrapper(self, entry_path: Path, license_key: str, api_url: str):
        """
        Inject license validation wrapper at the top of the entry file.

        For 'GENERIC_BUILD', prompts user for license at runtime.
        For fixed keys, validates the embedded key.
        """
        original_code = entry_path.read_text(encoding="utf-8")

        if license_key in ("GENERIC_BUILD", "generic", None, ""):
            # Runtime prompt - don't embed any key
            wrapper = self._get_generic_wrapper(api_url)
        elif license_key == "demo":
            # Demo mode - limited functionality
            wrapper = self._get_demo_wrapper()
        else:
            # Fixed license mode - embed the key
            wrapper = self._get_fixed_wrapper(license_key, api_url)

        # Write wrapper + original code
        entry_path.write_text(wrapper + "\n\n" + original_code, encoding="utf-8")

    def _get_generic_wrapper(self, api_url: str) -> str:
        """Generate wrapper that prompts for license at runtime."""
        # Using string formatting to avoid issues with braces
        return f'''# === CodeVault License Protection (Generic Mode) ===
import os as _cv_os
import sys as _cv_sys
import hashlib as _cv_hashlib
import platform as _cv_platform
import json as _cv_json
import secrets as _cv_secrets
import time as _cv_time
from urllib.request import Request as _cv_Request, urlopen as _cv_urlopen
from urllib.error import URLError as _cv_URLError

def _cv_get_hwid():
    """Generate hardware ID for license validation."""
    info = f"{{_cv_platform.node()}}|{{_cv_platform.system()}}|{{_cv_platform.machine()}}|{{_cv_platform.processor()}}"
    return _cv_hashlib.sha256(info.encode()).hexdigest()

def _cv_validate_license(key, hwid, api_url):
    """Validate license key with the server."""
    print(f"[CodeVault] Validating license with server...")
    print(f"[CodeVault] DEBUG: API URL = {{api_url}}")
    timestamp = int(_cv_time.time())
    nonce = _cv_secrets.token_hex(16)
    data = _cv_json.dumps({{
        "license_key": key, 
        "hwid": hwid, 
        "machine_name": _cv_platform.node(),
        "timestamp": timestamp,
        "nonce": nonce
    }}).encode()

    req = _cv_Request(api_url, data=data, headers={{"Content-Type": "application/json"}})
    try:
        with _cv_urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            print(f"[CodeVault] DEBUG: Server response = {{body[:200]}}")
            result = _cv_json.loads(body)
            return result.get("status") == "valid"
    except _cv_URLError as e:
        print(f"[CodeVault] Connection error: {{e}}")
        if hasattr(e, 'read'):
            print(f"[CodeVault] DEBUG: Response body = {{e.read().decode()[:500]}}")
        return False
    except Exception as e:
        print(f"[CodeVault] Validation error: {{type(e).__name__}}: {{e}}")
        return False

def _cv_license_check():
    """Main license validation entry point."""
    key_file = _cv_os.path.join(_cv_os.path.expanduser("~"), ".codevault_license")
    api_url = "{api_url}"
    hwid = _cv_get_hwid()
    print(f"[CodeVault] DEBUG: License file path = {{key_file}}")

    # Try saved key first
    if _cv_os.path.exists(key_file):
        try:
            with open(key_file, "r") as f:
                saved_key = f.read().strip()
                print(f"[CodeVault] Found saved license, validating...")
                if saved_key and _cv_validate_license(saved_key, hwid, api_url):
                    print("[CodeVault] License verified!")
                    return True
                else:
                    print("[CodeVault] Saved license is invalid or expired.")
        except Exception as ex:
            print(f"[CodeVault] Error reading saved license: {{ex}}")

    # Prompt for key
    print("=" * 50)
    print("  License Required")
    print("=" * 50)
    print()

    try:
        key = input("Enter license key: ").strip()
    except EOFError:
        print("[CodeVault] No input available - cannot prompt for license")
        input("Press Enter to exit...")
        _cv_sys.exit(1)

    if not key:
        print("[CodeVault] No license key entered")
        input("Press Enter to exit...")
        _cv_sys.exit(1)

    if _cv_validate_license(key, hwid, api_url):
        # Save for next time
        try:
            with open(key_file, "w") as f:
                f.write(key)
            print(f"[CodeVault] License saved to {{key_file}}")
        except Exception as ex:
            print(f"[CodeVault] Warning: Could not save license: {{ex}}")
        print("[CodeVault] ✓ License activated!")
        print()
        return True
    else:
        print("[CodeVault] ✗ Invalid license key")
        input("Press Enter to exit...")
        _cv_sys.exit(1)

# Run license check on startup
_cv_license_check()
# === End CodeVault License Protection ===
'''

    def _get_demo_wrapper(self) -> str:
        """Generate wrapper for demo mode with time limit."""
        return '''# === CodeVault License Protection (Demo Mode) ===
import time as _cv_time

_CV_DEMO_START = _cv_time.time()
_CV_DEMO_DURATION = 60 * 60  # 1 hour demo

print("[CodeVault] Running in DEMO mode (1 hour limit)")

def _cv_check_demo_expired():
    """Check if demo has expired."""
    elapsed = _cv_time.time() - _CV_DEMO_START
    if elapsed > _CV_DEMO_DURATION:
        print("[CodeVault] Demo period has expired!")
        import sys
        sys.exit(1)

# Check periodically (import this check into your main loop if needed)
_cv_check_demo_expired()
# === End CodeVault License Protection ===
'''

    def _get_fixed_wrapper(self, license_key: str, api_url: str) -> str:
        """Generate wrapper with embedded license key."""
        return f'''# === CodeVault License Protection (Fixed Key) ===
import os as _cv_os
import sys as _cv_sys
import hashlib as _cv_hashlib
import platform as _cv_platform
import json as _cv_json
import secrets as _cv_secrets
import time as _cv_time
from urllib.request import Request as _cv_Request, urlopen as _cv_urlopen
from urllib.error import URLError as _cv_URLError

_CV_LICENSE_KEY = "{license_key}"
_CV_API_URL = "{api_url}"

def _cv_get_hwid():
    info = f"{{_cv_platform.node()}}|{{_cv_platform.system()}}|{{_cv_platform.machine()}}|{{_cv_platform.processor()}}"
    return _cv_hashlib.sha256(info.encode()).hexdigest()

def _cv_validate():
    print(f"[CodeVault] Validating embedded license...")
    print(f"[CodeVault] DEBUG: API URL = {{_CV_API_URL}}")
    hwid = _cv_get_hwid()
    timestamp = int(_cv_time.time())
    nonce = _cv_secrets.token_hex(16)
    
    data = _cv_json.dumps({{
        "license_key": _CV_LICENSE_KEY, 
        "hwid": hwid, 
        "machine_name": _cv_platform.node(),
        "timestamp": timestamp,
        "nonce": nonce
    }}).encode()
    
    req = _cv_Request(_CV_API_URL, data=data, headers={{"Content-Type": "application/json"}})
    try:
        with _cv_urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            print(f"[CodeVault] DEBUG: Server response = {{body[:200]}}")
            result = _cv_json.loads(body)
            if result.get("status") == "valid":
                return True
            else:
                print(f"[CodeVault] Server returned status: {{result.get('status')}}")
    except _cv_URLError as e:
        print(f"[CodeVault] Connection error: {{e}}")
        if hasattr(e, 'read'):
            print(f"[CodeVault] DEBUG: Response body = {{e.read().decode()[:500]}}")
    except Exception as e:
        print(f"[CodeVault] Validation error: {{type(e).__name__}}: {{e}}")
    print("[CodeVault] License validation failed")
    input("Press Enter to exit...")
    _cv_sys.exit(1)

_cv_validate()
print("[CodeVault] License verified!")
# === End CodeVault License Protection ===
'''

    async def _run_nuitka(
        self,
        source_dir: Path,
        entry_file: str,
        output_dir: Path,
        output_name: str,
        options: dict,
        log_callback: Optional[Callable] = None,
    ) -> Path:
        """
        Run Nuitka compilation.

        Args:
            source_dir: Directory containing source files
            entry_file: Entry point file
            output_dir: Output directory for exe
            output_name: Base name for output
            options: Additional Nuitka options
            log_callback: Progress callback

        Returns:
            Path to compiled executable
        """
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build Nuitka command
        output_exe_name = (
            f"{output_name}.exe" if sys.platform == "win32" else output_name
        )
        output_path = output_dir / output_exe_name

        cmd = [
            sys.executable,
            "-m",
            "nuitka",
            "--standalone",
            "--onefile",
            "--remove-output",
            "--assume-yes-for-downloads",
            "--show-progress",  # Enable progress output for better UX
            f"--output-filename={output_exe_name}",
            f"--output-dir={output_dir}",
        ]

        # === PERFORMANCE OPTIMIZATIONS ===
        # Use all available CPU cores for parallel C compilation
        cpu_count = multiprocessing.cpu_count()
        cmd.append(f"--jobs={cpu_count}")
        await self.log(
            f"Using {cpu_count} CPU cores for parallel compilation", log_callback
        )

        # Blacklist: Exclude known-heavy modules that bloat builds
        # These are rarely needed by end-user applications
        blacklist_modules = [
            # Testing/debugging modules
            "test",
            "unittest",
            "pytest",
            "pdb",
            "doctest",
            "trace",
            "pyclbr",
            "pstats",
            "profile",
            "cProfile",
            # Network protocols rarely used in desktop apps
            "imaplib",
            "poplib",
            "smtplib",
            "nntplib",
            "ftplib",
            "telnetlib",
            # CGI/web serving (use requests instead)
            "cgi",
            "cgitb",
            "wsgiref",
            "http.server",
            # XML-RPC (legacy protocol)
            "xmlrpc",
            "xmlrpc.client",
            "xmlrpc.server",
            # Misc unused stdlib
            "pydoc",
            "webbrowser",
            "turtle",
            "turtledemo",
            "idlelib",
            "tkinter",
            "curses",
        ]

        for module in blacklist_modules:
            cmd.append(f"--nofollow-import-to={module}")

        # Turbo Mode: Aggressive optimizations for maximum speed
        turbo_mode = options.get("turbo_mode", False)
        if turbo_mode:
            await self.log(
                "⚡ TURBO MODE enabled - using aggressive optimizations", log_callback
            )
            # Additional exclusions for turbo mode
            turbo_exclusions = [
                # More encoding modules (keep only essential)
                "encodings.cp1006",
                "encodings.cp1026",
                "encodings.cp1125",
                "encodings.cp1140",
                "encodings.cp273",
                "encodings.cp424",
                "encodings.cp500",
                "encodings.cp720",
                "encodings.cp737",
                "encodings.cp775",
                "encodings.cp856",
                "encodings.cp857",
                "encodings.cp858",
                "encodings.cp860",
                "encodings.cp861",
                "encodings.cp862",
                "encodings.cp863",
                "encodings.cp864",
                "encodings.cp865",
                "encodings.cp866",
                "encodings.cp869",
                "encodings.cp874",
                "encodings.cp875",
                "encodings.iso2022_jp",
                "encodings.iso2022_kr",
                "encodings.johab",
                "encodings.koi8_r",
                "encodings.koi8_t",
                "encodings.koi8_u",
                "encodings.mac_arabic",
                "encodings.mac_croatian",
                "encodings.mac_cyrillic",
                "encodings.mac_farsi",
                "encodings.mac_greek",
                "encodings.mac_iceland",
                "encodings.mac_latin2",
                "encodings.mac_roman",
                "encodings.mac_romanian",
                "encodings.mac_turkish",
                "encodings.palmos",
                "encodings.ptcp154",
                # Compression rarely used
                "lzma",
                "bz2",
                # Calendar/time extras
                "calendar",
                "sched",
            ]
            for module in turbo_exclusions:
                cmd.append(f"--nofollow-import-to={module}")

            # Disable anti-bloat plugin for speed (safe for trusted code)
            cmd.append("--disable-plugins=anti-bloat")

        # Add the entry file last
        cmd.append(str(source_dir / entry_file))

        # Add optional flags
        if options.get("console", True):
            pass  # Default is console app
        else:
            cmd.append("--disable-console")

        if options.get("icon"):
            cmd.append(f"--windows-icon-from-ico={options['icon']}")

        await self.log(f"Running: {' '.join(cmd)}", log_callback)

        # Set environment for unbuffered output
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Run Nuitka
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(source_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        # Regex to parse progress percentages from Nuitka output
        # More specific pattern to avoid false matches (e.g., "Downloaded 100%")
        progress_pattern = re.compile(
            r"(?:Nuitka|C compilation|compil\w*).*?(\d+)%", re.IGNORECASE
        )

        # Stream output
        while True:
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=120.0)
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if decoded:
                    # Anti-spam filter for verbose Nuitka logs
                    # Block ALL Nuitka-Progress lines to reduce logs from 2000+ to ~100
                    if "Nuitka-Progress" in decoded:
                        continue
                    if (
                        "Optimizing module" in decoded
                        or "Doing module dependency" in decoded
                        or "Considered used module" in decoded
                    ):
                        continue

                    # Try to extract progress percentage
                    match = progress_pattern.search(decoded)
                    if match:
                        pct = int(match.group(1))
                        # Scale Nuitka's 0-100 to our 20-90 range
                        scaled_progress = 20 + int(pct * 0.7)
                        await self.log(
                            f"  nuitka: {decoded} [progress: {scaled_progress}%]",
                            log_callback,
                        )
                    else:
                        await self.log(f"  nuitka: {decoded}", log_callback)
            except asyncio.TimeoutError:
                if process.returncode is not None:
                    break
                await self.log(
                    "  nuitka: [Still compiling... C compilation can take several minutes]",
                    log_callback,
                )
                continue

        await process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"Nuitka failed with exit code {process.returncode}")

        # Find output exe
        if output_path.exists():
            return output_path

        # Nuitka might put it in a subdirectory - search for it
        for candidate in output_dir.rglob(output_exe_name):
            return candidate

        raise FileNotFoundError(f"Output executable not found: {output_exe_name}")


# Singleton pattern for easy access
_python_compiler: Optional[PythonCompiler] = None


def get_python_compiler() -> PythonCompiler:
    """Get or create the Python compiler singleton."""
    global _python_compiler
    if _python_compiler is None:
        _python_compiler = PythonCompiler()
    return _python_compiler
