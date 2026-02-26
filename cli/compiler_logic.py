import sys
import os
import json
import re
import shutil
import subprocess
import time
import select
import hashlib
import threading
import queue
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

try:
    from terminal import Colors, color_print, print_progress_bar
except ImportError:
    from cli.terminal import Colors, color_print, print_progress_bar

try:
    from generators.python_generator import get_python_wrapper
    from generators.nodejs_generator import get_nodejs_wrapper_inline
except ImportError:
    from cli.generators.python_generator import get_python_wrapper
    from cli.generators.nodejs_generator import get_nodejs_wrapper_inline

try:
    from url_utils import normalize_server_url
except ImportError:
    from cli.url_utils import normalize_server_url

try:
    from audit import log_build_failure, log_security_event, log_obfuscation_stats
except ImportError:
    from cli.audit import log_build_failure, log_security_event, log_obfuscation_stats

try:
    from compiler_constants import (
        JAVASCRIPT_OBFUSCATOR_VERSION,
        OBFUSCATE_TIMEOUT,
        PARALLEL_WORKERS,
        COMPILE_TIMEOUT,
    )
except ImportError:
    from cli.compiler_constants import (
        JAVASCRIPT_OBFUSCATOR_VERSION,
        OBFUSCATE_TIMEOUT,
        PARALLEL_WORKERS,
        COMPILE_TIMEOUT,
    )


def _read_output_thread(pipe, output_queue):
    """Thread function to read from pipe and put lines in queue."""
    try:
        for line in iter(pipe.readline, b""):
            output_queue.put(line)
    finally:
        pipe.close()


def _wait_for_output_with_timeout(process, timeout=1.0):
    """Cross-platform way to wait for output with timeout.

    On Unix: uses select.select()
    On Windows: uses threading and queue

    Returns True if output is available, False otherwise.
    """
    if sys.platform == "win32":
        # On Windows, select.select() doesn't work with pipes
        # Use a queue-based approach with threads
        if not hasattr(process, "_output_queue"):
            process._output_queue = queue.Queue()
            process._reader_thread = threading.Thread(
                target=_read_output_thread, args=(process.stdout, process._output_queue)
            )
            process._reader_thread.daemon = True
            process._reader_thread.start()

        # Check if there's data in the queue (non-blocking)
        return not process._output_queue.empty()
    else:
        # On Unix-like systems, use select.select()
        if process.stdout:
            readable, _, _ = select.select([process.stdout], [], [], timeout)
            return bool(readable)
        return False


def _readline_from_process(process):
    """Cross-platform way to read a line from process stdout."""
    if sys.platform == "win32":
        # On Windows, read from the queue
        if hasattr(process, "_output_queue"):
            try:
                return process._output_queue.get(block=False)
            except queue.Empty:
                return None
        return None
    else:
        # On Unix-like systems, read directly
        if process.stdout:
            return process.stdout.readline()
        return None


# =============================================================================
# Path Traversal Prevention & Security
# =============================================================================


class PathTraversalError(Exception):
    """Raised when a path traversal attack is detected."""

    pass


class BuildTimeoutError(Exception):
    """Raised when build exceeds time limit."""

    pass


# Regex for valid output names: alphanumeric, underscores, hyphens, dots (no path separators)
OUTPUT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,99}$")

# Dangerous path patterns that could indicate traversal attempts
DANGEROUS_PATTERNS = [
    "..",  # Parent directory traversal
    "//",  # Double slashes
    "\\\\",  # Double backslashes
    "\x00",  # Null byte injection
    "%2e",  # URL-encoded dot
    "%2f",  # URL-encoded forward slash
    "%5c",  # URL-encoded backslash
    "%00",  # URL-encoded null
    "%c0%ae",  # UTF-8 overlong encoding attack (dot)
    "%c0%af",  # UTF-8 overlong encoding attack (slash)
]


def _handle_security_violation(
    violation_type: str, details: Dict[str, Any], entry_file: Optional[str] = None
) -> None:
    """Log security violation and display warning.

    Args:
        violation_type: Type of security violation
        details: Additional details about the violation
        entry_file: Optional entry file name for context
    """
    log_security_event(
        violation_type, {**details, "entry_file": entry_file, "source": "cli_compiler"}
    )
    print(
        f"\n{Colors.RED}[SECURITY] {violation_type.upper()}: {details.get('message', 'Unknown violation')}{Colors.RESET}"
    )
    print(
        f"{Colors.YELLOW}   This event has been logged for security review.{Colors.RESET}\n"
    )


def validate_entry_file(entry_file: str, project_dir: Path) -> Path:
    """Validate entry file path to prevent path traversal.

    Args:
        entry_file: The entry file path from config
        project_dir: The base project directory

    Returns:
        Validated absolute path to the entry file

    Raises:
        PathTraversalError: If path traversal is detected
    """
    if not entry_file:
        _handle_security_violation(
            "empty_entry_file", {"message": "Entry file cannot be empty"}, entry_file
        )
        raise PathTraversalError("Entry file cannot be empty")

    # Check for dangerous patterns in the raw input
    entry_lower = entry_file.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in entry_lower:
            _handle_security_violation(
                "traversal_pattern",
                {
                    "message": f"Contains forbidden pattern '{pattern}'",
                    "pattern": pattern,
                },
                entry_file,
            )
            raise PathTraversalError(
                f"Invalid entry file path: contains forbidden pattern '{pattern}'"
            )

    # Normalize the path
    entry_path = Path(entry_file)

    # Ensure it's not absolute (should be relative to project)
    if entry_path.is_absolute():
        _handle_security_violation(
            "absolute_path",
            {"message": "Absolute path not allowed", "path": str(entry_path)},
            entry_file,
        )
        raise PathTraversalError("Entry file must be a relative path, not absolute")

    # Resolve relative to project directory
    full_path = (project_dir / entry_path).resolve()
    project_resolved = project_dir.resolve()

    # Verify the resolved path is within the project directory
    try:
        full_path.relative_to(project_resolved)
    except ValueError:
        _handle_security_violation(
            "path_escape",
            {
                "message": "Path resolves outside project directory",
                "path": str(full_path),
            },
            entry_file,
        )
        raise PathTraversalError(
            f"Path traversal detected: entry file '{entry_file}' "
            f"resolves outside project directory"
        )

    return full_path


def validate_output_name(output_name: str) -> str:
    """Validate and sanitize output name to prevent path traversal in output files.

    Args:
        output_name: The desired output filename (without extension)

    Returns:
        Validated and sanitized output name

    Raises:
        PathTraversalError: If the output name is invalid after sanitization
    """
    if not output_name:
        raise PathTraversalError("Output name cannot be empty")

    # Strip common path separators first
    output_name = output_name.replace("/", "").replace("\\", "")

    # Check for dangerous patterns
    output_lower = output_name.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in output_lower:
            raise PathTraversalError(
                f"Invalid output name: contains forbidden pattern '{pattern}'"
            )

    # Auto-sanitize: replace spaces with underscores
    original_name = output_name
    output_name = output_name.replace(" ", "_")

    # Replace multiple consecutive underscores with single underscore
    output_name = re.sub(r"_+", "_", output_name)

    # Remove leading/trailing underscores and dots
    output_name = output_name.strip("_.")

    # Validate against allowed pattern
    if not OUTPUT_NAME_PATTERN.match(output_name):
        raise PathTraversalError(
            f"Invalid output name '{original_name}' (sanitized to '{output_name}'): "
            "must be alphanumeric with underscores, hyphens, or dots only "
            "(max 100 chars, must start with alphanumeric)"
        )

    return output_name


