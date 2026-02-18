"""
Build preset management commands for CodeVault CLI.

Presets allow users to save and reuse build configurations.
"""

import json
import typer
from pathlib import Path
from typing import Optional
from rich.table import Table
from rich.panel import Panel

from codevault_cli.console import (
    get_console,
    print_error,
    print_success,
    print_info,
)

app = typer.Typer(
    name="preset",
    help="Build preset management",
    rich_markup_mode="rich",
)

console = get_console()

PRESETS_DIR = Path.home() / ".codevault"
PRESETS_FILE = PRESETS_DIR / "presets.json"

DEFAULT_PRESETS = {
    "fast": {
        "description": "Fast build with minimal protection",
        "config": {
            "onefile": True,
            "console": True,
            "lto": False,
            "enable_lease": False,
            "obfuscate_level": "none",
        },
    },
    "balanced": {
        "description": "Balanced protection and speed",
        "config": {
            "onefile": True,
            "console": True,
            "lto": True,
            "enable_lease": True,
            "lease_duration_hours": 24,
            "obfuscate_level": "balanced",
        },
    },
    "secure": {
        "description": "Maximum protection build",
        "config": {
            "onefile": True,
            "console": False,
            "lto": True,
            "enable_lease": True,
            "lease_duration_hours": 4,
            "obfuscate_level": "maximum",
            "anti_debug": True,
        },
    },
}


