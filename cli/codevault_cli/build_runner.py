"""
Build runner that integrates existing compiler logic with the new CLI dashboard.

This module bridges the gap between the old compiler_logic.py and the new
Rich-based dashboard, providing real-time build monitoring.
"""

import sys
import os
import re
import json
import time
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, Callable
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import existing compiler logic
from compiler_logic import (
    inject_license_wrapper,
    inject_js_wrapper,
    validate_entry_file,
    validate_output_name,
    PathTraversalError,
    _wait_for_output_with_timeout,
    _readline_from_process,
)
from compiler_constants import COMPILE_TIMEOUT

# Import new CLI components
from codevault_cli.console import get_console, print_error
from codevault_cli.build_dashboard import BuildDashboard

console = get_console()


class BuildRunner:
    """
    Runs builds with real-time dashboard updates.

    Wraps the existing compiler logic from compiler_logic.py and
    provides live progress updates to the dashboard.
    """

    def __init__(self, dashboard: Optional[BuildDashboard] = None):
        self.dashboard = dashboard
        self.current_phase = ""
        self.start_time = time.time()
        self.debug_log = []

    def _log(self, level: str, message: str):
        """Phase 5: Add detailed logging."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.debug_log.append(log_entry)
        if level in ["ERROR", "WARN"]:
            console.print(f"[{level.lower()}]{log_entry}[/]")

    def _run_preflight_checks(
        self, project_dir: Path, config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Phase 5: Pre-flight checks before starting build."""
        console.print("\n[dim]Running pre-flight checks...[/dim]\n")

        checks_passed = True

        # Check 1: Python version
        try:
            py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            console.print(f"  [CHECK] Python version: {py_version} ✓")
        except Exception as e:
            console.print(f"  [CHECK] Python version: ✗ ({e})")
            checks_passed = False

        # Check 2: Nuitka installed (for Python projects)
        lang = config.get("language", "python")
        if lang == "python":
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "nuitka", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    nuitka_version = result.stdout.strip().split("\n")[0]
                    console.print(f"  [CHECK] Nuitka installed: {nuitka_version} ✓")
                else:
                    console.print("  [CHECK] Nuitka installed: ✗ (not found)")
                    checks_passed = False
            except Exception as e:
                console.print(f"  [CHECK] Nuitka installed: ✗ ({e})")
                checks_passed = False

        # Check 3: Entry file exists
        entry_file = config.get("entry_file", "")
        if entry_file:
            entry_path = project_dir / entry_file
            if entry_path.exists():
                console.print(f"  [CHECK] Entry file exists: {entry_file} ✓")
            else:
                # Try to find it recursively
                found = False
                for f in project_dir.rglob("*.py" if lang == "python" else "*.js"):
                    if (
                        f.name == entry_file
                        or f.name == "main.py"
                        or f.name == "index.js"
                    ):
                        console.print(
                            f"  [CHECK] Entry file exists: {f.name} ✓ (found at {f.relative_to(project_dir)})"
                        )
                        found = True
                        break
                if not found:
                    console.print(
                        f"  [CHECK] Entry file exists: {entry_file} ✗ (not found)"
                    )
                    checks_passed = False

        # Check 4: Project files count
        try:
            if lang == "python":
                file_count = len(list(project_dir.rglob("*.py")))
            else:
                file_count = len(list(project_dir.rglob("*.js")))
            console.print(f"  [CHECK] Project files: {file_count} files found ✓")
        except Exception as e:
            console.print(f"  [CHECK] Project files: ✗ ({e})")

        # Check 5: Disk space (at least 1GB free recommended)
        try:
            import shutil

            total, used, free = shutil.disk_usage(project_dir)
            free_gb = free / (1024**3)
            if free_gb >= 1:
                console.print(f"  [CHECK] Disk space: {free_gb:.1f} GB available ✓")
            else:
                console.print(f"  [WARN] Disk space: {free_gb:.1f} GB available (low)")
        except Exception as e:
            console.print(f"  [CHECK] Disk space: ? ({e})")

        console.print()

        if not checks_passed:
            return False, "Pre-flight checks failed. Please fix the issues above."

        console.print("[START] Launching compiler...\n")
        return True, ""

    def update_phase(self, phase: str, progress: int = 0, status: str = ""):
        """Update dashboard phase and progress."""
        self.current_phase = phase
        if self.dashboard:
            self.dashboard.update_phase(phase, progress)
            if status:
                self.dashboard.set_status(status)
            self.dashboard.refresh()
        else:
            console.print(f"[{phase}] {status}" if status else phase)

    def run_build(
        self,
        project_dir: Path,
        config: Dict[str, Any],
        download_bundle_func: Optional[Callable] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Run a complete build with dashboard updates.

        Args:
            project_dir: The project directory
            config: Build configuration
            download_bundle_func: Optional function to download bundle (for remote builds)

        Returns:
            Tuple of (success: bool, output_path: Path|None, error_message: str)
        """
        try:
            # Phase 1: Fetch/Prepare configuration
            self.update_phase("Prepare", 0, "Loading build configuration...")
            time.sleep(0.2)  # Brief pause for UI
            self.update_phase("Prepare", 50, "Validating project files...")

            # Validate entry file
            try:
                entry_file = validate_entry_file(
                    config.get("entry_file", ""), project_dir
                )
                self.update_phase("Prepare", 100, "Configuration loaded")
            except PathTraversalError as e:
                return False, None, f"Security violation: {e}"
            except Exception as e:
                return False, None, f"Failed to validate entry file: {e}"

            # Phase 5: Run pre-flight checks
            checks_ok, checks_error = self._run_preflight_checks(project_dir, config)
            if not checks_ok:
                return False, None, checks_error

            # Phase 2: Download bundle (if remote build)
            if download_bundle_func:
                self.update_phase("Download", 0, "Downloading project bundle...")
                try:
                    download_bundle_func(self._make_progress_callback("Download"))
                    self.update_phase("Download", 100, "Download complete")
                except Exception as e:
                    return False, None, f"Download failed: {e}"

            # Phase 3: Extract/Prepare source
            self.update_phase("Extract", 0, "Preparing source files...")
            time.sleep(0.3)
            self.update_phase("Extract", 100, "Source ready")

            # Phase 4: Inject license wrapper
            self.update_phase("Inject", 0, "Injecting license protection...")
            try:
                lang = config.get("language", "python")
                if lang == "nodejs":
                    success = inject_js_wrapper(entry_file, config)
                else:
                    success = inject_license_wrapper(project_dir, config)

                if not success:
                    return False, None, "License wrapper injection failed"

                self.update_phase("Inject", 100, "License protection added")
            except Exception as e:
                return False, None, f"License injection failed: {e}"

            # Phase 5: Compile (the main event)
            self.update_phase("Compile", 0, "Starting compilation...")

            try:
                success, build_dir = self._run_compiler_with_progress(
                    project_dir, config
                )

                if not success:
                    return False, None, "Compilation failed"

                self.update_phase("Compile", 100, "Compilation complete")
            except Exception as e:
                return False, None, f"Compilation error: {e}"

            # Phase 6: Copy output
            self.update_phase("Package", 0, "Packaging output...")
            try:
                output_path = self._copy_output(project_dir, config, build_dir)
                
                # Register binary integrity hash with server (SEC2)
                if output_path and output_path.exists():
                    try:
                        from cli.compiler_logic import register_binary_hash_with_server
                        register_binary_hash_with_server(config["project_id"], output_path, config)
                    except Exception as e:
                        # Log but don't fail the build for registration errors
                        self.log(f"   [WARN] Could not register integrity hash: {e}")

                self.update_phase("Package", 100, "Build complete!")
                return True, output_path, ""
            except Exception as e:
                return False, None, f"Failed to copy output: {e}"

        except Exception as e:
            return False, None, f"Unexpected error: {e}"

    def _run_compiler_with_progress(
        self, project_dir: Path, config: Dict[str, Any]
    ) -> Tuple[bool, Optional[Path]]:
        """
        Run the compiler with real-time progress parsing.

        This wraps the existing run_compiler but intercepts output
        to update the dashboard in real-time.
        """
        lang = config.get("language", "python")

        if lang == "nodejs":
            return self._run_pkg_with_progress(project_dir, config)
        else:
            return self._run_nuitka_with_progress(project_dir, config)

    def _run_nuitka_with_progress(
        self, project_dir: Path, config: Dict[str, Any]
    ) -> Tuple[bool, Optional[Path]]:
        """Run Nuitka with real-time progress parsing."""
        import subprocess

        entry_file = config.get("entry_file", "")
        output_name = (
            config.get("output_name") or config.get("project_name") or "output"
        )
        fast_build = config.get("fast_build", False)

        # Validate paths
        try:
            entry_path = validate_entry_file(entry_file, project_dir)
            output_name = validate_output_name(output_name)
        except PathTraversalError as e:
            print_error(f"Security violation: {e}")
            return False, None

        # Fallback: if entry file doesn't exist at resolved path, search recursively
        if not entry_path.exists():
            found = False
            for f in project_dir.rglob("*.py"):
                if f.name == entry_file or f.name == "main.py":
                    entry_path = f
                    found = True
                    console.print(f"[INFO] Found entry file at: {f.relative_to(project_dir)}")
                    break
            if not found:
                print_error(f"Entry file not found: {entry_file}")
                return False, None

        # Build command
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

        # Run with real-time output parsing
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            process = subprocess.Popen(
                cmd,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                bufsize=0,
                env=env,
                creationflags=creationflags,
            )

            last_percent = 0
            start_time = time.time()
            last_output_time = time.time()
            heartbeat_interval = 30  # Log heartbeat every 30 seconds
            no_output_timeout = 60  # Kill if no output for 60 seconds

            console.print(f"[Nuitka] Started with PID {process.pid}")
            console.print(f"[Nuitka] Working directory: {project_dir}")
            console.print(f"[Nuitka] Command: {' '.join(cmd[:5])}...")
            console.print("[Nuitka] Waiting for output...")

            while True:
                # Check for overall timeout
                elapsed = time.time() - start_time
                if elapsed > COMPILE_TIMEOUT:
                    console.print(
                        f"\n[ERROR] Compilation exceeded {COMPILE_TIMEOUT}s limit"
                    )
                    process.kill()
                    return False, None

                # Check for no-output timeout (critical fix for hanging)
                time_since_output = time.time() - last_output_time
                if time_since_output > no_output_timeout:
                    console.print(
                        f"\n[ERROR] No output for {no_output_timeout}s - compiler may be stuck"
                    )
                    console.print("[ERROR] Killing process...")
                    process.kill()
                    return False, None

                # Heartbeat logging every 30 seconds
                if int(elapsed) % heartbeat_interval == 0 and int(elapsed) > 0:
                    mins, secs = divmod(int(elapsed), 60)
                    console.print(
                        f"[ALIVE] Compiler still running ({mins}m {secs}s elapsed)"
                    )

                # NON-BLOCKING read with cross-platform helper
                # Wait up to 1 second for output before checking timeout again
                if _wait_for_output_with_timeout(process, timeout=1.0):
                    line_bytes = _readline_from_process(process)
                    if line_bytes:
                        last_output_time = time.time()  # Reset output timer
                        if isinstance(line_bytes, bytes):
                            line = line_bytes.decode("utf-8", errors="replace").strip()
                        else:
                            line = (
                                line_bytes.strip()
                                if isinstance(line_bytes, str)
                                else str(line_bytes).strip()
                            )

                        # Parse Nuitka progress
                        percent = self._parse_nuitka_percent(line)
                        if percent and percent > last_percent:
                            last_percent = percent
                            phase = self._parse_nuitka_phase(line)
                            self.update_phase(
                                "Compile", percent, f"{phase}... ({percent}%)"
                            )

                        # Check for errors
                        if "error" in line.lower() and "no errors" not in line.lower():
                            console.print(f"[red][ERROR] {line}[/red]")

                # Check if process has finished
                if process.poll() is not None:
                    # Process finished, drain remaining output
                    if process.stdout:
                        remaining = process.stdout.read()
                        if remaining:
                            for line in (
                                remaining.decode("utf-8", errors="replace")
                                .strip()
                                .split("\n")
                            ):
                                if line:
                                    if (
                                        "error" in line.lower()
                                        and "no errors" not in line.lower()
                                    ):
                                        console.print(f"[red][ERROR] {line}[/red]")
                    break

            process.wait()

            if process.returncode == 0:
                # Determine build directory
                if fast_build:
                    build_dir = project_dir / "build"
                else:
                    build_dir = project_dir
                return True, build_dir
            else:
                return False, None

        except Exception as e:
            print_error(f"Nuitka error: {e}")
            return False, None

    def _run_pkg_with_progress(
        self, project_dir: Path, config: Dict[str, Any]
    ) -> Tuple[bool, Optional[Path]]:
        """Run pkg with real-time progress parsing."""
        import subprocess

        entry_file = config.get("entry_file", "")
        output_name = (
            config.get("output_name") or config.get("project_name") or "output"
        )

        # Validate paths
        try:
            entry_path = validate_entry_file(entry_file, project_dir)
            output_name = validate_output_name(output_name)
        except PathTraversalError as e:
            print_error(f"Security violation: {e}")
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

        try:
            process = subprocess.Popen(
                cmd,
                cwd=pkg_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )

            start_time = time.time()
            last_output_time = time.time()
            current_phase = "analyzing"
            no_output_timeout = 60
            heartbeat_interval = 30

            console.print(f"[pkg] Started with PID {process.pid}")
            console.print(f"[pkg] Working directory: {pkg_cwd}")
            console.print("[pkg] Waiting for output...")

            while True:
                elapsed = time.time() - start_time

                # Check for no-output timeout
                time_since_output = time.time() - last_output_time
                if time_since_output > no_output_timeout:
                    console.print(
                        f"\n[ERROR] No output for {no_output_timeout}s - pkg may be stuck"
                    )
                    process.kill()
                    return False, None

                # Heartbeat
                if int(elapsed) % heartbeat_interval == 0 and int(elapsed) > 0:
                    mins, secs = divmod(int(elapsed), 60)
                    console.print(
                        f"[ALIVE] pkg still running ({mins}m {secs}s elapsed)"
                    )

                # NON-BLOCKING read with cross-platform helper
                if _wait_for_output_with_timeout(process, timeout=1.0):
                    line_bytes = _readline_from_process(process)
                    if line_bytes:
                        last_output_time = time.time()
                        if isinstance(line_bytes, bytes):
                            line = line_bytes.decode("utf-8", errors="replace")
                        else:
                            line = (
                                line_bytes
                                if isinstance(line_bytes, str)
                                else str(line_bytes)
                            )
                        # Parse pkg output for phase detection
                        if "bundling" in line.lower():
                            current_phase = "bundling"
                        elif "compil" in line.lower():
                            current_phase = "compiling"
                        elif "pack" in line.lower():
                            current_phase = "packaging"

                        # Estimate progress (pkg doesn't provide %)
                        estimated_percent = min(95, int(elapsed / 180 * 100))
                        self.update_phase(
                            "Compile", estimated_percent, f"{current_phase}..."
                        )

                if process.poll() is not None:
                    break

            process.wait()

            if process.returncode == 0:
                return True, pkg_cwd
            else:
                return False, None

        except Exception as e:
            print_error(f"pkg error: {e}")
            return False, None

    def _parse_nuitka_percent(self, line: str) -> Optional[int]:
        """Extract percentage from Nuitka output."""
        if "%" in line:
            match = re.search(r"(\d+)%", line)
            if match:
                return int(match.group(1))
        return None

    def _parse_nuitka_phase(self, line: str) -> str:
        """Determine compilation phase from Nuitka output."""
        if "GGG:" in line or "module" in line.lower():
            return "Optimizing modules"
        elif "SCons:" in line or "compile" in line.lower():
            return "Compiling C code"
        elif "link" in line.lower():
            return "Linking"
        elif "onefile" in line.lower():
            return "Creating single file"
        return "Processing"

    def _copy_output(
        self, project_dir: Path, config: Dict[str, Any], build_dir: Optional[Path]
    ) -> Path:
        """Copy output to final location."""
        output_name = (
            config.get("output_name") or config.get("project_name") or "output"
        )

        # Determine source path
        if config.get("fast_build"):
            src = build_dir / f"{output_name}.exe"
        else:
            src = build_dir / f"{output_name}.exe"

        # Ensure output directory exists
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Copy file
        dst = output_dir / f"{output_name}.exe"
        if src.exists():
            shutil.copy2(src, dst)
            return dst

        # If not found at expected location, search for it
        for exe_file in build_dir.rglob("*.exe"):
            if output_name.lower() in exe_file.stem.lower():
                shutil.copy2(exe_file, dst)
                return dst

        raise FileNotFoundError("Could not find output executable")

    def _make_progress_callback(self, phase: str) -> Callable[[int], None]:
        """Create a progress callback for download operations."""

        def callback(percent: int):
            self.update_phase(phase, percent, f"Downloading... ({percent}%)")

        return callback


def run_local_build(
    entry_path: Path, config: Dict[str, Any], dashboard: Optional[BuildDashboard] = None
) -> Tuple[bool, Optional[Path], str]:
    """
    Run a local file build with dashboard.

    This is the main entry point for local builds in the new CLI.
    """
    if not entry_path.exists():
        return False, None, f"File not found: {entry_path}"

    runner = BuildRunner(dashboard)

    # Use temp directory for build
    with tempfile.TemporaryDirectory() as tmpdir:
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

        return runner.run_build(tmp_project_dir, build_config)


def run_remote_build(
    project_id: str,
    config: Dict[str, Any],
    headers: Dict[str, str],
    api_url: str,
    dashboard: Optional[BuildDashboard] = None,
    project_data: Optional[Dict] = None,
    max_retries: int = 3,
) -> Tuple[bool, Optional[Path], str]:
    """
    Run a remote project build with dashboard.

    Phase 8: Smart retry and error recovery

    Tries multiple sources in order:
    1. Check for local project files (if local_path provided)
    2. Ask user if they want to use local files
    3. Download bundle from API (with retries)
    4. If download fails, prompt user to select source manually
    """

    runner = BuildRunner(dashboard)
    project_name = config.get("project_name", project_id[:8])

    last_error = None

    # Phase 8: Automatic retry loop
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            console.print(f"\n[TRY {attempt}] Retrying build...")
            time.sleep(2 ** (attempt - 1))  # Exponential backoff: 2, 4, 8 seconds

        try:
            result = _run_remote_build_once(
                runner, project_id, config, headers, api_url, dashboard, project_data
            )
            if result[0]:  # Success
                return result
            else:
                last_error = result[2]
                console.print(f"[WARN] Build attempt {attempt} failed: {last_error}")
        except Exception as e:
            last_error = str(e)
            console.print(f"[WARN] Build attempt {attempt} error: {last_error}")

    # All retries exhausted
    console.print(f"\n[ERROR] Build failed after {max_retries} attempts")
    console.print(f"[ERROR] Last error: {last_error}")
    return (
        False,
        None,
        f"Build failed after {max_retries} attempts. Last error: {last_error}",
    )


def _run_remote_build_once(
    runner: BuildRunner,
    project_id: str,
    config: Dict[str, Any],
    headers: Dict[str, str],
    api_url: str,
    dashboard: Optional[BuildDashboard] = None,
    project_data: Optional[Dict] = None,
) -> Tuple[bool, Optional[Path], str]:
    """Single attempt at remote build (extracted for retry logic)."""
    import requests
    import zipfile
    from codevault_cli.file_browser import (
        prompt_for_source,
        check_and_use_local_path,
        extract_or_use_source,
    )

    project_name = config.get("project_name", project_id[:8])

    # Step 1: Check if user has local files they want to use
    if project_data and "local_path" in project_data:
        local_path = check_and_use_local_path(project_data["local_path"], project_name)
        if local_path:
            with tempfile.TemporaryDirectory() as tmpdir:
                project_dir, error = extract_or_use_source(local_path, Path(tmpdir))
                if error:
                    return False, None, error

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
                    except Exception as e:
                        console.print(f"[WARN] Could not load config.json: {e}")

                return runner.run_build(project_dir, config)

    # Step 2: Try to download from API
    console.print("[INFO] Attempting to download project bundle from server...")
    bundle_downloaded = False
    download_error = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            bundle_path = tmpdir / "bundle.zip"

            # Try to download
            bundle_params = {}
            if config.get("license_key"):
                bundle_params["license_id"] = config["license_key"]

            resp = requests.get(
                f"{api_url}/projects/{project_id}/build-bundle",
                headers=headers,
                params=bundle_params,
                timeout=120,
                stream=True,
            )

            if resp.status_code == 200:
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(bundle_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            # Could add progress callback here

                # Verify download
                if bundle_path.exists() and bundle_path.stat().st_size > 0:
                    bundle_downloaded = True
                    console.print(
                        f"[OK] Downloaded bundle: {bundle_path.stat().st_size} bytes"
                    )
                else:
                    download_error = "Bundle file is empty"
            else:
                download_error = f"Server returned HTTP {resp.status_code}"

    except Exception as e:
        download_error = str(e)

    # If download succeeded, extract and build
    if bundle_downloaded:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                bundle_path = tmpdir / "bundle.zip"
                project_dir = tmpdir / "project"
                project_dir.mkdir()

                # Extract bundle
                try:
                    with zipfile.ZipFile(bundle_path, "r") as zf:
                        zf.extractall(project_dir)
                    console.print("[OK] Extracted bundle successfully")
                except zipfile.BadZipFile as e:
                    return False, None, f"Invalid ZIP file: {e}"

                # Load config.json if present
                bundle_config_path = project_dir / "config.json"
                if bundle_config_path.exists():
                    try:
                        bundle_config = json.loads(bundle_config_path.read_text())
                        for key in [
                            "license_key",
                            "api_url",
                            "server_url",
                            "language",
                            "entry_file",
                            "output_name",
                        ]:
                            if key in bundle_config and bundle_config[key]:
                                config[key] = bundle_config[key]
                    except Exception:
                        pass

                return runner.run_build(project_dir, config)
        except Exception as e:
            download_error = str(e)
            bundle_downloaded = False

    # Step 3: Download failed, ask user to provide source manually
    if not bundle_downloaded:
        console.print(
            f"\n[yellow]Download failed: {download_error or 'Unknown error'}[/yellow]"
        )
        console.print("[INFO] The server bundle is not available.")
        console.print()

        source_path = prompt_for_source(project_name)
        if not source_path:
            return False, None, "Build cancelled - no source provided"

        # Process the user-selected source
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, error = extract_or_use_source(source_path, Path(tmpdir))
            if error:
                return False, None, error

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
                except Exception as e:
                    console.print(f"[WARN] Could not load config.json: {e}")

            return runner.run_build(project_dir, config)

    return False, None, "Unexpected error in build process"
