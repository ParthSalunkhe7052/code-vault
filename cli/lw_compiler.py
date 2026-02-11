#!/usr/bin/env python3
"""
Legacy entry point for CodeVault CLI (lw-compiler).

This file is kept for backward compatibility — users may have it in their PATH
or reference it in scripts. It delegates all functionality to the new
codevault_cli package (Typer + Rich based).

Usage:
    python lw_compiler.py [command] [options]

All commands are handled by codevault_cli.app. Run with --help for details.
"""

import sys

# Require requests — fail explicitly if missing (never auto-install)
try:
    import requests  # noqa: F401
except ImportError:
    print("[ERROR] 'requests' module not found.")
    print("        Install it with: pip install codevault-cli  OR  pip install requests")
    sys.exit(1)

from codevault_cli.app import run


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nCancelled. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        print("   If this persists, check your internet connection.")
        sys.exit(1)
