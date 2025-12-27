"""
License wrappers for Python and Node.js.
These are injected into the entry files during compilation.
"""


def get_python_wrapper(license_key: str, server_url: str) -> str:
    """Get Python license wrapper code."""
    return f'''# ============ LICENSE WRAPPER - DO NOT REMOVE ============
import sys as _lw_sys
import os as _lw_os
import hashlib as _lw_hash
import json as _lw_json
import time as _lw_time
import platform as _lw_platform

def _lw_show_error(title, message, details=None):
    """Show error with formatting and wait for user."""
    print("\\n" + "=" * 60)
    print(f"  ❌ {{title}}")
    print("=" * 60)
    print(f"\\n{{message}}")
    if details:
        print(f"\\nDetails: {{details}}")
    print("\\n" + "=" * 60)
    print("Please take a screenshot of this error and report it.")
    print("=" * 60)
    try:
        input("\\nPress Enter to exit...")
    except Exception:
        pass
    _lw_sys.exit(1)

def _lw_check_gui_available():
    \"\"\"Check if tkinter GUI is available.\"\"\"
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception as e:
        print("[License Wrapper] GUI not available, using console mode")
        print(f"[License Wrapper] Reason: {{e}}")
        return False

def _lw_get_hwid():
    \"\"\"Generate hardware ID.\"\"\"
    try:
        info = f"{{_lw_platform.node()}}|{{_lw_platform.machine()}}|{{_lw_platform.processor()}}"
        return _lw_hash.sha256(info.encode()).hexdigest()[:32]
    except Exception as e:
        print(f"[License Wrapper] Warning: Could not generate HWID: {{e}}")
        return "unknown-hwid"

def _lw_get_license_key_path():
    \"\"\"Get path to license.key file next to the executable.\"\"\"
    try:
        if getattr(_lw_sys, 'frozen', False):
            exe_dir = _lw_os.path.dirname(_lw_sys.executable)
        else:
            exe_dir = _lw_os.path.dirname(_lw_os.path.abspath(__file__))
        return _lw_os.path.join(exe_dir, "license.key")
    except Exception as e:
        print(f"[License Wrapper] Warning: Could not get license path: {{e}}")
        return "license.key"

def _lw_prompt_for_license():
    \"\"\"Prompt user for license key using GUI or console fallback.\"\"\"
    try:
        import tkinter as tk
        from tkinter import simpledialog
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        license_key = simpledialog.askstring(
            "License Key Required",
            "Please enter your License Key:",
            parent=root
        )
        
        root.destroy()
        
        if license_key and license_key.strip():
            return license_key.strip()
        return None
        
    except Exception as e:
        print(f"[License Wrapper] GUI prompt failed: {{e}}")
        try:
            print("\\\\n" + "="*50)
            print("  LICENSE KEY REQUIRED")
            print("="*50)
            license_key = input("Please enter your License Key: ").strip()
            if license_key:
                return license_key
            return None
        except Exception as e2:
            print(f"[License Wrapper] Console prompt failed: {{e2}}")
            return None

def _lw_load_or_prompt_license():
    \"\"\"Load license from file or prompt user for it.\"\"\"
    license_path = _lw_get_license_key_path()
    
    if _lw_os.path.exists(license_path):
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_key = f.read().strip()
                if license_key:
                    print(f"[License Wrapper] Loaded license from {{license_path}}")
                    return license_key
        except Exception as e:
            print(f"[License Wrapper] Warning: Could not read license file: {{e}}")
    
    print("[License Wrapper] No license key found. Please enter your license key.")
    license_key = _lw_prompt_for_license()
    
    if not license_key:
        _lw_show_error("NO LICENSE KEY", "No license key was provided.", "The application requires a valid license key to run.")
    
    try:
        with open(license_path, 'w', encoding='utf-8') as f:
            f.write(license_key)
        print(f"[License Wrapper] License key saved to {{license_path}}")
    except Exception as e:
        print(f"[License Wrapper] Warning: Could not save license file: {{e}}")
    
    return license_key

def _lw_validate():
    \"\"\"Validate license with server.\"\"\"
    LICENSE_KEY = "{license_key}"
    SERVER_URL = "{server_url}"
    
    # Check GUI availability at startup
    _lw_check_gui_available()
    
    if LICENSE_KEY == "DEMO":
        print("[License Wrapper] Running in DEMO mode")
        return True
    
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
                try:
                    license_path = _lw_get_license_key_path()
                    if _lw_os.path.exists(license_path):
                        _lw_os.remove(license_path)
                        print("License file removed. Please try again with a valid key.")
                except Exception:
                    pass
                _lw_show_error("LICENSE INVALID", f"The license key was rejected by the server.", f"Server message: {{msg}}")
                
    except urllib.error.URLError as e:
        print(f"⚠️ Could not reach license server: {{e.reason}}")
        print("Running in offline mode...")
        return True
    except Exception as e:
        _lw_show_error("LICENSE VALIDATION ERROR", f"An error occurred during license validation.", f"{{type(e).__name__}}: {{e}}")

_lw_validate()
# ============ END LICENSE WRAPPER ============

'''