def validate_include_package(package_name: str) -> str:
    """Validate Nuitka include-package names to prevent command injection.

    Args:
        package_name: The package name from config

    Returns:
        Validated package name

    Raises:
        PathTraversalError: If the package name is invalid
    """
    if not package_name:
        return ""

    # Skip __pycache__
    if package_name == "__pycache__":
        return ""

    # Convert path separators to dots for module names
    module_name = package_name.replace("/", ".").replace("\\", ".")

    # Validate: only alphanumeric, dots, underscores
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", module_name):
        raise PathTraversalError(
            f"Invalid package name '{package_name}': contains invalid characters"
        )

    # Prevent double dots (path traversal attempt)
    if ".." in module_name:
        raise PathTraversalError(
            f"Invalid package name '{package_name}': contains '..' sequence"
        )

    return module_name


def safe_resolve_path(base_dir: Path, relative_path: str) -> Path:
    """Safely resolve a relative path against a base directory.

    Prevents path traversal by ensuring the result stays within base_dir.

    Args:
        base_dir: The base directory (must exist)
        relative_path: The relative path to resolve

    Returns:
        The resolved absolute path

    Raises:
        PathTraversalError: If traversal is detected or path escapes base
    """
    if not base_dir.exists():
        raise PathTraversalError(f"Base directory does not exist: {base_dir}")

    base_resolved = base_dir.resolve()

    # Handle empty or current directory references
    if not relative_path or relative_path in (".", "./"):
        return base_resolved

    # Check for dangerous patterns
    path_lower = relative_path.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in path_lower:
            raise PathTraversalError(
                f"Invalid path: contains forbidden pattern '{pattern}'"
            )

    # Resolve and validate
    target = (base_resolved / relative_path).resolve()

    try:
        target.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalError(
            f"Path traversal detected: '{relative_path}' escapes base directory"
        )

    return target


def inject_license_wrapper(project_dir: Path, config: Dict[str, Any]) -> bool:
    """Inject license validation code into entry file.

    Args:
        project_dir: The project directory path
        config: Build configuration dictionary

    Returns:
        bool: True if injection successful, False otherwise
    """
    entry_file_path = config.get("entry_file", "")
    license_key = config.get("license_key", "DEMO")

    try:
        entry_file = validate_entry_file(entry_file_path, project_dir)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        log_security_event(
            "traversal_injection", {"error": str(e), "entry_file": entry_file_path}
        )
        return False

    if not entry_file.exists():
        for f in project_dir.rglob("*.py"):
            if f.name == config["entry_file"] or f.name == "main.py":
                entry_file = f
                break

    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {config['entry_file']}", flush=True)
        log_security_event("missing_entry_file", {"entry_file": entry_file_path})
        return False

    try:
        original_code = entry_file.read_text(encoding="utf-8")
        server_url = config.get("server_url", "http://localhost:8000")
        server_url = normalize_server_url(server_url)
        lease_enabled = config.get("lease_enabled", False)
        show_branding = config.get("show_branding", True)

        branding_status = (
            "ENABLED (Free tier)" if show_branding else "DISABLED (Pro/Enterprise)"
        )
        print(f"[BUILD] Branding: {branding_status}", flush=True)

        public_key = config.get("signing_public_key") or ""
        secret_key = config.get("signing_secret") or "dev-secret-key"
        heartbeat_interval = config.get("heartbeat_interval", 300)

        app_name = (
            config.get("app_name")
            or config.get("project_name")
            or "Protected Application"
        )
        brand_name = config.get("brand_name", "CodeVault")
        brand_url = config.get("brand_url", "https://codevault.dev")
        brand_primary_color = config.get("brand_primary_color", "#6366f1")
        binary_hash = config.get("binary_hash", "skip")

        wrapper = get_python_wrapper(
            license_key,
            server_url,
            secret_key,
            lease_enabled,
            show_branding,
            public_key=public_key,
            heartbeat_interval=heartbeat_interval,
            app_name=app_name,
            brand_name=brand_name,
            brand_url=brand_url,
            brand_primary_color=brand_primary_color,
            binary_hash=binary_hash,
        )
        entry_file.write_text(wrapper + original_code, encoding="utf-8")
        print(f"[BUILD] Injected wrapper into: {entry_file.name}", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to inject wrapper: {e}", flush=True)
        log_build_failure(
            project_id=config.get("project_id"),
            language="python",
            error_message=f"Wrapper injection failed: {str(e)}",
            error_type="injection_error",
            license_mode=license_key,
        )
        return False


def inject_js_wrapper(entry_file: Path, config: Dict[str, Any]) -> bool:
    """Inject JS license wrapper by wrapping entry file in async IIFE.

    Args:
        entry_file: Path to the entry file
        config: Build configuration dictionary

    Returns:
        bool: True if injection successful, False otherwise
    """
    license_key = config.get("license_key", "DEMO")

    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {entry_file}", flush=True)
        log_security_event("missing_entry_file_js", {"entry_file": str(entry_file)})
        return False

    try:
        original_code = entry_file.read_text(encoding="utf-8")
        server_url = config.get("server_url", "http://localhost:8000")
        server_url = normalize_server_url(server_url)
        lease_enabled = config.get("lease_enabled", False)
        show_branding = config.get("show_branding", True)

        branding_status = (
            "ENABLED (Free tier)" if show_branding else "DISABLED (Pro/Enterprise)"
        )
        print(f"[BUILD] Branding: {branding_status}", flush=True)

        shebang = ""
        if original_code.startswith("#!"):
            first_newline = original_code.find("\n")
            if first_newline != -1:
                shebang = original_code[: first_newline + 1]
                original_code = original_code[first_newline + 1 :]
                print(f"[BUILD] Stripped shebang: {shebang.strip()}", flush=True)

        public_key = config.get("signing_public_key") or ""
        heartbeat_interval = config.get("heartbeat_interval", 300)
        app_name = (
            config.get("app_name")
            or config.get("project_name")
            or "Protected Application"
        )
        binary_hash = config.get("binary_hash", "skip")

        prefix, suffix = get_nodejs_wrapper_inline(
            license_key,
            server_url,
            lease_enabled,
            show_branding,
            public_key=public_key,
            heartbeat_interval=heartbeat_interval,
            app_name=app_name,
            binary_hash=binary_hash,
        )
        wrapped_code = shebang + prefix + original_code + suffix
        entry_file.write_text(wrapped_code, encoding="utf-8")
        print(f"[BUILD] Injected JS wrapper into: {entry_file.name}", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to inject JS wrapper: {e}", flush=True)
        log_build_failure(
            project_id=config.get("project_id"),
            language="nodejs",
            error_message=f"JS wrapper injection failed: {str(e)}",
            error_type="injection_error",
            license_mode=license_key,
        )
        return False


def run_compiler(
    project_dir: Path, config: Dict[str, Any]
) -> Tuple[bool, Optional[Path]]:
    """Dispatch to correct compiler based on language.

    Args:
        project_dir: The project directory path
        config: Build configuration dictionary

    Returns:
        Tuple[bool, Optional[Path]]: (success: bool, build_dir: Path | None)
    """
    lang = config.get("language", "python")
    if lang == "nodejs":
        return run_pkg(project_dir, config)
    else:
        success = run_nuitka(project_dir, config)
        return success, project_dir if success else None


def run_js_obfuscation(project_dir: Path) -> bool:
    """Run javascript-obfuscator on project directory.

    Obfuscates all JS files (excluding node_modules) to make code
    harder to reverse-engineer. Uses optimized settings for faster builds
    while maintaining strong protection.

    [WARN] SECURITY NOTICE:
    - Obfuscation does NOT provide strong security - just slows reverse engineering
    - Obfuscator runs locally but downloads from npm if not installed
    - Obfuscation can break code if dependencies are incompatible
    - Always test obfuscated code before distribution

    Returns:
        bool: True if successful, False otherwise
    """
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"

    # Find JS files to obfuscate (excluding node_modules)
    js_files = [f for f in project_dir.rglob("*.js") if "node_modules" not in str(f)]

    if not js_files:
        print("   No JS files to obfuscate")
        return True

    print(f"   Obfuscating {len(js_files)} JS files in parallel...")

    # Obfuscation settings: BALANCED profile (SEC5)
    # Optimized for security with reasonable build time
    obfuscate_args = [
        "--compact",
        "true",
        "--rename-globals",
        "true",
        "--rename-properties",
        "false",  # Can break code, keep off
        # String protection (balanced)
        "--string-array",
        "true",
        "--string-array-threshold",
        "1.0",
        "--string-array-encoding",
        "base64",  # Changed from "rc4" - rc4 is weak, base64 is sufficient
        "--string-array-shuffle",
        "true",
        # Identifier obfuscation
        "--identifier-names-generator",
        "hexadecimal",
        # Advanced protection (balanced)
        "--control-flow-flattening",
        "true",
        "--control-flow-flattening-threshold",
        "0.5",  # Was 0.75 - reduced for better performance
        "--dead-code-injection",
        "true",
        "--dead-code-injection-threshold",
        "0.2",  # Was 0.4 - reduced for better performance
        "--self-defending",
        "true",
        "--split-strings",
        "false",  # Disabled for better performance
        "--split-strings-chunk-length",
        "10",
        # Preserve require/import statements
        "--ignore-imports",
        "true",
    ]

    def _obfuscate_single_file(js_file: Path) -> tuple[Path, bool, str]:
        """Obfuscate a single file, return success status."""
        try:
            cmd = [
                npx_cmd,
                "-y",
                f"javascript-obfuscator@{JAVASCRIPT_OBFUSCATOR_VERSION}",
                str(js_file),
                "--output",
                str(js_file),
            ] + obfuscate_args

            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=OBFUSCATE_TIMEOUT,
                stdin=subprocess.DEVNULL,  # Prevent blocking on input prompts
            )

            return (
                js_file,
                result.returncode == 0,
                result.stderr if result.returncode != 0 else "",
            )

        except subprocess.TimeoutExpired:
            return (js_file, False, "Timeout")
        except Exception as e:
            return (js_file, False, str(e))

    try:
        # Process files in parallel using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed

        start_time = time.time()
        failed_files = []

        total = len(js_files)

        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
            # Submit all files
            future_to_file = {
                executor.submit(_obfuscate_single_file, js_file): js_file
                for js_file in js_files
            }

            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_file):
                completed += 1
                js_file, success, error = future.result()

                if not success:
                    failed_files.append((js_file, error))

                # Show progress bar
                percent = int((completed / total) * 100)
                bar_length = 25
                filled = int(bar_length * completed / total)
                bar = "#" * filled + "-" * (bar_length - filled)

                print(
                    f"\r   [{bar}] {percent}% ({completed}/{total})", end="", flush=True
                )

        duration_ms = int((time.time() - start_time) * 1000)

        print()  # New line after progress

        # Log obfuscation statistics
        log_obfuscation_stats(
            files_processed=len(js_files),
            files_failed=len(failed_files),
            duration_ms=duration_ms,
        )

        if failed_files:
            print(
                f"   [WARN] {len(failed_files)}/{len(js_files)} files had obfuscation warnings"
            )
            # Only show first 3 errors
            for js_file, error in failed_files[:3]:
                print(f"   - {js_file.name}: {error[:100]}")
            return len(failed_files) < len(js_files) * 0.5  # Return True if <50% failed

        print(f"   [OK] Obfuscation complete ({duration_ms}ms)")
        return True

    except ImportError:
        # ThreadPoolExecutor not available
        print("   [WARN] Parallel processing unavailable, using sequential mode")
        failed_count = 0
        for js_file in js_files:
            _, success, _ = _obfuscate_single_file(js_file)
            if not success:
                failed_count += 1

        log_obfuscation_stats(
            files_processed=len(js_files), files_failed=failed_count, duration_ms=0
        )
        return failed_count == 0

    except Exception as e:
        print(f"   Obfuscation error: {e}")
        return False


