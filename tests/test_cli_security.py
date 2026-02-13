"""
CLI Security Tests — Path Traversal and Input Validation.

Tests the compiler_logic.py security validators that prevent
path traversal, command injection, and malicious input.
"""

import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cli"))


# =============================================================================
# Path Traversal Prevention Tests
# =============================================================================

@pytest.mark.security
class TestPathTraversalPrevention:
    """Test validate_entry_file blocks all traversal attempts."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import (
                validate_entry_file,
                validate_output_name,
                validate_include_package,
                safe_resolve_path,
                PathTraversalError,
            )
            self.validate_entry_file = validate_entry_file
            self.validate_output_name = validate_output_name
            self.validate_include_package = validate_include_package
            self.safe_resolve_path = safe_resolve_path
            self.PathTraversalError = PathTraversalError
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_parent_directory_traversal_blocked(self, temp_project_dir):
        """../../../etc/passwd must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("../../../etc/passwd", temp_project_dir)

    def test_windows_traversal_blocked(self, temp_project_dir):
        """..\\..\\windows\\system32 must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("..\\..\\windows\\system32\\config\\sam", temp_project_dir)

    def test_url_encoded_traversal_blocked(self, temp_project_dir):
        """%2e%2e%2f patterns must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("%2e%2e%2fetc/passwd", temp_project_dir)

    def test_null_byte_injection_blocked(self, temp_project_dir):
        """Null byte injection must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("main.py%00.txt", temp_project_dir)

    def test_absolute_path_rejected(self, temp_project_dir):
        """Absolute paths must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("/etc/passwd", temp_project_dir)

    def test_empty_entry_file_rejected(self, temp_project_dir):
        """Empty entry file must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("", temp_project_dir)

    def test_valid_entry_file_accepted(self, temp_project_dir):
        """A valid relative entry file within project dir should work."""
        result = self.validate_entry_file("main.py", temp_project_dir)
        assert result.exists()
        assert str(result).startswith(str(temp_project_dir.resolve()))

    def test_utf8_overlong_encoding_blocked(self, temp_project_dir):
        """%c0%ae (UTF-8 overlong dot) must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("%c0%ae%c0%ae/etc/passwd", temp_project_dir)

    def test_double_slash_blocked(self, temp_project_dir):
        """Double slashes must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_entry_file("src//../../etc/passwd", temp_project_dir)


# =============================================================================
# Output Name Validation Tests
# =============================================================================

@pytest.mark.security
class TestOutputNameValidation:
    """Test validate_output_name sanitizes and validates output names."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import validate_output_name, PathTraversalError
            self.validate_output_name = validate_output_name
            self.PathTraversalError = PathTraversalError
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_valid_name_accepted(self):
        """Simple alphanumeric names should pass."""
        assert self.validate_output_name("myapp") == "myapp"

    def test_hyphens_and_dots_accepted(self):
        """Names with hyphens and dots should pass."""
        assert self.validate_output_name("my-app.v2") == "my-app.v2"

    def test_spaces_converted_to_underscores(self):
        """Spaces should be auto-sanitized to underscores."""
        assert self.validate_output_name("my app") == "my_app"

    def test_path_separators_stripped(self):
        """Forward/back slashes should be stripped."""
        result = self.validate_output_name("path/to/app")
        assert "/" not in result
        assert "\\" not in result

    def test_parent_traversal_in_name_blocked(self):
        """.. in output name must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_output_name("../evil")

    def test_empty_name_rejected(self):
        """Empty output name must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_output_name("")

    def test_null_byte_in_name_blocked(self):
        """Null bytes in output name must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_output_name("app\x00.exe")

    def test_very_long_name_rejected(self):
        """Names over 100 chars must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_output_name("a" * 101)

    def test_max_length_name_accepted(self):
        """Names at exactly 100 chars should pass."""
        result = self.validate_output_name("a" * 100)
        assert len(result) == 100


# =============================================================================
# Package Name Validation Tests
# =============================================================================

@pytest.mark.security
class TestIncludePackageValidation:
    """Test validate_include_package prevents injection."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import validate_include_package, PathTraversalError
            self.validate_include_package = validate_include_package
            self.PathTraversalError = PathTraversalError
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_valid_package_accepted(self):
        """Simple module names should pass."""
        assert self.validate_include_package("mypackage") == "mypackage"

    def test_dotted_package_accepted(self):
        """Dotted module names should pass."""
        assert self.validate_include_package("my.package.module") == "my.package.module"

    def test_path_separators_converted_to_dots(self):
        """Path separators should be converted to dots."""
        result = self.validate_include_package("my/package/module")
        assert result == "my.package.module"

    def test_double_dots_rejected(self):
        """.. in package name must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_include_package("my..evil")

    def test_pycache_skipped(self):
        """__pycache__ should return empty string."""
        assert self.validate_include_package("__pycache__") == ""

    def test_empty_returns_empty(self):
        """Empty string should return empty."""
        assert self.validate_include_package("") == ""

    def test_special_chars_rejected(self):
        """Special characters like ; should be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.validate_include_package("pkg; rm -rf /")


# =============================================================================
# Safe Path Resolution Tests
# =============================================================================

@pytest.mark.security
class TestSafeResolvePath:
    """Test safe_resolve_path prevents directory escape."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from compiler_logic import safe_resolve_path, PathTraversalError
            self.safe_resolve_path = safe_resolve_path
            self.PathTraversalError = PathTraversalError
        except ImportError:
            pytest.skip("compiler_logic not importable")

    def test_valid_relative_path_resolved(self, temp_project_dir):
        """Valid relative paths should resolve within base dir."""
        result = self.safe_resolve_path(temp_project_dir, "main.py")
        assert str(result).startswith(str(temp_project_dir.resolve()))

    def test_traversal_escape_blocked(self, temp_project_dir):
        """Paths that escape the base directory must be rejected."""
        with pytest.raises(self.PathTraversalError):
            self.safe_resolve_path(temp_project_dir, "../../../etc/passwd")

    def test_current_dir_reference_accepted(self, temp_project_dir):
        """'.' should resolve to base directory."""
        result = self.safe_resolve_path(temp_project_dir, ".")
        assert result == temp_project_dir.resolve()

    def test_empty_path_accepted(self, temp_project_dir):
        """Empty path should resolve to base directory."""
        result = self.safe_resolve_path(temp_project_dir, "")
        assert result == temp_project_dir.resolve()

    def test_nonexistent_base_rejected(self):
        """Non-existent base directory must raise."""
        with pytest.raises(self.PathTraversalError):
            self.safe_resolve_path(Path("/nonexistent/path"), "file.py")