def get_nodejs_wrapper(license_key: str, server_url: str, target_filename: str) -> str:
    """Get Node.js license wrapper code (legacy - uses require, not pkg-compatible)."""
    # Escaping for f-string content
    target_file = target_filename.replace("'", "\\'")

    # We use a placeholder for the require statement to ensure it looks like a static require to pkg analysis
    # However, pkg needs a LITERAL string in require(). It cannot be a variable.
    # Since we are generating this code, we can inject the literal string directly.

    wrapper_code = f'''// ============ LICENSE WRAPPER ============
const crypto = require('crypto');
const os = require('os');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

function _lw_getExeDir() {{
    if (process.pkg) {{
        return path.dirname(process.execPath);
    }}
    return __dirname;
}}

function _lw_getLicenseKeyPath() {{
    return path.join(_lw_getExeDir(), 'license.key');
}}

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

async function _lw_loadOrPromptLicense() {{
    const licensePath = _lw_getLicenseKeyPath();
    
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
    
    console.log('[License Wrapper] No license key found. Please enter your license key.');
    const licenseKey = await _lw_promptForLicenseKey();
    
    if (!licenseKey) {{
        console.log('\\n❌ No license key provided. Exiting...');
        process.exit(1);
    }}
    
    try {{
        fs.writeFileSync(licensePath, licenseKey, 'utf-8');
        console.log(`[License Wrapper] License key saved to ${{licensePath}}`);
    }} catch (e) {{
        console.log(`[License Wrapper] Warning: Could not save license file: ${{e.message}}`);
    }}
    
    return licenseKey;
}}

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
    
    if (LICENSE_KEY === "GENERIC_BUILD") {{
        LICENSE_KEY = await _lw_loadOrPromptLicense();
    }}
    
    return new Promise((resolve, reject) => {{
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
                        if ("{license_key}" === "GENERIC_BUILD") {{
                            _lw_deleteSavedLicense();
                        }}
                        process.exit(1);
                    }}
                }});
            }});
            
            req.on('error', (e) => {{
                console.error(`⚠️ Connection error: ${{e.message}}`);
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

function _lw_pauseAndExit(code) {{
    if (process.platform === 'win32') {{
        const rl = readline.createInterface({{
            input: process.stdin,
            output: process.stdout
        }});
        rl.question('\\nPress Enter to exit...', () => {{
            rl.close();
            process.exit(code);
        }});
    }} else {{
        process.exit(code);
    }}
}}

// Bootstrap
_lw_validate().then(() => {{
    // Load original application
    try {{
        console.log("[License Wrapper] Starting application...");
        require('./{target_file}');
    }} catch (e) {{
        console.error('\\n❌ Runtime Error:', e);
        _lw_pauseAndExit(1);
    }}
}}).catch(e => {{
    console.error(e);
    _lw_pauseAndExit(1);
}});
'''
    return wrapper_code