def run_pkg(project_dir: Path, config: Dict[str, Any]) -> Tuple[bool, Optional[Path]]:
    """Run pkg compilation for Node.js.

    Args:
        project_dir: The project directory path
        config: Build configuration dictionary

    Returns:
        Tuple[bool, Optional[Path]]: (success: bool, build_dir: Path | None)

    [WARN] SECURITY NOTICE:
    - pkg bundles Node.js code but does NOT obfuscate by default
    - npm install may download packages from the internet
    - No container isolation - runs directly on your local machine
    - Only compile code you trust
    """
    entry_file = config.get("entry_file", "")
    output_name = config.get("output_name") or config.get("project_name") or "output"

    # Validate entry file path for security
    try:
        entry_path = validate_entry_file(entry_file, project_dir)
    except PathTraversalError as e:
        color_print(f"[ERROR] Security violation: {e}", Colors.RED)
        return False, None

    # Validate output name for security
    try:
        original_name = output_name
        output_name = validate_output_name(output_name)
        if original_name != output_name:
            print(f"[INFO] Output name sanitized: '{original_name}' -> '{output_name}'")
    except PathTraversalError as e:
        color_print(f"[ERROR] Security violation: {e}", Colors.RED)
        return False, None

    compiler_opts = config.get("compiler_options", {})

    # B26: Support platform targeting
    platform_target = config.get("platform")
    if platform_target:
        # Map platform to pkg target format
        platform_map = {"windows": "win", "linux": "linux", "macos": "macos"}
        platform_code = platform_map.get(platform_target, "win")
        target = f"node20-{platform_code}-x64"
        color_print(f"[T] Target platform: {platform_target} ({target})", Colors.CYAN)
    else:
        target = compiler_opts.get("target", "node20-win-x64")

    # Validate target format (should be like node20-win-x64)
    if not re.match(r"^node\d+-[a-z]+-[a-z0-9]+$", target):
        color_print(f"[ERROR] Invalid target format: {target}", Colors.RED)
        return False, None

    # Find package.json
    package_json = None

    search_dir = entry_path.parent
    while search_dir >= project_dir:
        candidate = search_dir / "package.json"
        if candidate.exists():
            package_json = candidate
            break
        if search_dir == project_dir:
            break
        search_dir = search_dir.parent

    if not package_json and (project_dir / "package.json").exists():
        package_json = project_dir / "package.json"

    if not package_json:
        color_print(
            "[WARN] No package.json found - skipping npm install", Colors.YELLOW
        )
        pkg_cwd = project_dir
    else:
        pkg_cwd = package_json.parent
        node_modules = pkg_cwd / "node_modules"

        # Downgrade axios logic...
        try:
            pkg_json_content = json.loads(package_json.read_text(encoding="utf-8"))
            deps = pkg_json_content.get("dependencies", {})
            if "axios" in deps:
                axios_ver = deps["axios"]
                if (
                    axios_ver.startswith("^1")
                    or axios_ver.startswith("~1")
                    or axios_ver.startswith("1")
                ):
                    deps["axios"] = "0.27.2"
                    pkg_json_content["dependencies"] = deps
                    package_json.write_text(
                        json.dumps(pkg_json_content, indent=2), encoding="utf-8"
                    )
                    print("   ⚙️ Downgraded axios to 0.27.2 (pkg compatibility)")
        except Exception as e:
            print(f"   [WARN] Could not check axios version: {e}")

        if not node_modules.exists():
            color_print("[PKG] Installing npm dependencies...", Colors.CYAN)

            # Try to detect dependency count for estimation
            try:
                pkg_json_content = json.loads(package_json.read_text(encoding="utf-8"))
                dep_count = len(pkg_json_content.get("dependencies", {}))
                print(f"   Found {dep_count} dependencies (est. {dep_count * 2}s)")
            except Exception:
                pass

            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
            try:
                # B16: Use --prefer-offline --no-audit --no-fund for faster installs
                # B15: Add timeout to prevent hanging
                from compiler_constants import PKG_TIMEOUT

                process = subprocess.Popen(
                    [
                        npm_cmd,
                        "install",
                        "--production",
                        "--prefer-offline",
                        "--no-audit",
                        "--no-fund",
                    ],
                    cwd=pkg_cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )

                # Parse output for progress indicators with timeout
                spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                spinner_idx = 0
                last_update = time.time()
                start_time = time.time()
                last_output_time = time.time()
                no_output_timeout = 60  # Kill if no output for 60 seconds

                while True:
                    # B15: Check for timeout
                    elapsed = time.time() - start_time
                    if elapsed > PKG_TIMEOUT:
                        process.kill()
                        raise subprocess.TimeoutExpired(process.args, PKG_TIMEOUT)

                    # Check for no-output timeout (critical fix)
                    time_since_output = time.time() - last_output_time
                    if time_since_output > no_output_timeout:
                        print(
                            f"\n[ERROR] No output for {no_output_timeout}s - npm may be stuck"
                        )
                        process.kill()
                        raise subprocess.TimeoutExpired(process.args, no_output_timeout)

                    # NON-BLOCKING read with cross-platform helper
                    if _wait_for_output_with_timeout(process, timeout=1.0):
                        line = _readline_from_process(process)
                        if line:
                            last_output_time = time.time()  # Reset timer
                            line_str = (
                                line.decode("utf-8", errors="replace")
                                if isinstance(line, bytes)
                                else line
                            )
                            # Look for progress indicators in npm output
                            if (
                                "added" in line_str.lower()
                                or "removed" in line_str.lower()
                            ):
                                print(
                                    f"\r   [OK] {line_str.strip()[:80]}",
                                    end="",
                                    flush=True,
                                )

                    # Show spinner while processing
                    current_time = time.time()
                    if current_time - last_update > 0.2:
                        spinner_idx = (spinner_idx + 1) % len(spinner)
                        print(
                            f"\r   {spinner[spinner_idx]} Installing... ",
                            end="",
                            flush=True,
                        )
                        last_update = current_time

                    if process.poll() is not None:
                        break

                process.wait()

                if process.returncode == 0:
                    print(f"\r   [OK] Dependencies installed{' ' * 40}")
                else:
                    print(f"\r   [WARN] npm install completed with warnings{' ' * 40}")

            except subprocess.TimeoutExpired:
                color_print(
                    f"\n[ERROR] npm install timed out after {PKG_TIMEOUT}s", Colors.RED
                )
                return False, None
            except FileNotFoundError:
                color_print("\n[ERROR] npm not found. Install Node.js.", Colors.RED)
                return False, None
        else:
            print("   [OK] node_modules already exists")

        # Add pkg config for ESM/CJS and ensure all dependencies are bundled
        try:
            pkg_json_content = json.loads(package_json.read_text(encoding="utf-8"))
            if "pkg" not in pkg_json_content:
                pkg_json_content["pkg"] = {}
            pkg_json_content["pkg"]["scripts"] = pkg_json_content["pkg"].get(
                "scripts", []
            )
            pkg_json_content["pkg"]["assets"] = pkg_json_content["pkg"].get(
                "assets", []
            )

            # Add all JS files from node_modules (critical for express, axios, etc.)
            # pkg needs these in assets to bundle them properly
            asset_patterns = [
                "node_modules/**/*.js",
                "node_modules/**/*.cjs",
                "node_modules/**/*.json",
                "node_modules/**/*.node",  # Native addons
            ]
            for pat in asset_patterns:
                if pat not in pkg_json_content["pkg"]["assets"]:
                    pkg_json_content["pkg"]["assets"].append(pat)

            # Add all project source files to scripts for bytecode compilation
            if "build/**/*.js" not in pkg_json_content["pkg"]["scripts"]:
                pkg_json_content["pkg"]["scripts"].append("build/**/*.js")
            if "src/**/*.js" not in pkg_json_content["pkg"]["scripts"]:
                pkg_json_content["pkg"]["scripts"].append("src/**/*.js")

            package_json.write_text(
                json.dumps(pkg_json_content, indent=2), encoding="utf-8"
            )
            print("   [PKG] Configured package.json for dependency bundling")
        except Exception:
            pass

    # Run obfuscation if enabled in project settings
    obfuscate_enabled = config.get("obfuscate_enabled", False)
    if obfuscate_enabled:
        color_print("[SEC] Obfuscating JavaScript code...", Colors.CYAN)
        if run_js_obfuscation(pkg_cwd):
            color_print("   [OK] Obfuscation complete", Colors.GREEN)
        else:
            color_print("   [WARN] Continuing without obfuscation...", Colors.YELLOW)
    elif config.get("fast_build"):
        print(
            f"   {Colors.DIM}[FAST MODE] Skipping obfuscation for faster build{Colors.RESET}"
        )
    else:
        # Check if fast_build is explicitly false (user wants normal obfuscation but it's off)
        print(f"   {Colors.DIM}[INFO] Obfuscation disabled in settings{Colors.RESET}")

    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    if package_json:
        entry_path_rel = entry_path.relative_to(pkg_cwd)
    else:
        entry_path_rel = entry_file

    # Build pkg command with optimizations
    # Using @yao-pkg/pkg (maintained fork of archived vercel/pkg)
    cmd = [
        npx_cmd,
        "-y",
        "@yao-pkg/pkg",
        str(entry_path_rel),
        "--targets",
        target,
        "--output",
        str(pkg_cwd / output_name),
        "--compress",
        "GZip",  # Optimization: Compress for smaller output
        "--public-packages",
        "*",  # Include all public npm packages (express, axios, etc.)
    ]

    # Debug mode: show less verbose output for cleaner logs
    if not config.get("fast_build"):
        cmd.append("--debug")  # Show more detailed output for debugging

    print(f"   Command: {' '.join(cmd)}")
    print(f"   CWD: {pkg_cwd}")

    # Show time warning for large builds
    if not config.get("fast_build"):
        print(
            f"\n   {Colors.YELLOW}[T]️  This may take 2-5 minutes depending on project size{Colors.RESET}"
        )

    try:
        # Use real-time streaming for pkg progress
        print(f"\n   {Colors.CYAN}Bundling with pkg...{Colors.RESET}")

        process = subprocess.Popen(
            cmd,
            cwd=pkg_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,  # Prevent blocking on input prompts
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = 0
        last_update = time.time()
        start_time = time.time()
        last_output_time = time.time()
        current_phase = "analyzing"
        no_output_timeout = 60  # Kill if no output for 60 seconds

        print(f"[pkg] Started with PID {process.pid}")
        print(f"[pkg] Working directory: {pkg_cwd}")
        print("[pkg] Waiting for output...")

        while True:
            elapsed = time.time() - start_time

            # Check for no-output timeout (critical fix)
            time_since_output = time.time() - last_output_time
            if time_since_output > no_output_timeout:
                print(
                    f"\n[ERROR] No output for {no_output_timeout}s - pkg may be stuck"
                )
                process.kill()
                raise subprocess.TimeoutExpired(process.args, no_output_timeout)

            # NON-BLOCKING read with cross-platform helper
            line = None
            if _wait_for_output_with_timeout(process, timeout=1.0):
                line = _readline_from_process(process)
                if line:
                    last_output_time = time.time()
                    line_str = (
                        line.decode("utf-8", errors="replace")
                        if isinstance(line, bytes)
                        else line
                    )

                    # Parse pkg output for phase detection
                    if ">>> Bundling" in line_str or "bundling" in line_str.lower():
                        current_phase = "bundling"
                    elif "compil" in line_str.lower():
                        current_phase = "compiling"
                    elif "pack" in line_str.lower():
                        current_phase = "packaging"

            if process.poll() is not None:
                break

            current_time = time.time()
            elapsed_int = int(current_time - start_time)
            mins, secs = divmod(elapsed_int, 60)
            elapsed_str = f"{mins}m{secs}s"

            # Estimate progress based on time (pkg doesn't output percentages)
            # Typical pkg build takes 1-5 minutes
            estimated_percent = min(95, int(elapsed / 180 * 100))  # Assume ~3 min max

            # Update display every 0.5s
            if current_time - last_update > 0.5:
                spinner_idx = (spinner_idx + 1) % len(spinner)
                last_update = current_time

                # Show progress bar with estimated progress
                print_progress_bar(
                    estimated_percent,
                    width=30,
                    phase=current_phase,
                    elapsed_time=elapsed_str,
                )

            # Parse pkg output for phase detection
            if line and (">>> Bundling" in line or "bundling" in line.lower()):
                current_phase = "bundling"
            elif line and "compil" in line.lower():
                current_phase = "compiling"
            elif line and "pack" in line.lower():
                current_phase = "packaging"

        process.wait()
        print("\r" + " " * 70 + "\r", end="", flush=True)

        if process.returncode != 0:
            # Double bell for error
            sys.stdout.write("\a\a")
            sys.stdout.flush()
            color_print(
                f"[ERROR] pkg failed with exit code {process.returncode}", Colors.RED
            )
            return False, None

        color_print("[OK] pkg completed successfully", Colors.GREEN)

        # Verify the output file exists
        expected_exe = pkg_cwd / f"{output_name}.exe"
        print(f"   [S] Checking for: {expected_exe}")

        if not expected_exe.exists():
            # Try alternative name patterns (pkg sometimes uses different naming)
            for p in pkg_cwd.glob(f"{output_name}*.exe"):
                expected_exe = p
                print(f"   [WARN] Found alternative: {expected_exe}")
                break
        if not expected_exe.exists():
            # Also check for file without .exe extension (pkg might name it differently)
            for p in pkg_cwd.glob("*.exe"):
                if output_name.lower() in p.stem.lower():
                    expected_exe = p
                    print(f"   [WARN] Found partial match: {expected_exe}")
                    break
        if not expected_exe.exists():
            # Last resort: search entire parent temp directory
            temp_search = []
            for parent in list(pkg_cwd.parents)[:4]:  # Search up 4 levels
                if "temp" in str(parent).lower() or "tmp" in str(parent).lower():
                    for p in parent.rglob("*.exe"):
                        if (
                            output_name.lower() in p.stem.lower()
                            or "node" in p.stem.lower()
                        ):
                            temp_search.append(p)

            if temp_search:
                color_print(
                    f"[WARN] Found exe elsewhere: {temp_search[0].name}", Colors.YELLOW
                )
                expected_exe = temp_search[0]
            else:
                color_print(
                    "[ERROR] pkg succeeded but output file not found", Colors.RED
                )
                color_print(f"   Expected: {pkg_cwd / output_name}.exe", Colors.YELLOW)
                color_print(f"   Search dir: {pkg_cwd}", Colors.YELLOW)
                exe_files = list(pkg_cwd.glob("*.exe"))
                if exe_files:
                    color_print(
                        f"   Found exe files: {[p.name for p in exe_files]}",
                        Colors.YELLOW,
                    )
                return False, None

        color_print(f"   [OK] Output found: {expected_exe.name}", Colors.GREEN)
        return True, pkg_cwd
    except FileNotFoundError:
        color_print("[ERROR] npx/pkg not found. Install Node.js.", Colors.RED)
        return False, None


def detect_heavy_dependencies(project_dir: Path) -> bool:
    """Quickly check if project uses heavy dependencies.

    Args:
        project_dir: The project directory to check

    Returns:
        bool: True if heavy ML/data libraries are detected
    """
    check_files = []

    # Check entry file and first 5 python files
    py_files = list(project_dir.rglob("*.py"))[:6]

    for py_file in py_files:
        if py_file.exists():
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore").lower()
                check_files.append(content)
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read or decoded
                continue

    # Look for heavy dependency imports
    heavy_patterns = [
        "import numpy",
        "from numpy",
        "import pandas",
        "from pandas",
        "import sklearn",
        "from sklearn",
        "import tensorflow",
        "from tensorflow",
        "import torch",
        "from torch",
        "import scipy",
        "from scipy",
    ]

    content_text = "\n".join(check_files)
    return any(pattern in content_text for pattern in heavy_patterns)


def detect_heavy_deps_detailed(project_dir: Path) -> list:
    """Detect which heavy dependencies are used (detailed version).

    Args:
        project_dir: The project directory to check

    Returns:
        list: List of detected heavy dependency names
    """
    heavy_map = {
        "numpy": ["numpy"],
        "pandas": ["pandas"],
        "scipy": ["scipy"],
        "sklearn": ["sklearn", "scikit-learn"],
        "tensorflow": ["tensorflow"],
        "torch": ["torch", "pytorch"],
    }

    found = []
    py_files = [f for f in project_dir.rglob("*.py") if f.is_file()][
        :10
    ]  # Check first 10

    for dep_name, import_patterns in heavy_map.items():
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore").lower()
                if any(pattern in content for pattern in import_patterns):
                    if dep_name not in found:
                        found.append(dep_name)
                    break
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read or decoded
                continue

    return found


def parse_nuitka_percent(line: str) -> int | None:
    """Extract percentage from Nuitka output like 'GGG:  15% [1500/10000]'

    Args:
        line: A line of Nuitka output

    Returns:
        The extracted percentage as an integer, or None if no percentage found
    """
    if "%" in line:
        match = re.search(r"(\d+)%", line)
        if match:
            return int(match.group(1))
    return None


def parse_nuitka_phase(line: str) -> str:
    """Determine compilation phase from Nuitka output"""
    if "GGG:" in line or "module" in line.lower():
        return "modules"
    elif "SCons:" in line or "compile" in line.lower():
        return "C code"
    elif "link" in line.lower():
        return "linking"
    elif "onefile" in line.lower():
        return "packaging"
    return "processing"


def run_nuitka(project_dir: Path, config: Dict[str, Any]) -> bool:
    """Run Nuitka compilation for Python.

    Args:
        project_dir: The project directory path
        config: Build configuration dictionary

    Returns:
        bool: True if compilation successful

    [WARN] SECURITY NOTICE:
    - Nuitka may download packages from the internet during compilation
    - Use --assume-yes-for-downloads which can install untrusted packages
    - Only compile trusted code
    - This runs on your local machine - no network isolation
    """
    entry_file = config.get("entry_file", "")
    output_name = config.get("output_name") or config.get("project_name") or "output"
    nuitka_opts = config.get("nuitka_options", {})
    fast_build = config.get("fast_build", False)

    # Validate entry file path for security
    try:
        entry_path = validate_entry_file(entry_file, project_dir)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        log_security_event(
            "traversal_compiler", {"error": str(e), "entry_file": entry_file}
        )
        return False

    # Validate output name for security
    try:
        original_name = output_name
        output_name = validate_output_name(output_name)
        if original_name != output_name:
            print(
                f"[BUILD] Output name sanitized: '{original_name}' -> '{output_name}'",
                flush=True,
            )
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        log_security_event(
            "invalid_output_name", {"error": str(e), "output_name": original_name}
        )
        return False

    if not entry_path.exists():
        for f in project_dir.rglob("*.py"):
            if f.name == entry_file or f.name == "main.py":
                entry_path = f
                break

    if not entry_path.exists():
        print(f"[ERROR] Entry file not found: {entry_file}", flush=True)
        return False

    # SECURITY WARNING: Nuitka with --assume-yes-for-downloads can download packages
    # Add warning if this is a first-time compilation
    print(
        f"\n{Colors.YELLOW}[SECURITY] Nuitka will compile Python to machine code.{Colors.RESET}"
    )
    print(
        f"{Colors.YELLOW}    [WARN]  Network access may be used to download dependencies{Colors.RESET}"
    )
    print(f"{Colors.YELLOW}    [WARN]  Only compile code you trust{Colors.RESET}")
    print(
        f"{Colors.YELLOW}    [WARN]  No container isolation - runs directly on your system{Colors.RESET}\n"
    )

    # CPU core detection and optimization
    cpu_count = os.cpu_count() or 4
    max_jobs = min(cpu_count, 8)  # Cap at 8 to prevent memory issues

    # Check for manual job override
    env_jobs = os.environ.get("CODEVAULT_JOBS")
    if env_jobs:
        try:
            max_jobs = min(int(env_jobs), 16)  # Allow up to 16 if user explicitly sets
        except ValueError:
            pass

    # Also check for CLI override in config
    if config.get("jobs"):
        max_jobs = min(config.get("jobs"), 16)

    # Detect heavy dependencies
    has_heavy_deps = detect_heavy_dependencies(project_dir)

    # Build command based on mode
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
    ]

    # Base Nuitka options (common for both modes)
    # Note: --lto=no for faster builds (LTO adds significant compile time)
    # --assume-yes-for-downloads allows automatic dependency downloads
    base_options = [
        "--standalone",
        "--lto=no",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--enable-plugin=tk-inter",
        "--no-prefer-source-code",
        "--python-flag=no_site",
        # Optimization: Skip importing test/doc modules
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=sphinx",
        "--nofollow-import-to=setuptools",
        # Performance: Skip heavy data science libraries in import scanning
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=PIL",
        "--nofollow-import-to=matplotlib",
    ]

    # Performance: Use all available CPU cores for parallel compilation
    import os

    cpu_count = os.cpu_count() or 4
    base_options.append(f"--jobs={cpu_count}")

    # B26: Support platform targeting for cross-compilation
    platform_target = config.get("platform")
    if platform_target:
        color_print(f"[T] Target platform: {platform_target}", Colors.CYAN)
        if platform_target == "linux":
            base_options.append("--target=linux")
        elif platform_target == "macos":
            base_options.append("--target=macos")
        # Windows is default

    # Add fast-build specific optimizations
    if fast_build:
        # Fast mode: no --onefile, use --jobs
        print(f"{Colors.YELLOW}[FAST MODE]{Colors.RESET} Compiling without --onefile")
        print(
            f"{Colors.YELLOW}[FAST MODE]{Colors.RESET} Output will be a folder, not single .exe\n"
        )

        cmd.extend(base_options)
        cmd.extend(
            [
                f"--jobs={max_jobs}",
                f"--output-dir={project_dir / 'build'}",
            ]
        )
    else:
        # Standard mode: add --onefile for single executable output
        print(f"{Colors.YELLOW}[STANDARD MODE]{Colors.RESET} Compiling with --onefile")
        print(
            f"{Colors.YELLOW}[STANDARD MODE]{Colors.RESET} Output will be a single .exe file\n"
        )

        cmd.extend(base_options)
        cmd.extend(
            [
                "--onefile",
                f"--jobs={max_jobs}",
                f"--output-filename={output_name}.exe",
            ]
        )

        # For very large projects, disable console window (runs as background process)
        if has_heavy_deps or cpu_count >= 8:
            cmd.append("--windows-console-mode=disable")

    # Add include packages
    for pkg in nuitka_opts.get("include_packages", []):
        # Validate each package name for security
        try:
            module_name = validate_include_package(pkg)
            if module_name:  # Skip empty strings
                cmd.append(f"--include-package={module_name}")
        except PathTraversalError as e:
            print(f"[WARN] Skipping invalid package: {e}", flush=True)
            continue

    cmd.append(str(entry_path))

    # Print optimization info
    print(
        f"{Colors.CYAN}[OPTIMIZATION]{Colors.RESET} Using {max_jobs} CPU cores for parallel compilation"
    )
    if has_heavy_deps:
        print(
            f"{Colors.CYAN}[OPTIMIZATION]{Colors.RESET} Heavy dependencies detected - applying speed optimizations"
        )
    print(
        f"{Colors.CYAN}[OPTIMIZATION]{Colors.RESET} Expected speedup: 2-4x vs. current build\n"
    )
    print(f"[NUITKA] Starting compilation: {entry_path.name}", flush=True)

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        creationflags = 0
        if sys.platform == "win32":
            creationflags = (
                subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0x08000000
            )

        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,  # Prevent blocking on input prompts
            bufsize=0,
            env=env,
            creationflags=creationflags,
        )

        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = 0
        last_update = 0
        last_percent = 0
        last_phase = "starting"
        start_time = time.time()
        last_output_time = time.time()
        no_output_timeout = 60  # Kill if no output for 60 seconds
        heartbeat_interval = 30  # Log heartbeat every 30 seconds

        print(f"[Nuitka] Started with PID {process.pid}")
        print(f"[Nuitka] Working directory: {project_dir}")
        print(f"[Nuitka] Command: {' '.join(cmd[:5])}...")
        print("[Nuitka] Waiting for output...")

        while True:
            # B15: Check for compile timeout
            elapsed = time.time() - start_time
            if elapsed > COMPILE_TIMEOUT:
                process.kill()
                print(
                    f"\n{Colors.RED}[TIMEOUT] Compilation exceeded {COMPILE_TIMEOUT}s limit{Colors.RESET}"
                )
                raise BuildTimeoutError(
                    f"Nuitka compilation timed out after {COMPILE_TIMEOUT} seconds"
                )

            # Check for no-output timeout (critical fix for hanging)
            time_since_output = time.time() - last_output_time
            if time_since_output > no_output_timeout:
                print(
                    f"\n[ERROR] No output for {no_output_timeout}s - compiler may be stuck"
                )
                print("[ERROR] Killing process...")
                process.kill()
                raise BuildTimeoutError(f"No output for {no_output_timeout} seconds")

            # Heartbeat logging every 30 seconds
            if (
                int(elapsed) % heartbeat_interval == 0
                and int(elapsed) > 0
                and int(elapsed) != last_update
            ):
                mins, secs = divmod(int(elapsed), 60)
                print(f"\n[ALIVE] Compiler still running ({mins}m {secs}s elapsed)")

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

                    # Parse progress from Nuitka output
                    percent = parse_nuitka_percent(line)
                    if percent:
                        last_percent = percent
                        last_phase = parse_nuitka_phase(line)
                        # Show visual progress bar with phase and time
                        elapsed_int = int(elapsed)
                        mins, secs = divmod(elapsed_int, 60)
                        elapsed_str = f"{mins}m{secs}s"
                        print_progress_bar(
                            percent,
                            width=30,
                            phase=last_phase,
                            elapsed_time=elapsed_str,
                        )

                    # Log errors/warnings but don't spam output
                    if "error" in line.lower() and "no errors" not in line.lower():
                        print(f"\n[ERROR] {line}", flush=True)
                    elif (
                        "warning" in line.lower() and "no warnings" not in line.lower()
                    ):
                        print(f"\n[WARN] {line}", flush=True)

            # Update display every second
            elapsed_int = int(elapsed)
            if elapsed_int != last_update:
                last_update = elapsed_int
                spinner_idx = (spinner_idx + 1) % len(spinner)

                # Use progress bar if we have percent, otherwise use spinner
                if last_percent > 0:
                    mins, secs = divmod(elapsed_int, 60)
                    elapsed_str = f"{mins}m{secs}s"
                    print_progress_bar(
                        last_percent,
                        width=30,
                        phase=last_phase,
                        elapsed_time=elapsed_str,
                    )
                else:
                    print(
                        f"\r{spinner[spinner_idx]} Starting compilation... {elapsed_str}  ",
                        end="",
                        flush=True,
                    )

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
                                    print(f"\n[ERROR] {line}", flush=True)
                break

        # Clear line at end
        print("\r" + " " * 60 + "\r", end="", flush=True)
        process.wait()

        if process.returncode == 0:
            return True
        else:
            # Error notification (double bell)
            sys.stdout.write("\a\a")
            sys.stdout.flush()
            print(
                f"\n{Colors.RED}[NUITKA ERROR] Compilation failed with exit code {process.returncode}{Colors.RESET}"
            )
            return False

    except Exception as e:
        sys.stdout.write("\a\a")
        sys.stdout.flush()
        print(f"\n{Colors.RED}[ERROR] Nuitka error: {e}{Colors.RESET}")
        return False


