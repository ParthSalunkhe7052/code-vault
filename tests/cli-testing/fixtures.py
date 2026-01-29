"""
Test Fixtures and Configuration for CLI Testing

This module contains test accounts, configurations, and helper functions
for automated CLI testing.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# =============================================================================
# Paths
# =============================================================================

TESTS_DIR = Path(__file__).parent
CLI_DIR = TESTS_DIR.parent.parent / "cli"
TEST_PROJECTS_DIR = TESTS_DIR / "test_projects"
BUILD_OUTPUT_DIR = TESTS_DIR / "build_output"

# =============================================================================
# Test Accounts
# =============================================================================


@dataclass
class TestAccount:
    email: str
    password: str
    name: str
    plan: str

    def to_login_dict(self):
        return {"email": self.email, "password": self.password}


# Pre-configured test accounts (must match mock_server.py)
ACCOUNTS = {
    "free": TestAccount(
        email="test@codevault.local",
        password="testpass123",
        name="Test User",
        plan="free",
    ),
    "pro": TestAccount(
        email="pro@codevault.local", password="propass123", name="Pro User", plan="pro"
    ),
    "admin": TestAccount(
        email="admin@codevault.local",
        password="adminpass123",
        name="Admin User",
        plan="enterprise",
    ),
}

# Default account for testing
DEFAULT_ACCOUNT = ACCOUNTS["free"]

# =============================================================================
# Test Licenses
# =============================================================================


@dataclass
class TestLicense:
    key: str
    status: str
    description: str


LICENSES = {
    "active_lifetime": TestLicense(
        key="CV-TEST-0001-AAAA-BBBB",
        status="active",
        description="Active license, lifetime, 3 activations",
    ),
    "active_30days": TestLicense(
        key="CV-TEST-0002-CCCC-DDDD",
        status="active",
        description="Active license, 30 days, 1 activation",
    ),
    "expired": TestLicense(
        key="CV-EXPIRED-0001-XXXX-YYYY", status="expired", description="Expired license"
    ),
}

DEFAULT_LICENSE = LICENSES["active_lifetime"]

# =============================================================================
# Test Projects
# =============================================================================


@dataclass
class TestProject:
    id: int
    name: str
    language: str
    entry_file: str
    description: str


PROJECTS = {
    "hello_world": TestProject(
        id=1,
        name="Hello World Test",
        language="python",
        entry_file="main.py",
        description="Simple Python test project",
    ),
    "node_app": TestProject(
        id=2,
        name="Node Test App",
        language="nodejs",
        entry_file="index.js",
        description="Node.js test project",
    ),
}

DEFAULT_PROJECT = PROJECTS["hello_world"]

# =============================================================================
# Configuration
# =============================================================================


@dataclass
class TestConfig:
    """Configuration for CLI testing."""

    mock_server_host: str = "127.0.0.1"
    mock_server_port: int = 8000
    timeout_seconds: int = 300  # 5 minutes for builds
    fast_build_mode: bool = True  # Use fast build by default for testing
    cleanup_after_test: bool = True
    verbose: bool = True

    @property
    def api_url(self) -> str:
        return f"http://{self.mock_server_host}:{self.mock_server_port}/api/v1"

    @property
    def server_url(self) -> str:
        return f"http://{self.mock_server_host}:{self.mock_server_port}"


DEFAULT_CONFIG = TestConfig()

# =============================================================================
# Helper Functions
# =============================================================================


def ensure_directories():
    """Create required directories."""
    TEST_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_cli_path() -> Path:
    """Get path to the CLI entry point."""
    return CLI_DIR / "lw_compiler.py"


def get_test_project_path(project_name: str = "hello_world") -> Path:
    """Get path to a test project."""
    return TEST_PROJECTS_DIR / project_name


def cleanup_build_output():
    """Clean up build output directory."""
    import shutil

    if BUILD_OUTPUT_DIR.exists():
        for item in BUILD_OUTPUT_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


def create_cli_config(
    api_url: str, token: Optional[str] = None, email: Optional[str] = None
):
    """Create a config.json for the CLI pointing to our mock server."""
    config_path = CLI_DIR / "config.json"
    config = {"api_url": api_url}
    if email:
        config["email"] = email

    # Write config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return config_path


def get_env_for_testing(config: TestConfig = DEFAULT_CONFIG) -> dict:
    """Get environment variables for testing."""
    env = os.environ.copy()
    env["LW_API_URL"] = config.api_url
    env["CODEVAULT_TEST_MODE"] = "1"
    return env
