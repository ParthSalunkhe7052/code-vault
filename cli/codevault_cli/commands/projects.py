"""
Project management commands for CodeVault CLI.
"""

import typer
from typing import Optional, Tuple
from datetime import datetime
from pathlib import Path
from rich.table import Table
from rich.panel import Panel
from rich import box

from codevault_cli.console import (
    get_console,
    print_error,
    print_info,
    print_header,
)
from codevault_cli.interactive import (
    select_project,
    select_build_mode,
    confirm_action,
)
from codevault_cli.build_dashboard import (
    BuildDashboard,
    show_build_summary,
)
from codevault_cli.simple_build_runner import (
    run_local_build_simple,
    run_remote_build_simple,
)

app = typer.Typer(
    name="project",
    help="Project management and building",
    rich_markup_mode="rich",
)

console = get_console()


@app.command()
def list() -> None:
    """
    List all your projects.

    [bold]Example:[/bold]

    $ codevault project list
    """
    try:
        import sys

        sys.path.insert(0, "..")
        from cli_config import get_api_base, get_headers
        import requests
    except ImportError as e:
        print_error(f"Failed to load modules: {e}")
        raise typer.Exit(1)

    headers = get_headers()
    if not headers:
        print_error("Not logged in. Run 'codevault auth login' first.")
        raise typer.Exit(1)

    api_url = get_api_base()

    with console.status("[bold blue]Fetching projects..."):
        try:
            resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            print_error(f"Connection error: {e}")
            raise typer.Exit(1)

    if resp.status_code != 200:
        print_error(f"Failed to fetch projects: HTTP {resp.status_code}")
        raise typer.Exit(1)

    projects = resp.json()

    if not projects:
        console.print(
            Panel(
                "[yellow]No projects found.[/yellow]\n\n"
                "Create a project on the web dashboard first.",
                title="Projects",
                border_style="yellow",
            )
        )
        return

    # Create projects table
    table = Table(
        title=f"Your Projects ({len(projects)} total)",
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
    )

    table.add_column("#", style="dim", justify="right", width=3)
    table.add_column("Name", style="cyan", min_width=20)
    table.add_column("ID", style="dim", min_width=15)
    table.add_column("Type", style="green", width=15)
    table.add_column("Upload Status", style="yellow", width=15)

    for i, p in enumerate(projects, 1):
        settings = p.get("settings", {})
        if isinstance(settings, str):
            import json

            try:
                settings = json.loads(settings) if settings else {}
            except:
                settings = {}

        is_multi = settings.get("is_multi_folder", False)
        project_type = "[DIR] Multi-folder" if is_multi else "[FILE] Single file"

        # Phase 7: Check upload status
        has_uploads = p.get("has_uploads", False)
        last_upload = p.get("last_upload_at")
        if has_uploads and last_upload:
            try:
                from datetime import datetime

                upload_dt = datetime.fromisoformat(last_upload.replace("Z", "+00:00"))
                hours_ago = int(
                    (datetime.now(upload_dt.tzinfo) - upload_dt).total_seconds() / 3600
                )
                if hours_ago < 1:
                    upload_status = "✓ Ready (<1h ago)"
                elif hours_ago < 24:
                    upload_status = f"✓ Ready ({hours_ago}h ago)"
                else:
                    days_ago = hours_ago // 24
                    upload_status = f"✓ Ready ({days_ago}d ago)"
            except:
                upload_status = "✓ Ready"
        elif has_uploads:
            upload_status = "✓ Ready"
        else:
            upload_status = "⚠ Empty"

        table.add_row(
            str(i),
            p.get("name", "Unknown"),
            p.get("id", "N/A")[:12] + "...",
            project_type,
            upload_status,
        )

    console.print(table)
    console.print()
    print_info("Tip: Run 'codevault project build <ID>' to compile a project")


