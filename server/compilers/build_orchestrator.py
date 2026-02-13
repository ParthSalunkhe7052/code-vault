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
import os
import hashlib
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Literal
from dataclasses import dataclass, field

from .python_compiler import get_python_compiler

logger = logging.getLogger(__name__)


# =============================================================================
# Utility Functions
# =============================================================================


def atomic_write_text(path: Path, content: str) -> None:
    """
    Atomically write text to a file.

    Prevents race conditions and file corruption by using temp file + atomic rename.
    """
    import tempfile

    # Create temp file in same directory for atomic rename
    fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # Atomic operation on same filesystem
        os.replace(temp_path, str(path))
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def check_disk_space(path: Path, required_gb: float = 2.0) -> bool:
    """
    Check if enough disk space is available for compilation.

    Args:
        path: Directory to check space in
        required_gb: Required space in GB

    Returns:
        True if enough space available

    Raises:
        BuildError: If insufficient disk space
    """
    stat = shutil.disk_usage(path)
    available_gb = stat.free / (1024**3)
    if available_gb < required_gb:
        raise BuildError(
            f"Insufficient disk space: {available_gb:.1f}GB available, "
            f"{required_gb}GB required",
            "resource_error",
        )
    return True


def get_build_cache_key(source_dir: Path, config: "BuildConfig") -> str:
    """
    Generate cache key based on source code and configuration.

    Args:
        source_dir: Source directory
        config: Build configuration

    Returns:
        Cache key (hex string)
    """
    m = hashlib.md5()
    # Include config in cache key
    m.update(str(config).encode())

    # Include all source files (sorted for consistency)
    for py_file in sorted(source_dir.rglob("*.py")):
        try:
            m.update(py_file.read_bytes())
        except (OSError, PermissionError):
            pass

    # Include package.json for Node.js
    pkg_json = source_dir / "package.json"
    if pkg_json.exists():
        try:
            m.update(pkg_json.read_bytes())
        except (OSError, PermissionError):
            pass

    return m.hexdigest()[:16]


def check_cache(cache_dir: Path, cache_key: str) -> Optional[Path]:
    """
    Check if cached build exists.

    Args:
        cache_dir: Directory containing cache
        cache_key: Cache key to check

    Returns:
        Path to cached exe or None
    """
    if not cache_dir.exists():
        return None

    cached_exe = cache_dir / f"{cache_key}.exe"
    if cached_exe.exists():
        age_days = (time.time() - cached_exe.stat().st_mtime) / 86400
        if age_days < 7:  # Cache valid for 7 days
            return cached_exe
    return None


def save_to_cache(cache_dir: Path, cache_key: str, exe_path: Path) -> None:
    """
    Save build result to cache.

    Args:
        cache_dir: Cache directory
        cache_key: Cache key
        exe_path: Compiled executable
    """
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_exe = cache_dir / f"{cache_key}.exe"
        shutil.copy2(exe_path, cached_exe)
        logger.info(f"[Cache] Saved to cache: {cache_key}")
    except Exception as e:
        logger.warning(f"[Cache] Failed to save cache: {e}")


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


