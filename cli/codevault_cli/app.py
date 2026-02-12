"""
Main CodeVault CLI application using Typer.

This is the new entry point that provides a modern, rich CLI experience.
"""

import typer
from rich.markdown import Markdown
from codevault_cli import __version__, __description__
from codevault_cli.console import get_console, print_welcome_banner
from codevault_cli.commands import auth, projects, system

# Create the main Typer app
app = typer.Typer(
    name="codevault",
    help=__description__,
    rich_markup_mode="rich",
    no_args_is_help=False,  # We'll handle no-args case manually
)

# Add command groups
app.add_typer(auth.app, name="auth", help="Authentication commands")
app.add_typer(projects.app, name="project", help="Project management commands")
app.add_typer(system.app, name="system", help="System and status commands")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version information",
        is_eager=True,
    ),
) -> None:
    """
    CodeVault CLI - Build license-protected executables.
    
    [bold]Quick Start:[/bold]
    
    1. [cyan]codevault auth login[/cyan] - Authenticate with your account
    2. [cyan]codevault project list[/cyan] - View your projects
    3. [cyan]codevault project build[/cyan] - Build a project
    
    [dim]Run 'codevault --help' for more information.[/dim]
    """
    if version:
        get_console().print(f"CodeVault CLI v{__version__}")
        raise typer.Exit()
    
    # If no subcommand was invoked, show help
    if ctx.invoked_subcommand is None:
        get_console().print(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def welcome() -> None:
    """Display the welcome banner."""
    print_welcome_banner()


@app.command()
def docs() -> None:
    """Open CodeVault documentation."""
    get_console().print("📚 Opening documentation at https://docs.codevault.dev")
    # In real implementation, would use webbrowser module
    import webbrowser
    webbrowser.open("https://docs.codevault.dev")


def run() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
