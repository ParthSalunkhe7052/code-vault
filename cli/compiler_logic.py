import sys
import os
import json
import shutil
import subprocess
import time
from pathlib import Path
from terminal import Colors, color_print
from wrappers import get_python_wrapper, get_nodejs_wrapper_inline

def inject_license_wrapper(project_dir: Path, config: dict):
    """Inject license validation code into entry file."""
    entry_file = project_dir / config["entry_file"]

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


def run_pkg(project_dir: Path, config: dict) -> tuple:
    """Run pkg compilation for Node.js.

    Returns:
        tuple: (success: bool, build_dir: Path | None)
    """
    entry_file = config["entry_file"]
    output_name = config.get("output_name") or config.get("project_name") or "output"

    compiler_opts = config.get("compiler_options", {})
    target = compiler_opts.get("target", "node18-win-x64")

    # Find package.json
    package_json = None
    entry_path = project_dir / entry_file

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
        result = subprocess.run(cmd, cwd=pkg_cwd, capture_output=False, text=True)
        if result.returncode != 0:
            color_print(f"❌ pkg failed with exit code {result.returncode}", Colors.RED)
            return False, None
        color_print("✅ pkg completed successfully", Colors.GREEN)

        # Verify the output file exists
        expected_exe = pkg_cwd / f"{output_name}.exe"
        if not expected_exe.exists():
            # Try alternative name patterns (pkg sometimes uses different naming)
            for p in pkg_cwd.glob(f"{output_name}*.exe"):
                expected_exe = p
                break
        if not expected_exe.exists():
            # Also check for file without .exe extension (pkg might name it differently)
            for p in pkg_cwd.glob("*.exe"):
                if output_name.lower() in p.stem.lower():
                    expected_exe = p
                    break
        if not expected_exe.exists():
            color_print(f"❌ pkg succeeded but output file not found", Colors.RED)
            color_print(f"   Expected: {pkg_cwd / output_name}.exe", Colors.YELLOW)
            color_print(f"   Search dir: {pkg_cwd}", Colors.YELLOW)
            # List what exe files exist
            exe_files = list(pkg_cwd.glob("*.exe"))
            if exe_files:
                color_print(f"   Found exe files: {[p.name for p in exe_files]}", Colors.YELLOW)
            return False, None

        return True, pkg_cwd
    except FileNotFoundError:
        color_print("❌ npx/pkg not found. Install Node.js.", Colors.RED)
        return False, None


def run_nuitka(project_dir: Path, config: dict) -> bool:
    """Run Nuitka compilation for Python."""
    entry_file = config["entry_file"]
    output_name = config.get("output_name") or config.get("project_name") or "output"
    nuitka_opts = config.get("nuitka_options", {})

    entry_path = project_dir / entry_file
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
        if pkg and pkg != "__pycache__":
            module_name = pkg.replace("/", ".").replace("\\", ".")
            cmd.append(f"--include-package={module_name}")

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
            
    for search_dir in search_paths:
        if not search_dir.exists():
            continue
        if (search_dir / exe_name).exists():
            exe_path = search_dir / exe_name
            break
        for p in search_dir.glob("*.exe"):
            if p.stem == output_name or output_name in p.name:
                exe_path = p
                break
        if exe_path:
            break

    if not exe_path:
        for p in Path.cwd().rglob("*.exe"):
            if p.stem == output_name or output_name in p.name:
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
