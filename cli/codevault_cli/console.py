"""
Unified console output module using Rich.

This module provides a single, consistent interface for all terminal output,
replacing the old dual terminal.py/terminal_rich.py system.
"""

import sys
from typing import Optional
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)

# CodeVault color theme
codevault_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "magenta",
    "dim": "dim",
    "bold": "bold",
})

# Global console instance
_console: Optional[Console] = None

# Symbol configuration (can be toggled for accessibility)
_symbols = {
    "success": "[OK]",
    "error": "[ERROR]",
    "warning": "[!]",
    "info": "[i]",
}


def enable_unicode_symbols():
    """Enable Unicode symbols for better visuals (may not work on all terminals)."""
    global _symbols
    _symbols = {
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "info": "ℹ",
    }


def get_console() -> Console:
    """Get or create the global Rich console."""
    global _console
    if _console is None:
        # Use safe encoding for Windows
        _console = Console(theme=codevault_theme, force_terminal=True)
    return _console


def set_console(console: Console) -> None:
    """Set a custom console (useful for testing)."""
    global _console
    _console = console


# Convenience functions for styled output
def print(msg: str, style: str = "", **kwargs) -> None:
    """Print a message to the console."""
    get_console().print(msg, style=style, **kwargs)


def print_success(msg: str, **kwargs) -> None:
    """Print a success message with checkmark."""
    get_console().print(f"{_symbols['success']} {msg}", style="success", **kwargs)


def print_error(msg: str, details: str = None, **kwargs) -> None:
    """Print an error message with X mark."""
    get_console().print(f"{_symbols['error']} {msg}", style="error", **kwargs)
    if details:
        get_console().print(f"  {details}", style="dim", **kwargs)


def print_warning(msg: str, **kwargs) -> None:
    """Print a warning message with warning symbol."""
    get_console().print(f"{_symbols['warning']} {msg}", style="warning", **kwargs)


def print_info(msg: str, **kwargs) -> None:
    """Print an info message with info symbol."""
    get_console().print(f"{_symbols['info']} {msg}", style="info", **kwargs)


def print_header(title: str) -> None:
    """Print a styled header panel."""
    panel = Panel(
        Text(title, style="bold cyan"),
        border_style="cyan",
        padding=(0, 2),
    )
    get_console().print(panel)


def print_welcome_banner() -> None:
    """Print the welcome banner."""
    banner = Panel(
        Text("CodeVault CLI", style="bold cyan") +
        Text("\nBuild license-protected executables", style="dim"),
        border_style="cyan",
        padding=(1, 4),
    )
    get_console().print(banner)
    get_console().print()


def create_progress(description: str = "Processing...") -> Progress:
    """Create a Rich Progress instance with CodeVault styling."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=get_console(),
        transient=False,
    )


def print_build_summary(build_info: dict) -> None:
    """Print a build summary table."""
    table = Table(
        title="Build Summary",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in build_info.items():
        table.add_row(key.replace("_", " ").title(), str(value))
    
    get_console().print(table)


def print_error_panel(title: str, message: str, suggestions: list = None, details: dict = None) -> None:
    """Print a rich error panel with context and suggestions."""
    content = f"[bold red]{message}[/bold red]\n"
    
    if details:
        content += "\n[dim]Context:[/dim]\n"
        for key, value in details.items():
            content += f"  • {key}: {value}\n"
    
    if suggestions:
        content += "\n[bold yellow]Suggested fixes:[/bold yellow]\n"
        for i, suggestion in enumerate(suggestions, 1):
            content += f"  {i}. {suggestion}\n"
    
    panel = Panel(
        content,
        title=f"❌ {title}",
        border_style="red",
    )
    get_console().print(panel)


def print_success_panel(title: str, message: str, details: dict = None, next_steps: list = None) -> None:
    """Print a rich success panel with details and next steps."""
    content = f"[bold green]{message}[/bold green]\n"
    
    if details:
        content += "\n"
        for key, value in details.items():
            content += f"[dim]{key}:[/dim] {value}\n"
    
    if next_steps:
        content += "\n[bold cyan]Next Steps:[/bold cyan]\n"
        for step in next_steps:
            content += f"  • {step}\n"
    
    panel = Panel(
        content,
        title=f"✅ {title}",
        border_style="green",
    )
    get_console().print(panel)


# Compatibility aliases for old code
def color_print(msg: str, style: str = "") -> None:
    """Legacy compatibility function."""
    print(msg, style=style)
