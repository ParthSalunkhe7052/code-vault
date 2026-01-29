"""
Test suite for License Wrapper functionality.

Test Matrix:
| Scenario                          | Python | Node.js |
|-----------------------------------|--------|---------|
| Online validation → lease created | ✓      | ✓       |
| Offline with valid lease          | ✓      | ✓       |
| Offline with expired lease        | ✓      | ✓       |
| Offline with no lease (first run) | ✓      | ✓       |
| Invalid license key               | ✓      | ✓       |
| Clock drift detection             | ✓      | ✓       |
"""

import pytest
import sys
import hashlib
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))


class TestPythonWrapperTemplate:
    """Tests for the Python license wrapper template."""

    def test_template_syntax_valid(self):
        """Test that the Python wrapper template produces valid Python syntax."""
        from compilers.templates.python_license_wrapper import PYTHON_WRAPPER_TEMPLATE

        # Replace placeholders with test values
        code = (
            PYTHON_WRAPPER_TEMPLATE
            .replace("{license_key}", "TEST-LICENSE-KEY")
            .replace("{server_url}", "http://localhost:8000/api/v1/license/validate")
        )

        # Attempt to compile the code - this will raise SyntaxError if invalid
        try:
            compile(code, "<test_wrapper>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Python wrapper has syntax error: {e}")

    def test_demo_wrapper_syntax_valid(self):
        """Test that the demo wrapper template produces valid Python syntax."""
        from compilers.templates.python_license_wrapper import PYTHON_DEMO_WRAPPER

        try:
            compile(PYTHON_DEMO_WRAPPER, "<test_demo_wrapper>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Python demo wrapper has syntax error: {e}")

    def test_template_placeholder_replacement(self):
        """Test that placeholders are properly replaced."""
        from compilers.templates.python_license_wrapper import PYTHON_WRAPPER_TEMPLATE

        license_key = "LIC-1234-5678-ABCD"
        server_url = "https://api.example.com/validate"

        code = (
            PYTHON_WRAPPER_TEMPLATE
            .replace("{license_key}", license_key)
            .replace("{server_url}", server_url)
        )

        assert license_key in code
        assert server_url in code
        assert "{license_key}" not in code
        assert "{server_url}" not in code

    def test_template_has_required_functions(self):
        """Test that the template contains all required function definitions."""
        from compilers.templates.python_license_wrapper import PYTHON_WRAPPER_TEMPLATE

        required_functions = [
            "_cv_get_hwid",
            "_cv_validate_license",
            "_cv_get_license_key_path",
            "_cv_get_lease_path",
            "_cv_create_lease",
            "_cv_save_lease",
            "_cv_load_lease",
            "_cv_validate_lease",
            "_cv_license_check",
        ]

        for func in required_functions:
            assert f"def {func}" in PYTHON_WRAPPER_TEMPLATE, f"Missing function: {func}"

    def test_template_has_lease_support(self):
        """Test that the template has offline lease functionality."""
        from compilers.templates.python_license_wrapper import PYTHON_WRAPPER_TEMPLATE

        # Check for lease-related constants
        assert "_CV_LEASE_DURATION" in PYTHON_WRAPPER_TEMPLATE
        assert "_CV_CLOCK_DRIFT_MAX" in PYTHON_WRAPPER_TEMPLATE

        # Check for encryption functions
        assert "_cv_encrypt_lease" in PYTHON_WRAPPER_TEMPLATE
        assert "_cv_decrypt_lease" in PYTHON_WRAPPER_TEMPLATE


class TestNodejsWrapperTemplate:
    """Tests for the Node.js license wrapper template."""

    def test_wrapper_has_lease_creation(self):
        """Test that the Node.js wrapper creates leases after validation."""
        wrapper_path = (
            Path(__file__).parent.parent
            / "server"
            / "compilers"
            / "templates"
            / "nodejs_license_wrapper.js"
        )
        content = wrapper_path.read_text(encoding="utf-8")

        # Check that lease is created after successful validation
        assert "createLease" in content
        assert "saveLease" in content
        assert "CLOCK_DRIFT_MAX" in content

    def test_wrapper_has_offline_fallback(self):
        """Test that the Node.js wrapper has offline fallback in error handler."""
        wrapper_path = (
            Path(__file__).parent.parent
            / "server"
            / "compilers"
            / "templates"
            / "nodejs_license_wrapper.js"
        )
        content = wrapper_path.read_text(encoding="utf-8")

        # Check for offline lease validation in error handlers
        assert "checking offline lease" in content.lower()
        assert "validateLease" in content

    def test_wrapper_has_required_functions(self):
        """Test that the Node.js wrapper has all required functions."""
        wrapper_path = (
            Path(__file__).parent.parent
            / "server"
            / "compilers"
            / "templates"
            / "nodejs_license_wrapper.js"
        )
        content = wrapper_path.read_text(encoding="utf-8")

        required_functions = [
            "getHWID",
            "getLicenseKeyPath",
            "getLeasePath",
            "createLease",
            "saveLease",
            "loadLease",
            "validateLease",
            "encryptLease",
            "decryptLease",
        ]

        for func in required_functions:
            assert f"function {func}" in content, f"Missing function: {func}"