@app.command()
def build(
    project_id: Optional[str] = typer.Argument(
        None,
        help="Project ID or path to entry file",
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        "-f",
        help="Fast build mode (3-4x faster, directory output)",
    ),
    license_key: Optional[str] = typer.Option(
        None,
        "--license",
        "-l",
        help="License key to embed",
    ),
    jobs: Optional[int] = typer.Option(
        None,
        "--jobs",
        "-j",
        help="Number of CPU cores to use (default: auto)",
    ),
    obfuscate: bool = typer.Option(
        False,
        "--obfuscate",
        help="Enable code obfuscation",
    ),
    lease: bool = typer.Option(
        False,
        "--lease",
        help="Enable offline lease (24h cached validation)",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode with prompts",
    ),
    dashboard: bool = typer.Option(
        True,
        "--dashboard/--no-dashboard",
        help="Show live build dashboard",
    ),
    demo: bool = typer.Option(
        False,
        "--demo",
        help="Build in demo mode (time-limited trial)",
    ),
    demo_duration: Optional[int] = typer.Option(
        None,
        "--demo-duration",
        help="Demo duration in minutes (default: 60)",
    ),
    open_build: bool = typer.Option(
        False,
        "--open",
        help="Build without license protection (open build)",
    ),
    platform: Optional[str] = typer.Option(
        None,
        "--platform",
        help="Target platform (windows, linux, macos)",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Non-interactive mode: skip all prompts and use defaults",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        help="Force language selection (python, nodejs)",
    ),
    simple: bool = typer.Option(
        True,  # Default to simple mode
        "--simple/--rich",
        help="Use simple text output (default) or Rich dashboard",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show verbose output",
    ),
) -> None:
    """
    Build a project locally.

    [bold]Examples:[/bold]

    # Interactive build with prompts
    $ codevault project build --interactive

    # Build with default settings
    $ codevault project build my-project-id

    # Fast build for testing
    $ codevault project build my-project-id --fast

    # Build with specific license
    $ codevault project build my-project-id --license KEY-123
    """
    try:
        import sys

        sys.path.insert(0, "..")
        from cli_config import get_api_base, get_headers
        import requests

        headers = get_headers()
        if not headers:
            print_error("Not logged in. Run 'codevault auth login' first.")
            raise typer.Exit(1)
        api_url = get_api_base()
    except ImportError:
        print_error("Failed to load configuration")
        raise typer.Exit(1)

    print_header("Build Project")

    # Check user's tier/plan for Node.js enforcement
    try:
        resp = requests.get(f"{api_url}/auth/me", headers=headers, timeout=10)
        if resp.status_code == 200:
            user_data = resp.json()
            user_plan = user_data.get("plan", "free")
            has_node_support = user_data.get("node_support", False)
        else:
            user_plan = "unknown"
            has_node_support = False
    except Exception:
        user_plan = "unknown"
        has_node_support = False

    # Store selected project data for local path detection
    selected_project_data = None

    # Handle open build mode (no license protection)
    if open_build:
        license_key = None

    # Handle demo mode
    if demo and not license_key:
        license_key = "DEMO"

    # Non-interactive mode skips all prompts
    if non_interactive:
        interactive = False

    # Interactive mode - let user select project and options
    if interactive or (not project_id and not non_interactive):
        console.print("[dim]Loading projects...[/dim]\n")

        # Fetch projects
        try:
            resp = requests.get(f"{api_url}/projects", headers=headers, timeout=10)
            if resp.status_code != 200:
                print_error(f"Failed to fetch projects: HTTP {resp.status_code}")
                raise typer.Exit(1)
            projects = resp.json()
        except requests.exceptions.RequestException as e:
            print_error(f"Connection error: {e}")
            raise typer.Exit(1)

        if not projects:
            print_error("No projects found. Create one on the web dashboard.")
            raise typer.Exit(1)

        # Interactive project selection
        selected_id = select_project(projects)
        if not selected_id:
            console.print("\n[yellow]Build cancelled.[/yellow]")
            raise typer.Exit(0)

        project_id = selected_id

        # Get project data for local path
        selected_project_data = next(
            (p for p in projects if p.get("id") == project_id), None
        )

        # Get project name for display
        project_name = (
            selected_project_data.get("name", "Unknown")
            if selected_project_data
            else "Unknown"
        )

        # Interactive build mode selection
        console.print()
        build_mode = select_build_mode()
        fast = build_mode == "fast"

        # Phase 2: License is now handled at runtime, not build-time
        # Default to GENERIC_BUILD mode for runtime license prompt
        if not open_build and not license_key:
            license_key = "GENERIC_BUILD"
            console.print("[dim]License will be prompted at runtime[/dim]")

        # Confirm build
        console.print()
        if not confirm_action(f"Start building '{project_name}'?", default=True):
            console.print("\n[yellow]Build cancelled.[/yellow]")
            raise typer.Exit(0)
    else:
        # Non-interactive mode
        # For local file builds, extract a cleaner project name
        if project_id and Path(project_id).exists():
            # Use the file stem (without extension) or parent folder name
            path = Path(project_id)
            project_name = path.stem or path.parent.name or "output"
        else:
            project_name = (
                project_id[:20] + "..." if len(project_id or "") > 20 else project_id
            )
        if not license_key and not open_build:
            license_key = "GENERIC_BUILD"

    # Get project language for tier enforcement (check before building)
    build_language = language
    if not build_language:
        # For local file builds, detect language from file extension
        is_local_build = Path(project_id).exists() if project_id else False
        if is_local_build:
            # Detect from file extension
            if project_id.endswith(".js"):
                build_language = "nodejs"
            elif project_id.endswith(".py"):
                build_language = "python"
            else:
                build_language = "python"  # Default
        else:
            # Remote build - get from API
            try:
                proj_resp = requests.get(
                    f"{api_url}/projects/{project_id}", headers=headers, timeout=10
                )
                if proj_resp.status_code == 200:
                    proj_data = proj_resp.json()
                    build_language = proj_data.get("language", "python")
            except Exception:
                build_language = "python"

    # Tier enforcement: Check if user can build Node.js
    # Skip tier check for local file builds
    is_local_build = Path(project_id).exists() if project_id else False
    if build_language == "nodejs" and not has_node_support and not is_local_build:
        console.print()
        print_error("Node.js builds require a Pro plan or higher.")
        console.print(f"[yellow]Your current plan: {user_plan.title()}[/yellow]")
        console.print("[dim]Visit https://codevault.dev/pricing to upgrade[/dim]")
        raise typer.Exit(1)

    # Build configuration
    config = {
        "project_id": project_id,
        "fast_build": fast,
        "license_key": license_key,
        "jobs": jobs,
        "obfuscate": obfuscate,
        "lease": lease,
        "runtime_license": not open_build,
        "demo": demo,
        "demo_duration": demo_duration or 60,
        "open_build": open_build,
        "platform": platform,
        "language": build_language,  # Use detected language, not CLI arg
    }

    # Show configuration
    if open_build:
        license_display = "[Open Build] No protection"
    elif demo:
        license_display = f"[Demo] {demo_duration or 60} min trial"
    elif license_key == "GENERIC_BUILD":
        license_display = "[Runtime Prompt]"
    else:
        license_display = license_key or "None"

    config_lines = [
        f"[bold]Project:[/bold] {project_name}",
        f"[bold]Mode:[/bold] {'[FAST] Fast (directory output)' if fast else '[STD] Standard (single .exe)'}",
        f"[bold]License:[/bold] {license_display}",
        f"[bold]CPU Cores:[/bold] {jobs or 'Auto-detect'}",
    ]
    if platform:
        config_lines.append(f"[bold]Platform:[/bold] {platform}")
    if language:
        config_lines.append(f"[bold]Language:[/bold] {language}")
    if obfuscate:
        config_lines.append("[bold]Obfuscation:[/bold] Enabled")
    if lease:
        config_lines.append("[bold]Offline Lease:[/bold] Enabled (24h)")

    console.print(
        Panel(
            "\n".join(config_lines),
            title="Build Configuration",
            border_style="cyan",
        )
    )

    console.print()

    # Start build
    start_time = datetime.now()

    try:
        if simple:
            # Use new simplified build runner (default)
            if Path(project_id).exists() or project_id.endswith((".py", ".js")):
                # Local file build
                entry_path = Path(project_id).resolve()
                success, output_path, error_message = run_local_build_simple(
                    entry_path, config, project_name
                )
            else:
                # Remote project build
                success, output_path, error_message = run_remote_build_simple(
                    project_id,
                    config,
                    headers,
                    api_url,
                    selected_project_data,
                    project_name,
                )
        else:
            # Use old Rich dashboard (for compatibility)
            if dashboard:
                with BuildDashboard(project_name, config) as dashboard:
                    success, output_path, error_message = _run_build_with_dashboard(
                        dashboard,
                        project_id,
                        config,
                        headers,
                        api_url,
                        selected_project_data,
                    )
            else:
                success, output_path, error_message = _run_build_simple(
                    project_id, config, headers, api_url, selected_project_data
                )

        duration = datetime.now() - start_time

        # Get output size if successful
        output_size = 0
        if success and output_path and output_path.exists():
            output_size = output_path.stat().st_size

        # Show summary only if not using simple mode (simple mode shows its own summary)
        if not simple:
            if success:
                show_build_summary(
                    project_name=project_name,
                    duration=duration,
                    output_path=str(output_path) if output_path else "",
                    output_size=output_size,
                    success=True,
                )
            else:
                show_build_summary(
                    project_name=project_name,
                    duration=duration,
                    output_path="",
                    output_size=0,
                    success=False,
                    error=error_message or "Build process failed",
                )
                raise typer.Exit(1)
        elif not success:
            # Simple mode already showed error, but we need to exit with error code
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Build cancelled by user.[/yellow]")
        raise typer.Exit(130)


