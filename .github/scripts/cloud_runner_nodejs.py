#!/usr/bin/env python3
"""
CodeVault Cloud Build Runner for Node.js
Standalone script to execute pkg builds in CI/CD environments.
Supports single-file and project-based Node.js builds.
License protection: Async HTTPS validation + License file fallback
"""

import os
import sys
import json
import logging
import subprocess
import argparse
import re
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [NodeRunner] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class NodeJSBuilder:
    """Build Node.js projects using @yao-pkg/pkg"""

    def __init__(self, config: dict, source_dir: Path):
        self.config = config
        self.source_dir = source_dir
        self.project_name = config.get("project_name", "app")
        self.output_name = config.get("output_name", "app")
        self.entry_file = config.get("entry_file", "index.js")
        self.license_key = config.get("license_key", "GENERIC_BUILD")
        self.license_mode = config.get("license_mode", "generic")  # 'generic' | 'demo'
        self.demo_duration = config.get("demo_duration", 60)  # minutes
        self.target_platforms = config.get("target_platforms", ["windows"])
        self.api_url = config.get("api_url", "")
        self.skip_obfuscation = config.get("skip_obfuscation", True)
        self._resolved_entry_file = None

    def _find_entry_file(self) -> Optional[str]:
        """Find and validate the entry file, handling various path formats"""
        possible_paths = [
            self.entry_file,
            self.entry_file.replace("node_app/", "").replace("node_app\\", ""),
            self.entry_file.replace("src/", "").replace("src\\", ""),
        ]

        for path in possible_paths:
            full_path = self.source_dir / path
            if full_path.exists():
                self._resolved_entry_file = path
                logger.info(f"Found entry file at: {path}")
                return path

        js_files = list(self.source_dir.glob("*.js"))
        if js_files:
            for priority in ["index.js", "main.js", "app.js"]:
                for f in js_files:
                    if f.name == priority:
                        self._resolved_entry_file = f.name
                        logger.info(f"Using auto-detected entry file: {f.name}")
                        return f.name

            self._resolved_entry_file = js_files[0].name
            logger.info(f"Using first JS file as entry: {js_files[0].name}")
            return js_files[0].name

        logger.error("No JavaScript entry file found!")
        return None

    def prepare_package_json(self) -> bool:
        """Prepare package.json for pkg, creating if needed"""
        package_json_path = self.source_dir / "package.json"

        if package_json_path.exists():
            try:
                with open(package_json_path, "r", encoding="utf-8") as f:
                    pkg_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not parse existing package.json: {e}")
                pkg_data = {}
        else:
            pkg_data = {}

        entry = self._resolved_entry_file or self._find_entry_file()
        if not entry:
            logger.error("Cannot prepare package.json without entry file")
            return False

        pkg_data["name"] = pkg_data.get(
            "name", self.output_name.lower().replace("-", "_").replace(" ", "_")
        )
        pkg_data["version"] = pkg_data.get("version", "1.0.0")
        pkg_data["main"] = entry
        pkg_data["bin"] = entry
        pkg_data["private"] = True

        pkg_data["pkg"] = {
            "outputPath": "build_output",
            "targets": ["node20-win-x64", "node20-linux-x64"],
            "assets": pkg_data.get("pkg", {}).get("assets", []),
        }

        try:
            with open(package_json_path, "w", encoding="utf-8") as f:
                json.dump(pkg_data, f, indent=2)
            logger.info(f"Created/updated package.json with main: {entry}")
            logger.info(
                f"Package content: name={pkg_data['name']}, private={pkg_data['private']}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to write package.json: {e}")
            return False

    def inject_license_protection(self) -> bool:
        """Inject license protection into entry file (async HTTPS + license file fallback)"""
        if not self._resolved_entry_file:
            self._find_entry_file()

        if not self._resolved_entry_file:
            logger.error("Entry file not found, skipping license protection")
            return False

        entry_path = self.source_dir / self._resolved_entry_file

        if not entry_path.exists():
            logger.error(f"Entry file not found: {self._resolved_entry_file}")
            return False

        try:
            with open(entry_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            if "CODEVAULT LICENSE PROTECTION" in original_code:
                logger.info("Entry file already has license protection")
                return True

            license_wrapper = self._generate_license_wrapper()
            protected_code = license_wrapper + "\n\n" + original_code

            with open(entry_path, "w", encoding="utf-8") as f:
                f.write(protected_code)

            logger.info("Injected license protection into entry file")
            return True

        except Exception as e:
            logger.error(f"Failed to inject license protection: {e}")
            return False

    def _generate_license_wrapper(self) -> str:
        """Generate license protection wrapper (Generic/Demo mode support)"""
        is_generic = self.license_key == "GENERIC_BUILD"
        license_mode = self.license_mode or "generic"
        demo_duration = self.demo_duration or 60
        
        return f'''// ============ CODEVAULT LICENSE PROTECTION ============
// This code protects your application with license validation
// Generated by CodeVault (codevault.app)
// Modes: Generic (license key prompt), Demo (time-limited)

const _cv_LICENSE_KEY = "{self.license_key}";
const _cv_SERVER_URL = "{self.api_url}";
const _cv_APP_NAME = "{self.project_name}";
const _cv_LICENSE_MODE = "{license_mode}";  // 'generic' or 'demo'
const _cv_DEMO_DURATION = {demo_duration};  // minutes
const _cv_LICENSE_FILE = "license.key";
const _cv_IS_GENERIC = {str(is_generic).lower()};

// Error handler for uncaught exceptions
process.on('uncaughtException', (err) => {{
    console.error("\\n" + "=".repeat(60));
    console.error("  [ERROR] Application crashed");
    console.error("  Error: " + err.message);
    console.error("=".repeat(60) + "\\n");
    process.exit(1);
}});

process.on('unhandledRejection', (reason, promise) => {{
    console.error("\\n" + "=".repeat(60));
    console.error("  [ERROR] Unhandled promise rejection");
    console.error("  Reason: " + String(reason));
    console.error("=".repeat(60) + "\\n");
    process.exit(1);
}});

// Demo mode - check if trial has expired
function _cv_checkDemoExpiry() {{
    try {{
        const fs = require('fs');
        const path = require('path');
        const crypto = require('crypto');
        const exeDir = path.dirname(process.execPath || process.cwd());
        const demoFile = path.join(exeDir, '.demo_' + _cv_APP_NAME.replace(/[^a-zA-Z0-9]/g, '_'));
        
        if (fs.existsSync(demoFile)) {{
            const data = fs.readFileSync(demoFile, 'utf8').trim();
            const startTime = parseInt(data);
            if (!isNaN(startTime)) {{
                const elapsed = Date.now() - startTime;
                const maxDuration = _cv_DEMO_DURATION * 60 * 1000;  // convert to ms
                if (elapsed > maxDuration) {{
                    return {{ expired: true, remaining: 0 }};
                }}
                return {{ expired: false, remaining: maxDuration - elapsed }};
            }}
        }}
        // No file - first run, create it
        fs.writeFileSync(demoFile, Date.now().toString());
        return {{ expired: false, remaining: _cv_DEMO_DURATION * 60 * 1000 }};
    }} catch {{
        return {{ expired: false, remaining: _cv_DEMO_DURATION * 60 * 1000 }};
    }}
}}

// License file check (for storing validated license key)
function _cv_checkLicenseFile() {{
    try {{
        const fs = require('fs');
        const path = require('path');
        const exeDir = path.dirname(process.execPath || process.cwd());
        const licensePath = path.join(exeDir, _cv_LICENSE_FILE);
        
        if (fs.existsSync(licensePath)) {{
            const key = fs.readFileSync(licensePath, 'utf8').trim();
            if (key && key.length > 0) {{
                return key;
            }}
        }}
        return null;
    }} catch {{
        return null;
    }}
}}

// Save license key to file
function _cv_saveLicenseFile(licenseKey) {{
    try {{
        const fs = require('fs');
        const path = require('path');
        const exeDir = path.dirname(process.execPath || process.cwd());
        const licensePath = path.join(exeDir, _cv_LICENSE_FILE);
        fs.writeFileSync(licensePath, licenseKey.trim());
        return true;
    }} catch (e) {{
        return false;
    }}
}}

// Readline for user input
const readline = require('readline');
function _cv_promptLicenseKey() {{
    return new Promise((resolve) => {{
        const rl = readline.createInterface({{
            input: process.stdin,
            output: process.stdout
        }});
        
        console.log("\\n" + "=".repeat(60));
        console.log("  CODEVAULT LICENSE ACTIVATION");
        console.log("  App: " + _cv_APP_NAME);
        console.log("=".repeat(60));
        console.log("");
        console.log("  Enter your license key to activate this application.");
        console.log("  Your license key was sent to your email.");
        console.log("");
        rl.question("  License Key: ", (answer) => {{
            rl.close();
            resolve(answer.trim());
        }});
    }});
}}

// Async HTTPS validation
async function _cv_validateLicenseOnline(licenseKey) {{
    try {{
        const https = require('https');
        const os = require('os');
        const crypto = require('crypto');
        
        const machineId = crypto.createHash('sha256')
            .update(os.hostname() + '-' + (os.cpus()[0]?.model || 'unknown'))
            .digest('hex').substring(0, 16);
        
        const body = JSON.stringify({{
            license_key: licenseKey,
            machine_id: machineId,
            app_name: _cv_APP_NAME
        }});
        
        return new Promise((resolve) => {{
            const url = new URL(_cv_SERVER_URL);
            const options = {{
                hostname: url.hostname,
                port: url.port || 443,
                path: url.pathname,
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(body)
                }},
                timeout: 10000
            }};
            
            const req = https.request(options, (res) => {{
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {{
                    try {{
                        const result = JSON.parse(data);
                        resolve({{ valid: result.valid === true, data: result }});
                    }} catch {{
                        resolve({{ valid: false, error: 'Invalid response' }});
                    }}
                }});
            }});
            
            req.on('error', (err) => {{
                resolve({{ valid: false, error: err.message }});
            }});
            
            req.on('timeout', () => {{
                req.destroy();
                resolve({{ valid: false, error: 'Timeout' }});
            }});
            
            req.write(body);
            req.end();
        }});
    }} catch (e) {{
        return {{ valid: false, error: e.message }};
    }}
}}

// Main license validation
async function _cv_validateLicense() {{
    console.log("\\n" + "=".repeat(60));
    console.log("  CODEVAULT LICENSE");
    console.log("  App: " + _cv_APP_NAME);
    console.log("  Mode: " + _cv_LICENSE_MODE.toUpperCase());
    console.log("=".repeat(60));
    
    // DEMO MODE - Time-limited trial
    if (_cv_LICENSE_MODE === 'demo') {{
        console.log("[License] Demo mode: " + _cv_DEMO_DURATION + " minutes trial");
        const demoStatus = _cv_checkDemoExpiry();
        if (demoStatus.expired) {{
            console.error("\\n[License] Demo period has expired!");
            console.error("  Please purchase a license to continue using this app.");
            console.error("  Visit: https://codevault.app");
            process.exit(1);
        }}
        const remainingMin = Math.round(demoStatus.remaining / 60000);
        console.log("[License] Demo time remaining: " + remainingMin + " minutes");
        console.log("[License] Demo mode active - starting app...\\n");
        return true;
    }}
    
    // GENERIC MODE - License key required
    console.log("[License] Generic build - license key required");
    
    // Check if license key already saved locally
    const savedKey = _cv_checkLicenseFile();
    if (savedKey) {{
        console.log("[License] Found saved license key, validating...");
        const result = await _cv_validateLicenseOnline(savedKey);
        if (result.valid) {{
            console.log("[License] Saved license key is valid!");
            console.log("[License] Starting app...\\n");
            return true;
        }} else {{
            console.log("[License] Saved license key is invalid or expired, removing...");
            try {{
                const fs = require('fs');
                const path = require('path');
                const exeDir = path.dirname(process.execPath || process.cwd());
                fs.unlinkSync(path.join(exeDir, _cv_LICENSE_FILE));
            }} catch {{}}
        }}
    }}
    
    // Prompt for license key
    console.log("");
    const licenseKey = await _cv_promptLicenseKey();
    
    if (!licenseKey) {{
        console.error("\\n[License] No license key entered!");
        process.exit(1);
    }}
    
    console.log("[License] Validating license key with server...");
    const result = await _cv_validateLicenseOnline(licenseKey);
    
    if (result.valid) {{
        console.log("[License] License key is valid!");
        
        // Save license key for future use
        if (_cv_saveLicenseFile(licenseKey)) {{
            console.log("[License] License key saved for future use");
        }}
        
        console.log("[License] Starting app...\\n");
        return true;
    }} else {{
        console.error("\\n[License] INVALID LICENSE KEY!");
        console.error("  Error: " + (result.error || 'Unknown error'));
        console.error("  ");
        console.error("  Please check your license key and try again.");
        console.error("  Visit https://codevault.app for help.");
        console.error("=".repeat(60) + "\\n");
        process.exit(1);
    }}
}}

// Heartbeat (for online license validation)
let _cv_heartbeatTimer = null;
function _cv_startHeartbeat() {{
    if (_cv_LICENSE_MODE === 'demo') return;
    
    _cv_heartbeatTimer = setInterval(async () => {{
        try {{
            const savedKey = _cv_checkLicenseFile();
            if (savedKey) {{
                await _cv_validateLicenseOnline(savedKey);
            }}
        }} catch {{}}
    }}, 3600000);
}}

// Initialize license check
(async () => {{
    try {{
        const valid = await _cv_validateLicense();
        
        if (!valid) {{
            process.exit(1);
        }}
        
        // Start heartbeat in background
        _cv_startHeartbeat();
        
        console.log("[CodeVault] Application starting...\\n");
    }} catch (err) {{
        console.error("[CodeVault] Startup error:", err.message);
        process.exit(1);
    }}
}})();
// ============ END LICENSE PROTECTION ============
'''
        
        if (fs.existsSync(licensePath)) {{
            const key = fs.readFileSync(licensePath, 'utf8').trim();
            if (key === _cv_LICENSE_KEY) {{
                return true;
            }}
        }}
        return false;
    }} catch {{
        return false;
    }}
}}

