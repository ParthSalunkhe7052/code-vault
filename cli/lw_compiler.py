#!/usr/bin/env python3
"""
License Wrapper CLI Compiler (lw-compiler)
Runs Nuitka locally to compile license-protected executables.

Usage:
    lw-compiler login              - Save your API key
    lw-compiler projects           - List your projects
    lw-compiler licenses <id>      - List licenses for a project
    lw-compiler build <id> -l KEY  - Build a project with license
    lw-compiler build              - Interactive build mode
"""

import os
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

# Configuration
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
DEFAULT_API_BASE = "http://localhost:8000/api/v1"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def color_print(msg, color=Colors.RESET):
    """Print colored message."""
    # Enable ANSI colors on Windows
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
    print(f"{color}{msg}{Colors.RESET}")


def load_config():
    """Load saved configuration."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(config):
    """Save configuration to file."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_base():
    """Get API base URL from config or environment."""
    config = load_config()
    return config.get("api_url", os.getenv("LW_API_URL", DEFAULT_API_BASE))


def get_headers():
    """Get request headers with API key."""
    config = load_config()
    api_key = config.get("api_key")
    if not api_key:
        return None
    return {"Authorization": f"Bearer {api_key}"}


def check_logged_in():
    """Check if user is logged in."""
    headers = get_headers()
    if not headers:
        color_print("❌ Not logged in. Run 'lw-compiler login' first.", Colors.RED)
        sys.exit(1)
    return headers


def cmd_login(args):
    """Login with API key or credentials."""
    config = load_config()
    
    print(f"\n{Colors.CYAN}{'='*50}")
    print("  License Wrapper CLI - Login")
    print(f"{'='*50}{Colors.RESET}\n")
    
    # Ask for API URL if not set
    api_url = config.get("api_url", DEFAULT_API_BASE)
    new_url = input(f"API URL [{api_url}]: ").strip()
    if new_url:
        api_url = new_url.rstrip("/")
        if not api_url.endswith("/api/v1"):
            api_url = api_url.rstrip("/") + "/api/v1"
    
    # Ask for credentials
    print("\nLogin with your License Wrapper account:")
    email = input("Email: ").strip()
    password = getpass("Password: ").strip()  # Secure password input
    
    if not email or not password:
        color_print("❌ Email and password are required.", Colors.RED)
        return
    
    # Attempt login
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
            
            # Save config
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
            except (json.JSONDecodeError, KeyError):
                error = resp.text
            color_print(f"❌ Login failed: {error}", Colors.RED)
    except requests.exceptions.ConnectionError:
        color_print(f"❌ Could not connect to {api_url}", Colors.RED)
        color_print("   Make sure the server is running.", Colors.YELLOW)
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)


def cmd_logout(args):
    """Logout and clear saved credentials."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    color_print("✅ Logged out successfully.", Colors.GREEN)


def cmd_projects(args):
    """List user's projects."""
    headers = check_logged_in()
    api_url = get_api_base()
    
    try:
        resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            projects = resp.json()
            
            print(f"\n{Colors.CYAN}{'='*60}")
            print("  Your Projects")
            print(f"{'='*60}{Colors.RESET}\n")
            
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
            
            print(f"\n{Colors.CYAN}{'='*60}")
            print(f"  Licenses for Project: {project_id[:16]}...")
            print(f"{'='*60}{Colors.RESET}\n")
            
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


