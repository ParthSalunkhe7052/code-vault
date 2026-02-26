import os
import json
import asyncio
import uuid
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple

from .base import BaseCompiler


class NodeJSCompiler(BaseCompiler):
    """
    Node.js compiler using pkg.
    Modernized with bootstrap wrapping and asyncio.
    """

    async def pre_flight(self) -> bool:
        """Verify Node.js and pkg are available."""
        from cli.codevault_cli.utils.health import check_node

        success, _, _ = await check_node()
        return success

    async def inject_wrapper(self) -> bool:
        """No-op for NodeJSCompiler as injection happens during compile()."""
        return True

    def _prepare_package_json(
        self, build_dir: Path, bootstrap_filename: str, entry_file: str
    ):
        """Configure package.json for pkg, including all assets."""
        package_json_path = build_dir / "package.json"

        all_js_files = []
        for js_file in build_dir.rglob("*.js"):
            if "node_modules" in str(js_file):
                continue
            all_js_files.append(js_file.relative_to(build_dir).as_posix())

        all_json_files = []
        for json_file in build_dir.rglob("*.json"):
            if "node_modules" in str(json_file) or json_file.name in (
                "package.json",
                "package-lock.json",
            ):
                continue
            all_json_files.append(json_file.relative_to(build_dir).as_posix())

        if not package_json_path.exists():
            package_data = {
                "name": "codevault-app",
                "version": "1.0.0",
                "bin": bootstrap_filename,
                "pkg": {
                    "scripts": all_js_files
                    + ["node_modules/**/*.js", "node_modules/**/*.cjs"],
                    "assets": all_json_files
                    + ["node_modules/**/*.json", "node_modules/**/*.node"],
                },
            }
        else:
            try:
                package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
            except:
                package_data = {"name": "codevault-app"}

            package_data["bin"] = bootstrap_filename
            package_data["pkg"] = {
                "scripts": all_js_files
                + ["node_modules/**/*.js", "node_modules/**/*.cjs"],
                "assets": all_json_files
                + ["node_modules/**/*.json", "node_modules/**/*.node"],
            }

        package_json_path.write_text(
            json.dumps(package_data, indent=2), encoding="utf-8"
        )

    async def compile(
        self, progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[bool, Optional[Path]]:
        """
        Compile Node.js project using pkg with bootstrap wrapping.
        """
        entry_file = self.config.get("entry_file", "")
        output_name = (
            self.config.get("output_name")
            or self.config.get("project_name")
            or "output"
        )

        build_dir = Path(tempfile.mkdtemp(prefix="cv_node_build_"))
        if progress_callback:
            progress_callback(5, "Preparing build directory...")

        try:
            # Copy source
            for item in self.project_dir.iterdir():
                if item.name in ("build", "dist", "node_modules", ".git"):
                    continue
                dest = build_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            if progress_callback:
                progress_callback(10, "Injecting bootstrap...")
            bootstrap_filename = f"_cv_bootstrap_{uuid.uuid4().hex[:8]}.js"
            bootstrap_path = build_dir / bootstrap_filename

            bootstrap_content = f"""
console.log('[CodeVault] Verifying license...');
require('./{entry_file.replace("\\", "/")}');
"""
            bootstrap_path.write_text(bootstrap_content, encoding="utf-8")
            self._prepare_package_json(build_dir, bootstrap_filename, entry_file)

            if progress_callback:
                progress_callback(20, "Running pkg...")
            target = self.config.get("platform", "node18-win-x64")
            if target == "windows":
                target = "node18-win-x64"

            cmd = [
                "npx.cmd",
                "-y",
                "@yao-pkg/pkg",
                ".",
                "--targets",
                target,
                "--output",
                str(build_dir / output_name),
                "--compress",
                "GZip",
                "--public-packages",
                "*",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            start_time = asyncio.get_event_loop().time()
            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break

                # Estimate progress for pkg
                elapsed = asyncio.get_event_loop().time() - start_time
                est_percent = min(95, 20 + int(elapsed / 120 * 75))
                if progress_callback:
                    progress_callback(est_percent, "Bundling...")

            await process.wait()

            if process.returncode == 0:
                exe_name = f"{output_name}.exe"
                if (build_dir / exe_name).exists():
                    shutil.copy2(build_dir / exe_name, self.project_dir / exe_name)
                    return True, self.project_dir

            return False, None

        finally:
            shutil.rmtree(build_dir, ignore_errors=True)
