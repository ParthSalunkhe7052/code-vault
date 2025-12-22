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
import json
import argparse
import zipfile
import subprocess
import tempfile
import shutil
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
    load_config, save_config, get_api_base, get_headers,
    is_logged_in, clear_config, DEFAULT_API_BASE
)
from wrappers import get_python_wrapper, get_nodejs_wrapper


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
        color_print("❌ Authentication failed. Run 'lw-compiler login' again.", Colors.RED)
    elif resp.status_code == 404:
        color_print(f"❌ Not found: {error}", Colors.RED)
    else:
        color_print(f"❌ Error: {error}", Colors.RED)


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_login(args):
    """Login with API key or credentials."""
    config = load_config()
    
    print_header("License Wrapper CLI - Login")
    
    api_url = config.get("api_url", DEFAULT_API_BASE)
    new_url = input(f"API URL [{api_url}]: ").strip()
    if new_url:
        api_url = new_url.rstrip("/")
        if not api_url.endswith("/api/v1"):
            api_url = api_url.rstrip("/") + "/api/v1"
    
    print("\nLogin with your License Wrapper account:")
    email = input("Email: ").strip()
    password = getpass("Password: ").strip()
    
    if not email or not password:
        color_print("❌ Email and password are required.", Colors.RED)
        return
    
    try:
        resp = requests.post(
            f"{api_url}/auth/login",
            json={"email": email, "password": password},
            timeout=10
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
            
            color_print(f"\n✅ Logged in as {user.get('name', email)} ({email})", Colors.GREEN)
            color_print(f"   API URL: {api_url}", Colors.CYAN)
        else:
            try:
                error = resp.json().get("detail", "Unknown error")
            except:
                error = resp.text
            color_print(f"❌ Login failed: {error}", Colors.RED)
    except requests.exceptions.ConnectionError:
        color_print(f"❌ Could not connect to {api_url}", Colors.RED)
        color_print("   Make sure the server is running.", Colors.YELLOW)
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)


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
                color_print("  No projects found. Create one on the web dashboard.", Colors.YELLOW)
                return
            
            for i, p in enumerate(projects, 1):
                settings = p.get('settings', {})
                if isinstance(settings, str):
                    settings = json.loads(settings) if settings else {}
                
                is_multi = settings.get('is_multi_folder', False)
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
        resp = requests.get(f"{api_url}/licenses?project_id={project_id}", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            licenses = resp.json()
            print_header(f"Licenses for Project: {project_id[:16]}...")
            
            if not licenses:
                color_print("  No licenses found. Create one on the web dashboard.", Colors.YELLOW)
                return
            
            for i, lic in enumerate(licenses, 1):
                status_color = Colors.GREEN if lic['status'] == 'active' else Colors.RED
                print(f"  {Colors.BOLD}{i}. {lic['license_key']}{Colors.RESET}")
                print(f"     Status: {status_color}{lic['status']}{Colors.RESET}")
                if lic.get('client_name'):
                    print(f"     Client: {lic['client_name']}")
                if lic.get('expires_at'):
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
        color_print(f"  ✅ Logged in as: {config.get('email', 'Unknown')}", Colors.GREEN)
        color_print(f"     API URL: {config.get('api_url', DEFAULT_API_BASE)}", Colors.CYAN)
    else:
        color_print("  ❌ Not logged in", Colors.RED)
    
    print()
    print("  Checking dependencies...")
    
    # Check Nuitka
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0] if result.stdout else "Unknown"
            color_print(f"  ✅ Nuitka: {version}", Colors.GREEN)
        else:
            color_print("  ❌ Nuitka: Not installed", Colors.RED)
            color_print("     Install with: pip install nuitka", Colors.YELLOW)
    except:
        color_print("  ❌ Nuitka: Not found", Colors.RED)
    
    # Check Node.js / pkg
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            color_print(f"  ✅ Node.js: {result.stdout.strip()}", Colors.GREEN)
        else:
            color_print("  ❌ Node.js: Not installed", Colors.YELLOW)
    except:
        color_print("  ❌ Node.js: Not found", Colors.YELLOW)
    
    color_print(f"  ✅ Python: {sys.version.split()[0]}", Colors.GREEN)
    print()


# =============================================================================
# Build Command
# =============================================================================

