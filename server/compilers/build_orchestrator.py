"""
Build Orchestrator for CodeVault
Coordinates the build process: compile → portable exe

Supports:
- Python projects (Nuitka → portable exe)
- Node.js projects (yao-pkg → portable exe)
"""

import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Literal
from dataclasses import dataclass, field

from .python_compiler import get_python_compiler

logger = logging.getLogger(__name__)


@dataclass
class BuildConfig:
    """Configuration for a build job"""

    # Project info
    project_name: str
    project_version: str = "1.0.0"
    publisher: str = "Unknown Publisher"

    # Source
    source_dir: Path = None
    entry_file: str = ""
    language: Literal["python", "nodejs"] = "python"

    # License
    license_key: str = "GENERIC_BUILD"
    api_url: str = ""
    license_mode: Literal["fixed", "generic", "demo"] = "generic"

    # Output
    output_dir: Path = None

    # Build options
    skip_obfuscation: bool = True
    pkg_target: str = "node18-win-x64"

    # Additional files to include
    include_files: list = field(default_factory=list)


class BuildOrchestrator:
    """
    Orchestrates the complete build process for Python and Node.js projects

    Build flow:
    1. Validate project structure
    2. Compile to standalone executable (Nuitka or yao-pkg)
    3. Return final output path (portable exe)
    """

    def __init__(self):
        self.python_compiler = get_python_compiler()

    async def log(self, message: str, callback: Optional[Callable] = None):
        """Log message and call callback if provided"""
        logger.info(f"[BuildOrchestrator] {message}")
        print(f"[BuildOrchestrator] {message}")
        if callback:
            await callback(message)

    async def build_python_project(
        self, config: BuildConfig, log_callback: Optional[Callable] = None
    ) -> Path:
        """
        Build a Python project

        Steps:
        1. Compile with Nuitka to standalone exe
        """
        await self.log(
            f"🐍 Building Python project: {config.project_name}", log_callback
        )

        # Create temp output for exe
        temp_dir = Path(tempfile.mkdtemp(prefix="cv_python_build_"))

        try:
            # Step 1: Compile with Nuitka
            await self.log("Compiling with Nuitka...", log_callback)

            # Build the project
            exe_path = await self._compile_python(config, temp_dir, log_callback)

            if not exe_path or not exe_path.exists():
                raise Exception("Python compilation failed - no executable produced")

            await self.log(f"✓ Compilation complete: {exe_path.name}", log_callback)

            # Copy exe to output
            final_path = config.output_dir / exe_path.name
            config.output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(exe_path, final_path)
            await self.log(f"✅ Portable exe ready: {final_path}", log_callback)
            return final_path

        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")

    async def _compile_python(
        self,
        config: BuildConfig,
        output_dir: Path,
        log_callback: Optional[Callable] = None,
    ) -> Path:
        """
        Compile Python project with Nuitka using PythonCompiler.

        Provides:
        - Runtime license validation (not embedded keys)
        - Support for generic, demo, and fixed license modes
        """
        await self.log("Using PythonCompiler for build...", log_callback)

        # Determine license key based on mode
        if config.license_mode == "fixed":
            license_key = config.license_key
        elif config.license_mode == "demo":
            license_key = "DEMO"
        else:
            license_key = "GENERIC_BUILD"

        # Call the PythonCompiler
        exe_path = await self.python_compiler.compile(
            source_dir=config.source_dir,
            entry_file=config.entry_file,
            output_dir=output_dir,
            output_name=config.project_name,
            license_key=license_key,
            api_url=config.api_url,
            options={
                "console": True,
                "icon": None,
            },
            log_callback=log_callback,
        )

        return exe_path

    async def build_nodejs_project(
        self, config: BuildConfig, log_callback: Optional[Callable] = None
    ) -> Path:
        """
        Build a Node.js project

        Steps:
        1. Compile with yao-pkg to standalone exe
        """
        await self.log(
            f"📦 Building Node.js project: {config.project_name}", log_callback
        )

        # Import nodejs_compiler
        from .nodejs_compiler import NodeJSCompiler

        # Get server node_modules path
        server_dir = Path(__file__).parent.parent
        node_modules = server_dir / "node_modules"

        compiler = NodeJSCompiler(node_modules)

        # Create temp output for exe
        temp_dir = Path(tempfile.mkdtemp(prefix="cv_nodejs_build_"))

        try:
            # Step 1: Compile with yao-pkg
            await self.log("Compiling with yao-pkg...", log_callback)

            # Determine license key based on mode
            if config.license_mode == "fixed":
                license_key = config.license_key
            elif config.license_mode == "demo":
                license_key = "DEMO"
            else:
                license_key = "GENERIC_BUILD"

            exe_path = await compiler.compile(
                source_dir=config.source_dir,
                entry_file=config.entry_file,
                output_dir=temp_dir,
                output_name=config.project_name,
                license_key=license_key,
                api_url=config.api_url,
                options={"target": config.pkg_target},
                log_callback=log_callback,
                skip_obfuscation=config.skip_obfuscation,
            )

            if not exe_path or not exe_path.exists():
                raise Exception("Node.js compilation failed - no executable produced")

            await self.log(f"✓ Compilation complete: {exe_path.name}", log_callback)

            # Copy exe to output
            final_path = config.output_dir / exe_path.name
            config.output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(exe_path, final_path)
            await self.log(f"✅ Portable exe ready: {final_path}", log_callback)
            return final_path

        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")

    async def build(
        self, config: BuildConfig, log_callback: Optional[Callable] = None
    ) -> Path:
        """
        Build a project based on its language

        Args:
            config: Build configuration
            log_callback: Optional async callback for progress

        Returns:
            Path to the final portable exe
        """
        if config.language == "python":
            return await self.build_python_project(config, log_callback)
        elif config.language == "nodejs":
            return await self.build_nodejs_project(config, log_callback)
        else:
            raise ValueError(f"Unsupported language: {config.language}")


# Singleton instance
_orchestrator: Optional[BuildOrchestrator] = None


def get_build_orchestrator() -> BuildOrchestrator:
    """Get or create the build orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BuildOrchestrator()
    return _orchestrator


def check_build_prerequisites() -> Dict[str, Any]:
    """Check if all build prerequisites are available"""
    # Check yao-pkg
    pkg_path = shutil.which("pkg")
    pkg_available = pkg_path is not None

    # Check Nuitka
    nuitka_path = shutil.which("nuitka")
    nuitka_available = nuitka_path is not None

    return {
        "pkg": {"available": pkg_available, "path": pkg_path},
        "nuitka": {"available": nuitka_available, "path": nuitka_path},
        "all_ready": pkg_available or nuitka_available,
    }
