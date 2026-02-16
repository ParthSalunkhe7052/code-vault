import os
import sys
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable

from .base import BaseCompiler
from cli.terminal import Colors
from cli.compiler_logic import (
    validate_entry_file, 
    validate_output_name, 
    validate_include_package,
    parse_nuitka_percent,
    parse_nuitka_phase
)

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
        from cli.codevault_cli.utils.health import check_nuitka
        success, _, _ = await check_nuitka()
        return success

    async def inject_wrapper(self) -> bool:
        """Inject license protection."""
        from cli.compiler_logic import inject_license_wrapper
        return inject_license_wrapper(self.project_dir, self.config)

    async def compile(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, Optional[Path]]:
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
            if progress_callback: progress_callback(0, f"Error: {e}")
            return False, None

        cpu_count = os.cpu_count() or 4
        max_jobs = min(cpu_count, 16)

        cmd = [
            sys.executable, "-m", "nuitka", 
            "--standalone", "--lto=no", "--remove-output", 
            "--assume-yes-for-downloads", "--no-prefer-source-code"
        ]
        
        for module in PYTHON_BLACKLIST:
            cmd.append(f"--nofollow-import-to={module}")
            
        if turbo_mode:
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

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        try:
            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break
                
                line = line_bytes.decode("utf-8", errors="replace").strip()
                percent = parse_nuitka_percent(line)
                
                if percent and progress_callback:
                    phase = parse_nuitka_phase(line)
                    progress_callback(percent, phase)

            await process.wait()
            return process.returncode == 0, self.project_dir
            
        except Exception as e:
            if progress_callback: progress_callback(0, f"Error: {e}")
            if process:
                try: process.kill()
                except: pass
            return False, None
