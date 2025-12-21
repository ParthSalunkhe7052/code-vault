import os
import shutil
import subprocess
import json
import logging
import asyncio
import uuid
import tempfile
from pathlib import Path
from typing import Optional, Callable

# License Wrapper Script for Node.js
# This script is injected into the entry file to validate the license before running the user's code.
NODE_LICENSE_WRAPPER = r"""
const crypto = require('crypto');
const os = require('os');
const https = require('https');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Configuration (Injected by compiler)
const LICENSE_KEY = '{{LICENSE_KEY}}';
const API_URL = '{{API_URL}}'; // e.g. https://api.codevault.com/api/v1/license/validate

// Helper to get HWID
function getHWID() {
  try {
      const cpus = os.cpus();
      const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : 'generic';
      const info = `${os.hostname()}|${os.platform()}|${os.arch()}|${os.totalmem()}|${cpuModel}`;
      return crypto.createHash('sha256').update(info).digest('hex');
  } catch (e) {
      return 'unknown-hwid';
  }
}

// Get the directory where the executable is located
function getExeDir() {
    // For pkg-compiled executables, process.execPath points to the exe
    // For regular node, it points to the node binary
    if (process.pkg) {
        return path.dirname(process.execPath);
    }
    return __dirname;
}

// Get the license key file path
function getLicenseKeyPath() {
    return path.join(getExeDir(), 'license.key');
}

// Prompt user for license key via console
function promptForLicenseKey() {
    return new Promise((resolve) => {
        // Check if we have a TTY (console) attached
        // If not (e.g., double-clicked exe), we cannot prompt
        if (!process.stdin.isTTY) {
            console.error('[CodeVault] ERROR: No console available for license key input.');
            console.error('[CodeVault] Please run this application from a command prompt,');
            console.error('[CodeVault] or create a license.key file next to the executable.');
            resolve(null);
            return;
        }
        
        try {
            const rl = readline.createInterface({
                input: process.stdin,
                output: process.stdout
            });
            
            console.log('\n' + '='.repeat(50));
            console.log('  LICENSE KEY REQUIRED');
            console.log('='.repeat(50));
            
            rl.question('Enter License Key: ', (answer) => {
                rl.close();
                const key = answer ? answer.trim() : null;
                resolve(key);
            });
        } catch (e) {
            console.error('[CodeVault] ERROR: Could not prompt for license key:', e.message);
            resolve(null);
        }
    });
}

// Load license from file or prompt user
async function loadOrPromptLicense() {
    const licensePath = getLicenseKeyPath();
    
    // Try to load from file first
    if (fs.existsSync(licensePath)) {
        try {
            const key = fs.readFileSync(licensePath, 'utf-8').trim();
            if (key) {
                console.log(`[CodeVault] Loaded license from ${licensePath}`);
                return key;
            }
        } catch (e) {
            console.log(`[CodeVault] Warning: Could not read license file: ${e.message}`);
        }
    }
    
    // Prompt for license
    console.log('[CodeVault] No license key found. Please enter your license key.');
    const licenseKey = await promptForLicenseKey();
    
    if (!licenseKey) {
        console.log('\n❌ No license key provided. Exiting...');
        process.exit(1);
    }
    
    // Save license for future runs
    try {
        fs.writeFileSync(licensePath, licenseKey, 'utf-8');
        console.log(`[CodeVault] License key saved to ${licensePath}`);
    } catch (e) {
        console.log(`[CodeVault] Warning: Could not save license file: ${e.message}`);
    }
    
    return licenseKey;
}

// Delete saved license file (on validation failure)
function deleteSavedLicense() {
    try {
        const licensePath = getLicenseKeyPath();
        if (fs.existsSync(licensePath)) {
            fs.unlinkSync(licensePath);
            console.log('License file removed. Please try again with a valid key.');
        }
    } catch (e) {
        // Ignore cleanup errors
    }
}

// Validate License
async function validateLicense() {
  let currentLicenseKey = LICENSE_KEY;
  
  if (currentLicenseKey === 'DEMO') {
    console.log('[CodeVault] Running in DEMO mode');
    return true;
  }
  
  // Handle GENERIC_BUILD mode - prompt for license at runtime
  if (currentLicenseKey === 'GENERIC_BUILD') {
    currentLicenseKey = await loadOrPromptLicense();
  }
  
  return new Promise((resolve, reject) => {
    const hwid = getHWID();
    const nonce = crypto.randomBytes(16).toString('hex');
    const timestamp = Math.floor(Date.now() / 1000);
    
    // Parse URL
    let urlObj;
    try {
        urlObj = new URL(API_URL);
    } catch (e) {
        console.error('[CodeVault] Invalid API URL');
        process.exit(1);
    }

    const postData = JSON.stringify({
      license_key: currentLicenseKey,
      hwid: hwid,
      nonce: nonce,
      timestamp: timestamp,
      machine_name: os.hostname()
    });
    
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || 443,
      path: urlObj.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };
    
    // Determine protocol
    const lib = urlObj.protocol === 'http:' ? require('http') : require('https');

    const req = lib.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
            if (res.statusCode !== 200) {
                 console.error(`[CodeVault] Validation failed (HTTP ${res.statusCode})`);
                 // Delete saved license on server error that indicates invalid
                 if (LICENSE_KEY === 'GENERIC_BUILD') {
                     deleteSavedLicense();
                 }
                 process.exit(1);
            }

            const response = JSON.parse(body);
            if (response.status === 'valid') {
              resolve(true);
            } else {
              console.error('[CodeVault] License invalid:', response.message || 'Unknown error');
              // Delete saved license on validation failure
              if (LICENSE_KEY === 'GENERIC_BUILD') {
                  deleteSavedLicense();
              }
              process.exit(1);
            }
        } catch (e) {
            console.error('[CodeVault] Failed to parse validation response');
            process.exit(1);
        }
      });
    });
    
    req.on('error', (e) => {
        console.error('[CodeVault] Connection error:', e.message);
        // Fail open or closed? Currently failing closed.
        process.exit(1); 
    });
    
    req.write(postData);
    req.end();
  });
}

// Export validation function
module.exports = validateLicense;
"""

