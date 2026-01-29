"""
Terminal utilities for License Wrapper CLI.
Provides colored output and console helpers.
"""

import sys


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


# ASCII replacements for emojis (Windows console compatibility)
EMOJI_REPLACEMENTS = {
    "✅": "[OK]",
    "❌": "[X]",
    "⚠️": "[!]",
    "📋": "[i]",
    "📡": "[>]",
    "⏳": "[..]",
    "💡": "[*]",
    "👤": "[U]",
    "📧": "[@]",
    "👑": "[P]",
    "🏗️": "[B]",
    "🛡️": "[A]",
    "█": "#",
    "░": "-",
}


def safe_str(text: str) -> str:
    """Convert text to be safe for Windows console output.

    Replaces emojis with ASCII alternatives if the console
    doesn't support Unicode.
    """
    try:
        # Try encoding with the current console encoding
        text.encode(sys.stdout.encoding or "utf-8")
        return text
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Replace emojis with ASCII equivalents
        result = text
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            result = result.replace(emoji, replacement)
        return result


def safe_print(msg: str, end: str = "\n", flush: bool = False):
    """Print message with Unicode-safe encoding."""
    try:
        print(msg, end=end, flush=flush)
    except UnicodeEncodeError:
        print(safe_str(msg), end=end, flush=flush)


def enable_colors():
    """Enable ANSI colors on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def color_print(msg, color=Colors.RESET):
    """Print colored message with Unicode-safe encoding."""
    enable_colors()
    output = f"{color}{msg}{Colors.RESET}"
    try:
        print(output)
    except UnicodeEncodeError:
        # Fallback for Windows consoles that don't support Unicode
        print(f"{color}{safe_str(msg)}{Colors.RESET}")


def print_header(title: str):
    """Print a styled header."""
    print(f"\n{Colors.CYAN}{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}{Colors.RESET}\n")


def print_success(msg: str):
    """Print success message."""
    color_print(f"✅ {msg}", Colors.GREEN)


def print_error(msg: str):
    """Print error message."""
    color_print(f"❌ {msg}", Colors.RED)


def print_warning(msg: str):
    """Print warning message."""
    color_print(f"⚠️  {msg}", Colors.YELLOW)


def print_info(msg: str):
    """Print info message."""
    color_print(f"📋 {msg}", Colors.BLUE)


def print_progress_bar(
    percent: int, width: int = 30, phase: str = "", elapsed_time: str = ""
) -> None:
    """Print a visual progress bar.

    Args:
        percent: Progress percentage (0-100)
        width: Width of the progress bar in characters
        phase: Current phase description (e.g., "modules", "C code")
        elapsed_time: Elapsed time string (e.g., "2m15s")
    """
    enable_colors()

    # Clamp percent to 0-100
    percent = max(0, min(100, percent))

    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)

    # Build the status text
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
        # Fallback for terminals without Unicode support
        filled_char = "#" * filled + "-" * (width - filled)
        print(f"\r[{filled_char}] {percent:3d}%{status_display}  ", end="", flush=True)
