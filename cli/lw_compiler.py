#!/usr/bin/env python3
"""
License Wrapper CLI Compiler (lw-compiler)
Runs Nuitka/pkg locally to compile license-protected executables.

Usage:
    lw-compiler login              - Save your API key
    lw-compiler projects           - List your projects
    lw-compiler licenses <id>      - List licenses for a project
    lw-compiler build <id> -l KEY  - Build a project with license
    lw-compiler build              - Interactive build mode
"""

import sys
import os
import json
import argparse
import zipfile
import subprocess
import tempfile
import shutil
import time
from pathlib import Path
from getpass import getpass

try:
    import requests
except ImportError:
    print("❌ 'requests' module not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# Import from extracted modules
from terminal import Colors, color_print, print_header
from cli_config import (
    load_config,
    save_config,
    get_api_base,
    get_headers,
    clear_config,
    DEFAULT_API_BASE,
)
from wrappers import get_python_wrapper, get_nodejs_wrapper_inline


def check_logged_in():
    """Check if user is logged in."""
    headers = get_headers()
    if not headers:
        color_print("❌ Not logged in. Run 'lw-compiler login' first.", Colors.RED)
        sys.exit(1)
    return headers


def handle_error(resp):
    """Handle API error response."""
    try:
        error = resp.json().get("detail", "Unknown error")
    except (json.JSONDecodeError, KeyError):
        error = resp.text or f"HTTP {resp.status_code}"

    if resp.status_code == 401:
        color_print(
            "❌ Authentication failed. Run 'lw-compiler login' again.", Colors.RED
        )
    elif resp.status_code == 404:
        color_print(f"❌ Not found: {error}", Colors.RED)
    else:
        color_print(f"❌ Error: {error}", Colors.RED)


# =============================================================================
# CLI Commands
# =============================================================================


def cmd_login(args):
    """Login with your CodeVault account."""
    config = load_config()

    print_header("CodeVault CLI - Login")

    # Use saved or default API URL - no confusing prompt
    api_url = config.get("api_url", DEFAULT_API_BASE)

    print(f"\n📡 Server: {api_url}")
    print("   (Set LW_API_URL env variable to use a different server)\n")

    print("Enter your CodeVault account credentials:\n")

    try:
        email = input("  Email: ").strip()
    except EOFError:
        color_print("\n❌ Input cancelled.", Colors.RED)
        return

    # Validate email format
    if not email:
        color_print("\n❌ Email is required.", Colors.RED)
        return
    if "@" not in email or "." not in email:
        color_print("\n❌ Please enter a valid email address.", Colors.RED)
        return

    try:
        password = getpass("  Password: ").strip()
    except EOFError:
        color_print("\n❌ Input cancelled.", Colors.RED)
        return

    if not password:
        color_print("\n❌ Password is required.", Colors.RED)
        return

    print("\n⏳ Logging in...")

    try:
        resp = requests.post(
            f"{api_url}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            user = data.get("user", {})

            config["api_key"] = token
            config["api_url"] = api_url
            config["email"] = email
            config["user_name"] = user.get("name", email)
            save_config(config)

            color_print(
                f"\n✅ Logged in as {user.get('name', email)} ({email})", Colors.GREEN
            )
            color_print(f"   Server: {api_url}\n", Colors.CYAN)
            color_print(
                "   Next: Run 'python lw_compiler.py build' to compile a project",
                Colors.DIM,
            )
        elif resp.status_code == 401:
            color_print("\n❌ Invalid email or password.", Colors.RED)
            color_print(
                "   Please check your credentials and try again.", Colors.YELLOW
            )
        else:
            try:
                error = resp.json().get("detail", "Unknown error")
            except Exception:
                error = resp.text or f"HTTP {resp.status_code}"
            color_print(f"\n❌ Login failed: {error}", Colors.RED)
    except requests.exceptions.Timeout:
        color_print("\n❌ Connection timed out.", Colors.RED)
        color_print("   The server is taking too long to respond.", Colors.YELLOW)
    except requests.exceptions.ConnectionError:
        color_print("\n❌ Cannot connect to server.", Colors.RED)
        color_print(f"\n   Server: {api_url}", Colors.YELLOW)
        color_print("\n   💡 Make sure:", Colors.CYAN)
        color_print(
            "      1. The CodeVault server is running (Run Web App.bat)", Colors.WHITE
        )
        color_print("      2. Check your internet connection", Colors.WHITE)
    except Exception as e:
        color_print(f"\n❌ Error: {e}", Colors.RED)


def cmd_logout(args):
    """Logout and clear saved credentials."""
    clear_config()
    color_print("✅ Logged out successfully.", Colors.GREEN)


def cmd_projects(args):
    """List user's projects."""
    headers = check_logged_in()
    api_url = get_api_base()

    try:
        resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)

        if resp.status_code == 200:
            projects = resp.json()
            print_header("Your Projects")

            if not projects:
                color_print(
                    "  No projects found. Create one on the web dashboard.",
                    Colors.YELLOW,
                )
                return

            for i, p in enumerate(projects, 1):
                settings = p.get("settings", {})
                if isinstance(settings, str):
                    settings = json.loads(settings) if settings else {}

                is_multi = settings.get("is_multi_folder", False)
                project_type = "📁 Multi-folder" if is_multi else "📄 Single file"

                print(f"  {Colors.BOLD}{i}. {p['name']}{Colors.RESET}")
                print(f"     ID: {Colors.CYAN}{p['id']}{Colors.RESET}")
                print(f"     Type: {project_type}")
                print()
        else:
            handle_error(resp)
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)


