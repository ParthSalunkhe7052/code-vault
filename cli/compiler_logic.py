import sys
import os
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from terminal import Colors, color_print
from wrappers import get_python_wrapper, get_nodejs_wrapper_inline


# =============================================================================
# Path Traversal Prevention
# =============================================================================

class PathTraversalError(Exception):
    """Raised when a path traversal attack is detected."""
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
]


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
        raise PathTraversalError("Entry file cannot be empty")

    # Check for dangerous patterns in the raw input
    entry_lower = entry_file.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in entry_lower:
            raise PathTraversalError(f"Invalid entry file path: contains forbidden pattern '{pattern}'")

    # Normalize the path
    entry_path = Path(entry_file)

    # Ensure it's not absolute (should be relative to project)
    if entry_path.is_absolute():
        raise PathTraversalError("Entry file must be a relative path, not absolute")

    # Resolve relative to project directory
    full_path = (project_dir / entry_path).resolve()
    project_resolved = project_dir.resolve()

    # Verify the resolved path is within the project directory
    try:
        full_path.relative_to(project_resolved)
    except ValueError:
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

def inject_license_wrapper(project_dir: Path, config: dict):
    """Inject license validation code into entry file."""
    entry_file_path = config.get("entry_file", "")

    # Validate entry file path for security
    try:
        entry_file = validate_entry_file(entry_file_path, project_dir)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        return

    if not entry_file.exists():
        for f in project_dir.rglob("*.py"):
            if f.name == config["entry_file"] or f.name == "main.py":
                entry_file = f
                break

    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {config['entry_file']}", flush=True)
        return

    original_code = entry_file.read_text(encoding="utf-8")
    license_key = config.get("license_key", "DEMO")
    server_url = config.get("server_url", "http://localhost:8000")
    lease_enabled = config.get("lease_enabled", False)

    wrapper = get_python_wrapper(license_key, server_url, lease_enabled)
    entry_file.write_text(wrapper + original_code, encoding="utf-8")
    print(f"[BUILD] Injected wrapper into: {entry_file.name}", flush=True)


def inject_js_wrapper(entry_file: Path, config: dict):
    """Inject JS license wrapper by wrapping entry file in async IIFE."""
    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {entry_file}", flush=True)
        return

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


def run_compiler(project_dir: Path, config: dict) -> tuple:
    """Dispatch to correct compiler.

    Returns:
        tuple: (success: bool, build_dir: Path | None)
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

    Returns:
        bool: True if successful, False otherwise
    """
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"

    # Find JS files to obfuscate (excluding node_modules)
    js_files = [f for f in project_dir.rglob("*.js") if "node_modules" not in str(f)]

    if not js_files:
        print("   No JS files to obfuscate")
        return True

    print(f"   Obfuscating {len(js_files)} JS files...")

    # Obfuscation settings optimized for speed + protection
    # Valid options for javascript-obfuscator@4.1.0
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

    try:
        failed_count = 0
        for js_file in js_files:
            # Build command: npx -y javascript-obfuscator@4.1.0 <input> --output <output> <options>
            cmd = [
                npx_cmd, "-y", "javascript-obfuscator@4.1.0",
                str(js_file),  # Input file
                "--output", str(js_file),  # Output (in-place obfuscation)
            ] + obfuscate_args

            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30  # Reduced timeout since faster settings
            )

            if result.returncode != 0:
                failed_count += 1
                if failed_count <= 3:  # Only show first 3 warnings
                    print(f"   Warning: Failed to obfuscate {js_file.name}")
                    # For debugging, show stderr if available
                    if result.stderr:
                        print(f"      Error: {result.stderr[:200]}")

        if failed_count > 0:
            print(f"   {failed_count}/{len(js_files)} files had obfuscation warnings")

        return True

    except subprocess.TimeoutExpired:
        color_print("   Obfuscation timed out", Colors.YELLOW)
        return False
    except FileNotFoundError:
        color_print("   javascript-obfuscator not found (npx will auto-install)", Colors.YELLOW)
        return False
    except Exception as e:
        color_print(f"   Obfuscation error: {e}", Colors.YELLOW)
        return False


