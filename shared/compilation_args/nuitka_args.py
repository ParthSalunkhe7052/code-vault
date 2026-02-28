import sys
import os
from pathlib import Path
from typing import Dict, Any, List

def get_nuitka_args(config: Dict[str, Any], project_dir: Path, entry_path: Path, output_name: str) -> List[str]:
    """
    Generate Nuitka compilation arguments based on config.
    Stateless function to ensure local and cloud builds use identical args.
    """
    fast_build = config.get("fast_build", False)
    nuitka_opts = config.get("nuitka_options", {})
    turbo_mode = config.get("turbo_mode", True)
    
    cpu_count = os.cpu_count() or 4
    max_jobs = min(cpu_count, 8)
    if config.get("jobs"):
        max_jobs = min(config.get("jobs"), 16)

    # Base Nuitka options
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--lto=no",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--enable-plugin=tk-inter",
        "--no-prefer-source-code",
        "--python-flag=no_site",
        f"--jobs={max_jobs}",
    ]
    
    # Common blacklists to speed up builds
    base_blacklist = [
        "pytest", "unittest", "sphinx", "setuptools"
    ]
    for mod in base_blacklist:
        cmd.append(f"--nofollow-import-to={mod}")

    # Turbo mode blacklists heavy data science libraries if requested
    if turbo_mode:
        turbo_blacklist = [
            "numpy", "pandas", "PIL", "matplotlib", "scipy", "sklearn", "torch", "tensorflow"
        ]
        for mod in turbo_blacklist:
            cmd.append(f"--nofollow-import-to={mod}")

    platform_target = config.get("platform")
    if platform_target:
        if platform_target == "linux":
            cmd.append("--target=linux")
        elif platform_target == "macos":
            cmd.append("--target=macos")

    if fast_build:
        cmd.extend([f"--output-dir={project_dir / 'build'}"])
    else:
        cmd.extend([
            "--onefile",
            f"--output-filename={output_name}.exe"
        ])
        # Disable console mode for onefile (usually preferred for desktop apps)
        if config.get("disable_console", False):
            cmd.append("--windows-console-mode=disable")

    from shared.security.validation import validate_include_package
    for pkg in nuitka_opts.get("include_packages", []):
        try:
            module_name = validate_include_package(pkg)
            if module_name:
                cmd.append(f"--include-package={module_name}")
        except Exception:
            pass

    cmd.append(str(entry_path))
    return cmd
