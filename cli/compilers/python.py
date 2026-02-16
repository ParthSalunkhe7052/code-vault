import os
import sys
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .base import BaseCompiler
from cli.terminal import Colors, print_progress_bar
from cli.compiler_logic import (
    validate_entry_file, 
    validate_output_name, 
    validate_include_package,
    detect_heavy_dependencies,
    parse_nuitka_percent,
    parse_nuitka_phase
)
from cli.compiler_constants import COMPILE_TIMEOUT

# Modules that are rarely needed in standalone protected binaries
PYTHON_BLACKLIST = [
    "test", "unittest", "pytest", "pdb", "doctest", "trace", "pyclbr", "pstats", "profile", "cProfile",
    "imaplib", "poplib", "smtplib", "nntplib", "ftplib", "telnetlib",
    "cgi", "cgitb", "wsgiref", "http.server",
    "xmlrpc", "xmlrpc.client", "xmlrpc.server",
    "pydoc", "webbrowser", "turtle", "turtledemo", "idlelib", "tkinter", "curses"
]

# Heavy encodings and miscellaneous modules excluded in Turbo Mode
PYTHON_TURBO_EXCLUSIONS = [
    "encodings.cp1006", "encodings.cp1026", "encodings.cp1125", "encodings.cp1140", "encodings.cp273",
    "encodings.cp424", "encodings.cp500", "encodings.cp720", "encodings.cp737", "encodings.cp775",
    "encodings.cp856", "encodings.cp857", "encodings.cp858", "encodings.cp860", "encodings.cp861",
    "encodings.cp862", "encodings.cp863", "encodings.cp864", "encodings.cp865", "encodings.cp866",
    "encodings.cp869", "encodings.cp874", "encodings.cp875", "encodings.iso2022_jp", "encodings.iso2022_kr",
    "encodings.johab", "encodings.koi8_r", "encodings.koi8_t", "encodings.koi8_u", "encodings.mac_arabic",
    "encodings.mac_croatian", "encodings.mac_cyrillic", "encodings.mac_farsi", "encodings.mac_greek",
    "encodings.mac_iceland", "encodings.mac_latin2", "encodings.mac_roman", "encodings.mac_romanian",
    "encodings.mac_turkish", "encodings.palmos", "encodings.ptcp154",
    "lzma", "bz2", "calendar", "sched"
]

class PythonCompiler(BaseCompiler):
    """
    Python compiler using Nuitka.
    Modernized with asyncio, modular logic, and Turbo Mode optimizations.
    """
    
    async def pre_flight(self) -> bool:
        """Verify Nuitka is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "nuitka", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def inject_wrapper(self) -> bool:
        """Inject license protection."""
        from cli.compiler_logic import inject_license_wrapper
        return inject_license_wrapper(self.project_dir, self.config)

    async def compile(self) -> Tuple[bool, Optional[Path]]:
        """
        Run Nuitka compilation asynchronously with Turbo Mode optimizations.
        """
        entry_file = self.config.get("entry_file", "")
        output_name = self.config.get("output_name") or self.config.get("project_name") or "output"
        nuitka_opts = self.config.get("nuitka_options", {})
        fast_build = self.config.get("fast_build", False)
        turbo_mode = self.config.get("turbo_mode", True)

        try:
            entry_path = validate_entry_file(entry_file, self.project_dir)
            output_name = validate_output_name(output_name)
        except Exception as e:
            print(f"[ERROR] Security violation: {e}")
            return False, None

        cpu_count = os.cpu_count() or 4
        max_jobs = min(cpu_count, 16) # Use more cores if available

        cmd = [
            sys.executable, "-m", "nuitka", 
            "--standalone", "--lto=no", "--remove-output", 
            "--assume-yes-for-downloads", "--no-prefer-source-code"
        ]
        
        # Apply standard blacklist
        for module in PYTHON_BLACKLIST:
            cmd.append(f"--nofollow-import-to={module}")
            
        # Apply Turbo Mode exclusions
        if turbo_mode:
            print(f"{Colors.CYAN}[TURBO]{Colors.RESET} Aggressive optimizations enabled")
            for module in PYTHON_TURBO_EXCLUSIONS:
                cmd.append(f"--nofollow-import-to={module}")
            cmd.append("--disable-plugins=anti-bloat")

        if fast_build:
            cmd.extend([f"--jobs={max_jobs}", f"--output-dir={self.project_dir / 'build'}"])
        else:
            cmd.extend(["--onefile", f"--jobs={max_jobs}", f"--output-filename={output_name}.exe"])

        for pkg in nuitka_opts.get("include_packages", []):
            module_name = validate_include_package(pkg)
            if module_name:
                cmd.append(f"--include-package={module_name}")

        cmd.append(str(entry_path))

        print(f"[PythonCompiler] Starting optimized build: {entry_path.name}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        start_time = time.time()
        last_percent = 0
        last_phase = "starting"

        try:
            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break
                
                line = line_bytes.decode("utf-8", errors="replace").strip()
                percent = parse_nuitka_percent(line)
                
                if percent:
                    last_percent = percent
                    last_phase = parse_nuitka_phase(line)
                    elapsed = int(time.time() - start_time)
                    mins, secs = divmod(elapsed, 60)
                    print_progress_bar(percent, width=30, phase=last_phase, elapsed_time=f"{mins}m{secs}s")

                if "error" in line.lower() and "no errors" not in line.lower():
                    print(f"\n[ERROR] {line}")

            await process.wait()
            return process.returncode == 0, self.project_dir
            
        except Exception as e:
            print(f"\n[ERROR] Compilation error: {e}")
            if process:
                try:
                    process.kill()
                except:
                    pass
            return False, None
