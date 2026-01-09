import sys
import os
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from terminal import Colors, color_print, print_progress_bar
from wrappers import get_python_wrapper, get_nodejs_wrapper_inline
from audit import log_build_failure, log_security_event, log_obfuscation_stats
from compiler_constants import (
    JAVASCRIPT_OBFUSCATOR_VERSION,
    PKG_VERSION,
    OBFUSCATE_TIMEOUT,
    PARALLEL_WORKERS
)


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
OUTPUT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,99}$')

# Dangerous path patterns that could indicate traversal attempts
DANGEROUS_PATTERNS = [
    '..',           # Parent directory traversal
    '//',           # Double slashes
    '\\\\',         # Double backslashes
    '\x00',         # Null byte injection
    '%2e',          # URL-encoded dot
    '%2f',          # URL-encoded forward slash
    '%5c',          # URL-encoded backslash
    '%00',          # URL-encoded null
    '%c0%ae',       # UTF-8 overlong encoding attack (dot)
    '%c0%af',       # UTF-8 overlong encoding attack (slash)
]


def _handle_security_violation(violation_type: str, details: Dict[str, Any], entry_file: Optional[str] = None) -> None:
    """Log security violation and display warning.

    Args:
        violation_type: Type of security violation
        details: Additional details about the violation
        entry_file: Optional entry file name for context
    """
    log_security_event(violation_type, {
        **details,
        "entry_file": entry_file,
        "source": "cli_compiler"
    })
    print(f"\n{Colors.RED}[SECURITY] {violation_type.upper()}: {details.get('message', 'Unknown violation')}{Colors.RESET}")
    print(f"{Colors.YELLOW}   This event has been logged for security review.{Colors.RESET}\n")


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
            "empty_entry_file",
            {"message": "Entry file cannot be empty"},
            entry_file
        )
        raise PathTraversalError("Entry file cannot be empty")

    # Check for dangerous patterns in the raw input
    entry_lower = entry_file.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in entry_lower:
            _handle_security_violation(
                "traversal_pattern",
                {"message": f"Contains forbidden pattern '{pattern}'", "pattern": pattern},
                entry_file
            )
            raise PathTraversalError(f"Invalid entry file path: contains forbidden pattern '{pattern}'")

    # Normalize the path
    entry_path = Path(entry_file)

    # Ensure it's not absolute (should be relative to project)
    if entry_path.is_absolute():
        _handle_security_violation(
            "absolute_path",
            {"message": "Absolute path not allowed", "path": str(entry_path)},
            entry_file
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
            {"message": "Path resolves outside project directory", "path": str(full_path)},
            entry_file
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
    output_name = output_name.replace('/', '').replace('\\', '')

    # Check for dangerous patterns
    output_lower = output_name.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in output_lower:
            raise PathTraversalError(f"Invalid output name: contains forbidden pattern '{pattern}'")

    # Auto-sanitize: replace spaces with underscores
    original_name = output_name
    output_name = output_name.replace(' ', '_')

    # Replace multiple consecutive underscores with single underscore
    output_name = re.sub(r'_+', '_', output_name)

    # Remove leading/trailing underscores and dots
    output_name = output_name.strip('_.')

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
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.]*$', module_name):
        raise PathTraversalError(
            f"Invalid package name '{package_name}': contains invalid characters"
        )

    # Prevent double dots (path traversal attempt)
    if '..' in module_name:
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
    if not relative_path or relative_path in ('.', './'):
        return base_resolved

    # Check for dangerous patterns
    path_lower = relative_path.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in path_lower:
            raise PathTraversalError(f"Invalid path: contains forbidden pattern '{pattern}'")

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

    # Validate entry file path for security
    try:
        entry_file = validate_entry_file(entry_file_path, project_dir)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        log_security_event("traversal_injection", {"error": str(e), "entry_file": entry_file_path})
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
        license_key = config.get("license_key", "DEMO")
        server_url = config.get("server_url", "http://localhost:8000")
        lease_enabled = config.get("lease_enabled", False)

        wrapper = get_python_wrapper(license_key, server_url, lease_enabled)
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
            license_mode=license_key
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
    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {entry_file}", flush=True)
        log_security_event("missing_entry_file_js", {"entry_file": str(entry_file)})
        return False

    try:
        original_code = entry_file.read_text(encoding="utf-8")
        license_key = config.get("license_key", "DEMO")
        server_url = config.get("server_url", "http://localhost:8000")
        lease_enabled = config.get("lease_enabled", False)

        # Strip shebang if present
        shebang = ""
        if original_code.startswith("#!"):
            first_newline = original_code.find("\n")
            if first_newline != -1:
                shebang = original_code[: first_newline + 1]
                original_code = original_code[first_newline + 1 :]
                print(f"[BUILD] Stripped shebang: {shebang.strip()}", flush=True)

        prefix, suffix = get_nodejs_wrapper_inline(license_key, server_url, lease_enabled)
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
            license_mode=license_key
        )
        return False