def cmd_build(args):
    """Build a project locally using Nuitka."""
    headers = check_logged_in()
    api_url = get_api_base()
    
    project_id = args.project_id
    license_key = args.license
    
    # Handle --generic flag: build once, sell to infinite customers
    if getattr(args, 'generic', False):
        license_key = "GENERIC_BUILD"
        color_print("🔓 Generic Build Mode: License will be prompted at runtime", Colors.CYAN)
    
    # If no project specified, show interactive selection
    if not project_id:
        project_id, interactive_license = interactive_build(headers, api_url)
        if not project_id:
            return
        # Only use interactive license if not in generic mode
        if not getattr(args, 'generic', False) and interactive_license:
            license_key = interactive_license
    
    print(f"\n{Colors.CYAN}{'='*60}")
    print("  License Wrapper - Local Compilation")
    print(f"{'='*60}{Colors.RESET}\n")
    
    try:
        # Step 1: Get compile config
        color_print("📋 Fetching project configuration...", Colors.BLUE)
        params = {"license_key": license_key} if license_key else {}
        resp = requests.get(
            f"{api_url}/projects/{project_id}/compile-config",
            headers=headers,
            params=params,
            timeout=10
        )
        
        if resp.status_code != 200:
            handle_error(resp)
            return
        
        config = resp.json()
        print(f"   Project: {config['project_name']}")
        print(f"   Entry file: {config['entry_file']}")
        print(f"   Output: {config['output_name']}.exe")
        if license_key:
            if license_key == "GENERIC_BUILD":
                print(f"   License: GENERIC BUILD (prompted at runtime)")
            else:
                print(f"   License: {license_key[:16]}...")
            
        # Override language if arg provided
        if args.language:
            config['language'] = args.language
        print(f"   Language: {config.get('language', 'python')}")
        
        # Step 2: Download project bundle
        color_print("\n📥 Downloading project files...", Colors.BLUE)
        resp = requests.get(
            f"{api_url}/projects/{project_id}/bundle",
            headers=headers,
            params=params,
            timeout=60
        )
        
        if resp.status_code != 200:
            handle_error(resp)
            return
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Extract bundle
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
            
            # Step 4: Check Compiler installation
            lang = config.get('language', 'python')
            color_print(f"\n🔍 Checking {lang} compiler...", Colors.BLUE)
            
            if lang == 'nodejs':
                 # Check node
                 pass # pkg logic will handle it
            else:
                nuitka_check = subprocess.run(
                    [sys.executable, "-m", "nuitka", "--version"],
                    capture_output=True, text=True
                )
                if nuitka_check.returncode != 0:
                    color_print("❌ Nuitka not found!", Colors.RED)
                    return
                color_print(f"   Found: Nuitka {nuitka_check.stdout.strip().split()[0]}", Colors.GREEN)
            
            # Step 5: Run Compiler
            color_print(f"\n⚙️  Compiling with {lang}...", Colors.BLUE)
            
            success = run_compiler(project_dir, config)
            
            if success:
                # Step 5: Copy output
                output_name = config['output_name']
                exe_name = f"{output_name}.exe"
                
                # Find the exe file
                exe_path = None
                for p in project_dir.rglob("*.exe"):
                    if output_name in p.name or p.name == exe_name:
                        exe_path = p
                        break
                
                if not exe_path:
                    # Check if it's an .exe in current directory
                    for p in Path.cwd().rglob("*.exe"):
                        if output_name in p.name:
                            exe_path = p
                            break
                
                if exe_path and exe_path.exists():
                    # Create output directory
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
                    color_print("   Check the project directory for the .exe file.", Colors.YELLOW)
            else:
                color_print("\n❌ Compilation failed. Check the errors above.", Colors.RED)
                
    except Exception as e:
        color_print(f"❌ Error: {e}", Colors.RED)
        import traceback
        traceback.print_exc()


