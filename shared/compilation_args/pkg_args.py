import sys
from pathlib import Path
from typing import Dict, Any, List

def get_pkg_args(config: Dict[str, Any], entry_path_rel: str, output_name: str, pkg_cwd: Path) -> List[str]:
    """
    Generate pkg compilation arguments based on config.
    Stateless function to ensure local and cloud builds use identical args.
    """
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    
    compiler_opts = config.get("compiler_options", {})
    
    platform_target = config.get("platform")
    if platform_target:
        # Map platform to pkg target format
        platform_map = {"windows": "win", "linux": "linux", "macos": "macos"}
        platform_code = platform_map.get(platform_target, "win")
        target = f"node20-{platform_code}-x64"
    else:
        target = compiler_opts.get("target", "node20-win-x64")

    cmd = [
        npx_cmd,
        "-y",
        "@yao-pkg/pkg",
        str(entry_path_rel),
        "--targets",
        target,
        "--output",
        str(pkg_cwd / output_name),
        "--compress",
        "GZip",
        "--public-packages",
        "*"
    ]
    
    if config.get("debug_build"):
        cmd.append("--debug")
        
    return cmd
