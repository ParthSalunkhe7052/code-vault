"""
Interactive prompts and selectors for CodeVault CLI.

Provides beautiful interactive UI using questionary.
"""

import questionary
from typing import List, Dict, Optional, Any
from rich.panel import Panel
from codevault_cli.console import get_console, print_error

console = get_console()


def select_project(projects: List[Dict[str, Any]]) -> Optional[str]:
    """
    Interactive project selector with fuzzy search.

    Args:
        projects: List of project dictionaries with 'id' and 'name' keys

    Returns:
        Selected project ID or None if cancelled
    """
    if not projects:
        print_error("No projects found")
        return None

    # Format choices for questionary
    choices = []
    for p in projects:
        settings = p.get("settings", {})
        if isinstance(settings, str):
            import json

            try:
                settings = json.loads(settings) if settings else {}
            except:
                settings = {}

        is_multi = settings.get("is_multi_folder", False)
        project_type = "[DIR]" if is_multi else "[FILE]"

        name = p.get("name", "Unknown")
        project_id = p.get("id", "")

        choices.append(
            questionary.Choice(
                title=f"{project_type} {name}",
                value=project_id,
                description=f"ID: {project_id[:16]}...",
            )
        )

    # Add cancel option
    choices.append(questionary.Separator())
    choices.append(
        questionary.Choice(
            title="Cancel", value=None, description="Return to main menu"
        )
    )

    try:
        selected = questionary.select(
            "Select a project:",
            choices=choices,
            use_arrow_keys=True,
            use_jk_keys=True,
            instruction="(Use arrow keys or type to search)",
        ).ask()

        return selected
    except KeyboardInterrupt:
        return None


def select_license(licenses: List[Dict[str, Any]]) -> Optional[str]:
    """
    Interactive license selector.

    Args:
        licenses: List of license dictionaries

    Returns:
        Selected license key or None
    """
    if not licenses:
        console.print("[yellow]No licenses found. Using demo mode.[/yellow]")
        return None

    # Format choices
    choices = [
        questionary.Choice(
            title="Demo Mode (no license)",
            value=None,
            description="Build without license protection",
        ),
        questionary.Separator(),
    ]

    for lic in licenses:
        status = lic.get("status", "unknown")
        key = lic.get("license_key", "Unknown")
        client = lic.get("client_name", "")
        expires = lic.get("expires_at", "")

        status_indicator = "[ACTIVE]" if status == "active" else "[INACTIVE]"
        description = f"{status_indicator}"
        if client:
            description += f" Client: {client}"
        if expires:
            description += f" Expires: {expires[:10]}"

        choices.append(
            questionary.Choice(title=key[:30], value=key, description=description)
        )

    try:
        selected = questionary.select(
            "Select a license (or Demo Mode):",
            choices=choices,
            use_arrow_keys=True,
        ).ask()

        return selected
    except KeyboardInterrupt:
        return None


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Confirmation prompt.

    Args:
        message: The question to ask
        default: Default value (True=yes, False=no)

    Returns:
        True if confirmed, False otherwise
    """
    try:
        return questionary.confirm(message, default=default).ask()
    except KeyboardInterrupt:
        return False


def select_build_mode() -> str:
    """
    Interactive build mode selector.

    Returns:
        "fast" or "standard"
    """
    choices = [
        questionary.Choice(
            title="Fast Mode [FAST] - Directory Output",
            value="fast",
            description="3-4x faster, outputs a directory with launcher script (lowest AV warnings)",
        ),
        questionary.Choice(
            title="Standard Mode [STD] - Single EXE",
            value="standard",
            description="Single .exe file, slower but easier to distribute (may trigger AV warnings)",
        ),
    ]

    try:
        selected = questionary.select(
            "Select build mode:",
            choices=choices,
            default="fast",
            use_arrow_keys=True,
        ).ask()

        # Show AV warning for standard mode
        if selected == "standard":
            try:
                console = get_console()
                console.print()
                console.print(
                    Panel(
                        "[yellow]⚠️  Antivirus Notice[/yellow]\n\n"
                        "Standard mode uses onefile compression which may trigger antivirus warnings.\n"
                        "This is a [bold]false positive[/bold] - your app is safe.\n\n"
                        "[dim]If users see warnings, they can:\n"
                        "• Click 'More info' → 'Run anyway'\n"
                        "• Add an exclusion in Windows Security\n"
                        "• Use Fast Mode for development/testing[/dim]",
                        title="",
                        border_style="yellow",
                    )
                )
                console.print()
            except:
                pass

        return selected or "fast"
    except KeyboardInterrupt:
        return "fast"


def text_input(message: str, default: str = "", validate=None) -> Optional[str]:
    """
    Text input with optional validation.

    Args:
        message: Prompt message
        default: Default value
        validate: Validation function

    Returns:
        User input or None if cancelled
    """
    try:
        return questionary.text(message, default=default, validate=validate).ask()
    except KeyboardInterrupt:
        return None


def password_input(message: str = "Password:") -> Optional[str]:
    """
    Password input (hidden).

    Returns:
        Password or None if cancelled
    """
    try:
        return questionary.password(message).ask()
    except KeyboardInterrupt:
        return None


def checkbox_select(
    message: str,
    choices: List[questionary.Choice],
    defaults: Optional[List[str]] = None,
) -> List[str]:
    """
    Multi-select checkbox.

    Args:
        message: Prompt message
        choices: List of choices
        defaults: Default selected values

    Returns:
        List of selected values
    """
    try:
        return (
            questionary.checkbox(message, choices=choices, default=defaults or []).ask()
            or []
        )
    except KeyboardInterrupt:
        return []


def select_from_list(
    message: str, choices: List[str], default: Optional[str] = None
) -> Optional[str]:
    """
    Simple list selection.

    Args:
        message: Prompt message
        choices: List of string choices
        default: Default selection

    Returns:
        Selected value or None
    """
    try:
        return questionary.select(message, choices=choices, default=default).ask()
    except KeyboardInterrupt:
        return None


def show_menu(title: str, options: Dict[str, str]) -> Optional[str]:
    """
    Show a menu and get selection.

    Args:
        title: Menu title
        options: Dict of {value: display_name}

    Returns:
        Selected value or None
    """
    choices = [
        questionary.Choice(title=name, value=value) for value, name in options.items()
    ]

    # Add separator and exit option
    choices.append(questionary.Separator())
    choices.append(questionary.Choice(title="Exit", value="exit"))

    try:
        selected = questionary.select(
            title,
            choices=choices,
            use_arrow_keys=True,
        ).ask()

        return None if selected == "exit" else selected
    except KeyboardInterrupt:
        return None


def autocomplete_input(
    message: str, choices: List[str], default: str = ""
) -> Optional[str]:
    """
    Input with autocomplete.

    Args:
        message: Prompt message
        choices: List of autocomplete options
        default: Default value

    Returns:
        User input or None
    """
    try:
        return questionary.autocomplete(message, choices=choices, default=default).ask()
    except KeyboardInterrupt:
        return None