def get_nodejs_wrapper_inline(license_key: str, server_url: str) -> tuple[str, str]:
    """
    Get Node.js license wrapper as prefix/suffix to wrap original code.

    Returns (prefix, suffix) tuple where:
    - prefix: License validation code + async IIFE opening
    - suffix: Async IIFE closing with error handling

    This is pkg-compatible because:
    - No top-level await (wrapped in async IIFE)
    - No file renaming
    - No dynamic require()

    IMPORTANT: Global error handlers are set up FIRST to catch any crash.
    """
    prefix = f'''// ============ LICENSE WRAPPER - DO NOT REMOVE ============
// Global error handlers - MUST BE FIRST to catch any crash
const _lw_readline_global = require('readline');

function _lw_showErrorAndWait(type, error) {{
    console.error('\\n' + '='.repeat(60));
    console.error('  ❌ ' + type);
    console.error('='.repeat(60));
    console.error('\\nError:', error.message || error);
    if (error.stack) {{
        console.error('\\nStack trace:');
        console.error(error.stack);
    }}
    console.error('\\n' + '='.repeat(60));
    console.error('Please take a screenshot and report this error.');
    console.error('='.repeat(60));
    
    // Keep window open on Windows
    if (process.platform === 'win32' && process.stdin.isTTY) {{
        const rl = _lw_readline_global.createInterface({{
            input: process.stdin,
            output: process.stdout
        }});
        rl.question('\\nPress Enter to exit...', () => {{
            rl.close();
            process.exit(1);
        }});
    }} else {{
        // Fallback: wait a bit so user can see error in terminal
        setTimeout(() => process.exit(1), 5000);
    }}
}}

// Catch uncaught exceptions (sync errors)
process.on('uncaughtException', (error) => {{
    _lw_showErrorAndWait('UNCAUGHT EXCEPTION', error);
}});

// Catch unhandled promise rejections (async errors)
process.on('unhandledRejection', (reason, promise) => {{
    _lw_showErrorAndWait('UNHANDLED REJECTION', reason);
}});

// ============ LICENSE WRAPPER CORE ============
const _lw_crypto = require('crypto');
const _lw_os = require('os');
const _lw_https = require('https');
const _lw_http = require('http');
const _lw_fs = require('fs');
const _lw_path = require('path');
const _lw_readline = require('readline');

function _lw_getExeDir() {{
    if (process.pkg) {{
        return _lw_path.dirname(process.execPath);
    }}
    return __dirname;
}}

function _lw_getLicenseKeyPath() {{
    return _lw_path.join(_lw_getExeDir(), 'license.key');
}}

function _lw_promptForLicenseKey() {{
    return new Promise((resolve) => {{
        // Try PowerShell GUI dialog on Windows (supports copy-paste)
        if (process.platform === 'win32') {{
            try {{
                const {{ execSync }} = require('child_process');
                const psCmd = 'powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::InputBox(\\'Please enter your License Key to activate this software:\\', \\'License Key Required\\', \\'\\')"';
                
                const result = execSync(psCmd, {{ 
                    encoding: 'utf-8',
                    windowsHide: true
                }});
                const key = result.trim();
                if (key) {{
                    resolve(key);
                    return;
                }}
            }} catch (e) {{
                console.log('[License Wrapper] GUI dialog failed, using console input');
            }}
        }}
        
        // Fallback to console input
        const rl = _lw_readline.createInterface({{
            input: process.stdin,
            output: process.stdout
        }});
        
        console.log('[License Wrapper] No license key found. Please enter your license key.');
        rl.question('Enter License Key: ', (answer) => {{
            rl.close();
            const key = answer ? answer.trim() : null;
            resolve(key);
        }});
    }});
}}

async function _lw_loadOrPromptLicense() {{
    const licensePath = _lw_getLicenseKeyPath();
    
    if (_lw_fs.existsSync(licensePath)) {{
        try {{
            const key = _lw_fs.readFileSync(licensePath, 'utf-8').trim();
            if (key) {{
                console.log(`[License Wrapper] Loaded license from ${{licensePath}}`);
                return key;
            }}
        }} catch (e) {{
            console.log(`[License Wrapper] Warning: Could not read license file: ${{e.message}}`);
        }}
    }}
    
    const licenseKey = await _lw_promptForLicenseKey();
    
    if (!licenseKey) {{
        console.log('\\n❌ No license key provided. Exiting...');
        process.exit(1);
    }}
    
    try {{
        _lw_fs.writeFileSync(licensePath, licenseKey, 'utf-8');
        console.log(`[License Wrapper] License key saved to ${{licensePath}}`);
    }} catch (e) {{
        console.log(`[License Wrapper] Warning: Could not save license file: ${{e.message}}`);
    }}
    
    return licenseKey;
}}

function _lw_deleteSavedLicense() {{
    try {{
        const licensePath = _lw_getLicenseKeyPath();
        if (_lw_fs.existsSync(licensePath)) {{
            _lw_fs.unlinkSync(licensePath);
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
    
    if (LICENSE_KEY === "GENERIC_BUILD") {{
        LICENSE_KEY = await _lw_loadOrPromptLicense();
    }}
    
    return new Promise((resolve, reject) => {{
        const cpus = _lw_os.cpus();
        const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
        const info = `${{_lw_os.hostname()}}|${{_lw_os.platform()}}|${{_lw_os.arch()}}|${{_lw_os.totalmem()}}|${{cpuModel}}`;
        const hwid = _lw_crypto.createHash('sha256').update(info).digest('hex').substring(0, 32);
        
        try {{
            const urlObj = new URL(SERVER_URL + "/api/v1/license/validate");
            const postData = JSON.stringify({{
                license_key: LICENSE_KEY,
                hwid: hwid,
                machine_name: _lw_os.hostname(),
                timestamp: Math.floor(Date.now() / 1000),
                nonce: _lw_crypto.randomBytes(16).toString('hex')
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
            
            const lib = urlObj.protocol === 'http:' ? _lw_http : _lw_https;
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
                        if ("{license_key}" === "GENERIC_BUILD") {{
                            _lw_deleteSavedLicense();
                        }}
                        process.exit(1);
                    }}
                }});
            }});
            
            req.on('error', (e) => {{
                console.error(`⚠️ Connection error: ${{e.message}}`);
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

// Wrap everything in async IIFE to use await
(async () => {{
    try {{
        await _lw_validate();
        console.log("[License Wrapper] Starting application...");
        // ============ END LICENSE WRAPPER - APP CODE BELOW ============

'''

    suffix = """
// ============ LICENSE WRAPPER CLEANUP ============
    } catch (e) {
        _lw_showErrorAndWait('APPLICATION ERROR', e);
    }
})().catch(e => {
    _lw_showErrorAndWait('STARTUP ERROR', e);
});
"""
    return prefix, suffix