// Show license prompt (for GENERIC_BUILD or when no license)
function _cv_showLicensePrompt() {{
    console.log("\\n" + "=".repeat(60));
    console.log("  CODEVAULT LICENSE");
    console.log("  App: " + _cv_APP_NAME);
    console.log("=".repeat(60));
    
    if (_cv_LICENSE_KEY === "GENERIC_BUILD") {{
        console.log("  This is a GENERIC BUILD - no license required");
        console.log("  Build ID: {self.license_key}");
        console.log("=".repeat(60) + "\\n");
        return true;
    }}
    
    console.log("  License Key: " + _cv_LICENSE_KEY.substring(0, 8) + "...");
    console.log("  ");
    console.log("  This app requires a valid license to run.");
    console.log("  ");
    console.log("  To activate offline:");
    console.log("    1. Create a file named 'license.key' next to this exe");
    console.log("    2. Enter your license key in that file");
    console.log("=".repeat(60) + "\\n");
    return true;
}}

// Async HTTPS validation
async function _cv_validateLicenseOnline() {{
    if (_cv_LICENSE_KEY === "GENERIC_BUILD") {{
        return true;
    }}
    
    try {{
        const https = require('https');
        const os = require('os');
        const crypto = require('crypto');
        
        const machineId = crypto.createHash('sha256')
            .update(os.hostname() + '-' + (os.cpus()[0]?.model || 'unknown'))
            .digest('hex').substring(0, 16);
        
        const body = JSON.stringify({{
            license_key: _cv_LICENSE_KEY,
            machine_id: machineId,
            app_name: _cv_APP_NAME
        }});
        
        return new Promise((resolve) => {{
            const url = new URL(_cv_SERVER_URL);
            const options = {{
                hostname: url.hostname,
                port: url.port || 443,
                path: url.pathname,
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(body)
                }},
                timeout: 5000
            }};
            
            const req = https.request(options, (res) => {{
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {{
                    try {{
                        const result = JSON.parse(data);
                        resolve(result.valid === true);
                    }} catch {{
                        resolve(false);
                    }}
                }});
            }});
            
            req.on('error', (err) => {{
                console.error("[License] Network error:", err.message);
                resolve(false);
            }});
            
            req.on('timeout', () => {{
                req.destroy();
                resolve(false);
            }});
            
            req.write(body);
            req.end();
        }});
    }} catch (e) {{
        console.error("[License] Validation error:", e.message);
        return false;
    }}
}}