def analyze_and_warn_project(project_dir: Path, config: dict) -> bool:
    """Analyze project and show warnings before build starts.

    Args:
        project_dir: The project directory
        config: Build configuration dictionary

    Returns:
        bool: True to proceed with build, False to cancel
    """
    language = config.get("language", "python")

    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.CYAN}📊 PROJECT ANALYSIS{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")

    if language == "python":
        # Count files
        py_files = [f for f in project_dir.rglob("*.py") if f.is_file()]

        # Estimate lines (sample 3 files)
        sample_files = py_files[:3] if len(py_files) >= 3 else py_files
        total_lines = 0
        for f in sample_files:
            try:
                total_lines += len(
                    f.read_text(encoding="utf-8", errors="ignore").splitlines()
                )
            except (OSError, UnicodeDecodeError) as e:
                # Skip files that can't be read or decoded, but log for debugging
                print(f"[DEBUG] Could not read {f.name}: {e}", flush=True)
                continue

        if len(sample_files) > 0 and len(py_files) > len(sample_files):
            total_lines = int(total_lines / len(sample_files) * len(py_files))

        # Check for heavy deps
        heavy_deps = detect_heavy_deps_detailed(project_dir)

        print(f"  Python files: {len(py_files)}")
        print(f"  Estimated lines: {total_lines:,}")

        if heavy_deps:
            heavy_names = ", ".join(heavy_deps)
            print(
                f"  {Colors.RED}[WARN]  Heavy dependencies: {heavy_names}{Colors.RESET}"
            )

        # Time estimation
        base_time = 30  # Base 30 seconds
        file_time = len(py_files) * 2  # 2s per file
        line_time = total_lines * 0.001  # 1ms per line
        dep_multiplier = 1.0

        if "numpy" in heavy_deps:
            dep_multiplier *= 2.5
        if "pandas" in heavy_deps:
            dep_multiplier *= 1.8
        if any(d in heavy_deps for d in ["tensorflow", "torch", "sklearn"]):
            dep_multiplier *= 2.0

        est_seconds = int((base_time + file_time + line_time) * dep_multiplier)

        # Nuitka --onefile adds 2-3x overhead
        est_onefile = est_seconds * 2.5

        print(f"\n  {Colors.YELLOW}[T]️  ESTIMATED BUILD TIME:{Colors.RESET}")

        # Show both modes if fast_build is available
        if not config.get("fast_build"):
            print(f"     Without --onefile: {est_seconds // 60}m {est_seconds % 60}s")
            print(f"     With --onefile:    {est_onefile // 60}m {est_onefile % 60}s")
        else:
            print(f"     Fast mode:         {est_seconds // 60}m {est_seconds % 60}s")

        if est_onefile > 1200:  # 20 minutes
            print(
                f"\n  {Colors.RED}[WARN]  WARNING: This is a large project!{Colors.RESET}"
            )
            print(f"  {Colors.RED}     Build may take 20-60 minutes{Colors.RESET}")
            print(f"\n  {Colors.YELLOW}💡 Tips to speed up:{Colors.RESET}")
            print("     - Add --fast-build flag (no onefile, ~15m)")
            print("     - Add --jobs=8 (use all CPU cores)")
            print("     - Build once, cache for future iterations")

            # Check if running in interactive mode
            if sys.stdin.isatty():
                print(
                    f"\n  {Colors.YELLOW}Continue with build? [Y/n]: {Colors.RESET}",
                    end="",
                )
                response = input().strip().lower()
                if response in ["n", "no"]:
                    print("  Build cancelled.")
                    return False
            else:
                # Non-interactive environment (CI/CD, scripts)
                print(
                    f"\n  {Colors.YELLOW}Non-interactive mode detected - continuing build{Colors.RESET}"
                )
                print(
                    f"  {Colors.DIM}Tip: Use --yes flag to auto-confirm in scripts{Colors.RESET}"
                )

        return True

    elif language == "nodejs":
        # Node.js estimation
        pkg_json = project_dir / "package.json"
        if pkg_json.exists():
            import json

            try:
                deps = json.loads(pkg_json.read_text()).get("dependencies", {})
                dep_count = len(deps)
                print(f"  Dependencies: {dep_count}")

                # Estimate: npm install ~2s per dep, pkg ~30-60s
                est_seconds = dep_count * 2 + 45

                print(
                    f"\n  {Colors.YELLOW}[T]️  ESTIMATED BUILD TIME: {est_seconds // 60}m{Colors.RESET}"
                )

                if dep_count > 20:
                    print(
                        f"\n  {Colors.RED}[WARN]  Large number of dependencies!{Colors.RESET}"
                    )
                    print(
                        f"  {Colors.YELLOW}     Consider: --fast-build to skip obfuscation{Colors.RESET}"
                    )

                    # Check if running in interactive mode
                    if sys.stdin.isatty():
                        print(
                            f"\n  {Colors.YELLOW}Continue with build? [Y/n]: {Colors.RESET}",
                            end="",
                        )
                        response = input().strip().lower()
                        if response in ["n", "no"]:
                            print("  Build cancelled.")
                            return False
                    else:
                        # Non-interactive environment (CI/CD, scripts)
                        print(
                            f"\n  {Colors.YELLOW}Non-interactive mode detected - continuing build{Colors.RESET}"
                        )
                        print(
                            f"  {Colors.DIM}Tip: Use --yes flag to auto-confirm in scripts{Colors.RESET}"
                        )
            except json.JSONDecodeError as e:
                print(
                    f"  {Colors.YELLOW}[WARN]  Warning: Could not parse package.json: {e}{Colors.RESET}"
                )
                print(
                    f"  {Colors.YELLOW}     Skipping dependency analysis{Colors.RESET}"
                )
            except OSError as e:
                print(
                    f"  {Colors.YELLOW}[WARN]  Warning: Could not read package.json: {e}{Colors.RESET}"
                )
                print(
                    f"  {Colors.YELLOW}     Skipping dependency analysis{Colors.RESET}"
                )

        return True

    return True


def calculate_file_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def register_binary_hash_with_server(
    project_id: str, binary_path: Path, config: Dict[str, Any]
) -> bool:
    """Register a compiled binary's hash with the server.

    This enables binary integrity checking (SEC2) - the client can verify
    that the running binary matches a known-good hash registered at build time.

    Args:
        project_id: The project ID
        binary_path: Path to the compiled binary
        config: Build configuration (must include api_url, api_key)

    Returns:
        bool: True if registration successful
    """
    if not binary_path.exists():
        print(
            f"[WARN] Binary not found for hash registration: {binary_path}", flush=True
        )
        return False

    if not project_id:
        print(
            "[WARN] No project_id provided, skipping binary hash registration",
            flush=True,
        )
        return False

    binary_hash = calculate_file_sha256(binary_path)
    binary_size = binary_path.stat().st_size

    api_url = config.get("api_url") or config.get(
        "server_url", "https://api.codevault.dev"
    )
    api_key = config.get("api_key")

    if not api_key:
        print(
            "[INFO] No API key configured, skipping binary hash registration",
            flush=True,
        )
        return False

    try:
        import requests

        payload = {
            "binary_hash": binary_hash,
            "binary_size": binary_size,
            "platform": config.get("platform", "windows"),
            "build_id": config.get("build_id", ""),
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            f"{api_url}/api/v1/projects/{project_id}/binary-hash",
            json=payload,
            headers=headers,
            timeout=15,
        )

        if resp.status_code == 200:
            print(
                f"[OK] Binary integrity hash registered: {binary_hash[:16]}...",
                flush=True,
            )
            return True
        elif resp.status_code == 401:
            print(
                "[WARN] Authentication failed for binary hash registration", flush=True
            )
            return False
        else:
            try:
                error = resp.json().get("detail", f"HTTP {resp.status_code}")
            except:
                error = f"HTTP {resp.status_code}"
            print(f"[WARN] Binary hash registration failed: {error}", flush=True)
            return False

    except requests.exceptions.Timeout:
        print("[WARN] Binary hash registration timed out", flush=True)
        return False
    except requests.exceptions.ConnectionError as e:
        print(
            f"[WARN] Could not connect to server for hash registration: {e}", flush=True
        )
        return False
    except Exception as e:
        print(f"[WARN] Binary hash registration error: {e}", flush=True)
        return False


def copy_output(
    project_dir: Path,
    config: Dict[str, Any],
    license_key: str,
    custom_output: Optional[str] = None,
    build_dir: Optional[Path] = None,
) -> None:
    """Copy compiled output to Desktop or custom path.

    Optimized output detection with minimal fallbacks for better reliability.

    Args:
        project_dir: The project directory
        config: Build configuration dictionary
        license_key: The license key used
        custom_output: Optional custom output path
        build_dir: The directory where the compiler output the exe (from run_pkg/run_nuitka)
    """
    output_name = config.get("output_name") or config.get("project_name") or "output"

    # Apply the same sanitization that was applied during compilation
    try:
        output_name = validate_output_name(output_name)
    except PathTraversalError:
        # If validation fails, fall back to a safe default
        output_name = "output"

    exe_name = f"{output_name}.exe"
    exe_path = None

    # OPTIMIZED SEARCH: Only 3 strategies instead of 5
    # Strategy 1: Use build_dir if provided (highest priority, from compiler)
    if build_dir and build_dir.exists():
        # Exact match first
        candidate = build_dir / exe_name
        if candidate.exists():
            exe_path = candidate
        else:
            # Partial match in build_dir only
            for p in build_dir.glob("*.exe"):
                if p.stem == output_name:
                    exe_path = p
                    break

    # Strategy 2: Check project_dir directly
    if not exe_path:
        candidate = project_dir / exe_name
        if candidate.exists():
            exe_path = candidate
        else:
            # Look for partial match in immediate directory
            for p in project_dir.glob("*.exe"):
                if p.stem == output_name:
                    exe_path = p
                    break

    # Strategy 3: Last resort - shallow search in parent dir (only 1 level up)
    if not exe_path:
        parent_dir = project_dir.parent
        if parent_dir.exists():
            for p in parent_dir.glob("*.exe"):
                if p.stem == output_name:
                    exe_path = p
                    break

    # Strategy 4: Extremely rare - check if nuitka/pkg placed it in a subdir of project
    if not exe_path and build_dir:
        # Nuitka might put output in a build subdirectory
        for p in build_dir.rglob("*.exe"):
            if p.stem == output_name and p.parent != build_dir:
                exe_path = p
                break

    if exe_path and exe_path.exists():
        # Register binary hash for integrity checking (SEC2)
        project_id = config.get("project_id")
        if project_id:
            register_binary_hash_with_server(project_id, exe_path, config)

        if custom_output:
            final_path = Path(custom_output)
            final_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            home = Path.home()
            desktop_paths = [home / "OneDrive" / "Desktop", home / "Desktop"]
            output_dir = next(
                (d for d in desktop_paths if d.exists()), Path.cwd() / "output"
            )
            if not output_dir.exists():
                output_dir.mkdir(exist_ok=True)
            final_path = output_dir / exe_name

        shutil.copy2(exe_path, final_path)
        size_mb = final_path.stat().st_size / (1024 * 1024)

        # Terminal bell for success
        import sys

        sys.stdout.write("\a")
        sys.stdout.flush()

        print()
        color_print(f"{'=' * 60}", Colors.GREEN)
        color_print("  [OK] BUILD SUCCESSFUL!", Colors.GREEN)
        color_print(f"{'=' * 60}", Colors.GREEN)
        print(f"\n  Output: {Colors.CYAN}{final_path}{Colors.RESET}")
        print(f"  Size: {size_mb:.1f} MB")
        if license_key and license_key != "None":
            mode = "Runtime prompt" if license_key == "GENERIC_BUILD" else license_key
            print(f"  License: {mode}")
        print()
        print(
            f"{Colors.DIM}Tip: Terminal bell played. Press Windows+V to view clipboard history{Colors.RESET}"
        )
        print()
    else:
        # Double bell for error
        import sys

        sys.stdout.write("\a\a")
        sys.stdout.flush()

        color_print(
            "[WARN]  Compilation succeeded but output file not found.", Colors.YELLOW
        )
        # Show debug info
        print("\n  Debug Info:")
        print(f"    Output name: {output_name}")
        print(f"    Expected exe: {exe_name}")
        print(f"    Project dir: {project_dir}")
        print(f"    Build dir: {build_dir}")

        # Show what exe files were found in immediate locations
        found_exes = []
        search_dirs = [
            d for d in [build_dir, project_dir, project_dir.parent] if d and d.exists()
        ]
        for parent in search_dirs:
            for p in parent.glob("*.exe"):
                found_exes.append(f"      {p.relative_to(parent)} (in {parent.name})")

        if found_exes:
            print("\n  Found .exe files in search locations:")
            for exe in found_exes:
                print(exe)

            print(
                f"\n  {Colors.YELLOW}Suggestion:{Colors.RESET} The exe might have a different name."
            )
            print(f"  Try: Search manually in {project_dir}")
        else:
            print("    No .exe files found in expected locations")

        print(
            f"\n  {Colors.YELLOW}This is a bug - please report with the above debug info!{Colors.RESET}"
        )
