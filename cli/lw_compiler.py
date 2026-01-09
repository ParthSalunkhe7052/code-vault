#!/usr/bin/env python3
"""
License Wrapper CLI Compiler (lw-compiler)
Runs Nuitka/pkg locally to compile license-protected executables.

Usage:
    lw-compiler login              - Save your API key
    lw-compiler projects           - List your projects
    lw-compiler licenses <id>      - List licenses for a project
    lw-compiler build <id> -l KEY  - Build a project with license
    lw-compiler build              - Interactive build mode
    lw-compiler version            - Show CLI version
"""

__version__ = "1.0.0"

import sys
import argparse

# Check for requests module before anything else
try:
    import requests
except ImportError:
    import subprocess
    print("❌ 'requests' module not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests  # noqa: F401 - imported after auto-install

from terminal import Colors
from commands.auth import cmd_login, cmd_logout
from commands.projects import cmd_projects, cmd_licenses
from commands.system import cmd_status
from commands.build import cmd_build


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="lw-compiler",
        description="License Wrapper CLI - Compile apps with license protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lw-compiler login                           Login with your account
  lw-compiler projects                        List your projects
  lw-compiler licenses PROJECT_ID             List licenses for a project
  lw-compiler build PROJECT_ID -l KEY         Build project with license
  lw-compiler build script.py --fast          Fast build (3-4x faster)
  lw-compiler build script.py --jobs=8        Use 8 CPU cores
  lw-compiler build                           Interactive build mode

Build Tips:
  • --fast or --fast-build: 3-4x faster, directory output (not single .exe)
  • --jobs=N: Use N CPU cores (default: auto-detect, max: 8, override with CODEVAULT_JOBS)
  • Large projects: 20-60 min standard, 10-15 min with --fast
  • Terminal bell plays when build completes (double bell on error)
  • Press Windows+V after bell to see clipboard history with output path
        """,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("login", help="Login with your account")
    subparsers.add_parser("logout", help="Logout and clear credentials")
    subparsers.add_parser("projects", help="List your projects")
    subparsers.add_parser("status", help="Show current status and environment")
    subparsers.add_parser("version", help="Show CLI version")

    licenses_parser = subparsers.add_parser(
        "licenses", help="List licenses for a project"
    )
    licenses_parser.add_argument("project_id", help="Project ID")

    build_parser = subparsers.add_parser("build", help="Build a project locally")
    build_parser.add_argument(
        "project_id",
        nargs="?",
        help="Project ID or path to entry file (for local build)",
    )
    build_parser.add_argument("-l", "--license", help="License key to embed")
    build_parser.add_argument(
        "--generic",
        action="store_true",
        help="Build in generic mode (prompt for license at runtime)",
    )
    build_parser.add_argument(
        "--language", choices=["python", "nodejs"], help="Force language selection"
    )
    build_parser.add_argument(
        "--output", help="Output path for the executable (local build only)"
    )
    build_parser.add_argument("--api-url", help="Override API URL (local build only)")
    build_parser.add_argument(
        "--demo", action="store_true", help="Build in demo mode (local build only)"
    )
    build_parser.add_argument(
        "--demo-duration", type=int, help="Demo duration in minutes (local build only)"
    )
    build_parser.add_argument(
        "--open",
        action="store_true",
        help="Build without license protection (open build)",
    )
    build_parser.add_argument(
        "--obfuscate",
        action="store_true",
        help="Enable code obfuscation (slower build, better protection)",
    )
    build_parser.add_argument(
        "--enable-lease",
        action="store_true",
        help="Enable offline lease (24-hour cached validation)",
    )
    build_parser.add_argument(
        "--fast-build",
        action="store_true",
        default=None,
        help="Fast build mode: Compile without --onefile (directory output, much faster)",
    )
    build_parser.add_argument(
        "--jobs",
        type=int,
        help="Override CPU core count for parallel compilation (default: auto-detect, max: 8)",
    )
    build_parser.add_argument(
        "--fast",
        action="store_true",
        dest="fast_build",  # Same as --fast-build
        default=None,
        help="Alias for --fast-build",
    )

    args = parser.parse_args()

    # Validate --jobs argument if provided
    if getattr(args, 'jobs', None) is not None:
        if args.jobs < 1:
            print(f"{Colors.RED}Error: --jobs must be >= 1{Colors.RESET}")
            sys.exit(1)

    def cmd_version(args):
        """Show CLI version."""
        print(f"CodeVault CLI v{__version__}")

    commands = {
        "login": cmd_login,
        "logout": cmd_logout,
        "projects": cmd_projects,
        "licenses": cmd_licenses,
        "build": cmd_build,
        "status": cmd_status,
        "version": cmd_version,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        # Show welcome banner with Quick Start guide
        print(f"""
{Colors.CYAN}╔════════════════════════════════════════════════════════════╗
║  {Colors.BOLD}CodeVault CLI{Colors.CYAN} - Build license-protected executables    ║
╚════════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.GREEN}🚀 Quick Start:{Colors.RESET}
  1. python lw_compiler.py login      {Colors.DIM}← Login first{Colors.RESET}
  2. python lw_compiler.py build      {Colors.DIM}← Interactive build{Colors.RESET}

{Colors.CYAN}📋 All Commands:{Colors.RESET}
  login      Log in to your CodeVault account
  logout     Log out and clear credentials
  projects   List your projects
  build      Build a project into an executable
  status     Check login status and environment
  version    Show CLI version

{Colors.YELLOW}💡 Tip:{Colors.RESET} Run 'python lw_compiler.py status' to check your setup.
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Cancelled. Goodbye!{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.RESET}")
        print(
            f"{Colors.YELLOW}   If this persists, check your internet connection.{Colors.RESET}"
        )
        sys.exit(1)