def cmd_build(args):
    """Build a project locally using Nuitka or pkg."""
    headers = check_logged_in()
    api_url = get_api_base()
    
    project_id = args.project_id
    license_key = args.license
    
    if getattr(args, 'generic', False):
        license_key = "GENERIC_BUILD"
        color_print("🔓 Generic Build Mode: License will be prompted at runtime", Colors.CYAN)
    
    if not project_id:
        project_id, interactive_license = interactive_build(headers, api_url)
        if not project_id:
            return
        if not getattr(args, 'generic', False) and interactive_license:
            license_key = interactive_license
    
    print_header("License Wrapper - Local Compilation")
    
    try:
        # Step 1: Get compile config
        color_print("📋 Fetching project configuration...", Colors.BLUE)
        params = {"license_key": license_key} if license_key else {}
        resp = requests.get(f"{api_url}/projects/{project_id}/compile-config", headers=headers, params=params, timeout=10)
        
        if resp.status_code != 200:
            handle_error(resp)
            return
        
        config = resp.json()
        print(f"   Project: {config['project_name']}")
        print(f"   Entry file: {config['entry_file']}")
        print(f"   Output: {config['output_name']}.exe")
        
        if args.language:
            config['language'] = args.language
        print(f"   Language: {config.get('language', 'python')}")
        
        # Step 2: Download project bundle
        color_print("\n📥 Downloading project files...", Colors.BLUE)
        resp = requests.get(f"{api_url}/projects/{project_id}/bundle", headers=headers, params=params, timeout=60)
        
        if resp.status_code != 200:
            handle_error(resp)
            return
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            bundle_path = tmpdir / "bundle.zip"
            bundle_path.write_bytes(resp.content)
            
            project_dir = tmpdir / "project"
            project_dir.mkdir()
            
            with zipfile.ZipFile(bundle_path, 'r') as zf:
                zf.extractall(project_dir)
            
            print(f"   Extracted to: {project_dir}")
            
            # Step 3: Inject license wrapper
            if license_key:
                color_print("\n🔐 Injecting license protection...", Colors.BLUE)
                lang = config.get('language', 'python')
                if lang == 'nodejs':
                    inject_js_wrapper(project_dir / config['entry_file'], config)
                else:
                    inject_license_wrapper(project_dir, config)
            
            # Step 4: Run compiler
            lang = config.get('language', 'python')
            color_print(f"\n⚙️  Compiling with {lang}...", Colors.BLUE)
            
            success = run_compiler(project_dir, config)
            
            if success:
                copy_output(project_dir, config, license_key)
            else:
                color_print("\n❌ Compilation failed. Check the errors above.", Colors.RED)
                
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        import traceback
        traceback.print_exc()


def interactive_build(headers, api_url):
    """Interactive project and license selection."""
    try:
        resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
        if resp.status_code != 200:
            handle_error(resp)
            return None, None
        
        projects = resp.json()
        if not projects:
            color_print("❌ No projects found. Create one on the web dashboard.", Colors.RED)
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
        
        project_id = project['id']
        
        resp = requests.get(f"{api_url}/licenses?project_id={project_id}", headers=headers, timeout=10)
        if resp.status_code == 200:
            licenses = resp.json()
            if licenses:
                active_licenses = [l for l in licenses if l['status'] == 'active']
                if active_licenses:
                    print(f"\n{Colors.CYAN}Select a license (or 0 for no license):{Colors.RESET}\n")
                    print("  0. No license (demo mode)")
                    for i, lic in enumerate(active_licenses, 1):
                        client = f" - {lic['client_name']}" if lic.get('client_name') else ""
                        print(f"  {i}. {lic['license_key']}{client}")
                    
                    try:
                        choice = int(input("\nEnter number: ").strip())
                        if choice > 0 and choice <= len(active_licenses):
                            return project_id, active_licenses[choice - 1]['license_key']
                    except (ValueError, IndexError):
                        pass
        
        return project_id, None
        
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        return None, None


def inject_license_wrapper(project_dir: Path, config: dict):
    """Inject license validation code into entry file."""
    entry_file = project_dir / config['entry_file']
    
    if not entry_file.exists():
        for f in project_dir.rglob("*.py"):
            if f.name == config['entry_file'] or f.name == "main.py":
                entry_file = f
                break
    
    if not entry_file.exists():
        color_print(f"   ⚠️ Entry file not found: {config['entry_file']}", Colors.YELLOW)
        return
    
    original_code = entry_file.read_text(encoding='utf-8')
    license_key = config.get('license_key', 'DEMO')
    server_url = config.get('server_url', 'http://localhost:8000')
    
    wrapper = get_python_wrapper(license_key, server_url)
    entry_file.write_text(wrapper + original_code, encoding='utf-8')
    print(f"   Injected into: {entry_file.name}")


def inject_js_wrapper(entry_file: Path, config: dict):
    """Inject JS license wrapper."""
    original_code = entry_file.read_text(encoding='utf-8')
    license_key = config.get('license_key', 'DEMO')
    server_url = config.get('server_url', 'http://localhost:8000')
    
    wrapper = get_nodejs_wrapper(license_key, server_url, original_code)
    entry_file.write_text(wrapper, encoding='utf-8')
    print(f"   Injected JS wrapper into: {entry_file.name}")


def run_compiler(project_dir: Path, config: dict) -> bool:
    """Dispatch to correct compiler."""
    lang = config.get('language', 'python')
    if lang == 'nodejs':
        return run_pkg(project_dir, config)
    else:
        return run_nuitka(project_dir, config)


