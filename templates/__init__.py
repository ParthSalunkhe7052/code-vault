"""
CodeVault Unified Wrapper Templates

This module provides unified license wrapper templates for both CLI and cloud builds.
Uses string.Template for variable substitution.

Usage:
    from templates import load_template, fill_template

    template = load_template('python')
    filled = fill_template(template, {
        'LICENSE_KEY': 'ABC123',
        'PRODUCT_ID': 'my-app',
        'HWID_ENABLED': 'True',
        'LEASE_ENABLED': 'True',
        'SECRET_KEY': 'secret123',
        'API_BASE': 'https://api.example.com',
        'FUNC_PREFIX': '_lw',
    })
"""

import sys
from pathlib import Path
from string import Template

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from templates.wrapper_python import UNIFIED_PYTHON_WRAPPER

# Load Node.js template
template_dir = Path(__file__).parent
nodejs_template_path = template_dir / "wrapper_nodejs.js"
if nodejs_template_path.exists():
    with open(nodejs_template_path, "r") as f:
        content = f.read()
        # Extract the template string from the JS file
        start = content.find("`") + 1
        end = content.rfind("`")
        UNIFIED_NODEJS_WRAPPER = content[start:end]
else:
    UNIFIED_NODEJS_WRAPPER = ""

TEMPLATES = {
    "python": UNIFIED_PYTHON_WRAPPER,
    "nodejs": UNIFIED_NODEJS_WRAPPER,
}


def load_template(language: str) -> str:
    """Load a template by language ('python' or 'nodejs')."""
    if language not in TEMPLATES:
        raise ValueError(
            f"Unknown template language: {language}. Available: {list(TEMPLATES.keys())}"
        )
    return TEMPLATES[language]


def fill_template(template_str: str, variables: dict) -> str:
    """Fill a template with variables using string.Template."""
    t = Template(template_str)
    return t.safe_substitute(variables)


def get_available_templates() -> list:
    """Get list of available template languages."""
    return list(TEMPLATES.keys())


__all__ = [
    "UNIFIED_PYTHON_WRAPPER",
    "UNIFIED_NODEJS_WRAPPER",
    "load_template",
    "fill_template",
    "get_available_templates",
]
