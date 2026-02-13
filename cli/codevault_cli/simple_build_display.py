"""
Simplified build progress display for CodeVault CLI.

Provides clean, minimal progress output without excessive animations.
Uses simple text output by default, with optional Rich dashboard.
"""

import time
import sys
from typing import Optional, Dict, Any, List
from datetime import timedelta
from enum import Enum


class BuildPhase(Enum):
    """Build phases in order."""
    PREPARE = ("Prepare", "Loading configuration...")
    DOWNLOAD = ("Download", "Downloading source bundle...")
    EXTRACT = ("Extract", "Preparing source files...")
    INJECT = ("Inject", "Injecting license protection...")
    COMPILE = ("Compile", "Compiling source code...")
    PACKAGE = ("Package", "Packaging final output...")
    COMPLETE = ("Complete", "Build finished")
    ERROR = ("Error", "Build failed")
    
    def __init__(self, label: str, default_status: str):
        self.label = label
        self.default_status = default_status


class SimpleBuildDisplay:
    """
    Minimalist build progress display.
    
    Uses simple text output with minimal animations.
    Perfect for compatibility and avoiding terminal glitches.
    """
    
    def __init__(self, project_name: str, config: Dict[str, Any]):
        self.project_name = project_name
        self.config = config
        self.start_time = time.time()
        self.current_phase: Optional[BuildPhase] = None
        self.phase_progress = 0
        self.phase_status = ""
        self.completed_phases: List[BuildPhase] = []
        self.error_message: Optional[str] = None
        self._printed_header = False
        self._last_line_length = 0
        
    def _get_elapsed(self) -> str:
        """Get elapsed time as formatted string."""
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        return f"{mins:02d}:{secs:02d}"
    
    def _clear_line(self):
        """Clear current terminal line."""
        sys.stdout.write("\r" + " " * self._last_line_length + "\r")
        sys.stdout.flush()
    
    def _print(self, text: str, newline: bool = True):
        """Print text, tracking line length for clearing."""
        if not newline:
            self._last_line_length = len(text)
        try:
            sys.stdout.write(text)
        except UnicodeEncodeError:
            # Fallback for Windows cp1252 consoles that can't render Unicode
            sys.stdout.write(text.encode("ascii", errors="replace").decode("ascii"))
        if newline:
            sys.stdout.write("\n")
        sys.stdout.flush()
    
    def _print_header(self):
        """Print build header once."""
        if self._printed_header:
            return
        
        mode = "Fast" if self.config.get("fast_build") else "Standard"
        print(f"\n{'='*60}")
        print(f"CodeVault Build | {self.project_name} | {mode} Mode")
        print(f"{'='*60}\n")
        self._printed_header = True
    
    def start(self):
        """Start the display."""
        self._print_header()
        print("Starting build...\n")
    
    def update_phase(self, phase: BuildPhase, progress: int = 0, status: str = ""):
        """Update current phase and progress."""
        # If switching phases, mark previous as complete
        if self.current_phase and self.current_phase != phase:
            if self.current_phase not in self.completed_phases:
                self.completed_phases.append(self.current_phase)
        
        self.current_phase = phase
        self.phase_progress = progress
        self.phase_status = status or phase.default_status
        
        self._render()
    
    def _render(self):
        """Render current state."""
        self._print_header()
        
        # Print elapsed time
        elapsed = self._get_elapsed()
        self._print(f"Elapsed: {elapsed}")
        self._print("")
        
        # Print all phases
        for phase in BuildPhase:
            if phase == BuildPhase.COMPLETE or phase == BuildPhase.ERROR:
                continue
                
            if phase in self.completed_phases:
                # Completed phase
                self._print(f"  [{self._green('✓')}] {phase.label:12} 100%  Complete")
            elif phase == self.current_phase:
                # Current phase
                progress = self.phase_progress if self.phase_progress > 0 else 0
                status_text = (
                    f"{self.phase_status} ({progress}%)"
                    if progress > 0
                    else self.phase_status
                )
                bar = self._progress_bar(progress)
                self._print(
                    f"  [{self._yellow('>')}] {phase.label:12} {bar} {status_text}"
                )
            else:
                # Pending phase
                self._print(f"  [ ] {phase.label:12}       Waiting...")
        
        # Print error if present
        if self.error_message:
            self._print("")
            self._print(f"  {self._red('ERROR:')} {self.error_message}")
        
        # Print separator
        self._print("")
        self._print("-" * 60)
    
    def _progress_bar(self, percent: int, width: int = 20) -> str:
        """Create ASCII progress bar."""
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"{bar} {percent:3d}%"
    
    def _green(self, text: str) -> str:
        """Green text (if color supported)."""
        return f"\033[92m{text}\033[0m"
    
    def _yellow(self, text: str) -> str:
        """Yellow text (if color supported)."""
        return f"\033[93m{text}\033[0m"
    
    def _red(self, text: str) -> str:
        """Red text (if color supported)."""
        return f"\033[91m{text}\033[0m"
    
    def set_error(self, error: str):
        """Set error message."""
        self.error_message = error
        self._render()
    
    def complete(self, success: bool, output_path: Optional[str] = None, 
                 output_size: int = 0, duration: Optional[timedelta] = None):
        """Mark build as complete."""
        if success:
            self._print("")
            self._print(f"  {self._green('✓ BUILD SUCCESSFUL')}")
            if output_path:
                size_str = self._format_size(output_size)
                self._print(f"  Output: {output_path}")
                self._print(f"  Size: {size_str}")
            if duration:
                self._print(f"  Duration: {duration}")
        else:
            self._print("")
            self._print(f"  {self._red('✗ BUILD FAILED')}")
            if self.error_message:
                self._print(f"  Error: {self.error_message}")
        
        self._print(f"\n{'='*60}\n")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human readable."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def log(self, message: str):
        """Log a message without disrupting display."""
        # In simple mode, just print inline
        self._print(f"    → {message}")