// Combined validation: Online first, then file fallback
async function _cv_validateLicense() {{
    // Always show license info on startup
    _cv_showLicensePrompt();
    
    if (_cv_LICENSE_KEY === "GENERIC_BUILD") {{
        console.log("[License] Running in GENERIC BUILD mode - no validation needed");
        return true;
    }}
    
    console.log("[License] Validating license...");
    
    // Try online validation first
    try {{
        const onlineResult = await _cv_validateLicenseOnline();
        if (onlineResult) {{
            console.log("[License] Online validation successful");
            return true;
        }}
    }} catch (e) {{
        console.log("[License] Online validation failed:", e.message);
    }}
    
    // Fallback to license file
    const fileResult = _cv_checkLicenseFile();
    if (fileResult) {{
        console.log("[License] License file validation successful");
        return true;
    }}
    
    console.log("[License] No valid license found");
    return false;
}}

// Heartbeat
let _cv_heartbeatTimer = null;
async function _cv_startHeartbeat() {{
    if (_cv_LICENSE_KEY === "GENERIC_BUILD") return;
    
    _cv_heartbeatTimer = setInterval(async () => {{
        try {{
            await _cv_validateLicenseOnline();
        }} catch {{}}
    }}, _cv_HEARTBEAT_INTERVAL);
}}

