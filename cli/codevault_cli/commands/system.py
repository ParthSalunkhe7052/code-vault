"""
System and status commands for CodeVault CLI.
"""

import sys
import subprocess
import typer
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.tree import Tree

from codevault_cli.console import (
    get_console,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_header,
)
from codevault_cli import __version__

app = typer.Typer(
    name="system",
    help="System information and diagnostics",
    rich_markup_mode="rich",
)

console = get_console()


@app.command()
def status() -> None:
    """
    Show system status and environment health.
    
    [bold]Example:[/bold]
    
    $ codevault system status
    """
    print_header("System Status")
    
    # Check authentication
    try:
        import sys
        sys.path.insert(0, "..")
        from cli_config import load_config, DEFAULT_API_BASE
        config = load_config()
        
        if config.get("api_key"):
            auth_panel = Panel(
                f"[green][OK] Logged in as:[/green] {config.get('email', 'Unknown')}\n"
                f"[dim]API URL:[/dim] {config.get('api_url', DEFAULT_API_BASE)}",
                title="Authentication",
                border_style="green",
            )
        else:
            auth_panel = Panel(
                "[red][ERROR] Not logged in[/red]\n"
                "Run [cyan]codevault auth login[/cyan] to authenticate",
                title="Authentication",
                border_style="red",
            )
        console.print(auth_panel)
    except ImportError:
        console.print(Panel(
            "[yellow][!] Configuration module not found[/yellow]",
            title="Authentication",
            border_style="yellow",
        ))
    
    console.print()
    
    # Check dependencies
    console.print("[bold]Checking dependencies...[/bold]\n")
    
    deps_table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
    )
    deps_table.add_column("Dependency", style="cyan")
    deps_table.add_column("Status", style="green", justify="center")
    deps_table.add_column("Version", style="dim")
    
    # Check Nuitka
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0] if result.stdout else "Unknown"
            deps_table.add_row("Nuitka", "[OK]", version)
        else:
            deps_table.add_row("Nuitka", "[red][ERROR][/red]", "Not installed")
    except Exception:
        deps_table.add_row("Nuitka", "[red][ERROR][/red]", "Not found")
    
    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            deps_table.add_row("Node.js", "[OK]", result.stdout.strip())
        else:
            deps_table.add_row("Node.js", "[yellow][!][/yellow]", "Not working")
    except Exception:
        deps_table.add_row("Node.js", "[yellow][!][/yellow]", "Not installed (optional)")
    
    # Check Python
    deps_table.add_row("Python", "[OK]", sys.version.split()[0])
    
    # Check Rich
    try:
        import rich
        deps_table.add_row("Rich", "[OK]", "installed")
    except ImportError:
        deps_table.add_row("Rich", "[red][ERROR][/red]", "Not installed (required)")
    
    console.print(deps_table)
    console.print()
    
    # System info
    sys_panel = Panel(
        f"[dim]CLI Version:[/dim] {__version__}\n"
        f"[dim]Python:[/dim] {sys.version.split()[0]}\n"
        f"[dim]Platform:[/dim] {sys.platform}",
        title="System Information",
        border_style="cyan",
    )
    console.print(sys_panel)


@app.command()
def check() -> None:
    """
    Run comprehensive system diagnostics.
    
    [bold]Example:[/bold]
    
    $ codevault system check
    """
    print_header("System Diagnostics")
    
    # Create a diagnostic tree
    tree = Tree("[bold]System Check Results[/bold]")
    
    # Python check
    python_node = tree.add("[PYTHON] Python Environment")
    python_node.add(f"[green][OK][/green] Version: {sys.version.split()[0]}")
    python_node.add(f"[green][OK][/green] Executable: {sys.executable}")
    
    # Dependencies check
    deps_node = tree.add("[DEPS] Dependencies")
    
    # Check required packages
    required = ["rich", "typer", "requests"]
    for pkg in required:
        try:
            __import__(pkg)
            deps_node.add(f"[green][OK][/green] {pkg}")
        except ImportError:
            deps_node.add(f"[red][ERROR][/red] {pkg} [dim](required)[/dim]")
    
    # Configuration check
    config_node = tree.add("[CONFIG] Configuration")
    try:
        import sys
        sys.path.insert(0, "..")
        from cli_config import load_config
        config = load_config()
        if config.get("api_key"):
            config_node.add(f"[green][OK][/green] Authenticated as {config.get('email', 'Unknown')}")
        else:
            config_node.add("[yellow][!][/yellow] Not authenticated")
    except Exception as e:
        config_node.add(f"[red][ERROR][/red] Error: {e}")
    
    console.print(tree)
    console.print()
    print_info("Run 'codevault system status' for detailed information")


@app.command()
def version() -> None:
    """
    Show version information.
    
    [bold]Example:[/bold]
    
    $ codevault system version
    """
    console.print(Panel(
        f"[bold cyan]CodeVault CLI[/bold cyan]\n\n"
        f"Version: [bold]{__version__}[/bold]\n"
        f"Python: {sys.version.split()[0]}\n"
        f"Platform: {sys.platform}\n\n"
        f"[dim]Build license-protected executables with ease[/dim]",
        title="About",
        border_style="cyan",
    ))