async def register_binary_hash(
    project_id: str,
    exe_path: Path,
    db_pool = None
) -> bool:
    """
    Register binary hash in the database for integrity checking.

    Args:
        project_id: Project ID
        exe_path: Path to compiled executable
        db_pool: Database connection pool

    Returns:
        True if registration successful
    """
    try:
        if not exe_path.exists():
            logger.warning(f"[BinaryHash] Executable not found: {exe_path}")
            return False

        binary_hash = calculate_file_hash(exe_path)
        binary_size = exe_path.stat().st_size

        # If no database pool provided, log only
        if db_pool is None:
            logger.info(f"[BinaryHash] Hash: {binary_hash[:16]}... Size: {binary_size} bytes")
            return True

        # Register with database
        import asyncpg
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO binary_hashes (project_id, binary_hash, binary_size, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (project_id, binary_hash) DO NOTHING
                """,
                project_id,
                binary_hash,
                binary_size
            )
            logger.info(f"[BinaryHash] Registered hash for project {project_id}: {binary_hash[:16]}...")
            return True

    except Exception as e:
        logger.warning(f"[BinaryHash] Failed to register hash: {e}")
        return False


class BuildError(Exception):
    """
    Build-specific error with type and retry information.

    Attributes:
        message: Error message
        error_type: Type of error (e.g., "resource_error", "compile_error")
        retryable: Whether the build can be retried
    """

    def __init__(
        self, message: str, error_type: str = "general", retryable: bool = False
    ):
        self.message = message
        self.error_type = error_type
        self.retryable = retryable
        super().__init__(message)


class TempBuildDir:
    """
    Context manager for temporary build directories.

    Guarantees cleanup even if errors occur.
    """

    def __init__(self, prefix: str = "cv_build_"):
        self.prefix = prefix
        self.temp_dir: Optional[Path] = None

    def __enter__(self) -> Path:
        self.temp_dir = Path(tempfile.mkdtemp(prefix=self.prefix))
        return self.temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {self.temp_dir}: {e}")


@dataclass
class BuildConfig:
    """Configuration for a build job"""

    # Project info
    project_id: str = ""  # Database project ID for hash registration
    project_name: str = "App"
    project_version: str = "1.0.0"
    publisher: str = "Unknown Publisher"

    # Source
    source_dir: Optional[Path] = None
    entry_file: str = ""
    language: Literal["python", "nodejs"] = "python"

    # License
    license_key: str = "GENERIC_BUILD"
    api_url: str = ""
    license_mode: Literal["fixed", "generic", "demo"] = "generic"

    # Output
    output_dir: Optional[Path] = None

    # Build options
    skip_obfuscation: bool = True
    pkg_target: str = "node18-win-x64"

    # Additional files to include
    include_files: list = field(default_factory=list)
    
    # Database
    db_pool = None  # Database connection pool for hash registration


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
        1. Check build cache
        2. Check disk space
        3. Compile with Nuitka to standalone exe
        4. Save to cache
        """
        await self.log(
            f"🐍 Building Python project: {config.project_name}", log_callback
        )

        # Check cache first
        cache_key = get_build_cache_key(config.source_dir, config)
        cache_dir = Path.home() / ".codevault" / "cache"
        cached = check_cache(cache_dir, cache_key)
        if cached:
            await self.log(f"📦 Using cached build: {cache_key}", log_callback)
            return cached

        # Check disk space (2GB minimum)
        check_disk_space(config.output_dir or Path("."), 2.0)

        # Use context manager for guaranteed cleanup
        with TempBuildDir(prefix="cv_python_build_") as temp_dir:
            # Step 1: Compile with Nuitka
            await self.log("Compiling with Nuitka...", log_callback)

            # Build the project
            exe_path = await self._compile_python(config, temp_dir, log_callback)

            if not exe_path or not exe_path.exists():
                raise BuildError(
                    "Python compilation failed - no executable produced",
                    "compile_error",
                    retryable=True,
                )

            await self.log(f"✓ Compilation complete: {exe_path.name}", log_callback)

            # Copy exe to output
            final_path = config.output_dir / exe_path.name
            config.output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(exe_path, final_path)
            await self.log(f"✅ Portable exe ready: {final_path}", log_callback)

            # Save to cache for future builds
            save_to_cache(cache_dir, cache_key, final_path)
            
            # Register binary hash for integrity checking (SEC2)
            if config.project_id:
                await register_binary_hash(
                    project_id=config.project_id,
                    exe_path=final_path,
                    db_pool=config.db_pool
                )

            return final_path

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
        1. Check build cache
        2. Check disk space
        3. Compile with yao-pkg to standalone exe
        4. Save to cache
        """
        await self.log(
            f"📦 Building Node.js project: {config.project_name}", log_callback
        )

        # Check cache first
        cache_key = get_build_cache_key(config.source_dir, config)
        cache_dir = Path.home() / ".codevault" / "cache"
        cached = check_cache(cache_dir, cache_key)
        if cached:
            await self.log(f"📦 Using cached build: {cache_key}", log_callback)
            return cached

        # Check disk space (1GB minimum for Node.js)
        check_disk_space(config.output_dir or Path("."), 1.0)

        # Import nodejs_compiler
        from .nodejs_compiler import NodeJSCompiler

        # Get server node_modules path
        server_dir = Path(__file__).parent.parent
        node_modules = server_dir / "node_modules"

        compiler = NodeJSCompiler(node_modules)

        # Use context manager for guaranteed cleanup
        with TempBuildDir(prefix="cv_nodejs_build_") as temp_dir:
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
                raise BuildError(
                    "Node.js compilation failed - no executable produced",
                    "compile_error",
                    retryable=True,
                )

            await self.log(f"✓ Compilation complete: {exe_path.name}", log_callback)

            # Copy exe to output
            final_path = config.output_dir / exe_path.name
            config.output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(exe_path, final_path)
            await self.log(f"✅ Portable exe ready: {final_path}", log_callback)

            # Save to cache for future builds
            save_to_cache(cache_dir, cache_key, final_path)
            
            # Register binary hash for integrity checking (SEC2)
            if config.project_id:
                await register_binary_hash(
                    project_id=config.project_id,
                    exe_path=final_path,
                    db_pool=config.db_pool
                )

            return final_path

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

    async def build_parallel(
        self, configs: list[BuildConfig], log_callback: Optional[Callable] = None
    ) -> list[Path]:
        """
        Build multiple projects in parallel with concurrency limiting.

        Args:
            configs: List of build configurations
            log_callback: Optional async callback for progress

        Returns:
            List of paths to compiled executables

        Note:
            Maximum 2 concurrent builds to prevent resource exhaustion
        """
        import asyncio

        semaphore = asyncio.Semaphore(2)  # Max 2 concurrent builds

        async def build_with_limit(config: BuildConfig) -> Path:
            async with semaphore:
                await self.log(
                    f"🚀 Starting parallel build: {config.project_name}", log_callback
                )
                return await self.build(config, log_callback)

        return await asyncio.gather(*[build_with_limit(c) for c in configs])


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
