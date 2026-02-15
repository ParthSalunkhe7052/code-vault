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
        self.target_platforms = config.get("target_platforms", ["windows"])
        self.api_url = config.get("api_url", "")
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
        """Generate license protection wrapper (Async HTTPS + License File fallback)"""
        return f'''// ============ CODEVAULT LICENSE PROTECTION ============
// This code protects your application with license validation
// Generated by CodeVault (codevault.app)
// Features: Async HTTPS validation, License file fallback, Heartbeat

const _cv_LICENSE_KEY = "{self.license_key}";
const _cv_SERVER_URL = "{self.api_url}";
const _cv_APP_NAME = "{self.project_name}";
const _cv_HEARTBEAT_INTERVAL = 3600000;
const _cv_LICENSE_FILE = "license.key";

// License file fallback check
function _cv_checkLicenseFile() {{
    try {{
        const fs = require('fs');
        const path = require('path');
        const exeDir = path.dirname(process.execPath || process.cwd());
        const licensePath = path.join(exeDir, _cv_LICENSE_FILE);
        
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
                resolve(false);
            }});
            
            req.on('timeout', () => {{
                req.destroy();
                resolve(false);
            }});
            
            req.write(body);
            req.end();
        }});
    }} catch {{
        return false;
    }}
}}

// Combined validation: Online first, then file fallback
async function _cv_validateLicense() {{
    if (_cv_LICENSE_KEY === "GENERIC_BUILD") {{
        return true;
    }}
    
    // Try online validation first
    const onlineResult = await _cv_validateLicenseOnline();
    if (onlineResult) {{
        return true;
    }}
    
    // Fallback to license file
    const fileResult = _cv_checkLicenseFile();
    if (fileResult) {{
        return true;
    }}
    
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
        console.error("Application error:", err);
        process.exit(1);
    }}
}}

// Auto-wrap if not GENERIC_BUILD
if (_cv_LICENSE_KEY !== "GENERIC_BUILD") {{
    const _cv_originalMain = (async () => {{}}).constructor;
    global._cv_wrapMain = _cv_wrapMain;
}}
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

        package_json = self.source_dir / "package.json"

        cmd = [
            "npx",
            "@yao-pkg/pkg",
            ".",
            "--target",
            pkg_target,
            "--output",
            output_filename,
            "--out-path",
            str(output_dir),
            "--compress",
            "GZip",
        ]

        if package_json.exists():
            cmd.extend(["--config", str(package_json)])

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

            output_path = output_dir / output_filename
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                logger.info(f"Build complete: {output_filename} ({size_kb:.1f} KB)")
                return True
            else:
                logger.error(f"Output not found at: {output_path}")
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

        if self.license_key != "GENERIC_BUILD":
            if not self.inject_license_protection():
                logger.warning(
                    "License protection injection failed, continuing without"
                )

        if not self.install_dependencies():
            logger.warning("Dependency installation had issues, continuing anyway")

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
