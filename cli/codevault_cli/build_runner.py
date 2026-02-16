"""
Build runner that integrates existing compiler logic with the new CLI dashboard.
"""

import sys
import os
import asyncio
import time
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, Callable
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from cli.compilers.python import PythonCompiler
from cli.compilers.node import NodeJSCompiler
from codevault_cli.console import get_console, print_error, print_header

console = get_console()

class BuildRunner:
    """
    Runs builds with real-time Rich progress updates.
    """

    def __init__(self, project_name: str, config: Dict[str, Any]):
        self.project_name = project_name
        self.config = config
        self.lang = config.get("language", "python")
        self.compiler = (PythonCompiler(Path.cwd(), config) if self.lang == "python" 
                         else NodeJSCompiler(Path.cwd(), config))

    async def run_build(self) -> Tuple[bool, Optional[Path], str]:
        """Run the full build lifecycle with Rich Progress."""
        print_header(f"Building {self.project_name}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            # Phase 1: Pre-flight
            task_pre = progress.add_task("[cyan]Pre-flight checks...", total=100)
            if not await self.compiler.pre_flight():
                return False, None, "Environment pre-flight checks failed. Run 'codevault system check'."
            progress.update(task_pre, completed=100)

            # Phase 2: Inject Wrapper
            task_inj = progress.add_task("[magenta]Injecting protection...", total=100)
            if not await self.compiler.inject_wrapper():
                return False, None, "License wrapper injection failed."
            progress.update(task_inj, completed=100)

            # Phase 3: Compile
            task_comp = progress.add_task(f"[green]Compiling ({self.lang})...", total=100)
            
            def progress_callback(percent, status):
                progress.update(task_comp, completed=percent, description=f"[green]{status}... ({percent}%)")

            success, build_dir = await self.compiler.compile(progress_callback=progress_callback)
            
            if not success:
                return False, None, "Compilation failed. Check output for details."
            progress.update(task_comp, completed=100, description="[green]Compilation complete!")

            # Phase 4: Packaging
            task_pkg = progress.add_task("[yellow]Packaging...", total=100)
            # Find output exe
            output_name = self.config.get("output_name") or "output"
            exe_path = Path.cwd() / f"{output_name}.exe"
            
            if exe_path.exists():
                progress.update(task_pkg, completed=100)
                return True, exe_path, ""
            else:
                return False, None, "Could not find output executable."

async def run_local_build(entry_path: Path, config: Dict[str, Any], dashboard=None) -> Tuple[bool, Optional[Path], str]:
    """Entry point for local builds."""
    runner = BuildRunner(config.get("project_name", entry_path.name), {**config, "entry_file": str(entry_path)})
    return await runner.run_build()
