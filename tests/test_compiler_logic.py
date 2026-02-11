"""
Compiler Logic Unit Tests.

Tests the compiler pipeline: wrapper injection, compiler dispatch,
output detection, and build configuration handling.
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cli"))


# =============================================================================
# Wrapper Injection Tests
# =============================================================================

@pytest.mark.integration
class TestPythonWrapperInjection:
    """Test inject_license_wrapper correctly modifies Python entry files."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import inject_license_wrapper
            self.inject_license_wrapper = inject_license_wrapper
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_wrapper_prepended_to_entry_file(self, temp_project_dir):
        """Wrapper code should be prepended to the entry file."""
        original = temp_project_dir / "main.py"
        original_content = original.read_text()

        config = {
            "entry_file": "main.py",
            "license_key": "TEST-KEY",
            "server_url": "https://api.test.com",
            "signing_secret": "test-secret",
            "lease_enabled": False,
            "show_branding": True,
        }

        result = self.inject_license_wrapper(temp_project_dir, config)
        assert result is True

        modified = original.read_text()
        assert len(modified) > len(original_content)
        assert original_content in modified  # Original code preserved

    def test_wrapper_contains_license_key(self, temp_project_dir):
        """Injected wrapper should contain the license key."""
        config = {
            "entry_file": "main.py",
            "license_key": "MY-UNIQUE-KEY-123",
            "server_url": "https://api.test.com",
            "signing_secret": "test-secret",
            "lease_enabled": False,
            "show_branding": True,
        }

        self.inject_license_wrapper(temp_project_dir, config)
        content = (temp_project_dir / "main.py").read_text()
        assert "MY-UNIQUE-KEY-123" in content

    def test_wrapper_contains_server_url(self, temp_project_dir):
        """Injected wrapper should reference the correct server URL."""
        config = {
            "entry_file": "main.py",
            "license_key": "TEST-KEY",
            "server_url": "https://custom.server.com",
            "signing_secret": "test-secret",
            "lease_enabled": False,
            "show_branding": True,
        }

        self.inject_license_wrapper(temp_project_dir, config)
        content = (temp_project_dir / "main.py").read_text()
        assert "https://custom.server.com" in content

    def test_injection_fails_for_missing_entry_file(self, temp_project_dir):
        """Injection should fail gracefully if entry file doesn't exist."""
        config = {
            "entry_file": "nonexistent.py",
            "license_key": "TEST-KEY",
            "server_url": "https://api.test.com",
            "signing_secret": "test-secret",
            "lease_enabled": False,
            "show_branding": True,
        }

        result = self.inject_license_wrapper(temp_project_dir, config)
        assert result is False

    def test_injection_blocked_for_traversal_path(self, temp_project_dir):
        """Injection must be blocked for path traversal attempts."""
        config = {
            "entry_file": "../../../etc/passwd",
            "license_key": "TEST-KEY",
            "server_url": "https://api.test.com",
            "signing_secret": "test-secret",
            "lease_enabled": False,
            "show_branding": True,
        }

        result = self.inject_license_wrapper(temp_project_dir, config)
        assert result is False


# =============================================================================
# JavaScript Wrapper Injection Tests
# =============================================================================