def run_compiler(project_dir: Path, config: Dict[str, Any]) -> Tuple[bool, Optional[Path]]:
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

    ⚠️ SECURITY NOTICE:
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

    # Obfuscation settings optimized for speed + protection
    # Valid options for javascript-obfuscator
    obfuscate_args = [
        # Core obfuscation (fast, good protection)
        "--compact", "true",
        "--rename-globals", "true",
        "--rename-properties", "false",  # Can break code, keep off
        # String protection (good protection, moderate speed)
        "--string-array", "true",
        "--string-array-threshold", "0.75",
        "--string-array-encoding", "base64",  # Faster than rc4
        "--string-array-shuffle", "true",
        # Identifier obfuscation
        "--identifier-names-generator", "hexadecimal",
        # Disable slow options for faster builds
        "--control-flow-flattening", "false",  # Very slow, skip for speed
        "--dead-code-injection", "false",
        "--self-defending", "false",
        # Preserve require/import statements
        "--ignore-imports", "true",
    ]

    def _obfuscate_single_file(js_file: Path) -> tuple[Path, bool, str]:
        """Obfuscate a single file, return success status."""
        try:
            cmd = [
                npx_cmd, "-y", f"javascript-obfuscator@{JAVASCRIPT_OBFUSCATOR_VERSION}",
                str(js_file),
                "--output", str(js_file),
            ] + obfuscate_args

            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=OBFUSCATE_TIMEOUT
            )

            return (js_file, result.returncode == 0, result.stderr if result.returncode != 0 else "")

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
                bar = "█" * filled + "░" * (bar_length - filled)

                print(f"\r   [{bar}] {percent}% ({completed}/{total})", end="", flush=True)

        duration_ms = int((time.time() - start_time) * 1000)

        print()  # New line after progress

        # Log obfuscation statistics
        log_obfuscation_stats(
            files_processed=len(js_files),
            files_failed=len(failed_files),
            duration_ms=duration_ms
        )

        if failed_files:
            print(f"   ⚠️ {len(failed_files)}/{len(js_files)} files had obfuscation warnings")
            # Only show first 3 errors
            for js_file, error in failed_files[:3]:
                print(f"   - {js_file.name}: {error[:100]}")
            return len(failed_files) < len(js_files) * 0.5  # Return True if <50% failed

        print(f"   ✅ Obfuscation complete ({duration_ms}ms)")
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
            files_processed=len(js_files),
            files_failed=failed_count,
            duration_ms=0
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

    ⚠️ SECURITY NOTICE:
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
        color_print(f"❌ Security violation: {e}", Colors.RED)
        return False, None

    # Validate output name for security
    try:
        original_name = output_name
        output_name = validate_output_name(output_name)
        if original_name != output_name:
            print(f"📝 Output name sanitized: '{original_name}' → '{output_name}'")
    except PathTraversalError as e:
        color_print(f"❌ Security violation: {e}", Colors.RED)
        return False, None

    compiler_opts = config.get("compiler_options", {})
    target = compiler_opts.get("target", "node18-win-x64")

    # Validate target format (should be like node18-win-x64)
    if not re.match(r'^node\d+-[a-z]+-[a-z0-9]+$', target):
        color_print(f"❌ Invalid target format: {target}", Colors.RED)
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
        color_print("⚠️ No package.json found - skipping npm install", Colors.YELLOW)
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
            print(f"   ⚠️ Could not check axios version: {e}")

        if not node_modules.exists():
            color_print("📦 Installing npm dependencies...", Colors.CYAN)

            # Try to detect dependency count for estimation
            try:
                pkg_json_content = json.loads(package_json.read_text(encoding="utf-8"))
                dep_count = len(pkg_json_content.get("dependencies", {}))
                print(f"   Found {dep_count} dependencies (est. {dep_count * 2}s)")
            except Exception:
                pass

            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
            try:
                # Use subprocess with real-time output for progress
                process = subprocess.Popen(
                    [npm_cmd, "install", "--production"],
                    cwd=pkg_cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,  # Prevent blocking on input prompts
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Parse output for progress indicators
                spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                spinner_idx = 0
                last_update = time.time()

                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break

                    # Show spinner while processing
                    current_time = time.time()
                    if current_time - last_update > 0.2:
                        spinner_idx = (spinner_idx + 1) % len(spinner)
                        print(f"\r   {spinner[spinner_idx]} Installing... ", end="", flush=True)
                        last_update = current_time

                    # Look for progress indicators in npm output
                    if "added" in line.lower() or "removed" in line.lower():
                        print(f"\r   ✅ {line.strip()[:80]}", end="", flush=True)

                process.wait()

                if process.returncode == 0:
                    print(f"\r   ✅ Dependencies installed{' ' * 40}")
                else:
                    print(f"\r   ⚠️ npm install completed with warnings{' ' * 40}")

            except subprocess.TimeoutExpired:
                color_print("\n❌ npm install timed out", Colors.RED)
                return False, None
            except FileNotFoundError:
                color_print("\n❌ npm not found. Install Node.js.", Colors.RED)
                return False, None
        else:
            print("   ✅ node_modules already exists")
            
        # Add pkg config for ESM/CJS...
        try:
            pkg_json_content = json.loads(package_json.read_text(encoding="utf-8"))
            if "pkg" not in pkg_json_content:
                pkg_json_content["pkg"] = {}
            pkg_json_content["pkg"]["scripts"] = pkg_json_content["pkg"].get("scripts", [])
            pkg_json_content["pkg"]["assets"] = pkg_json_content["pkg"].get("assets", [])
            
            for pat in ["node_modules/**/*.cjs", "node_modules/**/*.json"]:
                 if pat not in pkg_json_content["pkg"]["assets"]:
                     pkg_json_content["pkg"]["assets"].append(pat)
                     
            package_json.write_text(json.dumps(pkg_json_content, indent=2), encoding="utf-8")
        except Exception:
            pass

    # Run obfuscation if enabled in project settings
    obfuscate_enabled = config.get("obfuscate_enabled", False)
    if obfuscate_enabled:
        color_print("🔒 Obfuscating JavaScript code...", Colors.CYAN)
        if run_js_obfuscation(pkg_cwd):
            color_print("   ✅ Obfuscation complete", Colors.GREEN)
        else:
            color_print("   ⚠️ Continuing without obfuscation...", Colors.YELLOW)
    elif config.get("fast_build"):
        print(f"   {Colors.DIM}[FAST MODE] Skipping obfuscation for faster build{Colors.RESET}")
    else:
        # Check if fast_build is explicitly false (user wants normal obfuscation but it's off)
        print(f"   {Colors.DIM}[INFO] Obfuscation disabled in settings{Colors.RESET}")

    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    if package_json:
        entry_path_rel = entry_path.relative_to(pkg_cwd)
    else:
        entry_path_rel = entry_file

    # Build pkg command with optimizations
    cmd = [
        npx_cmd, "-y", f"pkg@{PKG_VERSION}", str(entry_path_rel),
        "--targets", target,
        "--output", str(pkg_cwd / output_name),
        "--compress", "GZip",  # Optimization: Compress for smaller output
    ]

    # Debug mode: show less verbose output for cleaner logs
    if not config.get("fast_build"):
        cmd.append("--debug")  # Show more detailed output for debugging

    print(f"   Command: {' '.join(cmd)}")
    print(f"   CWD: {pkg_cwd}")

    # Show time warning for large builds
    if not config.get("fast_build"):
        print(f"\n   {Colors.YELLOW}⏱️  This may take 2-5 minutes depending on project size{Colors.RESET}")

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
            universal_newlines=True
        )

        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = 0
        last_update = time.time()
        start_time = time.time()
        current_phase = "analyzing"

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            current_time = time.time()
            elapsed = int(current_time - start_time)
            mins, secs = divmod(elapsed, 60)
            elapsed_str = f"{mins}m{secs}s"

            # Estimate progress based on time (pkg doesn't output percentages)
            # Typical pkg build takes 1-5 minutes
            estimated_percent = min(95, int(elapsed / 180 * 100))  # Assume ~3 min max

            # Update display every 0.5s
            if current_time - last_update > 0.5:
                spinner_idx = (spinner_idx + 1) % len(spinner)
                last_update = current_time

                # Show progress bar with estimated progress
                print_progress_bar(estimated_percent, width=30, phase=current_phase, elapsed_time=elapsed_str)

            # Parse pkg output for phase detection
            if ">>> Bundling" in line or "bundling" in line.lower():
                current_phase = "bundling"
            elif "compil" in line.lower():
                current_phase = "compiling"
            elif "pack" in line.lower():
                current_phase = "packaging"

        process.wait()
        print("\r" + " " * 70 + "\r", end="", flush=True)

        if process.returncode != 0:
            # Double bell for error
            sys.stdout.write('\a\a')
            sys.stdout.flush()
            color_print(f"❌ pkg failed with exit code {process.returncode}", Colors.RED)
            return False, None

        color_print("✅ pkg completed successfully", Colors.GREEN)

        # Verify the output file exists
        expected_exe = pkg_cwd / f"{output_name}.exe"
        print(f"   🔍 Checking for: {expected_exe}")

        if not expected_exe.exists():
            # Try alternative name patterns (pkg sometimes uses different naming)
            for p in pkg_cwd.glob(f"{output_name}*.exe"):
                expected_exe = p
                print(f"   ⚠️ Found alternative: {expected_exe}")
                break
        if not expected_exe.exists():
            # Also check for file without .exe extension (pkg might name it differently)
            for p in pkg_cwd.glob("*.exe"):
                if output_name.lower() in p.stem.lower():
                    expected_exe = p
                    print(f"   ⚠️ Found partial match: {expected_exe}")
                    break
        if not expected_exe.exists():
            # Last resort: search entire parent temp directory
            temp_search = []
            for parent in list(pkg_cwd.parents)[:4]:  # Search up 4 levels
                if 'temp' in str(parent).lower() or 'tmp' in str(parent).lower():
                    for p in parent.rglob("*.exe"):
                        if output_name.lower() in p.stem.lower() or "node" in p.stem.lower():
                            temp_search.append(p)

            if temp_search:
                color_print(f"⚠️ Found exe elsewhere: {temp_search[0].name}", Colors.YELLOW)
                expected_exe = temp_search[0]
            else:
                color_print("❌ pkg succeeded but output file not found", Colors.RED)
                color_print(f"   Expected: {pkg_cwd / output_name}.exe", Colors.YELLOW)
                color_print(f"   Search dir: {pkg_cwd}", Colors.YELLOW)
                exe_files = list(pkg_cwd.glob("*.exe"))
                if exe_files:
                    color_print(f"   Found exe files: {[p.name for p in exe_files]}", Colors.YELLOW)
                return False, None

        color_print(f"   ✅ Output found: {expected_exe.name}", Colors.GREEN)
        return True, pkg_cwd
    except FileNotFoundError:
        color_print("❌ npx/pkg not found. Install Node.js.", Colors.RED)
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
                content = py_file.read_text(encoding='utf-8', errors='ignore').lower()
                check_files.append(content)
            except Exception:
                pass

    # Look for heavy dependency imports
    heavy_patterns = [
        'import numpy', 'from numpy',
        'import pandas', 'from pandas',
        'import sklearn', 'from sklearn',
        'import tensorflow', 'from tensorflow',
        'import torch', 'from torch',
        'import scipy', 'from scipy',
    ]

    content_text = '\n'.join(check_files)
    return any(pattern in content_text for pattern in heavy_patterns)


