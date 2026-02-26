"""Tests for Python and Node.js wrapper generators."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cli"))

from cli.generators.python_generator import (
    get_python_wrapper,
    validate_license_key,
    validate_server_url,
    WrapperGenerationError,
)
from cli.generators.nodejs_generator import (
    get_nodejs_wrapper_inline,
    validate_license_key as node_validate_license_key,
    validate_server_url as node_validate_server_url,
)


class TestPythonGenerator:
    """Tests for Python wrapper generator."""

    def test_get_python_wrapper_generates_code(self):
        """Test that wrapper generates valid Python code."""
        code = get_python_wrapper(
            license_key="TEST-KEY-1234",
            server_url="https://api.codevault.app",
        )
        assert isinstance(code, str)
        assert len(code) > 0
        assert "CodeVault" in code

    def test_get_python_wrapper_with_custom_app_name(self):
        """Test wrapper with custom app name."""
        code = get_python_wrapper(
            license_key="TEST-KEY-1234",
            server_url="https://api.codevault.app",
            app_name="My Custom App",
        )
        assert "My Custom App" in code

    def test_get_python_wrapper_with_demo_key(self):
        """Test wrapper with DEMO key."""
        code = get_python_wrapper(
            license_key="DEMO",
            server_url="https://api.codevault.app",
        )
        assert isinstance(code, str)
        assert len(code) > 0

    def test_validate_license_key_accepts_valid_keys(self):
        """Test that valid license keys are accepted."""
        assert validate_license_key("TEST-KEY-1234") == "TEST-KEY-1234"
        assert validate_license_key("ABC_DEF_123") == "ABC_DEF_123"

    def test_validate_license_key_rejects_invalid_keys(self):
        """Test that invalid license keys raise WrapperGenerationError."""
        with pytest.raises(WrapperGenerationError):
            validate_license_key("invalid;key")

    def test_validate_server_url_accepts_valid_urls(self):
        """Test that valid URLs are accepted."""
        assert (
            validate_server_url("https://api.codevault.app")
            == "https://api.codevault.app"
        )
        assert validate_server_url("http://localhost:8000") == "http://localhost:8000"

    def test_validate_server_url_rejects_invalid_urls(self):
        """Test that invalid URLs raise WrapperGenerationError."""
        with pytest.raises(WrapperGenerationError):
            validate_server_url("not-a-url")
        with pytest.raises(WrapperGenerationError):
            validate_server_url("ftp://example.com")


class TestNodejsGenerator:
    """Tests for Node.js wrapper generator."""

    def test_get_nodejs_wrapper_inline_generates_code(self):
        """Test that inline wrapper generates valid code."""
        prefix, suffix = get_nodejs_wrapper_inline(
            license_key="TEST-KEY-1234",
            server_url="https://api.codevault.app",
        )
        assert isinstance(prefix, str)
        assert isinstance(suffix, str)
        assert len(prefix) > 0

    def test_get_nodejs_wrapper_with_demo_key(self):
        """Test wrapper with DEMO key."""
        prefix, suffix = get_nodejs_wrapper_inline(
            license_key="DEMO",
            server_url="https://api.codevault.app",
        )
        assert isinstance(prefix, str)
        assert "DEMO" in prefix

    def test_get_nodejs_wrapper_with_custom_app_name(self):
        """Test wrapper with custom app name."""
        prefix, suffix = get_nodejs_wrapper_inline(
            license_key="TEST-KEY-1234",
            server_url="https://api.codevault.app",
            app_name="My Node App",
        )
        assert "My Node App" in prefix

    def test_node_validate_license_key(self):
        """Test Node.js license key validation."""
        assert node_validate_license_key("TEST-KEY-1234") == "TEST-KEY-1234"

    def test_node_validate_server_url(self):
        """Test Node.js server URL validation."""
        assert (
            node_validate_server_url("https://api.codevault.app")
            == "https://api.codevault.app"
        )
