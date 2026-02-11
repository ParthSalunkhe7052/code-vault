"""
Simplified build runner with robust error handling and timeout detection.

This runner uses the simple display by default and has special handling
for detecting hangs during initialization phase vs. actual build.
"""

import sys
import os
import re
import json
import time
import shutil
import subprocess
import tempfile
import select
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, Callable
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import compiler logic
from compiler_logic import (
    inject_license_wrapper,
    inject_js_wrapper,
    validate_entry_file,
    validate_output_name,
    PathTraversalError,
    run_nuitka,
    _wait_for_output_with_timeout,
    _readline_from_process,
)
from compiler_constants import COMPILE_TIMEOUT

# Import new components
from codevault_cli.simple_build_display import (
    create_display,
    BuildPhase,
    SimpleBuildDisplay,
)
from codevault_cli.build_logger import create_logger, get_logger


class SimpleBuildRunner:
    """
    Simplified build runner with proper error handling.

    Key improvements:
    - Simple text output by default (no glitches)
    - Timeout only for initialization phase
    - Proper error logging
    - Clean error messages with suggestions
    """

    # Timeouts
    INIT_TIMEOUT = 30  # Seconds - only for pre-flight checks/initialization
    BUILD_TIMEOUT = COMPILE_TIMEOUT  # Seconds - for actual compilation (from constants)
    NO_OUTPUT_TIMEOUT = 600  # Kill compiler if no output for 10min during build

    def __init__(self, display=None, project_name: str = "Unknown"):
        self.display = display
        self.project_name = project_name
        self.logger = get_logger()
        self.start_time = time.time()

    def _log(self, level: str, message: str, context: Optional[Dict] = None):
        """Log message to file."""
        if self.logger:
            if level == "DEBUG":
                self.logger.debug(message, context)
            elif level == "INFO":
                self.logger.info(message, context)
            elif level == "WARN":
                self.logger.warn(message, context)
            elif level == "ERROR":
                self.logger.error(message, context)

        # Also log to display if available
        if self.display and level in ("INFO", "WARN", "ERROR"):
            self.display.log(f"[{level}] {message}")

    def _run_preflight_checks(
        self, project_dir: Path, config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Run pre-flight checks with timeout protection.

        Returns:
            Tuple of (success, error_message)
        """
        self._log("INFO", "Starting pre-flight checks")

        checks_passed = True
        check_results = []

        # Check 1: Python version
        try:
            py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            check_results.append(("Python version", py_version, True))
            self._log("INFO", f"Python version: {py_version}")
        except Exception as e:
            check_results.append(("Python version", str(e), False))
            checks_passed = False
            self._log("ERROR", f"Python version check failed: {e}")

        # Check 2: Entry file exists
        entry_file = config.get("entry_file", "")
        lang = config.get("language", "python")

        if entry_file:
            entry_path = project_dir / entry_file
            if entry_path.exists():
                check_results.append(("Entry file", entry_file, True))
                self._log("INFO", f"Entry file found: {entry_file}")
            else:
                # Try to find it recursively
                found = False
                search_pattern = "*.py" if lang == "python" else "*.js"
                main_file = "main.py" if lang == "python" else "index.js"

                for f in project_dir.rglob(search_pattern):
                    if f.name == entry_file or f.name == main_file:
                        check_results.append(
                            (
                                "Entry file",
                                f"{f.name} (found at {f.relative_to(project_dir)})",
                                True,
                            )
                        )
                        self._log(
                            "INFO", f"Entry file found at: {f.relative_to(project_dir)}"
                        )
                        found = True
                        break

                if not found:
                    check_results.append(
                        ("Entry file", f"{entry_file} not found", False)
                    )
                    checks_passed = False
                    self._log("ERROR", f"Entry file not found: {entry_file}")

        # Check 3: Project files count
        try:
            if lang == "python":
                file_count = len(list(project_dir.rglob("*.py")))
            else:
                file_count = len(list(project_dir.rglob("*.js")))
            check_results.append(("Project files", f"{file_count} files found", True))
            self._log("INFO", f"Project files: {file_count}")
        except Exception as e:
            self._log("WARN", f"Could not count project files: {e}")

        # Display check results
        if self.display:
            for check_name, check_value, check_ok in check_results:
                status = "✓" if check_ok else "✗"
                self.display.log(f"  [{status}] {check_name}: {check_value}")

        if not checks_passed:
            error_msg = (
                "Pre-flight checks failed. Please verify your project configuration."
            )
            self._log("ERROR", error_msg)
            return False, error_msg

        self._log("INFO", "All pre-flight checks passed")
        return True, ""

    def run_build(
        self,
        project_dir: Path,
        config: Dict[str, Any],
        download_bundle_func: Optional[Callable] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Run complete build with proper phase management.

        Args:
            project_dir: Project directory
            config: Build configuration
            download_bundle_func: Optional download function for remote builds

        Returns:
            Tuple of (success, output_path, error_message)
        """
        try:
            # Phase 1: Prepare (with timeout protection)
            if self.display:
                self.display.update_phase(
                    BuildPhase.PREPARE, 0, "Validating configuration..."
                )

            self._log("INFO", "Starting build preparation")

            try:
                entry_file = validate_entry_file(
                    config.get("entry_file", ""), project_dir
                )
                self._log("INFO", f"Entry file validated: {entry_file}")
            except PathTraversalError as e:
                error_msg = f"Security violation: {e}"
                self._log("ERROR", error_msg)
                return False, None, error_msg
            except Exception as e:
                error_msg = f"Failed to validate entry file: {e}"
                self._log("ERROR", error_msg)
                return False, None, error_msg

            # Run pre-flight checks (with init timeout)
            if self.display:
                self.display.update_phase(
                    BuildPhase.PREPARE, 50, "Running pre-flight checks..."
                )

            # Set a watchdog timer for initialization phase only
            init_start = time.time()

            checks_ok, checks_error = self._run_preflight_checks(project_dir, config)

            # Check if init took too long
            init_elapsed = time.time() - init_start
            if init_elapsed > self.INIT_TIMEOUT:
                error_msg = f"Initialization timeout: took {init_elapsed:.1f}s (max {self.INIT_TIMEOUT}s). The build system appears to be stuck."
                self._log("ERROR", error_msg)
                return False, None, error_msg

            if not checks_ok:
                return False, None, checks_error

            if self.display:
                self.display.update_phase(
                    BuildPhase.PREPARE, 100, "Configuration ready"
                )

            self._log("INFO", "Preparation complete")

            # Phase 2: Download (if remote)
            if download_bundle_func:
                if self.display:
                    self.display.update_phase(
                        BuildPhase.DOWNLOAD, 0, "Starting download..."
                    )

                self._log("INFO", "Starting bundle download")

                try:
                    download_bundle_func()

                    if self.display:
                        self.display.update_phase(
                            BuildPhase.DOWNLOAD, 100, "Download complete"
                        )

                    self._log("INFO", "Bundle download complete")
                except Exception as e:
                    error_msg = f"Download failed: {e}"
                    self._log("ERROR", error_msg)
                    return False, None, error_msg

            # Phase 3: Extract
            if self.display:
                self.display.update_phase(BuildPhase.EXTRACT, 0, "Extracting files...")

            self._log("INFO", "Extracting source files")
            time.sleep(0.2)  # Brief pause for UI

            if self.display:
                self.display.update_phase(BuildPhase.EXTRACT, 100, "Files ready")

            self._log("INFO", "Extraction complete")

            # Phase 4: Inject license
            if self.display:
                self.display.update_phase(
                    BuildPhase.INJECT, 0, "Injecting license wrapper..."
                )

            self._log("INFO", "Starting license injection")

            try:
                lang = config.get("language", "python")
                if lang == "nodejs":
                    success = inject_js_wrapper(entry_file, config)
                else:
                    success = inject_license_wrapper(project_dir, config)

                if not success:
                    error_msg = "License wrapper injection failed"
                    self._log("ERROR", error_msg)
                    return False, None, error_msg

                if self.display:
                    self.display.update_phase(
                        BuildPhase.INJECT, 100, "License protection added"
                    )

                self._log("INFO", "License injection complete")
            except Exception as e:
                error_msg = f"License injection failed: {e}"
                self._log("ERROR", error_msg, {"exception": str(e)})
                return False, None, error_msg

            # Phase 5: Compile
            if self.display:
                self.display.update_phase(
                    BuildPhase.COMPILE, 0, "Starting compilation..."
                )

            self._log("INFO", "Starting compilation phase")

            try:
                lang = config.get("language", "python")

                if lang == "nodejs":
                    success, build_dir = self._compile_nodejs(project_dir, config)
                else:
                    success = self._compile_python(project_dir, config)
                    build_dir = (
                        project_dir / "build"
                        if config.get("fast_build")
                        else project_dir
                    )

                if not success:
                    error_msg = "Compilation failed"
                    self._log("ERROR", error_msg)
                    return False, None, error_msg

                if self.display:
                    self.display.update_phase(
                        BuildPhase.COMPILE, 100, "Compilation complete"
                    )

                self._log("INFO", "Compilation complete")
            except Exception as e:
                error_msg = f"Compilation error: {e}"
                self._log("ERROR", error_msg, {"exception": str(e)})
                return False, None, error_msg

            # Phase 6: Package
            if self.display:
                self.display.update_phase(BuildPhase.PACKAGE, 0, "Packaging output...")

            self._log("INFO", "Packaging output")

            try:
                output_path = self._copy_output(project_dir, config, build_dir)

                # Register binary integrity hash with server (SEC2)
                if output_path and output_path.exists():
                    try:
                        from cli.compiler_logic import register_binary_hash_with_server
                        register_binary_hash_with_server(config["project_id"], output_path, config)
                    except Exception:
                        pass # Silent fail for simple runner

                if self.display:
                    self.display.update_phase(
                        BuildPhase.PACKAGE, 100, "Build complete!"
                    )

                self._log("INFO", f"Output packaged: {output_path}")
                return True, output_path, ""
            except Exception as e:
                error_msg = f"Failed to copy output: {e}"
                self._log("ERROR", error_msg)
                return False, None, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self._log("FATAL", error_msg, {"exception": str(e)})
            return False, None, error_msg

    def _compile_python(self, project_dir: Path, config: Dict[str, Any]) -> bool:
        """
        Compile Python project with Nuitka.

        This is the actual build phase - we don't apply init timeout here,
        but we do monitor for no-output conditions.
        """
        self._log("INFO", "Compiling with Nuitka")

        # Use the existing run_nuitka function but with progress monitoring
        # Since run_nuitka is blocking and complex, we'll use a subprocess approach

        entry_file = config.get("entry_file", "")
        output_name = (
            config.get("output_name") or config.get("project_name") or "output"
        )
        fast_build = config.get("fast_build", False)

        try:
            entry_path = validate_entry_file(entry_file, project_dir)
            output_name = validate_output_name(output_name)
        except PathTraversalError as e:
            self._log("ERROR", f"Security violation: {e}")
            return False

        # Fallback: if entry file doesn't exist at resolved path, search recursively
        if not entry_path.exists():
            self._log("WARN", f"Entry file not found at {entry_path}, searching recursively...")
            found = False
            for f in project_dir.rglob("*.py"):
                if f.name == entry_file or f.name == "main.py":
                    entry_path = f
                    found = True
                    self._log("INFO", f"Found entry file at: {f.relative_to(project_dir)}")
                    break
            if not found:
                self._log("ERROR", f"Entry file not found: {entry_file}")
                return False

        # Build Nuitka command
        cpu_count = os.cpu_count() or 4
        max_jobs = min(cpu_count, 8)
        if config.get("jobs"):
            max_jobs = min(config.get("jobs"), 16)

        cmd = [
            sys.executable,
            "-m",
            "nuitka",
            "--standalone",
            "--lto=no",
            "--remove-output",
            "--assume-yes-for-downloads",
            "--enable-plugin=tk-inter",
            "--no-prefer-source-code",
            "--nofollow-import-to=pytest",
            "--nofollow-import-to=unittest",
            "--nofollow-import-to=sphinx",
            "--nofollow-import-to=setuptools",
            f"--jobs={max_jobs}",
        ]

        if fast_build:
            cmd.extend([f"--output-dir={project_dir / 'build'}"])
        else:
            cmd.extend(
                [
                    "--onefile",
                    f"--output-filename={output_name}.exe",
                ]
            )

        # Add include packages
        nuitka_opts = config.get("nuitka_options", {})
        for pkg in nuitka_opts.get("include_packages", []):
            cmd.append(f"--include-package={pkg}")

        cmd.append(str(entry_path))

        self._log("INFO", f"Nuitka command: {' '.join(cmd[:5])}...")

        # Run with monitoring
        return self._run_subprocess_with_monitoring(
            cmd, project_dir, "Nuitka", is_build_phase=True
        )

    def _compile_nodejs(
        self, project_dir: Path, config: Dict[str, Any]
    ) -> Tuple[bool, Optional[Path]]:
        """Compile Node.js project with pkg."""
        self._log("INFO", "Compiling with pkg")

        entry_file = config.get("entry_file", "")
        output_name = (
            config.get("output_name") or config.get("project_name") or "output"
        )

        try:
            entry_path = validate_entry_file(entry_file, project_dir)
            output_name = validate_output_name(output_name)
        except PathTraversalError as e:
            self._log("ERROR", f"Security violation: {e}")
            return False, None

        npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
        pkg_cwd = entry_path.parent
        entry_path_rel = entry_path.relative_to(pkg_cwd)

        cmd = [
            npx_cmd,
            "-y",
            "@yao-pkg/pkg",
            str(entry_path_rel),
            "--targets",
            "node20-win-x64",
            "--output",
            str(pkg_cwd / output_name),
            "--compress",
            "GZip",
        ]

        self._log("INFO", f"pkg command: {' '.join(cmd)}")

        success = self._run_subprocess_with_monitoring(
            cmd, pkg_cwd, "pkg", is_build_phase=True
        )

        return success, pkg_cwd

    def _run_subprocess_with_monitoring(
        self, cmd: list, cwd: Path, name: str, is_build_phase: bool = False
    ) -> bool:
        """
        Run subprocess with progress monitoring.

        Args:
            cmd: Command to run
            cwd: Working directory
            name: Process name for logging
            is_build_phase: Whether this is the actual build (not init)
        """
        self._log("INFO", f"Starting {name} subprocess", {"cwd": str(cwd)})

        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                bufsize=0,
                env=env,
                creationflags=creationflags,
            )

            self._log("INFO", f"{name} started with PID {process.pid}")

            start_time = time.time()
            last_output_time = time.time()
            last_progress_update = 0
            last_heartbeat_time = time.time()
            current_progress = 0
            HEARTBEAT_INTERVAL = 15  # Show a heartbeat log every 15s of silence

            while True:
                elapsed = time.time() - start_time

                # Build phase timeout check
                if is_build_phase and elapsed > self.BUILD_TIMEOUT:
                    self._log(
                        "ERROR", f"{name} compilation timeout after {elapsed:.1f}s"
                    )
                    process.kill()
                    return False

                # No-output timeout (only during build phase, not init)
                time_since_output = time.time() - last_output_time
                if is_build_phase and time_since_output > self.NO_OUTPUT_TIMEOUT:
                    self._log(
                        "ERROR",
                        f"{name} no output for {time_since_output:.0f}s - process appears stuck",
                    )
                    process.kill()
                    return False

                # Heartbeat: show periodic progress during silent compilation phases
                if is_build_phase and (time.time() - last_heartbeat_time) > HEARTBEAT_INTERVAL:
                    last_heartbeat_time = time.time()
                    mins_elapsed = int(elapsed) // 60
                    secs_elapsed = int(elapsed) % 60
                    self._log("INFO", f"Compiling... ({mins_elapsed}m {secs_elapsed}s elapsed, CPU active)")
                    if self.display:
                        phase_label = f"Compiling... {mins_elapsed}m {secs_elapsed}s"
                        self.display.update_phase(
                            BuildPhase.COMPILE,
                            max(current_progress, 5),
                            phase_label,
                        )

                # Non-blocking read with cross-platform helper
                if _wait_for_output_with_timeout(process, timeout=1.0):
                    line_bytes = _readline_from_process(process)
                    if line_bytes:
                        last_output_time = time.time()
                        last_heartbeat_time = time.time()
                        if isinstance(line_bytes, bytes):
                            line = line_bytes.decode("utf-8", errors="replace").strip()
                        else:
                            line = (
                                line_bytes.strip()
                                if isinstance(line_bytes, str)
                                else str(line_bytes).strip()
                            )

                        # Parse progress for display
                        if name == "Nuitka":
                            progress = self._parse_nuitka_progress(line)
                            if progress and progress != current_progress:
                                current_progress = progress
                                phase = self._parse_nuitka_phase(line)
                                if (
                                    self.display
                                    and elapsed - last_progress_update > 1.0
                                ):
                                    self.display.update_phase(
                                        BuildPhase.COMPILE,
                                        progress,
                                        f"{phase} ({progress}%)",
                                    )
                                    last_progress_update = elapsed

                            # Show concise filtered Nuitka progress lines
                            if self._is_notable_nuitka_line(line):
                                self._log("INFO", f"{name}: {self._summarize_nuitka_line(line)}")
                            else:
                                self._log("DEBUG", f"{name}: {line}")
                        else:
                            # Non-Nuitka: log errors, debug everything else
                            if "error" in line.lower() and "no errors" not in line.lower():
                                self._log("ERROR", f"{name}: {line}")
                            else:
                                self._log("DEBUG", f"{name}: {line}")

                # Check if process finished
                if process.poll() is not None:
                    break

            # Drain any remaining output after process exits
            try:
                if process.stdout and not process.stdout.closed:
                    for raw_line in process.stdout:
                        line = raw_line.decode("utf-8", errors="replace").strip() if isinstance(raw_line, bytes) else str(raw_line).strip()
                        if line:
                            if "error" in line.lower() and "no errors" not in line.lower():
                                self._log("ERROR", f"{name}: {line}")
                            else:
                                self._log("DEBUG", f"{name}: {line}")
            except (ValueError, OSError):
                pass  # stdout already closed or unavailable

            if process.returncode == 0:
                self._log("INFO", f"{name} completed successfully")
                return True
            else:
                self._log("ERROR", f"{name} failed with code {process.returncode}")
                return False

        except Exception as e:
            self._log("ERROR", f"{name} error: {e}")
            return False

    def _parse_nuitka_progress(self, line: str) -> Optional[int]:
        """Parse progress percentage from Nuitka output."""
        if "%" in line:
            match = re.search(r"(\d+)%", line)
            if match:
                return int(match.group(1))
        return None

    def _parse_nuitka_phase(self, line: str) -> str:
        """Determine compilation phase from Nuitka output."""
        lower = line.lower()
        if "ggg:" in lower or "module" in lower:
            return "Optimizing modules"
        elif "scons:" in lower or "compiling" in lower:
            return "Compiling C code"
        elif "link" in lower:
            return "Linking"
        elif "onefile" in lower:
            return "Creating single file"
        return "Processing"

    def _is_notable_nuitka_line(self, line: str) -> bool:
        """Check if a Nuitka output line is worth showing to the user."""
        lower = line.lower()
        # Show phase transitions, warnings, errors, and progress milestones
        notable_keywords = [
            "nuitka-scons:", "scons:", "linking", "onefile",
            "backend c", "generating", "completed", "optimiz",
            "warning:", "error:", "fatal:", "creating",
            "including", "module", "data composer",
        ]
        # Show lines with percentage progress
        if "%" in line:
            return True
        return any(kw in lower for kw in notable_keywords)

    def _summarize_nuitka_line(self, line: str) -> str:
        """Create a concise summary of a Nuitka output line."""
        # Strip ANSI codes
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
        # Truncate very long lines (e.g. AST dumps)
        if len(clean) > 120:
            clean = clean[:117] + "..."
        return clean

    def _copy_output(
        self, project_dir: Path, config: Dict[str, Any], build_dir: Path
    ) -> Path:
        """Copy output to final location (Desktop by default)."""
        output_name = (
            config.get("output_name") or config.get("project_name") or self.project_name or "output"
        )
        output_name = validate_output_name(output_name)

        # Output goes to Desktop by default
        # Check OneDrive Desktop first (common on Windows with OneDrive)
        onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
        plain_desktop = Path.home() / "Desktop"

        if onedrive_desktop.exists():
            desktop_dir = onedrive_desktop
        elif plain_desktop.exists():
            desktop_dir = plain_desktop
        else:
            desktop_dir = Path.home()

        output_dir = desktop_dir / "CodeVault Builds"
        output_dir.mkdir(exist_ok=True)

        if config.get("fast_build"):
            # Fast mode (--standalone): Nuitka creates a .dist directory
            # with the exe + all DLLs mixed together.
            # We reorganize: project folder on Desktop with exe at top + runtime subfolder

            # Search for .dist directories in build output
            dist_dirs = list(build_dir.glob("*.dist"))
            if not dist_dirs:
                dist_dirs = list(build_dir.rglob("*.dist"))

            if dist_dirs:
                src_dist = dist_dirs[0]
                project_folder = output_dir / output_name
                if project_folder.exists():
                    shutil.rmtree(project_folder, ignore_errors=True)
                project_folder.mkdir(parents=True, exist_ok=True)

                # Find the exe name inside .dist
                exe_name = None
                for f in src_dist.glob("*.exe"):
                    exe_name = f.name
                    break

                if exe_name:
                    # Copy the entire .dist contents into a runtime subfolder
                    runtime_dir = project_folder / "_runtime"
                    shutil.copytree(src_dist, runtime_dir)

                    # Copy the exe to the top level of the project folder
                    top_exe = project_folder / f"{output_name}.exe"
                    shutil.copy2(runtime_dir / exe_name, top_exe)

                    # Create a launcher .bat at the top level
                    bat_path = project_folder / f"Run {output_name}.bat"
                    bat_content = f'@echo off\r\ncd /d "%~dp0_runtime"\r\nstart "" "{exe_name}"\r\n'
                    bat_path.write_text(bat_content, encoding="utf-8")

                    self._log("INFO", f"Output: {project_folder}")
                    self._log("INFO", f"  {output_name}.exe  (main executable)")
                    self._log("INFO", f"  Run {output_name}.bat  (launcher)")
                    self._log("INFO", f"  _runtime/  (dependencies)")
                    return top_exe
                else:
                    # No exe found, just copy dist as-is
                    shutil.copytree(src_dist, project_folder / "_runtime")
                    self._log("WARN", "No .exe found inside .dist directory")
                    return project_folder

            # Fallback: search for any .exe in the build directory
            for exe_file in build_dir.rglob("*.exe"):
                dst = output_dir / f"{output_name}.exe"
                shutil.copy2(exe_file, dst)
                self._log("INFO", f"Copied executable: {exe_file.name} -> {dst}")
                return dst

            raise FileNotFoundError(
                f"Could not find output in build directory. "
                f"Searched for .dist folders and .exe files in: {build_dir}"
            )
        else:
            # Standard mode (--onefile): single .exe output
            dst = output_dir / f"{output_name}.exe"

            # Try exact match first
            src = build_dir / f"{output_name}.exe"
            if src.exists():
                shutil.copy2(src, dst)
                return dst

            # Search for any .exe in the project directory
            for exe_file in build_dir.rglob("*.exe"):
                shutil.copy2(exe_file, dst)
                self._log("INFO", f"Copied executable: {exe_file.name} -> {dst}")
                return dst

            raise FileNotFoundError(f"Could not find output executable in: {build_dir}")


