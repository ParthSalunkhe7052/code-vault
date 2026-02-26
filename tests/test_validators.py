"""Tests for validators module."""

import pytest
from cli.validators import (
    ValidationError,
    validate_license_key,
    validate_server_url,
    validate_target_filename,
    validate_output_name,
    validate_include_package,
    validate_boolean,
    validate_string_not_empty,
    escape_for_python_string,
    escape_for_js_string,
)


class TestValidateLicenseKey:
    """Tests for validate_license_key function."""

    def test_valid_license_key(self):
        """Test valid license keys are accepted."""
        assert (
            validate_license_key("LIC-ABCD-1234-EFGH-5678") == "LIC-ABCD-1234-EFGH-5678"
        )
        assert validate_license_key("TEST_KEY") == "TEST_KEY"
        assert validate_license_key("abc123") == "abc123"

    def test_license_key_strips_whitespace(self):
        """Test that whitespace is stripped from license keys."""
        assert validate_license_key("  LIC-1234  ") == "LIC-1234"

    def test_empty_license_key_raises_error(self):
        """Test that empty license key raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_license_key("")

    def test_empty_after_strip_raises_error(self):
        """Test that whitespace-only license key raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_license_key("   ")

    def test_license_key_with_special_chars_raises_error(self):
        """Test that special characters raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid license key format"):
            validate_license_key("LIC-1234;echo")
        with pytest.raises(ValidationError, match="Invalid license key format"):
            validate_license_key("LIC-1234'OR'1'='1")

    def test_license_key_too_short(self):
        """Test that license keys shorter than 3 chars raise error."""
        with pytest.raises(ValidationError, match="must be between 3 and 100"):
            validate_license_key("ab")

    def test_license_key_too_long(self):
        """Test that license keys longer than 100 chars raise error."""
        with pytest.raises(ValidationError, match="must be between 3 and 100"):
            validate_license_key("A" * 101)


class TestValidateServerUrl:
    """Tests for validate_server_url function."""

    def test_valid_http_url(self):
        """Test valid HTTP URLs are accepted."""
        assert validate_server_url("http://localhost:8000") == "http://localhost:8000"
        assert validate_server_url("http://example.com") == "http://example.com"

    def test_valid_https_url(self):
        """Test valid HTTPS URLs are accepted."""
        assert (
            validate_server_url("https://api.codevault.app")
            == "https://api.codevault.app"
        )
        assert (
            validate_server_url("https://example.com:443") == "https://example.com:443"
        )

    def test_url_strips_whitespace(self):
        """Test that whitespace is stripped from URLs."""
        assert validate_server_url("  http://example.com  ") == "http://example.com"

    def test_empty_url_raises_error(self):
        """Test that empty URL raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_server_url("")

    def test_invalid_protocol_raises_error(self):
        """Test that non-http/https protocols raise error."""
        with pytest.raises(ValidationError, match="must use http:// or https://"):
            validate_server_url("ftp://example.com")

    def test_url_with_credentials_raises_error(self):
        """Test that URLs with embedded credentials raise error."""
        with pytest.raises(
            ValidationError, match="must not contain embedded credentials"
        ):
            validate_server_url("http://user:pass@example.com")  # pragma: allowlist secret

    def test_url_with_invalid_chars_raises_error(self):
        """Test that URLs with invalid characters raise error."""
        with pytest.raises(ValidationError, match="contains invalid character"):
            validate_server_url("http://example.com'")
        with pytest.raises(ValidationError, match="contains invalid character"):
            validate_server_url("http://ex\nample.com")


class TestValidateTargetFilename:
    """Tests for validate_target_filename function."""

    def test_valid_filename(self):
        """Test valid filenames are accepted."""
        assert validate_target_filename("app.js") == "app.js"
        assert validate_target_filename("my_script.py") == "my_script.py"

    def test_filename_with_path_traversal_raises_error(self):
        """Test that path traversal attempts raise error."""
        with pytest.raises(ValidationError, match="path traversal not allowed"):
            validate_target_filename("../etc/passwd")
        with pytest.raises(ValidationError, match="path traversal not allowed"):
            validate_target_filename("/absolute/path")

    def test_filename_with_special_chars_raises_error(self):
        """Test that special characters raise error."""
        with pytest.raises(ValidationError, match="contains invalid character"):
            validate_target_filename("app.js'rm -rf")
        with pytest.raises(ValidationError, match="contains invalid character"):
            validate_target_filename("app.js$HOME")


class TestValidateOutputName:
    """Tests for validate_output_name function."""

    def test_valid_output_name(self):
        """Test valid output names are accepted."""
        assert validate_output_name("my-app") == "my-app"
        assert validate_output_name("app.exe") == "app.exe"

    def test_spaces_replaced_with_underscores(self):
        """Test that spaces are replaced with underscores."""
        assert validate_output_name("my app") == "my_app"

    def test_path_separators_removed(self):
        """Test that path separators are removed."""
        assert validate_output_name("app/name") == "appname"

    def test_leading_alphanumeric_required(self):
        """Test that output name must start with alphanumeric."""
        with pytest.raises(ValidationError, match="must start with alphanumeric"):
            validate_output_name("-hidden")


class TestValidateBoolean:
    """Tests for validate_boolean function."""

    def test_boolean_values(self):
        """Test boolean values are returned as-is."""
        assert validate_boolean(True) is True
        assert validate_boolean(False) is False

    def test_string_values(self):
        """Test string boolean values are converted."""
        assert validate_boolean("true") is True
        assert validate_boolean("false") is False
        assert validate_boolean("yes") is True
        assert validate_boolean("no") is False

    def test_numeric_values(self):
        """Test numeric boolean values are converted."""
        assert validate_boolean(1) is True
        assert validate_boolean(0) is False


class TestEscapeFunctions:
    """Tests for escape functions."""

    def test_escape_for_python_string(self):
        """Test Python string escaping."""
        result = escape_for_python_string('hello"world')
        assert '"' in result or '\\"' in result

    def test_escape_for_js_string(self):
        """Test JavaScript string escaping."""
        result = escape_for_js_string('hello"world')
        assert '"' in result or '\\"' in result