def run_pkg(project_dir: Path, config: dict) -> tuple:
    """Run pkg compilation for Node.js.

    Returns:
        tuple: (success: bool, build_dir: Path | None)
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
            print("📦 Installing npm dependencies...")
            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
            try:
                result = subprocess.run(
                    [npm_cmd, "install", "--production"],
                    cwd=pkg_cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode != 0:
                    color_print("⚠️ npm install warnings/errors:", Colors.YELLOW)
                    if result.stderr:
                        print(result.stderr[:500])
                else:
                    print("   ✅ Dependencies installed")
            except subprocess.TimeoutExpired:
                color_print("❌ npm install timed out", Colors.RED)
                return False, None
            except FileNotFoundError:
                color_print("❌ npm not found. Install Node.js.", Colors.RED)
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
        print("🔒 Obfuscating JavaScript code...")
        if run_js_obfuscation(pkg_cwd):
            color_print("   ✅ Obfuscation complete", Colors.GREEN)
        else:
            color_print("   ⚠️ Continuing without obfuscation...", Colors.YELLOW)

    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    if package_json:
        entry_path_rel = entry_path.relative_to(pkg_cwd)
    else:
        entry_path_rel = entry_file

    cmd = [
        npx_cmd, "-y", "pkg@5.8.1", str(entry_path_rel),
        "--targets", target, "--output", str(pkg_cwd / output_name),
    ]

    print(f"   Command: {' '.join(cmd)}")
    print(f"   CWD: {pkg_cwd}")

    try:
        # Capture output for debugging
        result = subprocess.run(cmd, cwd=pkg_cwd, capture_output=True, text=True)

        # Show pkg output
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"   pkg: {line}")
        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    print(f"   pkg (err): {line}")

        if result.returncode != 0:
            color_print(f"❌ pkg failed with exit code {result.returncode}", Colors.RED)
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


def run_nuitka(project_dir: Path, config: dict) -> bool:
    """Run Nuitka compilation for Python."""
    entry_file = config.get("entry_file", "")
    output_name = config.get("output_name") or config.get("project_name") or "output"
    nuitka_opts = config.get("nuitka_options", {})

    # Validate entry file path for security
    try:
        entry_path = validate_entry_file(entry_file, project_dir)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        return False

    # Validate output name for security
    try:
        original_name = output_name
        output_name = validate_output_name(output_name)
        if original_name != output_name:
            print(f"[BUILD] Output name sanitized: '{original_name}' → '{output_name}'", flush=True)
    except PathTraversalError as e:
        print(f"[ERROR] Security violation: {e}", flush=True)
        return False

    if not entry_path.exists():
        for f in project_dir.rglob("*.py"):
            if f.name == entry_file or f.name == "main.py":
                entry_path = f
                break

    if not entry_path.exists():
        print(f"[ERROR] Entry file not found: {entry_file}", flush=True)
        return False

    cmd = [
        sys.executable, "-m", "nuitka", "--standalone", "--onefile",
        "--remove-output", "--assume-yes-for-downloads", "--enable-plugin=tk-inter",
        f"--output-filename={output_name}.exe",
    ]

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

    print(f"[NUITKA] Starting compilation: {entry_path.name}", flush=True)
    
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000

        process = subprocess.Popen(
            cmd, cwd=project_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, env=env, creationflags=creationflags,
        )

        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = 0
        last_update = 0
        start_time = time.time()

        while True:
            line_bytes = process.stdout.readline()
            if not line_bytes and process.poll() is not None:
                break
            
            elapsed = int(time.time() - start_time)
            if elapsed != last_update:
                last_update = elapsed
                spinner_idx = (spinner_idx + 1) % len(spinner)
                mins, secs = divmod(elapsed, 60)
                print(f"\r{spinner[spinner_idx]} Compiling... {mins}m {secs}s elapsed  ", end="", flush=True)

            if line_bytes:
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    if "error" in line.lower():
                        print(f"\n[NUITKA ERROR] {line}", flush=True)
                    elif "warning" in line.lower():
                        print(f"\n[NUITKA WARN] {line}", flush=True)
                    elif any(kw in line.lower() for kw in ["completed", "success"]):
                        print(f"\n[NUITKA OK] {line}", flush=True)

        print("\r" + " " * 50 + "\r", end="", flush=True)
        process.wait()

        if process.returncode == 0:
            print("[NUITKA] Compilation completed successfully!", flush=True)
            return True
        else:
            print(f"[NUITKA ERROR] Compilation failed with exit code {process.returncode}", flush=True)
            return False

    except Exception as e:
        print(f"[ERROR] Nuitka error: {e}", flush=True)
        return False


def copy_output(project_dir: Path, config: dict, license_key: str, custom_output: str = None, build_dir: Path = None):
    """Copy compiled output to Desktop or custom path.

    Args:
        project_dir: The project directory
        config: Build configuration
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

    # Build search paths with build_dir as highest priority
    search_paths = []
    if build_dir:
        search_paths.append(build_dir)
    search_paths.extend([project_dir, project_dir.parent])

    # Also check package.json dirs as fallback
    for parent in [project_dir] + list(project_dir.parents)[:3]:
        if (parent / "package.json").exists() and parent not in search_paths:
            search_paths.append(parent)
            break

    # Add more aggressive search - also check parent directories up to 3 levels
    for parent in list(project_dir.parents)[:3]:
        if parent not in search_paths:
            search_paths.append(parent)

    # First: try the exact path that run_pkg would have returned
    exe_path = None
    for search_dir in search_paths:
        if not search_dir.exists():
            continue
        # Check for exact match first
        if (search_dir / exe_name).exists():
            exe_path = search_dir / exe_name
            break
        # Check for partial match
        for p in search_dir.glob("*.exe"):
            if p.stem == output_name or output_name in p.name:
                exe_path = p
                break
        if exe_path:
            break

    # Second: if build_dir was set, check if run_pkg might have used a different subdir
    # This handles cases where pkg_cwd != the actual output location
    if not exe_path and build_dir and build_dir.exists():
        for p in build_dir.rglob("*.exe"):
            if p.stem == output_name or output_name in p.name:
                exe_path = p
                break

    # Last resort: deep search from project_dir up to 5 levels
    if not exe_path:
        for parent in [project_dir] + list(project_dir.parents)[:5]:
            for p in parent.rglob("*.exe"):
                if p.stem == output_name or output_name in p.name:
                    exe_path = p
                    break
            if exe_path:
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
    else:
        color_print("⚠️  Compilation succeeded but output file not found.", Colors.YELLOW)
        # Show debug info
        print("\n  Debug Info:")
        print(f"    Output name: {output_name}")
        print(f"    Expected exe: {exe_name}")
        print(f"    Project dir: {project_dir}")
        print(f"    Build dir: {build_dir}")
        print(f"    Search paths: {search_paths}")

        # Show what exe files were found in ANY parent directory
        found_exes = []
        for parent in [project_dir] + list(project_dir.parents)[:5]:
            if not parent.exists():
                continue
            for p in parent.rglob("*.exe"):
                # Show relative to parent for clarity
                found_exes.append(f"      {p}")

        if found_exes:
            print("\n  Found .exe files in parent directories:")
            for exe in found_exes:
                print(exe)

            # Suggest where to look
            print(f"\n  {Colors.YELLOW}Suggestion:{Colors.RESET} The exe might be in a subdirectory.")
            print(f"  Try: Search manually in {project_dir} for any .exe files")
        else:
            print("    No .exe files found in project or parent directories")

        print(f"\n  {Colors.YELLOW}This is a bug - please report with the above debug info!{Colors.RESET}")