def cmd_licenses(args):
    """List licenses for a project."""
    headers = check_logged_in()
    api_url = get_api_base()
    project_id = args.project_id

    try:
        resp = requests.get(
            f"{api_url}/licenses?project_id={project_id}", headers=headers, timeout=10
        )

        if resp.status_code == 200:
            licenses = resp.json()
            print_header(f"Licenses for Project: {project_id[:16]}...")

            if not licenses:
                color_print(
                    "  No licenses found. Create one on the web dashboard.",
                    Colors.YELLOW,
                )
                return

            for i, lic in enumerate(licenses, 1):
                status_color = Colors.GREEN if lic["status"] == "active" else Colors.RED
                print(f"  {Colors.BOLD}{i}. {lic['license_key']}{Colors.RESET}")
                print(f"     Status: {status_color}{lic['status']}{Colors.RESET}")
                if lic.get("client_name"):
                    print(f"     Client: {lic['client_name']}")
                if lic.get("expires_at"):
                    print(f"     Expires: {lic['expires_at']}")
                print()
        else:
            handle_error(resp)
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)


def cmd_status(args):
    """Show current status and environment."""
    config = load_config()
    print_header("License Wrapper CLI - Status")

    if config.get("api_key"):
        color_print(
            f"  ✅ Logged in as: {config.get('email', 'Unknown')}", Colors.GREEN
        )
        color_print(
            f"     API URL: {config.get('api_url', DEFAULT_API_BASE)}", Colors.CYAN
        )
    else:
        color_print("  ❌ Not logged in", Colors.RED)

    print()
    print("  Checking dependencies...")

    # Check Nuitka
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            version = (
                result.stdout.strip().split("\n")[0] if result.stdout else "Unknown"
            )
            color_print(f"  ✅ Nuitka: {version}", Colors.GREEN)
        else:
            color_print("  ❌ Nuitka: Not installed", Colors.RED)
            color_print("     Install with: pip install nuitka", Colors.YELLOW)
    except Exception:
        color_print("  ❌ Nuitka: Not found", Colors.RED)

    # Check Node.js / pkg
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            color_print(f"  ✅ Node.js: {result.stdout.strip()}", Colors.GREEN)
        else:
            color_print("  ❌ Node.js: Not installed", Colors.YELLOW)
    except Exception:
        color_print("  ❌ Node.js: Not found", Colors.YELLOW)

    color_print(f"  ✅ Python: {sys.version.split()[0]}", Colors.GREEN)
    print()


# =============================================================================
# Build Command
# =============================================================================