def _ensure_presets_dir() -> None:
    """Ensure presets directory exists."""
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def _load_presets() -> dict:
    """Load presets from file."""
    _ensure_presets_dir()

    if not PRESETS_FILE.exists():
        _save_presets(DEFAULT_PRESETS)
        return DEFAULT_PRESETS.copy()

    try:
        with open(PRESETS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_PRESETS.copy()


def _save_presets(presets: dict) -> None:
    """Save presets to file."""
    _ensure_presets_dir()

    with open(PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)


def get_preset(name: str) -> Optional[dict]:
    """Get a specific preset by name."""
    presets = _load_presets()
    return presets.get(name)


def list_preset_names() -> list:
    """List all preset names."""
    presets = _load_presets()
    return list(presets.keys())


@app.command("list")
def list_presets() -> None:
    """
    List all saved build presets.

    [bold]Example:[/bold]

    $ codevault preset list
    """
    presets = _load_presets()

    if not presets:
        console.print(
            Panel(
                "[yellow]No presets found.[/yellow]\n\n"
                "Create a preset with: codevault preset save <name>",
                title="Build Presets",
                border_style="yellow",
            )
        )
        return

    table = Table(
        title=f"Build Presets ({len(presets)} saved)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Name", style="green")
    table.add_column("Description", style="white")
    table.add_column("Config", style="dim")

    for name, preset_data in presets.items():
        config = preset_data.get("config", {})
        config_str = ", ".join(f"{k}={v}" for k, v in list(config.items())[:3])
        if len(config) > 3:
            config_str += "..."
        table.add_row(
            name,
            preset_data.get("description", ""),
            config_str,
        )

    console.print(table)
    console.print(f"\n[dim]Presets stored at: {PRESETS_FILE}[/dim]")


@app.command("save")
def save_preset(
    name: str = typer.Argument(..., help="Preset name"),
    description: str = typer.Option(
        "", "--description", "-d", help="Preset description"
    ),
    onefile: bool = typer.Option(
        True, "--onefile/--directory", help="Build as single file"
    ),
    console_app: bool = typer.Option(
        True, "--console/--windowed", help="Console or windowed app"
    ),
    lto: bool = typer.Option(
        True, "--lto/--no-lto", help="Enable link-time optimization"
    ),
    enable_lease: bool = typer.Option(
        True, "--lease/--no-lease", help="Enable offline leases"
    ),
    lease_hours: int = typer.Option(
        24, "--lease-hours", help="Lease duration in hours"
    ),
    obfuscate: str = typer.Option(
        "balanced", "--obfuscate", help="Obfuscation level: none, balanced, maximum"
    ),
    anti_debug: bool = typer.Option(
        False, "--anti-debug", help="Enable anti-debug protection"
    ),
    output_dir: str = typer.Option("", "--output-dir", help="Default output directory"),
) -> None:
    """
    Save a build preset with specified configuration.

    [bold]Examples:[/bold]

    $ codevault preset save my-release --description "Production release build"
    $ codevault preset save fast-dev --obfuscate none --no-lease
    """
    presets = _load_presets()

    config = {
        "onefile": onefile,
        "console": console_app,
        "lto": lto,
        "enable_lease": enable_lease,
        "lease_duration_hours": lease_hours,
        "obfuscate_level": obfuscate,
        "anti_debug": anti_debug,
    }

    if output_dir:
        config["output_dir"] = output_dir

    presets[name] = {
        "description": description,
        "config": config,
    }

    _save_presets(presets)
    print_success(f"Preset '{name}' saved successfully")
    console.print(f"[dim]Config: {json.dumps(config, indent=2)}[/dim]")


@app.command("load")
def load_preset(
    name: str = typer.Argument(..., help="Preset name to load"),
    show: bool = typer.Option(False, "--show", "-s", help="Only show, don't use"),
) -> None:
    """
    Load and display a preset configuration.

    [bold]Examples:[/bold]

    $ codevault preset load my-release
    $ codevault preset load fast-dev --show
    """
    preset = get_preset(name)

    if not preset:
        print_error(f"Preset '{name}' not found")
        console.print("[dim]Use 'codevault preset list' to see available presets[/dim]")
        raise typer.Exit(1)

    config = preset.get("config", {})
    description = preset.get("description", "")

    console.print(
        Panel(
            f"[bold]Description:[/bold] {description}\n\n"
            f"[bold]Configuration:[/bold]\n{json.dumps(config, indent=2)}",
            title=f"Preset: {name}",
            border_style="cyan",
        )
    )

    if show:
        return

    console.print(
        "\n[dim]Use this preset with: codevault project build --preset {name}[/dim]"
    )


@app.command("delete")
def delete_preset(
    name: str = typer.Argument(..., help="Preset name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Delete a saved preset.

    [bold]Examples:[/bold]

    $ codevault preset delete my-old-preset
    $ codevault preset delete my-old-preset --force
    """
    presets = _load_presets()

    if name not in presets:
        print_error(f"Preset '{name}' not found")
        raise typer.Exit(1)

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Delete preset '{name}'?"):
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    del presets[name]
    _save_presets(presets)
    print_success(f"Preset '{name}' deleted")


@app.command("reset")
def reset_presets(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Reset all presets to defaults.

    [bold]Example:[/bold]

    $ codevault preset reset --force
    """
    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask("Reset all presets to defaults? This cannot be undone."):
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    _save_presets(DEFAULT_PRESETS)
    print_success("All presets reset to defaults")


@app.command("export")
def export_presets(
    output: Path = typer.Argument(..., help="Output file path"),
) -> None:
    """
    Export presets to a JSON file.

    [bold]Example:[/bold]

    $ codevault preset export ./my-presets.json
    """
    presets = _load_presets()

    try:
        with open(output, "w") as f:
            json.dump(presets, f, indent=2)
        print_success(f"Exported {len(presets)} presets to {output}")
    except IOError as e:
        print_error(f"Failed to export: {e}")
        raise typer.Exit(1)


@app.command("import")
def import_presets(
    input_file: Path = typer.Argument(..., help="Input JSON file"),
    merge: bool = typer.Option(
        True, "--merge/--replace", help="Merge with existing or replace"
    ),
) -> None:
    """
    Import presets from a JSON file.

    [bold]Examples:[/bold]

    $ codevault preset import ./my-presets.json
    $ codevault preset import ./my-presets.json --replace
    """
    try:
        with open(input_file, "r") as f:
            imported = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print_error(f"Failed to read file: {e}")
        raise typer.Exit(1)

    if merge:
        presets = _load_presets()
        presets.update(imported)
    else:
        presets = imported

    _save_presets(presets)
    print_success(
        f"Imported {len(imported)} presets ({'merged' if merge else 'replaced'})"
    )