class NodeJSCompiler:
    def __init__(self, node_modules_path: Path):
        self.node_modules_path = node_modules_path
        
        # Robust path resolution for tools
        self.pkg_bin = self._find_tool("pkg")
        self.obfuscator_bin = self._find_tool("javascript-obfuscator")

    def _find_tool(self, tool_name: str) -> Path:
        """Find executable path for a node tool."""
        # 1. Check local node_modules/.bin (passed in init)
        local_bin = self.node_modules_path / ".bin" / tool_name
        if os.name == 'nt':
             local_bin = local_bin.with_suffix(".cmd")
        
        if local_bin.exists():
            return local_bin
            
        # 2. Check server root node_modules (one level up from where we assume main.py is)
        # This is heuristics.
        server_root_bin = self.node_modules_path.parent / "node_modules" / ".bin" / tool_name
        if os.name == 'nt':
             server_root_bin = server_root_bin.with_suffix(".cmd")
        
        if server_root_bin.exists():
            return server_root_bin
            
        # 3. Check system PATH
        system_path = shutil.which(tool_name)
        if system_path:
            return Path(system_path)
            
        # 4. Fallback to just the command name (hope it's in path at runtime)
        return Path(tool_name)

    async def log(self, message: str, callback: Optional[Callable] = None):
        print(f"[NodeJSCompiler] {message}")
        if callback:
            await callback(message)
    
    async def _run_npm_install(self, source_dir: Path, log_callback: Optional[Callable] = None) -> None:
        """
        Check if node_modules exists, run npm install if missing.
        Raises Exception if npm is not found or installation fails.
        """
        node_modules_path = source_dir / "node_modules"
        package_json_path = source_dir / "package.json"
        
        # Only run npm install if package.json exists
        if not package_json_path.exists():
            await self.log("No package.json found, skipping npm install.", log_callback)
            return
        
        if node_modules_path.exists() and any(node_modules_path.iterdir()):
            await self.log("✓ node_modules already exists, skipping npm install.", log_callback)
            return
        
        # Check if npm is available
        npm_path = shutil.which("npm")
        if not npm_path:
            raise Exception("❌ npm not found. Please install Node.js and npm first.")
        
        await self.log("📦 Installing dependencies (npm install)...", log_callback)
        
        try:
            process = await asyncio.create_subprocess_exec(
                npm_path, "install",
                cwd=str(source_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT  # Merge stderr into stdout for unified logging
            )
            
            # Stream output to log_callback
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode('utf-8', errors='replace').rstrip()
                if decoded_line:
                    await self.log(f"  npm: {decoded_line}", log_callback)
            
            await process.wait()
            
            if process.returncode != 0:
                raise Exception(f"npm install failed with exit code {process.returncode}")
            
            await self.log("✓ Dependencies installed successfully.", log_callback)
            
        except FileNotFoundError:
            raise Exception("❌ npm not found. Please install Node.js and npm first.")
        except Exception as e:
            raise Exception(f"❌ npm install failed: {str(e)}")

    def _prepare_package_json(self, build_dir: Path, bootstrap_filename: str, log_callback_sync=None) -> None:
        """
        Ensure package.json exists and has a proper 'bin' field pointing to our bootstrap.
        If no package.json exists, creates a minimal one.
        If package.json exists but lacks 'bin', adds it.
        """
        package_json_path = build_dir / "package.json"
        
        if not package_json_path.exists():
            # Create minimal package.json
            package_data = {
                "name": "codevault-wrapped-app",
                "version": "1.0.0",
                "bin": bootstrap_filename,
                "pkg": {
                    "assets": ["**/*"],
                    "outputPath": "dist"
                }
            }
            with open(package_json_path, 'w', encoding='utf-8') as f:
                json.dump(package_data, f, indent=2)
            return
        
        # Read existing package.json
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
        except json.JSONDecodeError:
            # Malformed package.json, create a fresh one
            package_data = {
                "name": "codevault-wrapped-app",
                "version": "1.0.0"
            }
        
        # Add or update bin field to point to bootstrap
        if "bin" not in package_data:
            package_data["bin"] = bootstrap_filename
        
        # Write back
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(package_data, f, indent=2)

    async def compile(self, 
                     source_dir: Path, 
                     entry_file: str, 
                     output_dir: Path, 
                     output_name: str, 
                     license_key: str, 
                     api_url: str,
                     options: dict, 
                     log_callback: Optional[Callable] = None,
                     skip_obfuscation: bool = True) -> Path:
        """
        Compiles a Node.js project:
        1. Install dependencies (npm install) if needed
        2. Copy source to temp build directory
        3. Inject license wrapper
        4. Obfuscate code (in-place on copy)
        5. Package with pkg
        6. Cleanup temp directory
        """
        
        await self.log("Starting Node.js compilation process...", log_callback)
        await self.log(f"Source directory: {source_dir}", log_callback)
        
        # Create a unique temporary build directory
        build_dir = None
        
        try:
            # ===============================================
            # STEP 1: Install dependencies in source_dir first
            # ===============================================
            await self._run_npm_install(source_dir, log_callback)
            
            # Validate entry file exists
            entry_path = source_dir / entry_file
            if not entry_path.exists():
                raise Exception(f"Entry file not found: {entry_path}")
            
            await self.log(f"✓ Entry file validated: {entry_file}", log_callback)
            
            # Check if required tools are available
            pkg_available = str(self.pkg_bin) != "pkg" or shutil.which("pkg") or shutil.which("npx")
            if not pkg_available:
                raise Exception("❌ 'pkg' not found. Please install Node.js and run: npm install -g pkg")
            
            obfuscator_available = str(self.obfuscator_bin) != "javascript-obfuscator" or shutil.which("javascript-obfuscator")
            should_obfuscate = not skip_obfuscation and obfuscator_available
            
            if skip_obfuscation:
                await self.log("⚡ Skipping obfuscation (faster build)", log_callback)
            elif not obfuscator_available:
                await self.log("⚠️ javascript-obfuscator not found. Code will not be obfuscated.", log_callback)

            # ===============================================
            # STEP 2: Copy source to temp build directory
            # ===============================================
            await self.log("📁 Creating temporary build directory...", log_callback)
            
            # Create temp directory in system temp
            build_dir = Path(tempfile.mkdtemp(prefix="cv_nodejs_build_"))
            await self.log(f"Build directory: {build_dir}", log_callback)
            
            # Copy entire source_dir to build_dir
            # Use shutil.copytree with dirs_exist_ok=True to copy contents
            for item in source_dir.iterdir():
                src_path = source_dir / item.name
                dst_path = build_dir / item.name
                
                if src_path.is_dir():
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
            
            await self.log("✓ Source copied to build directory.", log_callback)
            
            # Verify node_modules was copied if package.json has dependencies
            package_json_path = build_dir / "package.json"
            node_modules_in_build = build_dir / "node_modules"
            if package_json_path.exists():
                try:
                    with open(package_json_path, 'r', encoding='utf-8') as f:
                        pkg_data = json.load(f)
                    has_deps = bool(pkg_data.get('dependencies') or pkg_data.get('devDependencies'))
                    if has_deps and not node_modules_in_build.exists():
                        await self.log("⚠️ Warning: package.json has dependencies but node_modules was not copied.", log_callback)
                        await self.log("  The built executable may fail to load modules.", log_callback)
                except Exception:
                    pass

            # ===============================================
            # STEP 3: Inject License Wrapper into build_dir
            # ===============================================
            wrapper_path = build_dir / "cv_license_wrapper.js"
            wrapper_content = NODE_LICENSE_WRAPPER.replace('{{LICENSE_KEY}}', license_key).replace('{{API_URL}}', api_url)
            
            with open(wrapper_path, 'w', encoding='utf-8') as f:
                f.write(wrapper_content)
            
            # Create a bootstrap entry file with UNIQUE name
            bootstrap_filename = f"_cv_bootstrap_{uuid.uuid4().hex[:8]}.js"
            bootstrap_entry = build_dir / bootstrap_filename
            
            # cv_bootstrap.js triggers validation, then requires the MAIN file.
            # Normalize entry_file: replace backslashes with forward slashes for Node.js
            normalized_entry = entry_file.replace('\\', '/')
            
            bootstrap_content = f"""
const path = require('path');
const validateLicense = require('./cv_license_wrapper');

validateLicense().then(() => {{
    console.log('[CodeVault] License verified. Starting application...');
    // Use path.join for proper resolution inside pkg snapshot
    const entryPath = path.join(__dirname, '{normalized_entry}');
    require(entryPath);
}}).catch(err => {{
    console.error('[CodeVault] Startup error:', err);
    process.exit(1);
}});
"""
            with open(bootstrap_entry, 'w', encoding='utf-8') as f:
                f.write(bootstrap_content)
                
            await self.log("✓ License wrapper injected.", log_callback)
            
            # ===============================================
            # STEP 4: Update package.json bin field
            # ===============================================
            self._prepare_package_json(build_dir, bootstrap_filename)
            await self.log("✓ package.json configured.", log_callback)

            # ===============================================
            # STEP 5: Obfuscation (in-place on build_dir copy)
            # ===============================================
            if should_obfuscate:
                await self.log("🔒 Obfuscating JavaScript code (in-place)...", log_callback)
                
                # Obfuscate in-place, excluding node_modules
                # javascript-obfuscator with --output pointing to same dir overwrites files
                cmd = [
                    str(self.obfuscator_bin),
                    str(build_dir),
                    "--output", str(build_dir),
                    "--ignore-require-imports", "true",
                    "--compact", "true",
                    "--control-flow-flattening", "true",
                    "--string-array", "true",
                    "--string-array-encoding", "rc4",
                    "--exclude", "**/node_modules/**",
                    "--exclude", "node_modules/**"
                ]

                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        error_output = stderr.decode('utf-8', errors='replace')
                        await self.log(f"⚠️ Obfuscation warning: {error_output}", log_callback)
                        await self.log("Continuing without obfuscation...", log_callback)
                    else:
                        await self.log("✓ Obfuscation completed.", log_callback)
                except Exception as e:
                    await self.log(f"⚠️ Obfuscation failed: {e}. Continuing without obfuscation.", log_callback)
            
            # ===============================================
            # STEP 6: Packaging with pkg (from build_dir)
            # ===============================================
            await self.log("📦 Packaging application into executable...", log_callback)
            
            target = options.get('target', 'node18-win-x64')
            
            output_exe = output_dir / output_name
            if os.name == 'nt' and not output_name.endswith('.exe'):
                output_exe = output_exe.with_suffix('.exe')
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            pkg_entry = build_dir / bootstrap_filename
                
            pkg_cmd = [
                str(self.pkg_bin),
                str(pkg_entry),
                "--target", target,
                "--output", str(output_exe),
                "--public",
                "--no-bytecode",  # Disable bytecode to avoid "Failed to make bytecode" errors
                "--compress", "GZip"  # Add compression since we're not using bytecode
            ]
            
            await self.log(f"Running: {' '.join(pkg_cmd)}", log_callback)
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *pkg_cmd,
                    cwd=str(build_dir),  # Run pkg from build_dir so it finds node_modules
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT  # Merge for unified logging
                )
                
                # Stream output
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    if decoded_line:
                        await self.log(f"  pkg: {decoded_line}", log_callback)
                
                await process.wait()
                 
                if process.returncode != 0:
                    raise Exception(f"pkg failed with exit code {process.returncode}")
                 
                await self.log("✓ Packaging completed.", log_callback)
                 
            except Exception as e:
                await self.log(f"❌ Packaging error: {e}", log_callback)
                raise e
                
            if not output_exe.exists():
                raise Exception("Output executable was not created.")
            
            await self.log(f"✅ Build successful: {output_exe}", log_callback)
            return output_exe
            
        finally:
            # ===============================================
            # CLEANUP: Always remove temp build directory
            # ===============================================
            if build_dir and build_dir.exists():
                try:
                    await self.log("🧹 Cleaning up temporary build directory...", log_callback)
                    shutil.rmtree(build_dir)
                    await self.log("✓ Cleanup complete.", log_callback)
                except Exception as cleanup_error:
                    await self.log(f"⚠️ Cleanup warning: {cleanup_error}", log_callback)
                    # Don't raise - cleanup failure shouldn't fail the build