def cmd_build(args):
    """Build a project locally using Nuitka or pkg."""
    project_id = args.project_id
    license_key = args.license

    # Handle license mode flags
    if getattr(args, "open", False):
        # --open flag: No license protection
        license_key = None
        color_print("🔓 Open Build Mode: No license protection", Colors.YELLOW)
    elif getattr(args, "generic", False) or not license_key:
        # Default to GENERIC_BUILD (prompt at runtime) unless license explicitly provided
        license_key = "GENERIC_BUILD"
        color_print("🔐 License will be prompted at runtime (default)", Colors.CYAN)

    # Check if project_id is a file path -> Local Build Mode
    if project_id and (
        Path(project_id).exists()
        or project_id.endswith(".py")
        or project_id.endswith(".js")
    ):
        run_local_build(args)
        return

    headers = check_logged_in()
    api_url = get_api_base()

    if not project_id:
        project_id, interactive_license = interactive_build(headers, api_url)
        if not project_id:
            return
        # Only override if not in open mode and license was selected
        if not getattr(args, "open", False) and interactive_license:
            license_key = interactive_license

    print_header("CodeVault CLI - Local Compilation")
    print()

    try:
        # Step 1: Get compile config
        color_print("[1/5] Fetching project configuration...", Colors.BLUE)
        params = {}
        if license_key:
            params["license_key"] = license_key
        resp = requests.get(
            f"{api_url}/projects/{project_id}/compile-config",
            headers=headers,
            params=params,
            timeout=10,
        )

        if resp.status_code != 200:
            handle_error(resp)
            return

        config = resp.json()
        print(f"      Project: {config['project_name']}")
        print(f"      Entry file: {config['entry_file']}")
        print(f"      Output: {config['output_name']}.exe")

        if args.language:
            config["language"] = args.language

        # Auto-detect language from entry file extension if not set
        if not config.get("language"):
            entry_ext = Path(config.get("entry_file", "")).suffix.lower()
            if entry_ext in [".js", ".mjs", ".cjs", ".ts"]:
                config["language"] = "nodejs"
                print("      🔍 Auto-detected: Node.js project")
            else:
                config["language"] = "python"

        lang = config.get("language")
        print(f"      Language: {lang}")

        # Step 2: Download project bundle
        color_print("\n[2/5] Downloading project bundle...", Colors.BLUE)
        bundle_params = {}
        if license_key:
            # Get license_id from the license key if possible
            bundle_params["license_id"] = (
                license_key  # Will be ignored if not a valid ID
            )

        resp = requests.get(
            f"{api_url}/projects/{project_id}/build-bundle",
            headers=headers,
            params=bundle_params,
            timeout=120,  # Longer timeout for larger projects
            stream=True,  # Stream for progress indication
        )

        if resp.status_code == 400:
            error_data = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            detail = error_data.get("detail", "Unknown error")
            if "No source files" in detail:
                color_print("\n❌ Error: No source files found.", Colors.RED)
                color_print(
                    "   Please upload a project ZIP via the web interface first.",
                    Colors.YELLOW,
                )
                return
            handle_error(resp)
            return
        elif resp.status_code != 200:
            handle_error(resp)
            return

        # Create temp directory for build
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            bundle_path = tmpdir / "bundle.zip"

            # Download with progress indication
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(bundle_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int(downloaded * 100 / total_size)
                            print(f"\r      Downloaded: {pct}%", end="", flush=True)
            print()  # New line after progress

            project_dir = tmpdir / "project"
            project_dir.mkdir()

            # Step 3: Extract files
            color_print("[3/5] Extracting source files...", Colors.BLUE)
            try:
                with zipfile.ZipFile(bundle_path, "r") as zf:
                    zf.extractall(project_dir)
            except zipfile.BadZipFile:
                color_print("❌ Error: Invalid bundle file received.", Colors.RED)
                return

            # Check for config.json in bundle and merge with fetched config
            bundle_config_path = project_dir / "config.json"
            if bundle_config_path.exists():
                try:
                    bundle_config = json.loads(bundle_config_path.read_text())
                    # Merge bundle config (it takes precedence for server-side settings)
                    for key in ["license_key", "api_url", "server_url", "language"]:
                        if key in bundle_config and bundle_config[key]:
                            config[key] = bundle_config[key]
                    print("      Loaded config from bundle")
                except json.JSONDecodeError:
                    pass

            # Source files are in the 'source' subdirectory
            source_dir = project_dir / "source"
            if not source_dir.exists():
                # Fallback: files might be at project_dir root
                source_dir = project_dir

            file_count = sum(1 for _ in source_dir.rglob("*") if _.is_file())
            print(f"      Extracted {file_count} files")

            # Step 4: Inject license wrapper
            color_print("[4/5] Injecting license protection...", Colors.BLUE)
            effective_license = license_key or config.get("license_key")
            if effective_license:
                config["license_key"] = effective_license
                if lang == "nodejs":
                    inject_js_wrapper(source_dir / config["entry_file"], config)
                else:
                    inject_license_wrapper(source_dir, config)
                print(
                    f"      License mode: {'Generic (runtime prompt)' if effective_license == 'GENERIC_BUILD' else 'Fixed key'}"
                )
            else:
                print("      No license protection (open build)")

            # Step 5: Run compiler
            # Refresh language from config as it might have changed after bundle extraction
            # Re-apply auto-detection in case bundle config didn't have language set
            if not config.get("language"):
                entry_ext = Path(config.get("entry_file", "")).suffix.lower()
                if entry_ext in [".js", ".mjs", ".cjs", ".ts"]:
                    config["language"] = "nodejs"
                else:
                    config["language"] = "python"
            lang = config.get("language")
            compiler_name = "pkg" if lang == "nodejs" else "Nuitka"
            color_print(
                f"\n[5/5] Compiling with {compiler_name}... (this may take 2-5 minutes)",
                Colors.BLUE,
            )

            success = run_compiler(source_dir, config)

            if success:
                copy_output(source_dir, config, effective_license, args.output)
                color_print("\n✅ Build complete!", Colors.GREEN)
            else:
                color_print(
                    "\n❌ Compilation failed. Check the errors above.", Colors.RED
                )

    except requests.exceptions.Timeout:
        color_print(
            "❌ Error: Request timed out. Check your internet connection.", Colors.RED
        )
    except requests.exceptions.ConnectionError:
        color_print("❌ Error: Cannot connect to server. Is it running?", Colors.RED)
        color_print(f"   API URL: {api_url}", Colors.YELLOW)
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        import traceback

        traceback.print_exc()


def run_local_build(args):
    """Run build on a local file without Server communication."""
    entry_path = Path(args.project_id).resolve()
    if not entry_path.exists():
        print(f"[ERROR] File not found: {entry_path}", flush=True)
        return

    print("[BUILD] License Wrapper - Local Build Mode", flush=True)

    # Determine configuration
    config = {
        "project_name": entry_path.stem,
        "entry_file": entry_path.name,
        "output_name": Path(args.output).stem if args.output else entry_path.stem,
        "language": args.language
        or ("nodejs" if entry_path.suffix == ".js" else "python"),
        "license_key": args.license or "GENERIC_BUILD",
        "server_url": args.api_url or DEFAULT_API_BASE,
    }

    if args.generic:
        config["license_key"] = "GENERIC_BUILD"
        print(
            "[BUILD] Generic Build Mode: License will be prompted at runtime",
            flush=True,
        )
    elif args.demo:
        config["license_key"] = "DEMO"
        config["demo_duration"] = args.demo_duration or 60
        print(f"[BUILD] Demo Mode: {config['demo_duration']} minutes", flush=True)

    # Use a temp directory to avoid modifying source
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_project_dir = Path(tmpdir) / "project"
        tmp_project_dir.mkdir()

        source_dir = entry_path.parent
        print(f"[BUILD] Preparing source from: {source_dir}", flush=True)

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
            source_dir, tmp_project_dir, ignore=ignore_patterns, dirs_exist_ok=True
        )

        # Step 1: Inject license
        if config["license_key"]:
            print("[BUILD] Injecting license protection...", flush=True)
            lang = config.get("language", "python")
            if lang == "nodejs":
                inject_js_wrapper(tmp_project_dir / config["entry_file"], config)
            else:
                inject_license_wrapper(tmp_project_dir, config)

        # Step 2: Compile
        print(f"[BUILD] Compiling with {config['language']}...", flush=True)
        success = run_compiler(tmp_project_dir, config)

        if success:
            copy_output(tmp_project_dir, config, config["license_key"], args.output)
        else:
            print("[ERROR] Compilation failed.", flush=True)


