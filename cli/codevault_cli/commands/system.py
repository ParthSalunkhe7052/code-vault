"""
System and status commands for CodeVault CLI.
"""

import sys
import asyncio
import typer
from typing import Optional
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.tree import Tree

from codevault_cli.console import (
    get_console,
    print_info,
    print_header,
    print_success,
    print_error,
)
from codevault_cli.utils.health import check_nuitka, check_node, check_auth
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
    """
    print_header("System Status")

    async def run_checks():
        return await asyncio.gather(check_auth(), check_nuitka(), check_node())

    auth_res, nuitka_res, node_res = asyncio.run(run_checks())

    # Auth Panel
    if auth_res[0]:
        auth_panel = Panel(
            f"[green][OK][/green] {auth_res[1]}",
            title="Authentication",
            border_style="green",
        )
    else:
        auth_panel = Panel(
            f"[red][ERROR][/red] {auth_res[1]}",
            title="Authentication",
            border_style="red",
        )
    console.print(auth_panel)
    console.print()

    # Dependencies Table
    deps_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    deps_table.add_column("Dependency", style="cyan")
    deps_table.add_column("Status", justify="center")
    deps_table.add_column("Version/Note", style="dim")

    # Nuitka row
    n_status = (
        "[green][OK][/green]"
        if nuitka_res[0] and not nuitka_res[2]
        else "[yellow][!][/yellow]"
        if nuitka_res[0]
        else "[red][ERROR][/red]"
    )
    deps_table.add_row("Nuitka", n_status, nuitka_res[2] or nuitka_res[1])

    # Node row
    node_status = (
        "[green][OK][/green]"
        if node_res[0] and not node_res[2]
        else "[yellow][!][/yellow]"
        if node_res[0]
        else "[dim]Optional[/dim]"
    )
    deps_table.add_row("Node.js", node_status, node_res[2] or node_res[1])

    deps_table.add_row("Python", "[green][OK][/green]", sys.version.split()[0])

    console.print(deps_table)
    console.print()

    # System info
    sys_panel = Panel(
        f"[dim]CLI Version:[/dim] {__version__}\n[dim]Python:[/dim] {sys.version.split()[0]}\n[dim]Platform:[/dim] {sys.platform}",
        title="System Information",
        border_style="cyan",
    )
    console.print(sys_panel)


@app.command()
def check() -> None:
    """
    Run comprehensive system diagnostics.
    """
    print_header("System Diagnostics")

    async def run_checks():
        return await asyncio.gather(check_nuitka(), check_node(), check_auth())

    n_res, node_res, auth_res = asyncio.run(run_checks())

    tree = Tree("[bold]System Check Results[/bold]")

    # Python
    py_node = tree.add("[PYTHON] Python Environment")
    py_node.add(f"[green][OK][/green] Version: {sys.version.split()[0]}")

    # Nuitka
    n_node = tree.add("[BUILD] Python Compiler (Nuitka)")
    if n_res[0]:
        n_node.add(f"[green][OK][/green] Version: {n_res[1]}")
        if n_res[2]:
            n_node.add(f"[yellow][!][/yellow] {n_res[2]}")
        else:
            n_node.add("[green][OK][/green] C++ Compiler detected")
    else:
        n_node.add(f"[red][ERROR][/red] {n_res[2]}")

    # Node
    node_node = tree.add("[BUILD] Node.js Environment")
    if node_res[0]:
        node_node.add(f"[green][OK][/green] Version: {node_res[1]}")
        if node_res[2]:
            node_node.add(f"[yellow][!][/yellow] {node_res[2]}")
    else:
        node_node.add(f"[dim][!][/dim] {node_res[2]}")

    # Auth
    a_node = tree.add("[CONFIG] Authentication")
    a_node.add(
        f"{'[green][OK][/green]' if auth_res[0] else '[yellow][!][/yellow]'} {auth_res[1]}"
    )

    console.print(tree)
    console.print()


@app.command()
def version() -> None:
    """Show version information."""
    console.print(
        Panel(
            f"[bold cyan]CodeVault CLI[/bold cyan]\n\nVersion: [bold]{__version__}[/bold]\nPython: {sys.version.split()[0]}\nPlatform: {sys.platform}",
            title="About",
            border_style="cyan",
        )
    )


@app.command()
def config(
    server_url: Optional[str] = typer.Option(
        None,
        "--server-url",
        "-s",
        help="Set the license server URL for compiled binaries",
    ),
    dev_mode: Optional[bool] = typer.Option(
        None,
        "--dev-mode/--prod-mode",
        help="Enable development mode (localhost server)",
    ),
    show: bool = typer.Option(
        False,
        "--show",
        help="Show current configuration",
    ),
) -> None:
    """
    View or update CLI configuration.

    [bold]Examples:[/bold]

    # Show current configuration
    $ codevault system config --show

    # Set production server URL
    $ codevault system config --server-url https://api.codevault.dev

    # Enable development mode (localhost)
    $ codevault system config --dev-mode

    # Switch to production mode
    $ codevault system config --prod-mode
    """
    try:
        sys.path.insert(0, "..")
        from cli_config import (
            load_config,
            save_config,
            get_license_server_url,
            set_license_server_url,
            get_api_base,
            DEFAULT_API_BASE,
            DEV_API_BASE,
            LICENSE_SERVER_URL,
            DEV_LICENSE_SERVER_URL,
        )
    except ImportError as e:
        print_error(f"Failed to load configuration module: {e}")
        raise typer.Exit(1)

    config_data = load_config()

    # Handle --show flag
    if show:
        current_server = config_data.get("license_server_url") or LICENSE_SERVER_URL
        current_api = config_data.get("api_url") or DEFAULT_API_BASE

        config_table = Table(
            title="Current Configuration",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED,
        )
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")

        config_table.add_row("License Server URL", current_server)
        config_table.add_row("API URL", current_api)
        config_table.add_row("Auth Email", config_data.get("email", "Not logged in"))

        console.print(config_table)
        console.print()
        print_info("Use --server-url to change the license server URL")
        return

    # Handle --server-url flag
    if server_url:
        server_url = server_url.rstrip("/")

        if not server_url.startswith(("http://", "https://")):
            print_error("Server URL must start with http:// or https://")
            raise typer.Exit(1)

        set_license_server_url(server_url)
        print_success(f"License server URL set to: {server_url}")

        config_data["api_url"] = server_url + "/api/v1"
        save_config(config_data)
        print_info("API URL also updated for CLI commands")
        return

    # Handle --dev-mode/--prod-mode
    if dev_mode is not None:
        if dev_mode:
            set_license_server_url(DEV_LICENSE_SERVER_URL)
            config_data["api_url"] = DEV_API_BASE
            save_config(config_data)
            print_success("Development mode enabled")
            console.print(f"[dim]  License Server: {DEV_LICENSE_SERVER_URL}[/dim]")
            console.print(f"[dim]  API URL: {DEV_API_BASE}[/dim]")
        else:
            set_license_server_url(LICENSE_SERVER_URL)
            config_data["api_url"] = DEFAULT_API_BASE
            save_config(config_data)
            print_success("Production mode enabled")
            console.print(f"[dim]  License Server: {LICENSE_SERVER_URL}[/dim]")
            console.print(f"[dim]  API URL: {DEFAULT_API_BASE}[/dim]")
        return

    # No flags provided - show help
    console.print(
        Panel(
            "[bold]Configuration Options[/bold]\n\n"
            "Use one of the following options:\n\n"
            "[cyan]--show[/cyan]          Show current configuration\n"
            "[cyan]--server-url URL[/cyan] Set license server URL\n"
            "[cyan]--dev-mode[/cyan]       Use localhost for development\n"
            "[cyan]--prod-mode[/cyan]      Use production server (default)\n\n"
            "[bold]Current Settings:[/bold]\n"
            f"  License Server: {config_data.get('license_server_url') or LICENSE_SERVER_URL}\n"
            f"  API URL: {config_data.get('api_url') or DEFAULT_API_BASE}",
            title="Config Help",
            border_style="cyan",
        )
    )