// License wrapper for main code
async function _cv_wrapMain(mainFn) {{
    const valid = await _cv_validateLicense();
    
    if (!valid && _cv_LICENSE_KEY !== "GENERIC_BUILD") {{
        console.error("\\n" + "=".repeat(60));
        console.error("  [LICENSE ERROR] Invalid or expired license");
        console.error("  App: " + _cv_APP_NAME);
        console.error("  License key: " + _cv_LICENSE_KEY.substring(0, 8) + "...");
        console.error("  ");
        console.error("  To use offline, create a file named 'license.key'");
        console.error("  next to the executable with your license key.");
        console.error("  Please contact support@codevault.app");
        console.error("=".repeat(60) + "\\n");
        process.exit(1);
    }}
    
    _cv_startHeartbeat();
    
    try {{
        await mainFn();
    }} catch (err) {{
        console.error("\\n" + "=".repeat(60));
        console.error("  [APPLICATION ERROR]");
        console.error("  Error: " + err.message);
        console.error("  Stack: " + err.stack);
        console.error("=".repeat(60) + "\\n");
        process.exit(1);
    }}
}}

// Auto-initialize license check on startup
(async () => {{
    try {{
        const valid = await _cv_validateLicense();
        
        if (!valid && _cv_LICENSE_KEY !== "GENERIC_BUILD") {{
            console.error("\\n" + "=".repeat(60));
            console.error("  [LICENSE ERROR] Invalid or expired license");
            console.error("  App: " + _cv_APP_NAME);
            console.error("  Please contact support@codevault.app");
            console.error("=".repeat(60) + "\\n");
            process.exit(1);
        }}
        
        console.log("[CodeVault] Application starting...");
        
        // Start heartbeat
        if (_cv_LICENSE_KEY !== "GENERIC_BUILD") {{
            _cv_startHeartbeat();
        }}
    }} catch (err) {{
        console.error("[CodeVault] Startup error:", err.message);
        if (_cv_LICENSE_KEY !== "GENERIC_BUILD") {{
            process.exit(1);
        }}
    }}
}})();
// ============ END LICENSE PROTECTION ============
'''

    def install_dependencies(self) -> bool:
        """Install npm dependencies"""
        package_json_path = self.source_dir / "package.json"

        if not package_json_path.exists():
            logger.warning("No package.json found, skipping npm install")
            return True

        try:
            logger.info("Installing npm dependencies...")
            result = subprocess.run(
                ["npm", "install", "--quiet"],
                cwd=str(self.source_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                logger.warning(f"npm install stderr: {result.stderr}")
                logger.info(f"npm install stdout: {result.stdout}")
            else:
                logger.info("Dependencies installed successfully")

            return True
        except subprocess.TimeoutExpired:
            logger.error("npm install timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False

    def run_obfuscation(self) -> bool:
        """Run JavaScript obfuscation on source files"""
        if self.skip_obfuscation:
            logger.info("Skipping obfuscation (disabled in config)")
            return True

        logger.info("Installing JavaScript Obfuscator...")

        try:
            result = subprocess.run(
                ["npm", "install", "-g", "javascript-obfuscator", "--quiet"],
                cwd=str(self.source_dir),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                logger.warning(f"Failed to install obfuscator: {result.stderr}")
                logger.info("Continuing without obfuscation")
                return True

            logger.info("Obfuscating JavaScript files...")

            js_files = []
            for js_file in self.source_dir.rglob("*.js"):
                if "node_modules" in str(js_file):
                    continue
                if js_file.name.startswith("."):
                    continue
                # Exclude .github directory (contains build scripts, not source JS)
                if ".github" in str(js_file):
                    continue
                js_files.append(js_file)

            if not js_files:
                logger.warning("No JavaScript files found to obfuscate")
                return True

            obfuscate_args = [
                "--compact",
                "true",
                "--rename-globals",
                "true",
                "--string-array",
                "true",
                "--string-array-threshold",
                "0.75",
                "--string-array-encoding",
                "rc4",
                "--string-array-shuffle",
                "true",
                "--identifier-names-generator",
                "hexadecimal",
                "--control-flow-flattening",
                "true",
                "--dead-code-injection",
                "true",
                "--self-defending",
                "true",
                "--ignore-imports",
                "true",
            ]

            for js_file in js_files:
                # Backup original content
                original_content = js_file.read_text(encoding="utf-8")

                cmd = [
                    "npx",
                    "javascript-obfuscator",
                    str(js_file),
                    "--output",
                    str(js_file),
                ] + obfuscate_args

                result = subprocess.run(
                    cmd,
                    cwd=str(self.source_dir),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    # Obfuscation failed - restore original content
                    logger.warning(
                        f"Failed to obfuscate {js_file.name}: {result.stderr[:100] if result.stderr else 'Unknown error'}"
                    )
                    # Restore original to prevent corruption
                    js_file.write_text(original_content, encoding="utf-8")
                else:
                    logger.info(f"Obfuscated: {js_file.name}")

            logger.info("Obfuscation complete")
            return True

        except subprocess.TimeoutExpired:
            logger.warning("Obfuscation timed out, continuing without obfuscation")
            return True
        except Exception as e:
            logger.warning(f"Obfuscation error: {e}, continuing without obfuscation")
            return True

    def build_targets(self) -> dict:
        """Build for all target platforms"""
        results = {}

        target_map = {
            "windows": "node20-win-x64",
            "linux": "node20-linux-x64",
            "macos": "node20-macos-x64",
        }

        for platform in self.target_platforms:
            pkg_target = target_map.get(platform)
            if not pkg_target:
                logger.warning(f"Unknown platform: {platform}")
                continue

            logger.info(f"Building for {platform} ({pkg_target})...")
            success = self._build_single_target(pkg_target, platform)
            results[platform] = "completed" if success else "failed"

        return results

    def _build_single_target(self, pkg_target: str, platform: str) -> bool:
        """Build for a single target platform"""
        output_dir = self.source_dir / f"build_output_{platform}"
        output_dir.mkdir(parents=True, exist_ok=True)

        if platform == "windows":
            output_filename = f"{self.output_name}.exe"
        else:
            output_filename = self.output_name

        # Use full output path (combines out-path and filename)
        full_output_path = output_dir / output_filename

        # pkg command - don't use --config, pkg reads package.json automatically
        # Don't use both --output and --out-path, use --output with full path
        cmd = [
            "npx",
            "@yao-pkg/pkg",
            ".",
            "--target",
            pkg_target,
            "--output",
            str(full_output_path),
            "--compress",
            "GZip",
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        result = None
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.source_dir),
                capture_output=True,
                text=True,
                timeout=600,
            )

            logger.info(f"pkg stdout: {result.stdout}")

            if result.stderr:
                logger.info(f"pkg stderr: {result.stderr}")

            if result.returncode != 0:
                logger.error(f"pkg build failed with code {result.returncode}")
                logger.error(f"Full stdout: {result.stdout}")
                logger.error(f"Full stderr: {result.stderr}")

                logger.info("Retrying with debug mode...")
                debug_cmd = cmd + ["--debug"]
                debug_result = subprocess.run(
                    debug_cmd,
                    cwd=str(self.source_dir),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                logger.info(f"Debug output: {debug_result.stdout}")
                logger.info(f"Debug stderr: {debug_result.stderr}")

                return False

            if full_output_path.exists():
                size_kb = full_output_path.stat().st_size / 1024
                logger.info(f"Build complete: {output_filename} ({size_kb:.1f} KB)")
                return True
            else:
                logger.error(f"Output not found at: {full_output_path}")
                logger.info(f"Directory contents: {list(output_dir.iterdir())}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Build timed out (600s)")
            return False
        except Exception as e:
            logger.error(f"Build exception: {e}")
            if result:
                logger.error(f"Last stdout: {result.stdout}")
                logger.error(f"Last stderr: {result.stderr}")
            return False

    def run(self) -> bool:
        """Execute the full build process"""
        logger.info(f"Starting Node.js build for: {self.project_name}")
        logger.info(f"Source directory: {self.source_dir}")
        logger.info(f"Initial entry file config: {self.entry_file}")
        logger.info(f"Output name: {self.output_name}")
        logger.info(f"Target platforms: {self.target_platforms}")

        logger.info(
            f"Directory contents: {[f.name for f in self.source_dir.iterdir()]}"
        )

        entry = self._find_entry_file()
        if not entry:
            logger.error("Could not find entry file - aborting build")
            return False

        logger.info(f"Resolved entry file: {entry}")

        if not self.prepare_package_json():
            return False

        # Always inject license protection (even for GENERIC_BUILD to show license prompt)
        if not self.inject_license_protection():
            logger.warning("License protection injection failed, continuing without")

        if not self.install_dependencies():
            logger.warning("Dependency installation had issues, continuing anyway")

        if not self.run_obfuscation():
            logger.warning("Obfuscation failed, continuing without")

        results = self.build_targets()

        success = any(s == "completed" for s in results.values())

        if success:
            logger.info("Build completed successfully")
        else:
            logger.error("All builds failed")
            for platform, status in results.items():
                logger.error(f"  {platform}: {status}")

        return success


def main():
    parser = argparse.ArgumentParser(description="CodeVault Node.js Build Runner")
    parser.add_argument("--config", required=True, help="JSON config string")
    parser.add_argument("--source", required=True, help="Source directory path")

    args = parser.parse_args()

    try:
        config = json.loads(args.config)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid config JSON: {e}")
        sys.exit(1)

    source_dir = Path(args.source)
    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        sys.exit(1)

    builder = NodeJSBuilder(config, source_dir)
    success = builder.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