def interactive_build(headers, api_url):
    """Interactive project and license selection."""
    try:
        resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
        if resp.status_code != 200:
            handle_error(resp)
            return None, None

        projects = resp.json()
        if not projects:
            color_print(
                "❌ No projects found. Create one on the web dashboard.", Colors.RED
            )
            return None, None

        print(f"\n{Colors.CYAN}Select a project to build:{Colors.RESET}\n")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p['name']} ({p['id'][:16]}...)")

        try:
            choice = int(input("\nEnter number: ").strip())
            if choice < 1 or choice > len(projects):
                raise ValueError()
            project = projects[choice - 1]
        except (ValueError, IndexError):
            color_print("❌ Invalid selection.", Colors.RED)
            return None, None

        project_id = project["id"]

        resp = requests.get(
            f"{api_url}/licenses?project_id={project_id}", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            licenses = resp.json()
            if licenses:
                active_licenses = [lic for lic in licenses if lic["status"] == "active"]
                if active_licenses:
                    print(
                        f"\n{Colors.CYAN}Select a license (or 0 for no license):{Colors.RESET}\n"
                    )
                    print("  0. No license (demo mode)")
                    for i, lic in enumerate(active_licenses, 1):
                        client = (
                            f" - {lic['client_name']}" if lic.get("client_name") else ""
                        )
                        print(f"  {i}. {lic['license_key']}{client}")

                    try:
                        choice = int(input("\nEnter number: ").strip())
                        if choice > 0 and choice <= len(active_licenses):
                            return project_id, active_licenses[choice - 1][
                                "license_key"
                            ]
                    except (ValueError, IndexError):
                        pass

        return project_id, None

    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        return None, None


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

    wrapper = get_python_wrapper(license_key, server_url)
    entry_file.write_text(wrapper + original_code, encoding="utf-8")
    print(f"[BUILD] Injected wrapper into: {entry_file.name}", flush=True)


def inject_js_wrapper(entry_file: Path, config: dict):
    """Inject JS license wrapper by wrapping entry file in async IIFE.

    Uses prefix/suffix wrapper approach which is pkg-compatible:
    - No top-level await (wrapped in async IIFE)
    - No file renaming
    - No dynamic require()
    - Original code runs inside async IIFE after validation
    """
    if not entry_file.exists():
        print(f"[WARN] Entry file not found: {entry_file}", flush=True)
        return

    original_code = entry_file.read_text(encoding="utf-8")
    license_key = config.get("license_key", "DEMO")
    server_url = config.get("server_url", "http://localhost:8000")

    # Strip shebang if present (must be on line 1, invalid mid-file)
    shebang = ""
    if original_code.startswith("#!"):
        first_newline = original_code.find("\n")
        if first_newline != -1:
            shebang = original_code[: first_newline + 1]  # Include newline
            original_code = original_code[first_newline + 1 :]
            print(f"[BUILD] Stripped shebang: {shebang.strip()}", flush=True)

    # Get prefix and suffix that wrap code in async IIFE
    prefix, suffix = get_nodejs_wrapper_inline(license_key, server_url)

    # Wrap original code: shebang (if any) + prefix + original + suffix
    wrapped_code = shebang + prefix + original_code + suffix
    entry_file.write_text(wrapped_code, encoding="utf-8")
    print(f"[BUILD] Injected JS wrapper into: {entry_file.name}", flush=True)


def run_compiler(project_dir: Path, config: dict) -> bool:
    """Dispatch to correct compiler."""
    lang = config.get("language", "python")
    if lang == "nodejs":
        return run_pkg(project_dir, config)
    else:
        return run_nuitka(project_dir, config)


def run_pkg(project_dir: Path, config: dict) -> bool:
    """Run pkg compilation for Node.js.

    Steps:
    1. Find package.json (required for dependencies)
    2. Run npm install to install dependencies
    3. Run pkg to bundle the app
    """
    entry_file = config["entry_file"]
    output_name = config.get("output_name") or config.get("project_name") or "output"

    compiler_opts = config.get("compiler_options", {})
    target = compiler_opts.get("target", "node18-win-x64")

    # Find package.json - could be at project root or in a subdirectory
    package_json = None
    entry_path = project_dir / entry_file

    # Search upward from entry file to find package.json
    search_dir = entry_path.parent
    while search_dir >= project_dir:
        candidate = search_dir / "package.json"
        if candidate.exists():
            package_json = candidate
            break
        if search_dir == project_dir:
            break
        search_dir = search_dir.parent

    # Also check project_dir itself
    if not package_json and (project_dir / "package.json").exists():
        package_json = project_dir / "package.json"

    if not package_json:
        color_print("⚠️ No package.json found - skipping npm install", Colors.YELLOW)
        pkg_cwd = project_dir
    else:
        pkg_cwd = package_json.parent
        node_modules = pkg_cwd / "node_modules"

        # Downgrade axios if present (v1.x is incompatible with pkg due to ESM/CJS hybrid)
        try:
            pkg_json_content = json.loads(package_json.read_text(encoding="utf-8"))
            deps = pkg_json_content.get("dependencies", {})
            if "axios" in deps:
                # Check if it's a v1.x version
                axios_ver = deps["axios"]
                if (
                    axios_ver.startswith("^1")
                    or axios_ver.startswith("~1")
                    or axios_ver.startswith("1")
                ):
                    # Downgrade to 0.27.2 which is pkg-compatible
                    deps["axios"] = "0.27.2"
                    pkg_json_content["dependencies"] = deps
                    package_json.write_text(
                        json.dumps(pkg_json_content, indent=2), encoding="utf-8"
                    )
                    print("   ⚙️ Downgraded axios to 0.27.2 (pkg compatibility)")
        except Exception as e:
            print(f"   ⚠️ Could not check axios version: {e}")

        # Run npm install if node_modules doesn't exist
        if not node_modules.exists():
            print("📦 Installing npm dependencies...")
            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

            try:
                result = subprocess.run(
                    [npm_cmd, "install", "--production"],
                    cwd=pkg_cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )
                if result.returncode != 0:
                    color_print("⚠️ npm install warnings/errors:", Colors.YELLOW)
                    if result.stderr:
                        print(result.stderr[:500])
                else:
                    print("   ✅ Dependencies installed")
            except subprocess.TimeoutExpired:
                color_print("❌ npm install timed out", Colors.RED)
                return False
            except FileNotFoundError:
                color_print("❌ npm not found. Install Node.js.", Colors.RED)
                return False
        else:
            print("   ✅ node_modules already exists")

        # Add pkg configuration to package.json to bundle .cjs files (fixes axios ESM/CJS issue)
        try:
            pkg_json_content = json.loads(package_json.read_text(encoding="utf-8"))
            if "pkg" not in pkg_json_content:
                pkg_json_content["pkg"] = {}

            # Ensure scripts and assets include .cjs files for ESM/CJS hybrid packages like axios
            pkg_json_content["pkg"]["scripts"] = pkg_json_content["pkg"].get(
                "scripts", []
            )
            pkg_json_content["pkg"]["assets"] = pkg_json_content["pkg"].get(
                "assets", []
            )

            # Add patterns to bundle axios and similar ESM/CJS hybrid modules
            cjs_pattern = "node_modules/**/*.cjs"
            if cjs_pattern not in pkg_json_content["pkg"]["assets"]:
                pkg_json_content["pkg"]["assets"].append(cjs_pattern)

            json_pattern = "node_modules/**/*.json"
            if json_pattern not in pkg_json_content["pkg"]["assets"]:
                pkg_json_content["pkg"]["assets"].append(json_pattern)

            package_json.write_text(
                json.dumps(pkg_json_content, indent=2), encoding="utf-8"
            )
            print("   ✅ Added pkg config for ESM/CJS modules")
        except Exception as e:
            print(f"   ⚠️ Could not update pkg config: {e}")

    # Use npx.cmd on Windows, npx on others
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"

    # Calculate relative entry path from package.json directory
    if package_json:
        entry_path_rel = entry_path.relative_to(pkg_cwd)
    else:
        entry_path_rel = entry_file

    cmd = [
        npx_cmd,
        "-y",  # Auto-confirm package installation
        "pkg@5.8.1",
        str(entry_path_rel),
        "--targets",
        target,
        "--output",
        str(pkg_cwd / output_name),
    ]

    print(f"   Command: {' '.join(cmd)}")
    print(f"   CWD: {pkg_cwd}")

    try:
        # Don't capture output, let it stream to console so user sees progress (e.g. downloads)
        result = subprocess.run(cmd, cwd=pkg_cwd, capture_output=False, text=True)
        if result.returncode != 0:
            color_print(f"❌ pkg failed with exit code {result.returncode}", Colors.RED)
            return False
        color_print("✅ pkg completed successfully", Colors.GREEN)
        return True
    except FileNotFoundError:
        color_print("❌ npx/pkg not found. Install Node.js.", Colors.RED)
        return False


def run_nuitka(project_dir: Path, config: dict) -> bool:
    """Run Nuitka compilation for Python."""
    entry_file = config["entry_file"]
    # Fix: Fallback to project_name if output_name is empty
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
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--enable-plugin=tk-inter",  # Required for license dialog GUI
        f"--output-filename={output_name}.exe",
    ]

    for pkg in nuitka_opts.get("include_packages", []):
        if pkg and pkg != "__pycache__":
            # Convert path separators to dots for module names
            # e.g., "test3_fullstack/backend" -> "test3_fullstack.backend"
            module_name = pkg.replace("/", ".").replace("\\", ".")
            cmd.append(f"--include-package={module_name}")

    cmd.append(str(entry_path))

    print(f"[NUITKA] Starting compilation: {entry_path.name}", flush=True)
    print(f"[NUITKA] Command: {' '.join(cmd[:5])}...", flush=True)

    try:
        # Force unbuffered output for Nuitka and its children (Scons, cl.exe)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # On Windows, avoid creating a new console window
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
            bufsize=0,  # Unbuffered
            env=env,
            creationflags=creationflags,
        )

        line_count = 0
        start_time = time.time()
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = 0
        last_spinner_update = 0

        while True:
            line_bytes = process.stdout.readline()
            if not line_bytes and process.poll() is not None:
                break

            # Update progress spinner every second
            elapsed = int(time.time() - start_time)
            if elapsed != last_spinner_update:
                last_spinner_update = elapsed
                spinner_idx = (spinner_idx + 1) % len(spinner)
                mins, secs = divmod(elapsed, 60)
                print(
                    f"\r{spinner[spinner_idx]} Compiling... {mins}m {secs}s elapsed  ",
                    end="",
                    flush=True,
                )

            if line_bytes:
                # Decode bytes to string with error handling
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    line_count += 1
                    # Prefix with [NUITKA] for easy parsing
                    if "error" in line.lower():
                        print(f"\n[NUITKA ERROR] {line}", flush=True)
                    elif "warning" in line.lower():
                        print(f"\n[NUITKA WARN] {line}", flush=True)
                    elif any(
                        kw in line.lower()
                        for kw in ["completed", "success", "done", "creating"]
                    ):
                        print(f"\n[NUITKA OK] {line}", flush=True)
                    else:
                        # Only print every 10th line for progress, or important ones
                        if (
                            line_count % 10 == 0
                            or "Nuitka" in line
                            or "compil" in line.lower()
                        ):
                            print(f"\n[NUITKA] {line}", flush=True)

        # Clear the spinner line
        print("\r" + " " * 50 + "\r", end="", flush=True)
        process.wait()

        if process.returncode == 0:
            print("[NUITKA] Compilation completed successfully!", flush=True)
            return True
        else:
            print(
                f"[NUITKA ERROR] Compilation failed with exit code {process.returncode}",
                flush=True,
            )
            return False

    except subprocess.TimeoutExpired:
        print("[ERROR] Compilation timed out (10 minutes)", flush=True)
        return False
    except FileNotFoundError:
        print(
            "[ERROR] Nuitka not found. Install it with: pip install nuitka", flush=True
        )
        return False
    except Exception as e:
        print(f"[ERROR] Nuitka error: {e}", flush=True)
        return False