@pytest.mark.integration
class TestJSWrapperInjection:
    """Test inject_js_wrapper correctly modifies JavaScript entry files."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import inject_js_wrapper
            self.inject_js_wrapper = inject_js_wrapper
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_js_wrapper_wraps_original_code(self, temp_nodejs_project_dir):
        """JS wrapper should wrap the original code in an IIFE."""
        entry = temp_nodejs_project_dir / "index.js"
        original_content = entry.read_text()

        config = {
            "license_key": "TEST-KEY",
            "server_url": "https://api.test.com",
            "lease_enabled": False,
            "show_branding": True,
        }

        result = self.inject_js_wrapper(entry, config)
        assert result is True

        modified = entry.read_text()
        assert len(modified) > len(original_content)
        assert original_content in modified

    def test_js_shebang_preserved(self, temp_nodejs_project_dir):
        """If the JS file has a shebang, it should be preserved at the top."""
        entry = temp_nodejs_project_dir / "index.js"
        entry.write_text("#!/usr/bin/env node\nconsole.log('hello');")

        config = {
            "license_key": "TEST-KEY",
            "server_url": "https://api.test.com",
            "lease_enabled": False,
            "show_branding": True,
        }

        self.inject_js_wrapper(entry, config)
        content = entry.read_text()
        assert content.startswith("#!/usr/bin/env node")

    def test_js_injection_fails_for_missing_file(self):
        """Injection should fail for non-existent file."""
        config = {
            "license_key": "TEST-KEY",
            "server_url": "https://api.test.com",
            "lease_enabled": False,
            "show_branding": True,
        }

        result = self.inject_js_wrapper(Path("/nonexistent/index.js"), config)
        assert result is False


# =============================================================================
# Compiler Dispatch Tests
# =============================================================================

@pytest.mark.integration
class TestCompilerDispatch:
    """Test run_compiler dispatches to correct backend."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import run_compiler
            self.run_compiler = run_compiler
        except ImportError:
            pytest.skip("compiler_logic not importable")

    @patch("compiler_logic.run_nuitka")
    def test_python_dispatches_to_nuitka(self, mock_nuitka, temp_project_dir):
        """Python language config should dispatch to run_nuitka."""
        mock_nuitka.return_value = True
        config = {"language": "python", "entry_file": "main.py"}

        self.run_compiler(temp_project_dir, config)
        mock_nuitka.assert_called_once()

    @patch("compiler_logic.run_pkg")
    def test_nodejs_dispatches_to_pkg(self, mock_pkg, temp_nodejs_project_dir):
        """Node.js language config should dispatch to run_pkg."""
        mock_pkg.return_value = (True, temp_nodejs_project_dir)
        config = {"language": "nodejs", "entry_file": "index.js"}

        self.run_compiler(temp_nodejs_project_dir, config)
        mock_pkg.assert_called_once()


# =============================================================================
# Heavy Dependency Detection Tests
# =============================================================================

@pytest.mark.integration
class TestHeavyDependencyDetection:
    """Test detection of heavy ML/data dependencies."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import detect_heavy_dependencies, detect_heavy_deps_detailed
            self.detect_heavy = detect_heavy_dependencies
            self.detect_detailed = detect_heavy_deps_detailed
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_detects_numpy_import(self):
        """Should detect numpy usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "main.py").write_text("import numpy as np\nx = np.array([1,2,3])")
            assert self.detect_heavy(p) is True

    def test_detects_pandas_import(self):
        """Should detect pandas usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "main.py").write_text("import pandas as pd\ndf = pd.DataFrame()")
            assert self.detect_heavy(p) is True

    def test_no_heavy_deps_returns_false(self):
        """Should return False for lightweight projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "main.py").write_text("print('hello world')")
            assert self.detect_heavy(p) is False

    def test_detailed_returns_specific_deps(self):
        """Detailed detection should return specific library names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "main.py").write_text("import numpy\nimport pandas\nfrom scipy import stats")
            result = self.detect_detailed(p)
            assert "numpy" in result
            assert "pandas" in result
            assert "scipy" in result


# =============================================================================
# Nuitka Progress Parsing Tests
# =============================================================================

@pytest.mark.integration
class TestNuitkaProgressParsing:
    """Test Nuitka output parsing for progress reporting."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import parse_nuitka_percent, parse_nuitka_phase
            self.parse_percent = parse_nuitka_percent
            self.parse_phase = parse_nuitka_phase
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_parses_percentage_from_output(self):
        """Should extract percentage from Nuitka output lines."""
        assert self.parse_percent("GGG:  15% [1500/10000]") == 15
        assert self.parse_percent("GGG:  100% [10000/10000]") == 100

    def test_returns_none_for_no_percentage(self):
        """Should return None for lines without percentage."""
        assert self.parse_percent("Nuitka: Starting compilation") is None
        assert self.parse_percent("") is None

    def test_parses_module_phase(self):
        """Should detect module optimization phase."""
        assert self.parse_phase("GGG: module optimization") == "modules"

    def test_parses_compile_phase(self):
        """Should detect C compilation phase."""
        assert self.parse_phase("SCons: Compiling C code") == "C code"

    def test_parses_link_phase(self):
        """Should detect linking phase."""
        assert self.parse_phase("Linking executable...") == "linking"

    def test_parses_onefile_phase(self):
        """Should detect onefile packaging phase."""
        assert self.parse_phase("Creating onefile archive...") == "packaging"
