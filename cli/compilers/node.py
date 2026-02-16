import os
import json
import asyncio
import uuid
import shutil
import tempfile
import re
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple

from .base import BaseCompiler
from cli.terminal import Colors, print_progress_bar

class NodeJSCompiler(BaseCompiler):
    """
    Node.js compiler using pkg.
    Modernized with bootstrap wrapping and asyncio.
    """

    async def pre_flight(self) -> bool:
        """Verify Node.js and pkg are available."""
        try:
            # Check for npm/node
            node_check = await asyncio.create_subprocess_exec(
                "node", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await node_check.wait()
            return node_check.returncode == 0
        except Exception:
            return False

    async def inject_wrapper(self) -> bool:
        """
        No-op for NodeJSCompiler as injection happens during compile()
        in the temporary build directory.
        """
        return True

    def _prepare_package_json(self, build_dir: Path, bootstrap_filename: str, entry_file: str):
        """
        Configure package.json for pkg, including all assets.
        Ported from server/compilers/nodejs_compiler.py
        """
        package_json_path = build_dir / "package.json"

        # Scan ALL .js and .json files
        all_js_files = []
        for js_file in build_dir.rglob("*.js"):
            if "node_modules" in str(js_file): continue
            all_js_files.append(js_file.relative_to(build_dir).as_posix())

        all_json_files = []
        for json_file in build_dir.rglob("*.json"):
            if "node_modules" in str(json_file) or json_file.name in ("package.json", "package-lock.json"):
                continue
            all_json_files.append(json_file.relative_to(build_dir).as_posix())

        if not package_json_path.exists():
            package_data = {
                "name": "codevault-app",
                "version": "1.0.0",
                "bin": bootstrap_filename,
                "pkg": {
                    "scripts": all_js_files + ["node_modules/**/*.js", "node_modules/**/*.cjs"],
                    "assets": all_json_files + ["node_modules/**/*.json", "node_modules/**/*.node"]
                }
            }
        else:
            try:
                package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
            except:
                package_data = {"name": "codevault-app"}
            
            package_data["bin"] = bootstrap_filename
            package_data["pkg"] = {
                "scripts": all_js_files + ["node_modules/**/*.js", "node_modules/**/*.cjs"],
                "assets": all_json_files + ["node_modules/**/*.json", "node_modules/**/*.node"]
            }

        package_json_path.write_text(json.dumps(package_data, indent=2), encoding="utf-8")

    async def compile(self) -> Tuple[bool, Optional[Path]]:
        """
        Compile Node.js project using pkg with bootstrap wrapping.
        """
        entry_file = self.config.get("entry_file", "")
        output_name = self.config.get("output_name") or self.config.get("project_name") or "output"
        
        # 1. Create temporary build directory
        build_dir = Path(tempfile.mkdtemp(prefix="cv_node_build_"))
        print(f"[NodeJSCompiler] Created build directory: {build_dir}")

        try:
            # 2. Copy source to build directory
            for item in self.project_dir.iterdir():
                if item.name in ("build", "dist", "node_modules", ".git"): continue
                dest = build_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # 3. Create bootstrap file
            bootstrap_filename = f"_cv_bootstrap_{uuid.uuid4().hex[:8]}.js"
            bootstrap_path = build_dir / bootstrap_filename
            
            # Simplified wrapper logic for CLI
            bootstrap_content = f"""
// CodeVault Bootstrap Loader
console.log('[CodeVault] Verifying license...');

// In a real implementation, we would call the license validation here
// For now, we mock success to demonstrate the bootstrap flow
const startApp = () => {{
    console.log('[CodeVault] License verified. Starting application...');
    try {{
        require('./{entry_file.replace("", "/")}');
    }} catch (e) {{
        console.error('[CodeVault] Startup error:', e);
        process.exit(1);
    }}
}};

startApp();
"""
            bootstrap_path.write_text(bootstrap_content, encoding="utf-8")

            # 4. Prepare package.json
            self._prepare_package_json(build_dir, bootstrap_filename, entry_file)

            # 5. Run pkg
            target = self.config.get("platform", "node18-win-x64")
            if target == "windows": target = "node18-win-x64"

            cmd = ["npx.cmd", "-y", "@yao-pkg/pkg", ".", "--targets", target, "--output", str(build_dir / output_name), "--compress", "GZip"]
            
            print(f"[NodeJSCompiler] Running pkg: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes: break
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line: print(f"  pkg: {line}")

            await process.wait()
            
            if process.returncode == 0:
                # Move output back to project dir
                exe_name = f"{output_name}.exe"
                if (build_dir / exe_name).exists():
                    shutil.copy2(build_dir / exe_name, self.project_dir / exe_name)
                    return True, self.project_dir
            
            return False, None

        finally:
            # Cleanup
            # shutil.rmtree(build_dir, ignore_errors=True)
            pass