def _run_build_with_dashboard(
    dashboard: BuildDashboard,
    project_id: str,
    config: dict,
    headers: dict,
    api_url: str,
    project_data: Optional[dict] = None,
) -> Tuple[bool, Optional[Path], str]:
    """Run build with live dashboard updates using real compiler."""
    project_name = config.get("project_name", "Build")

    # Check if it's a local file build
    if Path(project_id).exists() or project_id.endswith((".py", ".js")):
        entry_path = Path(project_id).resolve()
        return run_local_build_simple(entry_path, config, project_name)
    else:
        # Remote project build (with local file fallback)
        return run_remote_build_simple(
            project_id, config, headers, api_url, project_data, project_name
        )


def _run_build_simple(
    project_id: str,
    config: dict,
    headers: dict,
    api_url: str,
    project_data: Optional[dict] = None,
) -> Tuple[bool, Optional[Path], str]:
    """Run build with simple progress bar using real compiler."""
    project_name = config.get("project_name", "Build")

    # Check if it's a local file build
    if Path(project_id).exists() or project_id.endswith((".py", ".js")):
        entry_path = Path(project_id).resolve()
        return run_local_build_simple(entry_path, config, project_name)
    else:
        # Remote project build (with local file fallback)
        return run_remote_build_simple(
            project_id, config, headers, api_url, project_data, project_name
        )


