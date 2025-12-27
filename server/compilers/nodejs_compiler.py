"""
Node.js Compiler for CodeVault.
Compiles Node.js projects with license protection using pkg.
"""

import os
import shutil
import json
import asyncio
import uuid
import tempfile
import re
from pathlib import Path
from typing import Optional, Callable


# Load the license wrapper template from file
def _load_wrapper_template() -> str:
    template_path = Path(__file__).parent / "templates" / "nodejs_license_wrapper.js"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    else:
        # Fallback: minimal inline template
        return """
const LICENSE_KEY = '{{LICENSE_KEY}}';
const API_URL = '{{API_URL}}';
console.log('[CodeVault] Template file not found. Running in DEMO mode.');
module.exports = async () => true;
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
        if os.name == "nt":
            local_bin = local_bin.with_suffix(".cmd")

        if local_bin.exists():
            return local_bin

        # 2. Check server root node_modules (one level up from where we assume main.py is)
        server_root_bin = (
            self.node_modules_path.parent / "node_modules" / ".bin" / tool_name
        )
        if os.name == "nt":
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

    async def _run_npm_install(
        self, source_dir: Path, log_callback: Optional[Callable] = None
    ) -> None:
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
            await self.log(
                "✓ node_modules already exists, skipping npm install.", log_callback
            )
            return

        # Check if npm is available
        npm_path = shutil.which("npm")
        if not npm_path:
            raise Exception("❌ npm not found. Please install Node.js and npm first.")

        await self.log("📦 Installing dependencies (npm install)...", log_callback)

        try:
            process = await asyncio.create_subprocess_exec(
                npm_path,
                "install",
                cwd=str(source_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="replace").rstrip()
                if decoded_line:
                    await self.log(f"  npm: {decoded_line}", log_callback)

            await process.wait()

            if process.returncode != 0:
                raise Exception(
                    f"npm install failed with exit code {process.returncode}"
                )

            await self.log("✓ Dependencies installed successfully.", log_callback)

        except FileNotFoundError:
            raise Exception("❌ npm not found. Please install Node.js and npm first.")
        except Exception as e:
            raise Exception(f"❌ npm install failed: {str(e)}")

    def _prepare_package_json(
        self, build_dir: Path, bootstrap_filename: str, entry_file: str
    ) -> None:
        """
        Ensure package.json exists and has a proper 'bin' field pointing to our bootstrap.
        Also configures 'pkg' scripts to ensure ALL JS files are included (fixes dynamic require).
        """
        package_json_path = build_dir / "package.json"

        # CRITICAL FIX: Scan ALL .js files in the project and add to scripts
        all_js_files = []
        for js_file in build_dir.rglob("*.js"):
            if "node_modules" in str(js_file):
                continue
            rel_path = js_file.relative_to(build_dir).as_posix()
            all_js_files.append(rel_path)

        # Also include .json files that might be required
        all_json_files = []
        for json_file in build_dir.rglob("*.json"):
            if "node_modules" in str(json_file) or json_file.name in (
                "package.json",
                "package-lock.json",
            ):
                continue
            rel_path = json_file.relative_to(build_dir).as_posix()
            all_json_files.append(rel_path)

        if not package_json_path.exists():
            package_data = {
                "name": "codevault-wrapped-app",
                "version": "1.0.0",
                "bin": bootstrap_filename,
                "pkg": {
                    "scripts": all_js_files
                    + [
                        "node_modules/**/*.js",
                        "node_modules/**/*.cjs",
                        "node_modules/**/*.mjs",
                    ],
                    "assets": all_json_files
                    + ["node_modules/**/*.json", "node_modules/**/*.node"],
                    "outputPath": "dist",
                },
            }
            with open(package_json_path, "w", encoding="utf-8") as f:
                json.dump(package_data, f, indent=2)
            return

        # Read existing package.json
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                package_data = json.load(f)
        except json.JSONDecodeError:
            package_data = {"name": "codevault-wrapped-app", "version": "1.0.0"}

        package_data["bin"] = bootstrap_filename
        package_data["pkg"] = {
            "scripts": all_js_files
            + [
                "node_modules/**/*.js",
                "node_modules/**/*.cjs",
                "node_modules/**/*.mjs",
            ],
            "assets": all_json_files
            + ["node_modules/**/*.json", "node_modules/**/*.node"],
        }

        with open(package_json_path, "w", encoding="utf-8") as f:
            json.dump(package_data, f, indent=2)

    async def compile(
        self,
        source_dir: Path,
        entry_file: str,
        output_dir: Path,
        output_name: str,
        license_key: str,
        api_url: str,
        options: dict,
        log_callback: Optional[Callable] = None,
        skip_obfuscation: bool = True,
    ) -> Path:
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

        build_dir = None

        try:
            # STEP 1: Validate entry file and tools before copying
            # Security: Validate entry_file doesn't escape source_dir
            entry_path = (source_dir / entry_file).resolve()
            source_resolved = source_dir.resolve()
            if (
                not str(entry_path).startswith(str(source_resolved) + os.sep)
                and entry_path != source_resolved
            ):
                raise Exception("Entry file path is invalid - path traversal detected")
            if not entry_path.exists():
                raise Exception("Entry file not found")

            await self.log(f"✓ Entry file validated: {entry_file}", log_callback)

            pkg_available = (
                str(self.pkg_bin) != "pkg" or shutil.which("pkg") or shutil.which("npx")
            )
            if not pkg_available:
                raise Exception(
                    "❌ 'pkg' not found. Please install Node.js and run: npm install -g pkg"
                )

            obfuscator_available = str(
                self.obfuscator_bin
            ) != "javascript-obfuscator" or shutil.which("javascript-obfuscator")
            should_obfuscate = not skip_obfuscation and obfuscator_available

            if skip_obfuscation:
                await self.log("⚡ Skipping obfuscation (faster build)", log_callback)
            elif not obfuscator_available:
                await self.log(
                    "⚠️ javascript-obfuscator not found. Code will not be obfuscated.",
                    log_callback,
                )

            # STEP 2: Copy source to temp build directory
            await self.log("📁 Creating temporary build directory...", log_callback)

            build_dir = Path(tempfile.mkdtemp(prefix="cv_nodejs_build_"))
            await self.log(f"Build directory: {build_dir}", log_callback)

            for item in source_dir.iterdir():
                src_path = source_dir / item.name
                dst_path = build_dir / item.name

                # lgtm[py/path-injection] - build_dir is from tempfile.mkdtemp(), item.name is validated
                if src_path.is_dir():
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)

            await self.log("✓ Source copied to build directory.", log_callback)

            # Check and install dependencies if needed
            package_json_path = build_dir / "package.json"
            node_modules_in_build = build_dir / "node_modules"
            if package_json_path.exists():
                try:
                    with open(package_json_path, "r", encoding="utf-8") as f:
                        pkg_data = json.load(f)
                    has_deps = bool(
                        pkg_data.get("dependencies") or pkg_data.get("devDependencies")
                    )
                    if has_deps and not node_modules_in_build.exists():
                        await self.log(
                            "📦 Installing dependencies in build directory...",
                            log_callback,
                        )
                        await self._run_npm_install(build_dir, log_callback)
                except Exception as e:
                    await self.log(
                        f"⚠️ Could not check/install dependencies: {e}", log_callback
                    )

            # STEP 3: Inject License Wrapper into build_dir
            wrapper_path = build_dir / "cv_license_wrapper.js"

            # Load wrapper template and inject values
            wrapper_template = _load_wrapper_template()
            safe_license_key = json.dumps(license_key)
            safe_api_url = json.dumps(api_url)
            wrapper_content = wrapper_template.replace(
                "'{{LICENSE_KEY}}'", safe_license_key
            ).replace("'{{API_URL}}'", safe_api_url)

            # lgtm[py/path-injection] - wrapper_path is in build_dir which is from tempfile.mkdtemp()
            with open(wrapper_path, "w", encoding="utf-8") as f:
                f.write(wrapper_content)

            # Create bootstrap entry file
            bootstrap_filename = f"_cv_bootstrap_{uuid.uuid4().hex[:8]}.js"
            bootstrap_entry = build_dir / bootstrap_filename

            normalized_entry = entry_file.replace("\\", "/")

            bootstrap_content = f"""
