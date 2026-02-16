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

class PythonCompiler(BaseCompiler):
    """
    Python compiler using Nuitka.
    Modernized with asyncio and modular logic.
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
        """
        Delegates wrapper injection to existing legacy function for now.
        TODO: Modernize injection logic in t3.
        """
        from cli.compiler_logic import inject_license_wrapper
        return inject_license_wrapper(self.project_dir, self.config)

    async def compile(self) -> Tuple[bool, Optional[Path]]:
        """
        Run Nuitka compilation asynchronously.
        """
        entry_file = self.config.get("entry_file", "")
        output_name = self.config.get("output_name") or self.config.get("project_name") or "output"
        nuitka_opts = self.config.get("nuitka_options", {})
        fast_build = self.config.get("fast_build", False)

        try:
            entry_path = validate_entry_file(entry_file, self.project_dir)
            output_name = validate_output_name(output_name)
        except Exception as e:
            print(f"[ERROR] Security violation: {e}")
            return False, None

        cpu_count = os.cpu_count() or 4
        max_jobs = min(cpu_count, 8)

        cmd = [sys.executable, "-m", "nuitka", "--standalone", "--lto=no", "--remove-output", "--assume-yes-for-downloads"]
        
        if fast_build:
            cmd.extend([f"--jobs={max_jobs}", f"--output-dir={self.project_dir / 'build'}"])
        else:
            cmd.extend(["--onefile", f"--jobs={max_jobs}", f"--output-filename={output_name}.exe"])

        for pkg in nuitka_opts.get("include_packages", []):
            module_name = validate_include_package(pkg)
            if module_name:
                cmd.append(f"--include-package={module_name}")

        cmd.append(str(entry_path))

        print(f"[PythonCompiler] Starting async compilation: {entry_path.name}")
        
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
                    print(f"
[ERROR] {line}")

            await process.wait()
            return process.returncode == 0, self.project_dir
            
        except Exception as e:
            print(f"
[ERROR] Compilation error: {e}")
            if process:
                try:
                    process.kill()
                except:
                    pass
            return False, None