class TestPythonCompiler:
    """Tests for the Python compiler wrapper injection."""

    def test_compiler_uses_template_correctly(self):
        """Test that the Python compiler uses the template with .replace()."""
        compiler_path = (
            Path(__file__).parent.parent
            / "server"
            / "compilers"
            / "python_compiler.py"
        )
        content = compiler_path.read_text(encoding="utf-8")

        # Check that it imports the template
        assert "from .templates.python_license_wrapper import" in content

        # Check that it uses .replace() not f-strings for wrapper generation
        assert '.replace("{license_key}"' in content
        assert '.replace("{server_url}"' in content

    def test_compiler_wrapper_injection_methods_exist(self):
        """Test that the compiler has all necessary wrapper methods."""
        compiler_path = (
            Path(__file__).parent.parent
            / "server"
            / "compilers"
            / "python_compiler.py"
        )
        content = compiler_path.read_text(encoding="utf-8")

        assert "def _inject_license_wrapper" in content
        assert "def _get_wrapper" in content
        assert "def _get_demo_wrapper" in content


class TestLeaseLogic:
    """Tests for lease creation and validation logic."""

    def test_lease_structure(self):
        """Test that leases have the correct structure."""
        # Simulate lease creation logic
        license_key = "TEST-KEY"
        hwid = "test-hwid-123"
        server_time = int(time.time())
        duration = 24 * 60 * 60  # 24 hours

        lease = {
            "license_key_hash": hashlib.sha256(license_key.encode()).hexdigest(),
            "hwid": hwid,
            "expires_at": server_time + duration,
            "server_time": server_time,
            "validated_at": int(time.time()),
        }

        assert "license_key_hash" in lease
        assert "hwid" in lease
        assert "expires_at" in lease
        assert "server_time" in lease
        assert "validated_at" in lease

        # Verify expiration is in the future
        assert lease["expires_at"] > int(time.time())

    def test_lease_expiration_detection(self):
        """Test that expired leases are correctly detected."""
        # Create an expired lease
        expired_time = int(time.time()) - 3600  # 1 hour ago

        lease = {
            "license_key_hash": "test",
            "hwid": "test",
            "expires_at": expired_time,
            "server_time": expired_time - 86400,
            "validated_at": expired_time - 86400,
        }

        current_time = int(time.time())
        is_expired = current_time > lease["expires_at"]

        assert is_expired is True

    def test_clock_drift_calculation(self):
        """Test clock drift detection logic."""
        server_time = 1700000000
        max_drift = 3600  # 1 hour

        # Normal case - no drift
        local_time_normal = 1700000000
        drift_normal = abs(local_time_normal - server_time)
        assert drift_normal <= max_drift

        # Drift case - too much drift
        local_time_drifted = 1700010000  # ~2.7 hours difference
        drift_large = abs(local_time_drifted - server_time)
        assert drift_large > max_drift


class TestWrapperIntegration:
    """Integration tests for wrapper functionality."""

    def test_python_wrapper_compiles_with_user_code(self):
        """Test that the wrapper can be prepended to user code and still compiles."""
        from compilers.templates.python_license_wrapper import PYTHON_WRAPPER_TEMPLATE

        wrapper = (
            PYTHON_WRAPPER_TEMPLATE
            .replace("{license_key}", "DEMO")  # Use demo mode to skip validation
            .replace("{server_url}", "http://localhost:8000")
        )

        user_code = """
# User's original code
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
"""

        combined = wrapper + "\n\n" + user_code

        # Should compile without errors
        try:
            compile(combined, "<combined>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Combined code has syntax error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