def run_local_build_simple(
    entry_path: Path, config: Dict[str, Any], project_name: str = "Local Build"
) -> Tuple[bool, Optional[Path], str]:
    """
    Run a local file build with simplified display.

    This is the main entry point for local builds.
    """
    if not entry_path.exists():
        return False, None, f"File not found: {entry_path}"

    # Create logger
    logger = create_logger(project_name)
    logger.info(f"Starting local build: {entry_path}")

    # Create display
    display = create_display(project_name, config, use_rich=False)
    display.start()

    # Create runner
    runner = SimpleBuildRunner(display, project_name)

    # Use temp directory for build - don't use context manager to avoid cleanup issues
    tmpdir = tempfile.mkdtemp(prefix="codevault_build_")
    final_output_path = None
    success = False
    error = None

    try:
        tmp_project_dir = Path(tmpdir) / "project"
        tmp_project_dir.mkdir()

        # Copy source
        def ignore_patterns(path, names):
            return {
                "__pycache__",
                "node_modules",
                ".git",
                ".env",
                "dist",
                "build",
                "output",
            }

        shutil.copytree(
            entry_path.parent,
            tmp_project_dir,
            ignore=ignore_patterns,
            dirs_exist_ok=True,
        )

        # Update config with temp paths
        build_config = config.copy()
        build_config["entry_file"] = entry_path.name

        # Run build
        success, output_path, error = runner.run_build(tmp_project_dir, build_config)

        # Copy output to final location BEFORE attempting temp cleanup
        if success and output_path and output_path.exists():
            final_output_path = output_path

        # Get output size
        output_size = 0
        if final_output_path and final_output_path.exists():
            output_size = final_output_path.stat().st_size

        duration = timedelta(seconds=int(time.time() - runner.start_time))

        # Complete display
        display.complete(
            success,
            str(final_output_path) if final_output_path else None,
            output_size,
            duration,
        )

        # Log completion
        logger.build_complete(success, error)

        if not success and logger:
            log_path = logger.get_log_path()
            if log_path:
                print(f"\nFull logs: {log_path}")

    except Exception as e:
        success = False
        error = str(e)
        logger.exception("Unexpected error in local build", e)
        display.set_error(f"Unexpected error: {e}")
        display.complete(False)
    finally:
        # Cleanup temp directory - ignore errors on Windows (file locking)
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
            if success:  # Only log cleanup success if build succeeded
                logger.info(f"Cleaned up temp directory: {tmpdir}")
        except Exception as e:
            # Log cleanup error but don't fail the build
            logger.warn(f"Could not clean up temp directory {tmpdir}: {e}")
            # Don't fail the build just because cleanup failed
            pass

    return success, final_output_path, error