def interactive_build(headers, api_url):
    """Interactive project and license selection."""
    try:
        # Get projects
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
        
        # Get licenses
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
        # Try to find it
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
    
    # Self-contained license wrapper (no external imports needed)
    wrapper = f'''# ============ LICENSE WRAPPER - DO NOT REMOVE ============
import sys as _lw_sys
import os as _lw_os
import hashlib as _lw_hash
import json as _lw_json
import time as _lw_time
import platform as _lw_platform

def _lw_get_hwid():
    """Generate hardware ID."""
    try:
        info = f"{{_lw_platform.node()}}|{{_lw_platform.machine()}}|{{_lw_platform.processor()}}"
        return _lw_hash.sha256(info.encode()).hexdigest()[:32]
    except:
        return "unknown-hwid"

def _lw_get_license_key_path():
    """Get path to license.key file next to the executable."""
    try:
        # For frozen executables (Nuitka, PyInstaller)
        if getattr(_lw_sys, 'frozen', False):
            exe_dir = _lw_os.path.dirname(_lw_sys.executable)
        else:
            exe_dir = _lw_os.path.dirname(_lw_os.path.abspath(__file__))
        return _lw_os.path.join(exe_dir, "license.key")
    except:
        return "license.key"

def _lw_prompt_for_license():
    """Prompt user for license key using GUI or console fallback."""
    # Try tkinter GUI first
    try:
        import tkinter as tk
        from tkinter import simpledialog
        
        # Create hidden root window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Show input dialog
        license_key = simpledialog.askstring(
            "License Key Required",
            "Please enter your License Key:",
            parent=root
        )
        
        root.destroy()
        
        if license_key and license_key.strip():
            return license_key.strip()
        return None
        
    except Exception:
        # Fallback to console input if tkinter is not available
        try:
            print("\\n" + "="*50)
            print("  LICENSE KEY REQUIRED")
            print("="*50)
            license_key = input("Please enter your License Key: ").strip()
            if license_key:
                return license_key
            return None
        except:
            return None

def _lw_load_or_prompt_license():
    """Load license from file or prompt user for it."""
    license_path = _lw_get_license_key_path()
    
    # Try to load from file
    if _lw_os.path.exists(license_path):
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_key = f.read().strip()
                if license_key:
                    print(f"[License Wrapper] Loaded license from {{license_path}}")
                    return license_key
        except Exception as e:
            print(f"[License Wrapper] Warning: Could not read license file: {{e}}")
    
    # File doesn't exist or is empty, prompt for license
    print("[License Wrapper] No license key found. Please enter your license key.")
    license_key = _lw_prompt_for_license()
    
    if not license_key:
        print("\\n❌ No license key provided. Exiting...")
        _lw_sys.exit(1)
    
    # Save the license key for future runs
    try:
        with open(license_path, 'w', encoding='utf-8') as f:
            f.write(license_key)
        print(f"[License Wrapper] License key saved to {{license_path}}")
    except Exception as e:
        print(f"[License Wrapper] Warning: Could not save license file: {{e}}")
    
    return license_key

def _lw_validate():
    """Validate license with server."""
    LICENSE_KEY = "{license_key}"
    SERVER_URL = "{server_url}"
    
    # Skip validation for DEMO mode
    if LICENSE_KEY == "DEMO":
        print("[License Wrapper] Running in DEMO mode")
        return True
    
    # Handle GENERIC_BUILD mode - prompt for license at runtime
    if LICENSE_KEY == "GENERIC_BUILD":
        LICENSE_KEY = _lw_load_or_prompt_license()
    
    try:
        import urllib.request
        import urllib.error
        
        hwid = _lw_get_hwid()
        nonce = _lw_hash.sha256(str(_lw_time.time()).encode()).hexdigest()[:32]
        
        payload = _lw_json.dumps({{
            "license_key": LICENSE_KEY,
            "hwid": hwid,
            "machine_name": _lw_platform.node(),
            "nonce": nonce,
            "timestamp": int(_lw_time.time())
        }}).encode('utf-8')
        
        req = urllib.request.Request(
            SERVER_URL + "/api/v1/license/validate",
            data=payload,
            headers={{"Content-Type": "application/json"}}
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = _lw_json.loads(resp.read().decode('utf-8'))
            
            if result.get("status") == "valid":
                print("✅ License validated successfully")
                return True
            else:
                msg = result.get("message", "License invalid")
                print(f"❌ License error: {{msg}}")
                # If validation fails for GENERIC_BUILD, delete the saved license file
                try:
                    license_path = _lw_get_license_key_path()
                    if _lw_os.path.exists(license_path):
                        _lw_os.remove(license_path)
                        print("License file removed. Please try again with a valid key.")
                except:
                    pass
                input("Press Enter to exit...")
                _lw_sys.exit(1)
                
    except urllib.error.URLError as e:
        print(f"⚠️ Could not reach license server: {{e.reason}}")
        # Allow offline grace period here if desired
        print("Running in offline mode...")
        return True
    except Exception as e:
        print(f"⚠️ License validation error: {{e}}")
        input("Press Enter to exit...")
        _lw_sys.exit(1)

# Validate on startup
_lw_validate()
# ============ END LICENSE WRAPPER ============

'''
    
    # Write wrapped file
    entry_file.write_text(wrapper + original_code, encoding='utf-8')
    print(f"   Injected into: {entry_file.name}")