class RichBuildDisplay:
    """
    Rich-based build display with minimal animations.
    
    Uses Rich library for slightly nicer output but keeps it simple.
    """
    
    def __init__(self, project_name: str, config: Dict[str, Any]):
        self.project_name = project_name
        self.config = config
        self.start_time = time.time()
        self.current_phase: Optional[BuildPhase] = None
        self.phase_progress = 0
        self.phase_status = ""
        self.completed_phases: List[BuildPhase] = []
        self.error_message: Optional[str] = None
        self.console = None
        
        # Import rich components
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.progress import Progress, BarColumn, TextColumn
            self._rich_available = True
            self.console = Console()
        except ImportError:
            self._rich_available = False
    
    def _get_elapsed(self) -> str:
        """Get elapsed time as formatted string."""
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        return f"{mins:02d}:{secs:02d}"
    
    def start(self):
        """Start the display."""
        mode = "Fast" if self.config.get("fast_build") else "Standard"
        
        if not self._rich_available or self.console is None:
            print("\nCodeVault Build")
            print(f"Project: {self.project_name}")
            print(f"Mode: {mode}\n")
            return
        
        self.console.print(
            f"\n[bold cyan]CodeVault Build[/bold cyan] | {self.project_name} | {mode} Mode\n"
        )
    
    def update_phase(self, phase: BuildPhase, progress: int = 0, status: str = ""):
        """Update current phase and progress."""
        if self.current_phase and self.current_phase != phase:
            if self.current_phase not in self.completed_phases:
                self.completed_phases.append(self.current_phase)
        
        self.current_phase = phase
        self.phase_progress = progress
        self.phase_status = status or phase.default_status
        
        self._render()
    
    def _render(self):
        """Render current state using Rich."""
        if not self._rich_available or self.console is None:
            # Fallback to simple output
            phase_name = self.current_phase.label if self.current_phase else "Unknown"
            print(f"[{self._get_elapsed()}] {phase_name}: {self.phase_status}")
            return
        
        # Create table
        from rich.table import Table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Status", width=3)
        table.add_column("Phase", width=12)
        table.add_column("Progress", width=25)
        table.add_column("Status", min_width=30)
        
        for phase in BuildPhase:
            if phase == BuildPhase.COMPLETE or phase == BuildPhase.ERROR:
                continue
            
            if phase in self.completed_phases:
                table.add_row(
                    "[green]✓[/green]", phase.label, "[green]Complete[/green]", ""
                )
            elif phase == self.current_phase:
                bar = "█" * int(20 * self.phase_progress / 100) + "░" * (
                    20 - int(20 * self.phase_progress / 100)
                )
                table.add_row(
                    "[yellow]›[/yellow]",
                    f"[bold]{phase.label}[/bold]",
                    f"{bar} {self.phase_progress}%",
                    self.phase_status,
                )
            else:
                table.add_row(
                    "[dim]○[/dim]",
                    f"[dim]{phase.label}[/dim]",
                    "",
                    "[dim]Waiting...[/dim]",
                )
        
        # Clear and redraw (simple approach)
        self.console.print(f"\n[dim]Elapsed: {self._get_elapsed()}[/dim]\n")
        self.console.print(table)
        
        if self.error_message:
            self.console.print(f"\n[red]Error: {self.error_message}[/red]")
        
        self.console.print("\n[cyan]Press Ctrl+C to cancel[/cyan]")
    
    def set_error(self, error: str):
        """Set error message."""
        self.error_message = error
        if self._rich_available and self.console is not None:
            self.console.print(f"\n[red bold]Error: {error}[/red bold]\n")
        else:
            print(f"\nError: {error}\n")
    
    def complete(self, success: bool, output_path: Optional[str] = None,
                 output_size: int = 0, duration: Optional[timedelta] = None):
        """Mark build as complete."""
        if not self._rich_available or self.console is None:
            if success:
                print(f"\n✓ Build successful: {output_path}")
            else:
                print(f"\n✗ Build failed: {self.error_message}")
            return
        
        from rich.panel import Panel
        
        if success:
            size_str = self._format_size(output_size) if output_size > 0 else "Unknown"
            dur_str = str(duration).split(".")[0] if duration else self._get_elapsed()
            
            content = f"""
[bold green]✓ Build completed successfully![/bold green]

Project: {self.project_name}
Output: {output_path}
Size: {size_str}
Duration: {dur_str}
            """
            self.console.print(Panel(content, border_style="green", title="Build Complete"))
        else:
            content = f"""
[bold red]✗ Build failed[/bold red]

Project: {self.project_name}
Error: {self.error_message or "Unknown error"}
            """
            self.console.print(Panel(content, border_style="red", title="Build Failed"))
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human readable."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def log(self, message: str):
        """Log a message."""
        if self._rich_available and self.console is not None:
            self.console.print(f"  [dim]→ {message}[/dim]")
        else:
            print(f"  → {message}")


def create_display(project_name: str, config: Dict[str, Any], use_rich: bool = False):
    """
    Factory function to create appropriate display.
    
    Args:
        project_name: Name of the project being built
        config: Build configuration
        use_rich: Whether to use Rich display (default: simple)
    
    Returns:
        SimpleBuildDisplay or RichBuildDisplay instance
    """
    if use_rich:
        return RichBuildDisplay(project_name, config)
    return SimpleBuildDisplay(project_name, config)