def run_remote_build_simple(
    project_id: str,
    config: Dict[str, Any],
    headers: Dict[str, str],
    api_url: str,
    project_data: Optional[Dict] = None,
    project_name: str = "Remote Build",
    max_retries: int = 3,
) -> Tuple[bool, Optional[Path], str]:
    """
    Run a remote project build with simplified display.
    """
    import requests
    import zipfile

    # Create logger
    logger = create_logger(project_name)
    logger.info(f"Starting remote build: {project_id}")

    # Create display
    display = create_display(project_name, config, use_rich=False)
    display.start()

    # Create runner
    runner = SimpleBuildRunner(display, project_name)

    last_error = None
    final_output_path = None
    success = False

    # Build loop - ask user before retrying
    while True:

        # Use temp directory - don't use context manager to avoid cleanup issues on Windows
        tmpdir = tempfile.mkdtemp(prefix="codevault_build_")

        try:
            tmpdir_path = Path(tmpdir)
            project_dir = tmpdir_path / "project"
            project_dir.mkdir()

            # Download bundle
            display.update_phase(BuildPhase.DOWNLOAD, 0, "Downloading...")

            bundle_path = tmpdir_path / "bundle.zip"
            bundle_params = {}
            if config.get("license_key"):
                bundle_params["license_id"] = config["license_key"]

            try:
                resp = requests.get(
                    f"{api_url}/projects/{project_id}/build-bundle",
                    headers=headers,
                    params=bundle_params,
                    timeout=120,
                    stream=True,
                )

                if resp.status_code == 200:
                    with open(bundle_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    logger.info(
                        f"Bundle downloaded: {bundle_path.stat().st_size} bytes"
                    )
                else:
                    error_msg = f"Server returned HTTP {resp.status_code}"
                    logger.error(error_msg)
                    last_error = error_msg
                    # Cleanup before retry
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    continue

            except Exception as e:
                error_msg = f"Download failed: {e}"
                logger.error(error_msg)
                last_error = error_msg
                # Cleanup before retry
                shutil.rmtree(tmpdir, ignore_errors=True)
                continue

            # Extract bundle
            try:
                with zipfile.ZipFile(bundle_path, "r") as zf:
                    zf.extractall(project_dir)
                logger.info("Bundle extracted successfully")
            except zipfile.BadZipFile as e:
                error_msg = f"Invalid ZIP file: {e}"
                logger.error(error_msg)
                last_error = error_msg
                # Cleanup before retry
                shutil.rmtree(tmpdir, ignore_errors=True)
                continue

            # Load config.json if present
            config_path = project_dir / "config.json"
            if config_path.exists():
                try:
                    project_config = json.loads(config_path.read_text())
                    for key in [
                        "license_key",
                        "api_url",
                        "server_url",
                        "language",
                        "entry_file",
                        "output_name",
                    ]:
                        if key in project_config and project_config[key]:
                            config[key] = project_config[key]
                    logger.info("Loaded config.json")
                except Exception as e:
                    logger.warn(f"Could not load config.json: {e}")

            # Run build
            success, output_path, error = runner.run_build(project_dir, config)

            # Copy output reference BEFORE any cleanup
            if success and output_path and output_path.exists():
                final_output_path = output_path

            # Get output size
            output_size = 0
            if final_output_path and final_output_path.exists():
                output_size = final_output_path.stat().st_size

            duration = timedelta(seconds=int(time.time() - runner.start_time))

            # Complete display
            display.complete(
                success,
                str(final_output_path) if final_output_path else None,
                output_size,
                duration,
            )

            # Log completion
            logger.build_complete(success, error)

            if success:
                # Success! Cleanup temp dir but ignore errors
                try:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    logger.info(f"Cleaned up temp directory: {tmpdir}")
                except Exception as e:
                    logger.warn(f"Could not clean up temp directory {tmpdir}: {e}")

                return success, final_output_path, error
            else:
                # Build failed - cleanup and ask user
                last_error = error
                try:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                except:
                    pass

                log_path = logger.get_log_path()
                if log_path:
                    print(f"\nFull logs: {log_path}")

                # Ask user if they want to retry
                try:
                    retry_input = input("\nBuild failed. Would you like to retry? (Y/N): ").strip().lower()
                    if retry_input not in ("y", "yes"):
                        logger.info("User chose not to retry")
                        return False, None, last_error
                    print()
                    logger.info("User chose to retry")
                    # Reset display for next attempt
                    display = create_display(project_name, config, use_rich=False)
                    display.start()
                    runner = SimpleBuildRunner(display, project_name)
                except (KeyboardInterrupt, EOFError):
                    return False, None, last_error

        except Exception as e:
            last_error = str(e)
            logger.error(f"Build error: {e}")
            # Cleanup
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass

            log_path = logger.get_log_path()
            if log_path:
                print(f"\nFull logs: {log_path}")

            # Ask user if they want to retry
            try:
                retry_input = input("\nBuild failed. Would you like to retry? (Y/N): ").strip().lower()
                if retry_input not in ("y", "yes"):
                    return False, None, last_error
                print()
                display = create_display(project_name, config, use_rich=False)
                display.start()
                runner = SimpleBuildRunner(display, project_name)
            except (KeyboardInterrupt, EOFError):
                return False, None, last_error