def copy_output(
    project_dir: Path, config: dict, license_key: str, custom_output: str = None
):
    """Copy compiled output to Desktop or custom path."""
    # Fix: Fallback to project_name if output_name is empty
    output_name = config.get("output_name") or config.get("project_name") or "output"
    exe_name = f"{output_name}.exe"

    exe_path = None

    # For Node.js builds, pkg outputs to pkg_cwd (where package.json is)
    # For Python builds, Nuitka outputs to project_dir
    # Search in multiple locations:
    search_paths = [
        project_dir,  # Python output location
        project_dir.parent,  # Sometimes pkg outputs here
    ]

    # Find package.json directory (where Node.js exe would be)
    for parent in [project_dir] + list(project_dir.parents)[:3]:
        pkg_json = parent / "package.json"
        if pkg_json.exists():
            search_paths.insert(0, parent)  # Priority for Node.js
            break

    # Also check inside subdirectories that might contain package.json
    for subdir in project_dir.rglob("package.json"):
        search_paths.insert(0, subdir.parent)

    # Search for exe in all locations
    for search_dir in search_paths:
        if not search_dir.exists():
            continue
        # Look for exact match first
        exact_match = search_dir / exe_name
        if exact_match.exists():
            exe_path = exact_match
            break
        # Then look for output_name.exe anywhere in directory
        for p in search_dir.glob("*.exe"):
            if p.stem == output_name or output_name in p.name:
                exe_path = p
                break
        if exe_path:
            break

    if not exe_path:
        # Last resort: search current working directory
        for p in Path.cwd().rglob("*.exe"):
            if p.stem == output_name or output_name in p.name:
                exe_path = p
                break

    if exe_path and exe_path.exists():
        if custom_output:
            final_path = Path(custom_output)
            final_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Output to Desktop for easy access (support OneDrive)
            home = Path.home()
            desktop_paths = [
                home / "OneDrive" / "Desktop",  # OneDrive Desktop
                home / "Desktop",  # Regular Desktop
            ]
            output_dir = None
            for desktop in desktop_paths:
                if desktop.exists():
                    output_dir = desktop
                    break
            if not output_dir:
                output_dir = Path.cwd() / "output"
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
        color_print(
            "⚠️  Compilation succeeded but output file not found.", Colors.YELLOW
        )


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="lw-compiler",
        description="License Wrapper CLI - Compile apps with license protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lw-compiler login                       Login with your account
  lw-compiler projects                    List your projects
  lw-compiler licenses PROJECT_ID         List licenses for a project
  lw-compiler build PROJECT_ID -l KEY     Build project with license
  lw-compiler build                       Interactive build mode
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("login", help="Login with your account")
    subparsers.add_parser("logout", help="Logout and clear credentials")
    subparsers.add_parser("projects", help="List your projects")
    subparsers.add_parser("status", help="Show current status and environment")

    licenses_parser = subparsers.add_parser(
        "licenses", help="List licenses for a project"
    )
    licenses_parser.add_argument("project_id", help="Project ID")

    build_parser = subparsers.add_parser("build", help="Build a project locally")
    build_parser.add_argument(
        "project_id",
        nargs="?",
        help="Project ID or path to entry file (for local build)",
    )
    build_parser.add_argument("-l", "--license", help="License key to embed")
    build_parser.add_argument(
        "--generic",
        action="store_true",
        help="Build in generic mode (prompt for license at runtime)",
    )
    build_parser.add_argument(
        "--language", choices=["python", "nodejs"], help="Force language selection"
    )
    build_parser.add_argument(
        "--output", help="Output path for the executable (local build only)"
    )
    build_parser.add_argument("--api-url", help="Override API URL (local build only)")
    build_parser.add_argument(
        "--demo", action="store_true", help="Build in demo mode (local build only)"
    )
    build_parser.add_argument(
        "--demo-duration", type=int, help="Demo duration in minutes (local build only)"
    )
    build_parser.add_argument(
        "--open",
        action="store_true",
        help="Build without license protection (open build)",
    )

    args = parser.parse_args()

    commands = {
        "login": cmd_login,
        "logout": cmd_logout,
        "projects": cmd_projects,
        "licenses": cmd_licenses,
        "build": cmd_build,
        "status": cmd_status,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        # Show welcome banner with Quick Start guide
        print(f"""
{Colors.CYAN}╔════════════════════════════════════════════════════════════╗
║  {Colors.BOLD}CodeVault CLI{Colors.CYAN} - Build license-protected executables    ║
╚════════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.GREEN}🚀 Quick Start:{Colors.RESET}
  1. python lw_compiler.py login      {Colors.DIM}← Login first{Colors.RESET}
  2. python lw_compiler.py build      {Colors.DIM}← Interactive build{Colors.RESET}

{Colors.CYAN}📋 All Commands:{Colors.RESET}
  login      Log in to your CodeVault account
  logout     Log out and clear credentials
  projects   List your projects
  build      Build a project into an executable
  status     Check login status and environment

{Colors.YELLOW}💡 Tip:{Colors.RESET} Run 'python lw_compiler.py status' to check your setup.
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Cancelled. Goodbye!{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.RESET}")
        print(
            f"{Colors.YELLOW}   If this persists, check your internet connection.{Colors.RESET}"
        )
        sys.exit(1)