@app.command()
def licenses(
    project_id: str = typer.Argument(..., help="Project ID"),
) -> None:
    """
    List licenses for a project.

    [bold]Example:[/bold]

    $ codevault project licenses my-project-id
    """
    try:
        import sys

        sys.path.insert(0, "..")
        from cli_config import get_api_base, get_headers
        import requests
    except ImportError as e:
        print_error(f"Failed to load modules: {e}")
        raise typer.Exit(1)

    headers = get_headers()
    if not headers:
        print_error("Not logged in. Run 'codevault auth login' first.")
        raise typer.Exit(1)

    api_url = get_api_base()

    with console.status(f"[bold blue]Fetching licenses for {project_id[:16]}..."):
        try:
            resp = requests.get(
                f"{api_url}/licenses?project_id={project_id}",
                headers=headers,
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            print_error(f"Connection error: {e}")
            raise typer.Exit(1)

    if resp.status_code != 200:
        print_error(f"Failed to fetch licenses: HTTP {resp.status_code}")
        raise typer.Exit(1)

    licenses = resp.json()

    if not licenses:
        console.print(
            Panel(
                "[yellow]No licenses found.[/yellow]\n\n"
                "Create licenses on the web dashboard.",
                title=f"Licenses for {project_id[:16]}...",
                border_style="yellow",
            )
        )
        return

    # Create licenses table
    table = Table(
        title=f"Licenses ({len(licenses)} total)",
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
    )

    table.add_column("#", style="dim", justify="right", width=3)
    table.add_column("License Key", style="cyan", min_width=20)
    table.add_column("Status", style="green", width=10)
    table.add_column("Client", style="yellow", min_width=15)
    table.add_column("Expires", style="dim", width=12)

    for i, lic in enumerate(licenses, 1):
        status = lic.get("status", "unknown")
        status_style = "green" if status == "active" else "red"

        table.add_row(
            str(i),
            lic.get("license_key", "N/A"),
            f"[{status_style}]{status}[/{status_style}]",
            lic.get("client_name", "-"),
            lic.get("expires_at", "Never")[:10] if lic.get("expires_at") else "Never",
        )

    console.print(table)