def inject_js_wrapper(entry_file: Path, config: dict):
    """Inject JS license wrapper."""
    original_code = entry_file.read_text(encoding='utf-8')
    license_key = config.get('license_key', 'DEMO')
    server_url = config.get('server_url', 'http://localhost:8000')
    
    wrapper = f'''// ============ LICENSE WRAPPER ============
const crypto = require('crypto');
const os = require('os');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Get the directory where the executable is located
function _lw_getExeDir() {{
    if (process.pkg) {{
        return path.dirname(process.execPath);
    }}
    return __dirname;
}}

// Get the license key file path
function _lw_getLicenseKeyPath() {{
    return path.join(_lw_getExeDir(), 'license.key');
}}

// Prompt user for license key via console
function _lw_promptForLicenseKey() {{
    return new Promise((resolve) => {{
        const rl = readline.createInterface({{
            input: process.stdin,
            output: process.stdout
        }});
        
        console.log('\\n' + '='.repeat(50));
        console.log('  LICENSE KEY REQUIRED');
        console.log('='.repeat(50));
        
        rl.question('Enter License Key: ', (answer) => {{
            rl.close();
            const key = answer ? answer.trim() : null;
            resolve(key);
        }});
    }});
}}

// Load license from file or prompt user
async function _lw_loadOrPromptLicense() {{
    const licensePath = _lw_getLicenseKeyPath();
    
    // Try to load from file first
    if (fs.existsSync(licensePath)) {{
        try {{
            const key = fs.readFileSync(licensePath, 'utf-8').trim();
            if (key) {{
                console.log(`[License Wrapper] Loaded license from ${{licensePath}}`);
                return key;
            }}
        }} catch (e) {{
            console.log(`[License Wrapper] Warning: Could not read license file: ${{e.message}}`);
        }}
    }}
    
    // Prompt for license
    console.log('[License Wrapper] No license key found. Please enter your license key.');
    const licenseKey = await _lw_promptForLicenseKey();
    
    if (!licenseKey) {{
        console.log('\\n❌ No license key provided. Exiting...');
        process.exit(1);
    }}
    
    // Save license for future runs
    try {{
        fs.writeFileSync(licensePath, licenseKey, 'utf-8');
        console.log(`[License Wrapper] License key saved to ${{licensePath}}`);
    }} catch (e) {{
        console.log(`[License Wrapper] Warning: Could not save license file: ${{e.message}}`);
    }}
    
    return licenseKey;
}}

// Delete saved license file (on validation failure)
function _lw_deleteSavedLicense() {{
    try {{
        const licensePath = _lw_getLicenseKeyPath();
        if (fs.existsSync(licensePath)) {{
            fs.unlinkSync(licensePath);
            console.log('License file removed. Please try again with a valid key.');
        }}
    }} catch (e) {{
        // Ignore cleanup errors
    }}
}}

async function _lw_validate() {{
    let LICENSE_KEY = "{license_key}";
    const SERVER_URL = "{server_url}";
    
    if (LICENSE_KEY === "DEMO") {{
        console.log("[License Wrapper] Running in DEMO mode");
        return true;
    }}
    
    // Handle GENERIC_BUILD mode - prompt for license at runtime
    if (LICENSE_KEY === "GENERIC_BUILD") {{
        LICENSE_KEY = await _lw_loadOrPromptLicense();
    }}
    
    return new Promise((resolve, reject) => {{
        // HWID generation
        const cpus = os.cpus();
        const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
        const info = `${{os.hostname()}}|${{os.platform()}}|${{os.arch()}}|${{os.totalmem()}}|${{cpuModel}}`;
        const hwid = crypto.createHash('sha256').update(info).digest('hex').substring(0, 32);
        
        try {{
            const urlObj = new URL(SERVER_URL + "/api/v1/license/validate");
            const postData = JSON.stringify({{
                license_key: LICENSE_KEY,
                hwid: hwid,
                machine_name: os.hostname(),
                timestamp: Math.floor(Date.now() / 1000),
                nonce: crypto.randomBytes(16).toString('hex')
            }});
            
            const options = {{
                hostname: urlObj.hostname,
                port: urlObj.port,
                path: urlObj.pathname,
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                }}
            }};
            
            const lib = urlObj.protocol === 'http:' ? http : https;
            const req = lib.request(options, (res) => {{
                let body = '';
                res.on('data', (chunk) => body += chunk);
                res.on('end', () => {{
                    if (res.statusCode === 200) {{
                        try {{
                            const result = JSON.parse(body);
                            if (result.status === 'valid') {{
                                console.log("✅ License validated");
                                resolve(true);
                            }} else {{
                                console.error(`❌ License error: ${{result.message || 'Invalid'}}`);
                                // Delete saved license on validation failure
                                if ("{license_key}" === "GENERIC_BUILD") {{
                                    _lw_deleteSavedLicense();
                                }}
                                process.exit(1);
                            }}
                        }} catch (e) {{
                            console.error("❌ Failed to parse response");
                            process.exit(1);
                        }}
                    }} else {{
                        console.error(`⚠️  Server error ${{res.statusCode}}`);
                        // Delete saved license on server error
                        if ("{license_key}" === "GENERIC_BUILD") {{
                            _lw_deleteSavedLicense();
                        }}
                        process.exit(1);
                    }}
                }});
            }});
            
            req.on('error', (e) => {{
                console.error(`⚠️ Connection error: ${{e.message}}`);
                // Allow offline mode (Soft Fail)
                console.log("[License Wrapper] Running in offline mode...");
                resolve(true); 
            }});
            
            req.write(postData);
            req.end();
            
        }} catch (e) {{
            console.error(`❌ Validation error: ${{e.message}}`);
            process.exit(1);
        }}
    }});
}}

// Bootstrap
_lw_validate().then(() => {{
    // Original Code
    {original_code}
}}).catch(e => {{
    console.error(e);
    process.exit(1);
}});
'''
    entry_file.write_text(wrapper, encoding='utf-8')
    print(f"   Injected JS wrapper into: {entry_file.name}")


