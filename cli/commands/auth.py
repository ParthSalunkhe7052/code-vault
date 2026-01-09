import sys
import requests
from getpass import getpass
from terminal import Colors, color_print, print_header
from cli_config import (
    load_config,
    save_config,
    get_headers,
    clear_config,
    DEFAULT_API_BASE,
)

def check_logged_in():
    """Check if user is logged in."""
    headers = get_headers()
    if not headers:
        color_print("❌ Not logged in. Run 'lw-compiler login' first.", Colors.RED)
        color_print("\n💡 Quick start:", Colors.CYAN)
        color_print("   1. python lw_compiler.py login", Colors.WHITE)
        color_print("   2. python lw_compiler.py build", Colors.WHITE)
        color_print("", Colors.RESET)
        sys.exit(1)
    return headers

def handle_error(resp):
    """Handle API error response."""
    try:
        error = resp.json().get("detail", "Unknown error")
    except Exception:
        error = resp.text or f"HTTP {resp.status_code}"

    if resp.status_code == 401:
        color_print(
            "❌ Authentication failed. Run 'lw-compiler login' again.", Colors.RED
        )
    elif resp.status_code == 404:
        color_print(f"❌ Not found: {error}", Colors.RED)
    else:
        color_print(f"❌ Error: {error}", Colors.RED)

def cmd_login(args):
    """Login with your CodeVault account."""
    config = load_config()

    print_header("CodeVault CLI - Login")

    # Use saved or default API URL - no confusing prompt
    api_url = config.get("api_url", DEFAULT_API_BASE)

    print(f"\n📡 Server: {api_url}")
    print("   (Set LW_API_URL env variable to use a different server)\n")

    print("Enter your CodeVault account credentials:\n")

    try:
        email = input("  Email: ").strip().lower()  # Normalize to lowercase
    except EOFError:
        color_print("\n❌ Input cancelled.", Colors.RED)
        return

    # Validate email format
    if not email:
        color_print("\n❌ Email is required.", Colors.RED)
        return
    if "@" not in email or "." not in email:
        color_print("\n❌ Please enter a valid email address.", Colors.RED)
        return

    try:
        password = getpass("  Password: ").strip()
    except EOFError:
        color_print("\n❌ Input cancelled.", Colors.RED)
        return

    if not password:
        color_print("\n❌ Password is required.", Colors.RED)
        return

    print("\n⏳ Logging in...")

    try:
        resp = requests.post(
            f"{api_url}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            user = data.get("user", {})

            config["api_key"] = token
            config["api_url"] = api_url
            config["email"] = email
            config["user_name"] = user.get("name", email)
            save_config(config)

            color_print(
                f"\n✅ Logged in as {user.get('name', email)} ({email})", Colors.GREEN
            )
            color_print(f"   Server: {api_url}\n", Colors.CYAN)
            color_print(
                "   Next: Run 'lw-compiler build' to compile a project",
                Colors.DIM,
            )
        elif resp.status_code == 401:
            color_print("\n❌ Invalid email or password.", Colors.RED)
            color_print(
                "   Please check your credentials and try again.", Colors.YELLOW
            )
        else:
            handle_error(resp)
            color_print("\n❌ Login failed.", Colors.RED) # Fallback if handle_error prints nothing specific enough
            
    except requests.exceptions.Timeout:
        color_print("\n❌ Connection timed out.", Colors.RED)
        color_print("   The server is taking too long to respond.", Colors.YELLOW)
    except requests.exceptions.ConnectionError:
        color_print("\n❌ Cannot connect to server.", Colors.RED)
        color_print(f"\n   Server: {api_url}", Colors.YELLOW)
        color_print("\n   💡 Make sure:", Colors.CYAN)
        color_print(
            "      1. The CodeVault server is running (Run Web App.bat)", Colors.WHITE
        )
        color_print("      2. Check your internet connection", Colors.WHITE)
    except Exception as e:
        color_print(f"\n❌ Error: {e}", Colors.RED)

def cmd_logout(args):
    """Logout and clear saved credentials."""
    clear_config()
    color_print("✅ Logged out successfully.", Colors.GREEN)
