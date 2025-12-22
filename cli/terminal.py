"""
Terminal utilities for License Wrapper CLI.
Provides colored output and console helpers.
"""

import sys


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def enable_colors():
    """Enable ANSI colors on Windows."""
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def color_print(msg, color=Colors.RESET):
    """Print colored message."""
    enable_colors()
    print(f"{color}{msg}{Colors.RESET}")


def print_header(title: str):
    """Print a styled header."""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.RESET}\n")


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