def run_pkg(project_dir: Path, config: dict):
    """Run pkg compilation."""
    entry_file = config['entry_file']
    output_name = config['output_name']
    
    # Check for pkg (via npx to avoid global requirement, or check local)
    # We assume 'npx' is available if Node is installed.
    
    print(f"   Target: {config['entry_file']}")
    print(f"   Output: {output_name}")
    
    # pkg <file> --out-path <dir> --output <name> --targets <target>
    # Note: pkg arguments output handling is tricky.
    
    compiler_opts = config.get('compiler_options', {})
    target = compiler_opts.get('target', 'node18-win-x64')
    
    # Pin pkg version to ensure stability
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


def run_compiler(project_dir: Path, config: dict):
    """Dispatch to correct compiler."""
    lang = config.get('language', 'python')
    if lang == 'nodejs':
        return run_pkg(project_dir, config)
    else:
        return run_nuitka(project_dir, config)


def run_nuitka(project_dir: Path, config: dict):
    """Run Nuitka compilation."""
    entry_file = config['entry_file']
    output_name = config['output_name']
    nuitka_opts = config.get('nuitka_options', {})
    
    # Find entry file
    entry_path = project_dir / entry_file
    if not entry_path.exists():
        for f in project_dir.rglob("*.py"):
            if f.name == entry_file or f.name == "main.py":
                entry_path = f
                break
    
    if not entry_path.exists():
        color_print(f"❌ Entry file not found: {entry_file}", Colors.RED)
        return False
    
    # Build Nuitka command
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--output-filename={output_name}.exe",
    ]
    
    # Add include packages for multi-folder projects
    include_packages = nuitka_opts.get("include_packages", [])
    for pkg in include_packages:
        if pkg and pkg != "__pycache__":
            cmd.append(f"--include-package={pkg}")
    
    # Add entry file
    cmd.append(str(entry_path))
    
    print(f"   Command: {' '.join(cmd[:5])}...")
    print()
    
    # Run Nuitka with real-time output
    try:
        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Show real-time output
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                # Print compilation progress
                line = line.strip()
                if line:
                    # Highlight important messages
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


