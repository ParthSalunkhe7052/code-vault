"""
Entry point for running CodeVault CLI as a module.

Usage:
    python -m codevault_cli
    python -m codevault_cli --help
"""

from codevault_cli.app import run

if __name__ == "__main__":
    run()
