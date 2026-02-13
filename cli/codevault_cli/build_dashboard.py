"""
Live build dashboard for CodeVault CLI.

Provides real-time build monitoring with Rich components.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.console import Group
from rich.text import Text

from codevault_cli.console import get_console

console = get_console()


class BuildDashboard:
    """
    Live build dashboard for monitoring compilation progress.
    """
    
    def __init__(self, project_name: str, config: Dict[str, Any]):
        self.project_name = project_name
        self.config = config
        self.start_time = datetime.now()
        self.current_phase = "Initializing"
        self.phases_completed = []
        self.phases_pending = [
            "Fetch configuration",
            "Download source",
            "Extract files",
            "Inject license",
            "Compile",
            "Package output"
        ]
        self.overall_progress = 0
        self.phase_progress = 0
        self.status_message = "Starting build..."
        self.error_message = None
        
    def _make_header(self) -> Panel:
        """Create header panel."""
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        
        content = f"[bold]Project:[/bold] {self.project_name}\n"
        content += f"[bold]Mode:[/bold] {'Fast' if self.config.get('fast_build') else 'Standard'}\n"
        content += f"[bold]Elapsed:[/bold] {elapsed_str}"
        
        return Panel(
            content,
            title="[bold cyan]CodeVault Build[/bold cyan]",
            border_style="cyan"
        )
    
    def _make_progress_section(self) -> Panel:
        """Create progress section."""
        # Overall progress bar
        overall_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Overall"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        )
        overall_task = overall_progress.add_task("Build", total=100)
        overall_progress.update(overall_task, completed=self.overall_progress)
        
        # Current phase progress
        phase_progress = Progress(
            SpinnerColumn(),
            TextColumn(f"[bold]{self.current_phase}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=console,
        )
        phase_task = phase_progress.add_task(self.current_phase, total=100)
        phase_progress.update(phase_task, completed=self.phase_progress)
        
        content = Group(overall_progress, Text(), phase_progress)
        
        return Panel(
            content,
            title="[bold]Progress[/bold]",
            border_style="blue"
        )
    
    def _make_phases_section(self) -> Panel:
        """Create phases list."""
        lines = []
        
        # Completed phases
        for phase in self.phases_completed:
            lines.append(f"[green][OK][/green] {phase}")
        
        # Current phase
        if self.current_phase:
            lines.append(f"[yellow][>][/yellow] [bold]{self.current_phase}[/bold]")
        
        # Pending phases
        for phase in self.phases_pending:
            lines.append(f"[dim][ ] {phase}[/dim]")
        
        content = "\n".join(lines) if lines else "[dim]Waiting to start...[/dim]"
        
        return Panel(
            content,
            title="[bold]Phases[/bold]",
            border_style="yellow"
        )
    
    def _make_status_section(self) -> Panel:
        """Create status section."""
        if self.error_message:
            content = f"[red][ERROR] {self.error_message}[/red]"
            border_style = "red"
        else:
            content = f"[cyan]{self.status_message}[/cyan]"
            border_style = "green"
        
        return Panel(
            content,
            title="[bold]Status[/bold]",
            border_style=border_style
        )
    
    def _make_layout(self) -> Layout:
        """Create the full layout."""
        layout = Layout()
        
        # Split into sections
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="status", size=3)
        )
        
        # Main section split horizontally
        layout["main"].split_row(
            Layout(name="progress", ratio=2),
            Layout(name="phases", ratio=1)
        )
        
        # Set content
        layout["header"].update(self._make_header())
        layout["progress"].update(self._make_progress_section())
        layout["phases"].update(self._make_phases_section())
        layout["status"].update(self._make_status_section())
        
        return layout
    
    def update_phase(self, phase_name: str, progress: int = 0):
        """Update the current phase."""
        if self.current_phase and self.current_phase != phase_name:
            # Move old phase to completed
            if self.current_phase not in self.phases_completed:
                self.phases_completed.append(self.current_phase)
            # Remove from pending
            if self.current_phase in self.phases_pending:
                self.phases_pending.remove(self.current_phase)
        
        self.current_phase = phase_name
        self.phase_progress = progress
        
        # Calculate overall progress
        total_phases = len(self.phases_completed) + len(self.phases_pending) + 1
        completed_phases = len(self.phases_completed)
        current_phase_contribution = progress / 100
        self.overall_progress = int(((completed_phases + current_phase_contribution) / total_phases) * 100)
    
    def set_status(self, message: str):
        """Update status message."""
        self.status_message = message
    
    def set_error(self, error: str):
        """Set error message."""
        self.error_message = error
        self.status_message = f"Error: {error}"
    
    def __enter__(self):
        """Start the live dashboard."""
        self.live = Live(
            self._make_layout(),
            console=console,
            refresh_per_second=4,
            screen=False
        )
        self.live.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the live dashboard."""
        if hasattr(self, 'live'):
            self.live.stop()
    
    def refresh(self):
        """Refresh the display."""
        if hasattr(self, 'live'):
            self.live.update(self._make_layout())


class BuildProgressTracker:
    """
    Simple progress tracker for non-live builds.
    """
    
    def __init__(self, description: str = "Building..."):
        self.description = description
        self.progress = None
        self.task_id = None
        
    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        )
        self.progress.start()
        self.task_id = self.progress.add_task(self.description, total=100)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()
    
    def update(self, percent: int, description: Optional[str] = None):
        """Update progress."""
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, completed=percent)
            if description:
                self.progress.update(self.task_id, description=description)
    
    def advance(self, amount: int = 1):
        """Advance progress."""
        if self.progress and self.task_id is not None:
            self.progress.advance(self.task_id, amount)


def show_build_summary(
    project_name: str,
    duration: timedelta,
    output_path: str,
    output_size: int,
    success: bool = True,
    error: Optional[str] = None
):
    """
    Show build completion summary.
    
    Args:
        project_name: Name of the project
        duration: Build duration
        output_path: Path to output file
        output_size: Size in bytes
        success: Whether build succeeded
        error: Error message if failed
    """
    duration_str = str(duration).split('.')[0]  # Remove microseconds
    
    # Format file size
    if output_size < 1024:
        size_str = f"{output_size} B"
    elif output_size < 1024 * 1024:
        size_str = f"{output_size / 1024:.1f} KB"
    else:
        size_str = f"{output_size / (1024 * 1024):.1f} MB"
    
    if success:
        content = f"""
[bold green]Build completed successfully![/bold green]

[bold]Project:[/bold] {project_name}
[bold]Duration:[/bold] {duration_str}
[bold]Output:[/bold] {output_path}
[bold]Size:[/bold] {size_str}

[dim]Next steps:[/dim]
  • Test the executable: .\\{output_path.split('\\')[-1]}
  • Distribute to customers
        """
        border_style = "green"
        title = "Build Complete"
    else:
        content = f"""
[bold red]Build failed[/bold red]

[bold]Project:[/bold] {project_name}
[bold]Duration:[/bold] {duration_str}

[bold]Error:[/bold]
{error or 'Unknown error'}

[dim]Try:[/dim]
  • Run with --verbose for details
  • Check your internet connection
  • Verify project configuration
        """
        border_style = "red"
        title = "Build Failed"
    
    console.print(Panel(
        content,
        title=f"[bold]{title}[/bold]",
        border_style=border_style,
        padding=(1, 2)
    ))