def cmd_status(args):
    """Show current status and environment."""
    config = load_config()
    
    print(f"\n{Colors.CYAN}{'='*50}")
    print("  License Wrapper CLI - Status")
    print(f"{'='*50}{Colors.RESET}\n")
    
    # Login status
    if config.get("api_key"):
        color_print(f"  ✅ Logged in as: {config.get('email', 'Unknown')}", Colors.GREEN)
        color_print(f"     API URL: {config.get('api_url', DEFAULT_API_BASE)}", Colors.CYAN)
    else:
        color_print("  ❌ Not logged in", Colors.RED)
    
    print()
    
    # Check Nuitka
    print("  Checking dependencies...")
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
    except Exception:
        color_print("  ❌ Nuitka: Not found", Colors.RED)
    
    # Check requests
    try:
        import requests
        color_print(f"  ✅ Requests: {requests.__version__}", Colors.GREEN)
    except ImportError:
        color_print("  ❌ Requests: Not installed", Colors.RED)
    
    # Python version
    color_print(f"  ✅ Python: {sys.version.split()[0]}", Colors.GREEN)
    
    # Config file
    if CONFIG_FILE.exists():
        color_print(f"  ✅ Config: {CONFIG_FILE}", Colors.GREEN)
    else:
        color_print(f"  ⚠️  Config: Not created (run 'login' first)", Colors.YELLOW)
    
    print()



def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="lw-compiler",
        description="License Wrapper CLI - Compile Python apps with license protection",
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
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Login with your account")
    
    # Logout command
    logout_parser = subparsers.add_parser("logout", help="Logout and clear credentials")
    
    # Projects command
    projects_parser = subparsers.add_parser("projects", help="List your projects")
    
    # Licenses command
    licenses_parser = subparsers.add_parser("licenses", help="List licenses for a project")
    licenses_parser.add_argument("project_id", help="Project ID")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build a project locally")
    build_parser.add_argument("project_id", nargs="?", help="Project ID (optional for interactive mode)")
    build_parser.add_argument("-l", "--license", help="License key to embed")
    build_parser.add_argument("--generic", action="store_true", help="Build in generic mode (prompt for license at runtime)")
    build_parser.add_argument("--language", choices=['python', 'nodejs'], help="Force language selection")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show current status and environment")
    
    args = parser.parse_args()
    
    if args.command == "login":
        cmd_login(args)
    elif args.command == "logout":
        cmd_logout(args)
    elif args.command == "projects":
        cmd_projects(args)
    elif args.command == "licenses":
        cmd_licenses(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        # Show banner and help
        print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                            ║
║   {Colors.BOLD}License Wrapper CLI Compiler{Colors.CYAN}                          ║
║                                                            ║
║   Compile Python apps with license protection locally      ║
║                                                            ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
""")
        parser.print_help()


if __name__ == "__main__":
    main()
