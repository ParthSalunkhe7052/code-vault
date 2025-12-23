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
        if getattr(_lw_sys, 'frozen', False):
            exe_dir = _lw_os.path.dirname(_lw_sys.executable)
        else:
            exe_dir = _lw_os.path.dirname(_lw_os.path.abspath(__file__))
        return _lw_os.path.join(exe_dir, "license.key")
    except:
        return "license.key"

def _lw_prompt_for_license():
    """Prompt user for license key using GUI or console fallback."""
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
        
    except Exception:
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
        print("\\n❌ No license key provided. Exiting...")
        _lw_sys.exit(1)
    
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
                print(f"❌ License error: {{msg}}")
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
        print("Running in offline mode...")
        return True
    except Exception as e:
        print(f"⚠️ License validation error: {{e}}")
        input("Press Enter to exit...")
        _lw_sys.exit(1)

_lw_validate()
# ============ END LICENSE WRAPPER ============

'''


def get_nodejs_wrapper(license_key: str, server_url: str, original_code: str) -> str:
    """Get Node.js license wrapper code."""
    return f'''// ============ LICENSE WRAPPER ============
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

// Bootstrap
_lw_validate().then(() => {{
    // Original Code
    {original_code}
}}).catch(e => {{
    console.error(e);
    process.exit(1);
}});
'''
