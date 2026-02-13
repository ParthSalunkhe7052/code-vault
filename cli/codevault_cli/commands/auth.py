"""
Authentication commands for CodeVault CLI.

Replaces the old commands/auth.py with modern Typer-based commands.
"""

import typer
from typing import Optional
from rich.panel import Panel
from rich.table import Table
from rich import box

# Import from parent package
from codevault_cli.console import (
    get_console,
    print_success,
    print_error,
    print_info,
    print_header,
)

app = typer.Typer(
    name="auth",
    help="Authentication and account management",
    rich_markup_mode="rich",
)

console = get_console()


@app.command()
def login(
    email: Optional[str] = typer.Option(
        None,
        "--email",
        "-e",
        help="Email address (will prompt if not provided)",
    ),
    api_url: Optional[str] = typer.Option(
        None,
        "--api-url",
        help="Custom API URL (default: https://api.codevault.dev)",
    ),
) -> None:
    """
    Authenticate with your CodeVault account.
    
    [bold]Examples:[/bold]
    
    # Interactive login
    $ codevault auth login
    
    # Login with email
    $ codevault auth login --email user@example.com
    
    # Login to custom server
    $ codevault auth login --api-url https://custom.codevault.dev
    """
    print_header("Authentication")
    
    # Import old config for compatibility during transition
    try:
        import sys
        sys.path.insert(0, "..")
        from cli_config import load_config, save_config, DEFAULT_API_BASE
    except ImportError:
        print_error("Failed to load configuration module")
        raise typer.Exit(1)
    
    config = load_config()
    
    # Use provided or default API URL
    api_url = api_url or config.get("api_url", DEFAULT_API_BASE)
    console.print(f"[dim]Server:[/dim] {api_url}\n")
    
    # Get email if not provided
    if not email:
        email = typer.prompt("Email").strip().lower()
    
    # Validate email
    if "@" not in email or "." not in email:
        print_error("Please enter a valid email address")
        raise typer.Exit(1)
    
    # Get password securely
    password = typer.prompt("Password", hide_input=True)
    
    if not password:
        print_error("Password is required")
        raise typer.Exit(1)
    
    console.print("\n[blue]Logging in...[/blue]")
    
    # Attempt login
    try:
        import requests
        resp = requests.post(
            f"{api_url}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            user = data.get("user", {})
            
            # Save config
            config["api_key"] = token
            config["api_url"] = api_url
            config["email"] = email
            config["user_name"] = user.get("name", email)
            save_config(config)
            
            # Success output
            print_success(f"Logged in as {user.get('name', email)}")
            console.print(f"[dim]   Server: {api_url}[/dim]\n")
            print_info("Next: Run 'codevault project build' to compile a project")
            
        elif resp.status_code == 401:
            print_error("Invalid email or password")
            console.print("[yellow]   Please check your credentials and try again.[/yellow]")
            raise typer.Exit(1)
        else:
            try:
                error = resp.json().get("detail", "Unknown error")
            except:
                error = resp.text or f"HTTP {resp.status_code}"
            print_error(f"Login failed: {error}")
            raise typer.Exit(1)
            
    except requests.exceptions.Timeout:
        print_error("Connection timed out")
        console.print("[yellow]   The server is taking too long to respond.[/yellow]")
        raise typer.Exit(1)
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server")
        console.print(f"[yellow]   Server: {api_url}[/yellow]")
        console.print("\n[dim]Make sure:[/dim]")
        console.print("  1. The CodeVault server is running")
        console.print("  2. Check your internet connection")
        raise typer.Exit(1)


@app.command()
def logout(
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Logout and clear saved credentials.
    
    [bold]Example:[/bold]
    
    $ codevault auth logout
    """
    if not confirm:
        confirm = typer.confirm("Are you sure you want to logout?")
    
    if confirm:
        try:
            from cli_config import clear_config
            clear_config()
            print_success("Logged out successfully")
        except ImportError:
            print_error("Failed to clear configuration")
            raise typer.Exit(1)


@app.command()
def whoami() -> None:
    """
    Show current user information.
    
    [bold]Example:[/bold]
    
    $ codevault auth whoami
    """
    try:
        import sys
        sys.path.insert(0, "..")
        from cli_config import load_config, get_api_base, get_headers
        import requests
    except ImportError as e:
        print_error(f"Failed to load configuration: {e}")
        raise typer.Exit(1)
    
    # Check if logged in
    headers = get_headers()
    if not headers:
        print_error("Not logged in. Run 'codevault auth login' first.")
        raise typer.Exit(1)
    
    config = load_config()
    api_url = config.get("api_url", get_api_base())
    
    try:
        resp = requests.get(f"{api_url}/auth/me", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            user = resp.json()
            
            # Create user info table
            table = Table(
                title="User Profile",
                show_header=False,
                box=box.ROUNDED,
            )
            table.add_column("Field", style="cyan", justify="right")
            table.add_column("Value", style="green")
            
            table.add_row("Name", user.get("name", "Unknown"))
            table.add_row("Email", user.get("email", "Unknown"))
            table.add_row("Plan", user.get("plan", "free").title())
            table.add_row("Credits", str(user.get("build_credits", 0)))
            
            role = user.get("role", "user")
            if role == "admin":
                table.add_row("Role", "[red]Admin[/red]")
            
            console.print(table)
            
        elif resp.status_code == 401:
            print_error("Authentication failed. Please login again.")
            raise typer.Exit(1)
        else:
            print_error(f"Failed to fetch user info: HTTP {resp.status_code}")
            raise typer.Exit(1)
            
    except requests.exceptions.RequestException as e:
        print_error(f"Connection error: {e}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """
    Check authentication status.
    
    [bold]Example:[/bold]
    
    $ codevault auth status
    """
    try:
        from cli_config import load_config
    except ImportError:
        print_error("Failed to load configuration module")
        raise typer.Exit(1)
    
    config = load_config()
    
    if config.get("api_key"):
        console.print(Panel(
            f"[green][OK] Logged in as:[/green] {config.get('email', 'Unknown')}\n"
            f"[dim]API URL:[/dim] {config.get('api_url', 'Default')}",
            title="Authentication Status",
            border_style="green",
        ))
    else:
        console.print(Panel(
            "[red][ERROR] Not logged in[/red]\n\n"
            "Run [cyan]codevault auth login[/cyan] to authenticate",
            title="Authentication Status",
            border_style="red",
        ))