def detect_heavy_deps_detailed(project_dir: Path) -> list:
    """Detect which heavy dependencies are used (detailed version).

    Args:
        project_dir: The project directory to check

    Returns:
        list: List of detected heavy dependency names
    """
    heavy_map = {
        'numpy': ['numpy'],
        'pandas': ['pandas'],
        'scipy': ['scipy'],
        'sklearn': ['sklearn', 'scikit-learn'],
        'tensorflow': ['tensorflow'],
        'torch': ['torch', 'pytorch'],
    }

    found = []
    py_files = [f for f in project_dir.rglob("*.py") if f.is_file()][:10]  # Check first 10

    for dep_name, import_patterns in heavy_map.items():
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore').lower()
                if any(pattern in content for pattern in import_patterns):
                    if dep_name not in found:
                        found.append(dep_name)
                    break
            except Exception:
                pass

    return found


def parse_nuitka_percent(line: str) -> int:
    """Extract percentage from Nuitka output like 'GGG:  15% [1500/10000]'"""
    if "%" in line:
        import re
        match = re.search(r'(\d+)%', line)
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

    ⚠️ SECURITY NOTICE:
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
        log_security_event("traversal_compiler", {"error": str(e), "entry_file": entry_file})
        return False

    # Validate output name for security
    try:
        original_name = output_name
        output_name = validate_output_name(output_name)
        if original_name != output_name:
            print(f"[BUILD] Output name sanitized: '{original_name}' → '{output_name}'", flush=True)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        log_security_event("invalid_output_name", {"error": str(e), "output_name": original_name})
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
    print(f"\n{Colors.YELLOW}[SECURITY] Nuitka will compile Python to machine code.{Colors.RESET}")
    print(f"{Colors.YELLOW}    ⚠️  Network access may be used to download dependencies{Colors.RESET}")
    print(f"{Colors.YELLOW}    ⚠️  Only compile code you trust{Colors.RESET}")
    print(f"{Colors.YELLOW}    ⚠️  No container isolation - runs directly on your system{Colors.RESET}\n")

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
        sys.executable, "-m", "nuitka",
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
        # Optimization: Skip importing test/doc modules
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=sphinx",
        "--nofollow-import-to=setuptools",
    ]

    # Add fast-build specific optimizations
    if fast_build:
        # Fast mode: no --onefile, use --jobs
        print(f"{Colors.YELLOW}[FAST MODE]{Colors.RESET} Compiling without --onefile")
        print(f"{Colors.YELLOW}[FAST MODE]{Colors.RESET} Output will be a folder, not single .exe\n")

        cmd.extend(base_options)
        cmd.extend([
            f"--jobs={max_jobs}",
            f"--output-directory={project_dir / 'build'}",
        ])
    else:
        # Standard mode: add --onefile for single executable output
        print(f"{Colors.YELLOW}[STANDARD MODE]{Colors.RESET} Compiling with --onefile")
        print(f"{Colors.YELLOW}[STANDARD MODE]{Colors.RESET} Output will be a single .exe file\n")

        cmd.extend(base_options)
        cmd.extend([
            "--onefile",
            f"--jobs={max_jobs}",
            f"--output-filename={output_name}.exe",
        ])

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
    print(f"{Colors.CYAN}[OPTIMIZATION]{Colors.RESET} Using {max_jobs} CPU cores for parallel compilation")
    if has_heavy_deps:
        print(f"{Colors.CYAN}[OPTIMIZATION]{Colors.RESET} Heavy dependencies detected - applying speed optimizations")
    print(f"{Colors.CYAN}[OPTIMIZATION]{Colors.RESET} Expected speedup: 2-4x vs. current build\n")
    print(f"[NUITKA] Starting compilation: {entry_path.name}", flush=True)

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000

        process = subprocess.Popen(
            cmd, cwd=project_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,  # Prevent blocking on input prompts
            bufsize=0, env=env, creationflags=creationflags,
        )

        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = 0
        last_update = 0
        last_percent = 0
        last_phase = "starting"
        start_time = time.time()

        while True:
            line_bytes = process.stdout.readline()
            if not line_bytes and process.poll() is not None:
                break

            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            elapsed_str = f"{mins}m{secs}s"

            # Update display every second
            if elapsed != last_update:
                last_update = elapsed
                spinner_idx = (spinner_idx + 1) % len(spinner)

                # Use progress bar if we have percent, otherwise use spinner
                if last_percent > 0:
                    print_progress_bar(last_percent, width=30, phase=last_phase, elapsed_time=elapsed_str)
                else:
                    print(f"\r{spinner[spinner_idx]} Starting compilation... {elapsed_str}  ", end="", flush=True)

            if line_bytes:
                line = line_bytes.decode("utf-8", errors="replace").strip()

                # Parse progress from Nuitka output
                percent = parse_nuitka_percent(line)
                if percent:
                    last_percent = percent
                    last_phase = parse_nuitka_phase(line)
                    # Show visual progress bar with phase and time
                    print_progress_bar(percent, width=30, phase=last_phase, elapsed_time=elapsed_str)

                # Log errors/warnings but don't spam output
                if "error" in line.lower() and "no errors" not in line.lower():
                    print(f"\n[ERROR] {line}", flush=True)
                elif "warning" in line.lower() and "no warnings" not in line.lower():
                    print(f"\n[WARN] {line}", flush=True)

        # Clear line at end
        print("\r" + " " * 60 + "\r", end="", flush=True)
        process.wait()

        if process.returncode == 0:
            return True
        else:
            # Error notification (double bell)
            sys.stdout.write('\a\a')
            sys.stdout.flush()
            print(f"\n{Colors.RED}[NUITKA ERROR] Compilation failed with exit code {process.returncode}{Colors.RESET}")
            return False

    except Exception as e:
        sys.stdout.write('\a\a')
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

    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}📊 PROJECT ANALYSIS{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

    if language == "python":
        # Count files
        py_files = [f for f in project_dir.rglob("*.py") if f.is_file()]

        # Estimate lines (sample 3 files)
        sample_files = py_files[:3] if len(py_files) >= 3 else py_files
        total_lines = 0
        for f in sample_files:
            try:
                total_lines += len(f.read_text(encoding='utf-8', errors='ignore').splitlines())
            except Exception:
                pass

        if len(sample_files) > 0 and len(py_files) > len(sample_files):
            total_lines = int(total_lines / len(sample_files) * len(py_files))

        # Check for heavy deps
        heavy_deps = detect_heavy_deps_detailed(project_dir)

        print(f"  Python files: {len(py_files)}")
        print(f"  Estimated lines: {total_lines:,}")

        if heavy_deps:
            heavy_names = ", ".join(heavy_deps)
            print(f"  {Colors.RED}⚠️  Heavy dependencies: {heavy_names}{Colors.RESET}")

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

        print(f"\n  {Colors.YELLOW}⏱️  ESTIMATED BUILD TIME:{Colors.RESET}")

        # Show both modes if fast_build is available
        if not config.get("fast_build"):
            print(f"     Without --onefile: {est_seconds // 60}m {est_seconds % 60}s")
            print(f"     With --onefile:    {est_onefile // 60}m {est_onefile % 60}s")
        else:
            print(f"     Fast mode:         {est_seconds // 60}m {est_seconds % 60}s")

        if est_onefile > 1200:  # 20 minutes
            print(f"\n  {Colors.RED}⚠️  WARNING: This is a large project!{Colors.RESET}")
            print(f"  {Colors.RED}     Build may take 20-60 minutes{Colors.RESET}")
            print(f"\n  {Colors.YELLOW}💡 Tips to speed up:{Colors.RESET}")
            print("     • Add --fast-build flag (no onefile, ~15m)")
            print("     • Add --jobs=8 (use all CPU cores)")
            print("     • Build once, cache for future iterations")

            # Confirmation
            print(f"\n  {Colors.YELLOW}Continue with build? [Y/n]: {Colors.RESET}", end="")
            response = input().strip().lower()
            if response in ['n', 'no']:
                print("  Build cancelled.")
                return False

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

                print(f"\n  {Colors.YELLOW}⏱️  ESTIMATED BUILD TIME: {est_seconds // 60}m{Colors.RESET}")

                if dep_count > 20:
                    print(f"\n  {Colors.RED}⚠️  Large number of dependencies!{Colors.RESET}")
                    print(f"  {Colors.YELLOW}     Consider: --fast-build to skip obfuscation{Colors.RESET}")

                    print(f"\n  {Colors.YELLOW}Continue with build? [Y/n]: {Colors.RESET}", end="")
                    response = input().strip().lower()
                    if response in ['n', 'no']:
                        print("  Build cancelled.")
                        return False
            except Exception:
                pass

        return True

    return True


def copy_output(project_dir: Path, config: Dict[str, Any], license_key: str, custom_output: Optional[str] = None, build_dir: Optional[Path] = None) -> None:
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
        if custom_output:
            final_path = Path(custom_output)
            final_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            home = Path.home()
            desktop_paths = [home / "OneDrive" / "Desktop", home / "Desktop"]
            output_dir = next((d for d in desktop_paths if d.exists()), Path.cwd() / "output")
            if not output_dir.exists():
                output_dir.mkdir(exist_ok=True)
            final_path = output_dir / exe_name

        shutil.copy2(exe_path, final_path)
        size_mb = final_path.stat().st_size / (1024 * 1024)

        # Terminal bell for success
        import sys
        sys.stdout.write('\a')
        sys.stdout.flush()

        print()
        color_print(f"{'=' * 60}", Colors.GREEN)
        color_print("  ✅ BUILD SUCCESSFUL!", Colors.GREEN)
        color_print(f"{'=' * 60}", Colors.GREEN)
        print(f"\n  Output: {Colors.CYAN}{final_path}{Colors.RESET}")
        print(f"  Size: {size_mb:.1f} MB")
        if license_key and license_key != "None":
            mode = "Runtime prompt" if license_key == "GENERIC_BUILD" else license_key
            print(f"  License: {mode}")
        print()
        print(f"{Colors.DIM}Tip: Terminal bell played. Press Windows+V to view clipboard history{Colors.RESET}")
        print()
    else:
        # Double bell for error
        import sys
        sys.stdout.write('\a\a')
        sys.stdout.flush()

        color_print("⚠️  Compilation succeeded but output file not found.", Colors.YELLOW)
        # Show debug info
        print("\n  Debug Info:")
        print(f"    Output name: {output_name}")
        print(f"    Expected exe: {exe_name}")
        print(f"    Project dir: {project_dir}")
        print(f"    Build dir: {build_dir}")

        # Show what exe files were found in immediate locations
        found_exes = []
        search_dirs = [d for d in [build_dir, project_dir, project_dir.parent] if d and d.exists()]
        for parent in search_dirs:
            for p in parent.glob("*.exe"):
                found_exes.append(f"      {p.relative_to(parent)} (in {parent.name})")

        if found_exes:
            print("\n  Found .exe files in search locations:")
            for exe in found_exes:
                print(exe)

            print(f"\n  {Colors.YELLOW}Suggestion:{Colors.RESET} The exe might have a different name.")
            print(f"  Try: Search manually in {project_dir}")
        else:
            print("    No .exe files found in expected locations")

        print(f"\n  {Colors.YELLOW}This is a bug - please report with the above debug info!{Colors.RESET}")
