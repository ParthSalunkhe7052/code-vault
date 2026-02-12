"""
Rich TUI for CodeVault CLI
Replaces basic terminal output with rich library components.
B21-B23: Rich progress bars, tables, and panels
"""

import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeElapsedColumn,
    )
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.style import Style

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Global console instance
_console: Optional[Console] = None


def get_console() -> Console:
    """Get or create the global Rich console."""
    global _console
    if _console is None:
        _console = Console()
    return _console


class Colors:
    """ANSI color codes (fallback when rich unavailable)."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def enable_colors():
    """Enable ANSI colors on Windows (no-op with rich)."""
    if not RICH_AVAILABLE and sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def color_print(msg: str, color: str = Colors.RESET):
    """Print colored message using rich or ANSI fallback."""
    if RICH_AVAILABLE:
        console = get_console()
        style_map = {
            Colors.GREEN: "green",
            Colors.YELLOW: "yellow",
            Colors.RED: "red",
            Colors.BLUE: "blue",
            Colors.CYAN: "cyan",
            Colors.MAGENTA: "magenta",
            Colors.WHITE: "white",
            Colors.BOLD: "bold",
            Colors.DIM: "dim",
        }
        style = style_map.get(color, "")
        console.print(msg, style=style)
    else:
        output = f"{color}{msg}{Colors.RESET}"
        try:
            print(output)
        except UnicodeEncodeError:
            safe_output = output.encode(
                sys.stdout.encoding or "utf-8", errors="replace"
            ).decode(sys.stdout.encoding or "utf-8", errors="replace")
            print(safe_output)


def print_header(title: str):
    """Print a styled header using rich panels."""
    if RICH_AVAILABLE:
        console = get_console()
        console.print(Panel(title, style="cyan bold", border_style="cyan"))
    else:
        print(f"\n{Colors.CYAN}{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}{Colors.RESET}\n")


def print_success(msg: str):
    """Print success message with emoji."""
    color_print(f"[OK] {msg}", Colors.GREEN)


def print_error(msg: str):
    """Print error message with emoji."""
    color_print(f"[ERROR] {msg}", Colors.RED)


def print_warning(msg: str):
    """Print warning message with emoji."""
    color_print(f"[WARN] {msg}", Colors.YELLOW)


def print_info(msg: str):
    """Print info message with emoji."""
    color_print(f"[INFO] {msg}", Colors.BLUE)


def print_progress_bar(
    percent: int, width: int = 30, phase: str = "", elapsed_time: str = ""
) -> None:
    """Print a visual progress bar using rich or fallback."""
    if RICH_AVAILABLE:
        console = get_console()
        filled = int(width * percent / 100)
        bar = "#" * filled + "-" * (width - filled)

        status_parts = []
        if phase:
            status_parts.append(f"[cyan]{phase}[/cyan]")
        if elapsed_time:
            status_parts.append(f"[dim]{elapsed_time}[/dim]")

        status_text = " | ".join(status_parts)
        console.print(
            f"\r[cyan][{bar}][/cyan] [bold]{percent:3d}%[/bold] {status_text}", end=""
        )
    else:
        enable_colors()
        percent = max(0, min(100, percent))
        filled = int(width * percent / 100)
        bar = "#" * filled + "-" * (width - filled)

        status_parts = []
        if phase:
            status_parts.append(phase)
        if elapsed_time:
            status_parts.append(elapsed_time)

        status_text = " | ".join(status_parts) if status_parts else ""
        status_display = f" [{status_text}]" if status_text else ""

        output = f"\r{Colors.CYAN}[{bar}]{Colors.RESET} {percent:3d}%{status_display}  "

        try:
            print(output, end="", flush=True)
        except UnicodeEncodeError:
            filled_char = "#" * filled + "-" * (width - filled)
            print(
                f"\r[{filled_char}] {percent:3d}%{status_display}  ", end="", flush=True
            )


class BuildProgress:
    """Rich progress bar for build operations."""

    def __init__(self, description: str = "Building..."):
        self.description = description
        self.progress: Optional[Progress] = None
        self.task_id = None

    def __enter__(self):
        if RICH_AVAILABLE:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=get_console(),
                transient=False,
            )
            self.progress.start()
            self.task_id = self.progress.add_task(self.description, total=100)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()

    def update(self, percent: int, description: Optional[str] = None):
        """Update progress percentage."""
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, completed=percent)
            if description:
                self.progress.update(self.task_id, description=description)


def print_build_summary(build_info: dict):
    """Print a rich table with build summary."""
    if RICH_AVAILABLE:
        console = get_console()
        table = Table(
            title="Build Summary", show_header=True, header_style="bold magenta"
        )
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        for key, value in build_info.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        console.print(table)
    else:
        print("\n" + "=" * 60)
        print("BUILD SUMMARY")
        print("=" * 60)
        for key, value in build_info.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        print("=" * 60)


def print_welcome_banner():
    """Print welcome banner with rich styling."""
    if RICH_AVAILABLE:
        console = get_console()
        banner = Panel(
            Text("CodeVault CLI", style="bold cyan")
            + Text("\nBuild license-protected executables", style="dim"),
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(banner)
        console.print()

        # Quick start table
        table = Table(show_header=False, box=None)
        table.add_column("Command", style="bold green")
        table.add_column("Description", style="white")

        table.add_row("login", "Log in to your CodeVault account")
        table.add_row("build", "Build a project into an executable")
        table.add_row("projects", "List your projects")
        table.add_row("status", "Check login status and environment")

        console.print(table)
    else:
        print(f"""
{Colors.CYAN}+------------------------------------------------------------+
|  {Colors.BOLD}CodeVault CLI{Colors.CYAN} - Build license-protected executables    |
+------------------------------------------------------------+{Colors.RESET}

{Colors.GREEN}>> Quick Start:{Colors.RESET}
  1. python lw_compiler.py login      {Colors.DIM}<- Login first{Colors.RESET}
  2. python lw_compiler.py build      {Colors.DIM}<- Interactive build{Colors.RESET}
""")


# Compatibility: keep old function names
print_banner = print_welcome_banner
