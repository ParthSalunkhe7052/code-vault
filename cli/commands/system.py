import sys
import subprocess
from terminal import Colors, color_print, print_header
from cli_config import load_config, DEFAULT_API_BASE

def cmd_status(args):
    """Show current status and environment."""
    config = load_config()
    print_header("License Wrapper CLI - Status")

    if config.get("api_key"):
        color_print(
            f"  ✅ Logged in as: {config.get('email', 'Unknown')}", Colors.GREEN
        )
        color_print(
            f"     API URL: {config.get('api_url', DEFAULT_API_BASE)}", Colors.CYAN
        )
    else:
        color_print("  ❌ Not logged in", Colors.RED)

    print()
    print("  Checking dependencies...")

    # Check Nuitka
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            version = (
                result.stdout.strip().split("\n")[0] if result.stdout else "Unknown"
            )
            color_print(f"  ✅ Nuitka: {version}", Colors.GREEN)
        else:
            color_print("  ❌ Nuitka: Not installed", Colors.RED)
            color_print("     Install with: pip install nuitka", Colors.YELLOW)
    except Exception:
        color_print("  ❌ Nuitka: Not found", Colors.RED)

    # Check Node.js / pkg
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            color_print(f"  ✅ Node.js: {result.stdout.strip()}", Colors.GREEN)
        else:
            color_print("  ❌ Node.js: Not installed", Colors.YELLOW)
    except Exception:
        color_print("  ❌ Node.js: Not found", Colors.YELLOW)

    color_print(f"  ✅ Python: {sys.version.split()[0]}", Colors.GREEN)
    print()