def run_pkg(project_dir: Path, config: dict) -> bool:
    """Run pkg compilation for Node.js."""
    entry_file = config['entry_file']
    output_name = config['output_name']
    
    compiler_opts = config.get('compiler_options', {})
    target = compiler_opts.get('target', 'node18-win-x64')
    
    cmd = ["npx", "pkg@5.8.1", str(project_dir / entry_file), 
           "--targets", target,
           "--output", str(project_dir / output_name)]
    
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
        if result.returncode != 0:
            color_print(f"❌ pkg failed: {result.stderr}", Colors.RED)
            return False
        color_print("✅ pkg completed successfully", Colors.GREEN)
        return True
    except FileNotFoundError:
        color_print("❌ npx/pkg not found. Install Node.js.", Colors.RED)
        return False


def run_nuitka(project_dir: Path, config: dict) -> bool:
    """Run Nuitka compilation for Python."""
    entry_file = config['entry_file']
    output_name = config['output_name']
    nuitka_opts = config.get('nuitka_options', {})
    
    entry_path = project_dir / entry_file
    if not entry_path.exists():
        for f in project_dir.rglob("*.py"):
            if f.name == entry_file or f.name == "main.py":
                entry_path = f
                break
    
    if not entry_path.exists():
        color_print(f"❌ Entry file not found: {entry_file}", Colors.RED)
        return False
    
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone", "--onefile",
        "--remove-output", "--assume-yes-for-downloads",
        f"--output-filename={output_name}.exe",
    ]
    
    for pkg in nuitka_opts.get("include_packages", []):
        if pkg and pkg != "__pycache__":
            cmd.append(f"--include-package={pkg}")
    
    cmd.append(str(entry_path))
    
    print(f"   Command: {' '.join(cmd[:5])}...")
    print()
    
    try:
        process = subprocess.Popen(cmd, cwd=project_dir, stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                if line:
                    if 'error' in line.lower():
                        color_print(f"   {line}", Colors.RED)
                    elif 'warning' in line.lower():
                        color_print(f"   {line}", Colors.YELLOW)
                    elif any(kw in line.lower() for kw in ['completed', 'success', 'done']):
                        color_print(f"   {line}", Colors.GREEN)
                    else:
                        print(f"   {line}")
        
        return process.returncode == 0
    except subprocess.TimeoutExpired:
        color_print("❌ Compilation timed out (10 minutes)", Colors.RED)
        return False
    except FileNotFoundError:
        color_print("❌ Nuitka not found. Install it with: pip install nuitka", Colors.RED)
        return False
    except Exception as e:
        color_print(f"❌ Nuitka error: {e}", Colors.RED)
        return False


def copy_output(project_dir: Path, config: dict, license_key: str):
    """Copy compiled output to current directory."""
    output_name = config['output_name']
    exe_name = f"{output_name}.exe"
    
    exe_path = None
    for p in project_dir.rglob("*.exe"):
        if output_name in p.name or p.name == exe_name:
            exe_path = p
            break
    
    if not exe_path:
        for p in Path.cwd().rglob("*.exe"):
            if output_name in p.name:
                exe_path = p
                break
    
    if exe_path and exe_path.exists():
        output_dir = Path.cwd() / "output"
        output_dir.mkdir(exist_ok=True)
        
        final_path = output_dir / exe_name
        shutil.copy2(exe_path, final_path)
        
        size_mb = final_path.stat().st_size / (1024 * 1024)
        
        print()
        color_print(f"{'='*60}", Colors.GREEN)
        color_print(f"  ✅ BUILD SUCCESSFUL!", Colors.GREEN)
        color_print(f"{'='*60}", Colors.GREEN)
        print(f"\n  Output: {Colors.CYAN}{final_path}{Colors.RESET}")
        print(f"  Size: {size_mb:.1f} MB")
        if license_key:
            print(f"  License: {license_key}")
        print()
    else:
        color_print("⚠️  Compilation succeeded but output file not found.", Colors.YELLOW)


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
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("login", help="Login with your account")
    subparsers.add_parser("logout", help="Logout and clear credentials")
    subparsers.add_parser("projects", help="List your projects")
    subparsers.add_parser("status", help="Show current status and environment")
    
    licenses_parser = subparsers.add_parser("licenses", help="List licenses for a project")
    licenses_parser.add_argument("project_id", help="Project ID")
    
    build_parser = subparsers.add_parser("build", help="Build a project locally")
    build_parser.add_argument("project_id", nargs="?", help="Project ID (optional for interactive mode)")
    build_parser.add_argument("-l", "--license", help="License key to embed")
    build_parser.add_argument("--generic", action="store_true", help="Build in generic mode (prompt for license at runtime)")
    build_parser.add_argument("--language", choices=['python', 'nodejs'], help="Force language selection")
    
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
        print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                            ║
║   {Colors.BOLD}License Wrapper CLI Compiler{Colors.CYAN}                          ║
║                                                            ║
║   Compile Python/Node.js apps with license protection      ║
║                                                            ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
""")
        parser.print_help()


if __name__ == "__main__":
    main()