const validateLicense = require('./cv_license_wrapper');
const readline = require('readline');

function exitWithError(err) {{
    console.error('[CodeVault] Startup error:', err);
    console.log('\\nPress any key to exit...');
    
    if (process.stdin.isTTY) {{
        process.stdin.setRawMode(true);
    }}
    process.stdin.resume();
    process.stdin.on('data', () => process.exit(1));
}}

validateLicense().then(() => {{
    console.log('[CodeVault] License verified. Starting application...');
    try {{
        require('./{normalized_entry}');
    }} catch (e) {{
        exitWithError(e);
    }}
}}).catch(err => {{
    exitWithError(err);
}});
"""
            with open(bootstrap_entry, "w", encoding="utf-8") as f:
                f.write(bootstrap_content)

            await self.log("✓ License wrapper injected.", log_callback)

            # STEP 4: Update package.json bin field & pkg scripts
            self._prepare_package_json(build_dir, bootstrap_filename, entry_file)
            await self.log("✓ package.json configured.", log_callback)

            # STEP 5: Obfuscation (if enabled)
            if should_obfuscate:
                await self._run_obfuscation(build_dir, log_callback)

            # STEP 6: Packaging with pkg
            await self.log("📦 Packaging application into executable...", log_callback)

            target = options.get("target", "node18-win-x64")

            # Security: Sanitize output_name to prevent path traversal
            safe_output_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", output_name)
            if not safe_output_name:
                safe_output_name = "app"

            output_exe = output_dir / safe_output_name
            if os.name == "nt" and not safe_output_name.endswith(".exe"):
                output_exe = output_exe.with_suffix(".exe")

            # Security: Validate output_exe is within output_dir (CodeQL-recognized pattern)
            output_exe_resolved = output_exe.resolve()
            output_dir_resolved = output_dir.resolve()
            if not str(output_exe_resolved).startswith(
                str(output_dir_resolved) + os.sep
            ):
                raise Exception("Invalid output path - path traversal detected")

            output_dir.mkdir(parents=True, exist_ok=True)

            pkg_cmd = [
                str(self.pkg_bin),
                ".",
                "--target",
                target,
                "--output",
                str(output_exe),
                "--public",
                "--no-bytecode",
                "--compress",
                "GZip",
            ]

            await self.log(f"Running: {' '.join(pkg_cmd)}", log_callback)

            bundling_warnings = []

            try:
                process = await asyncio.create_subprocess_exec(
                    *pkg_cmd,
                    cwd=str(build_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded_line = line.decode("utf-8", errors="replace").rstrip()
                    if decoded_line:
                        # Filter out noisy warnings from test files and non-critical messages
                        is_noisy = any(
                            [
                                "Cannot find module" in decoded_line
                                and "/test" in decoded_line,
                                "Cannot find module 'tape'" in decoded_line,
                                "Cannot find module 'mock-property'" in decoded_line,
                                "Cannot find module 'for-each'" in decoded_line,
                                "Cannot find module 'es-value-fixtures'"
                                in decoded_line,
                                "Cannot find module 'benchmark'" in decoded_line,
                                "Cannot find module 'async'" in decoded_line,
                                "Cannot find module 'core-js" in decoded_line,
                                "Path must be a string" in decoded_line,
                                "Non-javascript file is specified" in decoded_line,
                                "Babel parse has failed" in decoded_line,
                            ]
                        )

                        # Only log non-noisy lines
                        if not is_noisy:
                            await self.log(f"  pkg: {decoded_line}", log_callback)

                        # Track critical warnings (excluding test file issues)
                        if (
                            "Cannot resolve" in decoded_line
                            or "was not included" in decoded_line
                        ) and "/test" not in decoded_line:
                            bundling_warnings.append(decoded_line)

                await process.wait()

                if bundling_warnings:
                    await self.log(
                        f"⚠️ Warning: {len(bundling_warnings)} file(s) may not be bundled correctly",
                        log_callback,
                    )
                    for warn in bundling_warnings[:3]:
                        await self.log(f"   → {warn}", log_callback)

                if process.returncode != 0:
                    raise Exception(f"pkg failed with exit code {process.returncode}")

                await self.log("✓ Packaging completed.", log_callback)

            except Exception as e:
                await self.log(f"❌ Packaging error: {e}", log_callback)
                raise e

            # Use the already-validated resolved path for the exists check
            if not output_exe_resolved.exists():
                raise Exception("Output executable was not created.")

            await self.log(f"✅ Build successful: {output_exe.name}", log_callback)
            return output_exe_resolved

        finally:
            # CLEANUP: Always remove temp build directory
            if build_dir and build_dir.exists():
                try:
                    await self.log(
                        "🧹 Cleaning up temporary build directory...", log_callback
                    )
                    shutil.rmtree(build_dir)
                    await self.log("✓ Cleanup complete.", log_callback)
                except Exception as cleanup_error:
                    await self.log(f"⚠️ Cleanup warning: {cleanup_error}", log_callback)

    async def _run_obfuscation(
        self, build_dir: Path, log_callback: Optional[Callable] = None
    ):
        """Run JavaScript obfuscation on the build directory."""
        await self.log("🔒 Obfuscating JavaScript code (in-place)...", log_callback)

        cmd = [
            str(self.obfuscator_bin),
            str(build_dir),
            "--output",
            str(build_dir),
            "--ignore-require-imports",
            "true",
            "--compact",
            "true",
            "--control-flow-flattening",
            "true",
            "--string-array",
            "true",
            "--string-array-encoding",
            "rc4",
            "--exclude",
            "**/node_modules/**",
            "--exclude",
            "node_modules/**",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_output = stderr.decode("utf-8", errors="replace")
                await self.log(f"⚠️ Obfuscation warning: {error_output}", log_callback)
                await self.log("Continuing without obfuscation...", log_callback)
            else:
                await self.log("✓ Obfuscation completed.", log_callback)
        except Exception as e:
            await self.log(
                f"⚠️ Obfuscation failed: {e}. Continuing without obfuscation.",
                log_callback,
            )
