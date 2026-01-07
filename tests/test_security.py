"""
Security Tests for CodeVault.

This module contains comprehensive security tests including:
- Code injection prevention in wrapper generators
- Path traversal prevention in compilers
- SSRF prevention in webhook URLs
- SQL injection prevention
- Authentication and authorization tests
- Rate limiting tests
"""

import pytest
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cli"))


# =============================================================================
# Code Injection Tests (Wrapper Generators)
# =============================================================================

@pytest.mark.security
class TestCodeInjectionPrevention:
    """Test that code injection attacks are prevented in wrapper generators."""

    def test_python_generator_rejects_code_injection_in_license_key(self, code_injection_payloads):
        """Test Python generator rejects malicious license keys."""
        try:
            from generators.python_generator import validate_license_key, WrapperGenerationError
        except ImportError:
            pytest.skip("Python generator not found")

        for payload in code_injection_payloads:
            with pytest.raises(WrapperGenerationError):
                validate_license_key(payload)

    def test_python_generator_rejects_code_injection_in_server_url(self):
        """Test Python generator rejects malicious server URLs."""
        try:
            from generators.python_generator import validate_server_url, WrapperGenerationError
        except ImportError:
            pytest.skip("Python generator not found")

        malicious_urls = [
            "http://example.com'; import os; os.system('id'); #",
            "javascript:alert(1)",
            "file:///etc/passwd",
            "http://localhost\"; __import__('os').system('id') #",
        ]

        for url in malicious_urls:
            with pytest.raises(WrapperGenerationError):
                validate_server_url(url)

    def test_python_generator_accepts_valid_license_keys(self):
        """Test Python generator accepts valid license keys."""
        try:
            from generators.python_generator import validate_license_key
        except ImportError:
            pytest.skip("Python generator not found")

        valid_keys = [
            "CV-ABCD-1234-EFGH",
            "TEST-LICENSE-KEY-123",
            "simple_key_123",
            "KEY-WITH-DASHES",
        ]

        for key in valid_keys:
            result = validate_license_key(key)
            assert result == key

    def test_nodejs_generator_rejects_code_injection(self, code_injection_payloads):
        """Test Node.js generator rejects malicious inputs."""
        try:
            from generators.nodejs_generator import validate_license_key, WrapperGenerationError
        except ImportError:
            pytest.skip("Node.js generator not found")

        for payload in code_injection_payloads:
            with pytest.raises(WrapperGenerationError):
                validate_license_key(payload)


# =============================================================================
# Path Traversal Tests (Compiler)
# =============================================================================

@pytest.mark.security
class TestPathTraversalPrevention:
    """Test that path traversal attacks are prevented in compilers."""

    def test_entry_file_validation_rejects_traversal(self, temp_project_dir, path_traversal_payloads):
        """Test entry file validation rejects path traversal attempts."""
        try:
            from compiler_logic import validate_entry_file, PathTraversalError
        except ImportError:
            pytest.skip("Compiler logic not found")

        for payload in path_traversal_payloads:
            with pytest.raises(PathTraversalError):
                validate_entry_file(payload, temp_project_dir)

    def test_entry_file_validation_accepts_valid_paths(self, temp_project_dir):
        """Test entry file validation accepts valid relative paths."""
        try:
            from compiler_logic import validate_entry_file
        except ImportError:
            pytest.skip("Compiler logic not found")

        # Create nested file
        subdir = temp_project_dir / "src"
        subdir.mkdir()
        (subdir / "app.py").write_text("print('app')")

        valid_paths = [
            "main.py",
            "src/app.py",
        ]

        for path in valid_paths:
            result = validate_entry_file(path, temp_project_dir)
            assert result.exists() or str(temp_project_dir) in str(result)

    def test_output_name_validation_rejects_traversal(self):
        """Test output name validation rejects path traversal."""
        try:
            from compiler_logic import validate_output_name, PathTraversalError
        except ImportError:
            pytest.skip("Compiler logic not found")

        malicious_names = [
            "../malware",
            "..\\evil",
            "output/../../../hack",
            "test\x00.exe",
            "%2e%2e%2fhack",
        ]

        for name in malicious_names:
            with pytest.raises(PathTraversalError):
                validate_output_name(name)

    def test_output_name_validation_accepts_valid_names(self):
        """Test output name validation accepts valid names."""
        try:
            from compiler_logic import validate_output_name
        except ImportError:
            pytest.skip("Compiler logic not found")

        valid_names = [
            "my_app",
            "MyApp",
            "my-app",
            "app_v1.0",
            "TestApplication",
        ]

        for name in valid_names:
            result = validate_output_name(name)
            assert result == name

    def test_include_package_validation_rejects_injection(self):
        """Test include package validation rejects command injection."""
        try:
            from compiler_logic import validate_include_package, PathTraversalError
        except ImportError:
            pytest.skip("Compiler logic not found")

        malicious_packages = [
            "os; rm -rf /",
            "module/../../../etc",
            "$(whoami)",
            "`id`",
            "test\nmalicious",
        ]

        for pkg in malicious_packages:
            with pytest.raises(PathTraversalError):
                validate_include_package(pkg)


# =============================================================================
# SSRF Prevention Tests (Webhooks)
# =============================================================================

@pytest.mark.security
class TestSSRFPrevention:
    """Test that SSRF attacks are prevented in webhook URL validation."""

    def test_webhook_url_rejects_internal_addresses(self, ssrf_payloads):
        """Test webhook URL validation rejects internal/private addresses."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server", "routes"))
            from webhook_routes import validate_webhook_url
        except ImportError:
            pytest.skip("Webhook routes not found")

        for url in ssrf_payloads:
            is_valid, error_msg = validate_webhook_url(url)
            assert not is_valid, f"Should reject SSRF payload: {url}"

    def test_webhook_url_accepts_valid_external_urls(self):
        """Test webhook URL validation accepts valid external URLs."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server", "routes"))
            from webhook_routes import validate_webhook_url
        except ImportError:
            pytest.skip("Webhook routes not found")

        valid_urls = [
            "https://example.com/webhook",
            "https://api.github.com/hooks",
            "https://hooks.slack.com/services/123",
            "https://webhook.site/abc123",
        ]

        for url in valid_urls:
            is_valid, error_msg = validate_webhook_url(url)
            assert is_valid, f"Should accept valid URL: {url}, got error: {error_msg}"

    def test_webhook_url_rejects_non_http_schemes(self):
        """Test webhook URL validation rejects non-HTTP schemes."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server", "routes"))
            from webhook_routes import validate_webhook_url
        except ImportError:
            pytest.skip("Webhook routes not found")

        invalid_schemes = [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "gopher://evil.com/",
            "dict://localhost:11211/",
            "ldap://localhost/",
        ]

        for url in invalid_schemes:
            is_valid, error_msg = validate_webhook_url(url)
            assert not is_valid, f"Should reject non-HTTP scheme: {url}"


# =============================================================================
# Authentication Tests
# =============================================================================

@pytest.mark.security
class TestAuthentication:
    """Test authentication security."""

    def test_protected_endpoints_require_auth(self, client):
        """Test that protected endpoints return 401/403 without auth."""
        protected_endpoints = [
            ("GET", "/api/v1/projects"),
            ("GET", "/api/v1/licenses"),
            ("GET", "/api/v1/webhooks"),
            ("GET", "/api/v1/auth/me"),
            ("GET", "/api/v1/stats/dashboard"),
        ]

        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})

            assert response.status_code in [401, 403], \
                f"{endpoint} should require authentication"

    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected."""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code in [401, 403]

    def test_expired_token_rejected(self, client, mock_user):
        """Test that expired tokens are rejected."""
        try:
            import jwt
            from config import JWT_SECRET_KEY
            from datetime import datetime, timedelta

            # Create expired token
            payload = {
                "sub": mock_user["id"],
                "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
                "iat": datetime.utcnow() - timedelta(hours=2),
            }
            expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

            headers = {"Authorization": f"Bearer {expired_token}"}
            response = client.get("/api/v1/projects", headers=headers)
            assert response.status_code in [401, 403]
        except ImportError:
            pytest.skip("JWT or config not available")

    def test_admin_endpoints_require_admin_role(self, client, auth_headers):
        """Test that admin endpoints require admin role."""
        admin_endpoints = [
            "/api/v1/admin/stats",
            "/api/v1/admin/users",
        ]

        for endpoint in admin_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            # Should be 403 Forbidden (not 401 Unauthorized)
            assert response.status_code in [401, 403]


# =============================================================================
# Rate Limiting Tests
# =============================================================================

@pytest.mark.security
class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_login_rate_limit_exists(self):
        """Test that login endpoint has rate limiting configured."""
        try:
            from middleware.rate_limiter import login_rate_limit
            assert login_rate_limit is not None
            assert login_rate_limit.max_requests > 0
            assert login_rate_limit.window_seconds > 0
        except ImportError:
            pytest.skip("Rate limiter not found")

    def test_license_validate_rate_limit_exists(self):
        """Test that license validation has rate limiting configured."""
        try:
            from middleware.rate_limiter import license_validate_rate_limit
            assert license_validate_rate_limit is not None
        except ImportError:
            pytest.skip("Rate limiter not found")


# =============================================================================
# Input Validation Tests
# =============================================================================

@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization."""

    def test_project_name_sanitization(self, client, auth_headers):
        """Test that project names are properly validated."""
        malicious_names = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE projects; --",
            "../../../etc/passwd",
        ]

        for name in malicious_names:
            response = client.post(
                "/api/v1/projects",
                json={"name": name},
                headers=auth_headers
            )
            # Should either reject or sanitize - not blindly accept
            # 422 = validation error, 400 = bad request, 401/403 = auth error
            assert response.status_code in [400, 401, 403, 422]

    def test_email_validation(self, client):
        """Test that email addresses are validated."""
        invalid_emails = [
            "not-an-email",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
        ]

        for email in invalid_emails:
            response = client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "SecurePass123!", "name": "Test"}
            )
            # Should reject invalid email format
            assert response.status_code in [400, 422]


# =============================================================================
# Stripe Webhook Security Tests
# =============================================================================

@pytest.mark.security
class TestStripeWebhookSecurity:
    """Test Stripe webhook signature verification."""

    def test_webhook_rejects_missing_signature(self, client):
        """Test that webhooks without signature are rejected."""
        response = client.post(
            "/api/v1/stripe/webhook",
            content=b'{"type": "checkout.session.completed"}',
            headers={"Content-Type": "application/json"}
        )
        # Should reject - either 400 or 500 depending on config
        assert response.status_code in [400, 401, 403, 500]

    def test_webhook_rejects_invalid_signature(self, client):
        """Test that webhooks with invalid signature are rejected."""
        response = client.post(
            "/api/v1/stripe/webhook",
            content=b'{"type": "checkout.session.completed"}',
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1234567890,v1=invalid_signature_here"
            }
        )
        # Should reject invalid signature
        assert response.status_code in [400, 401, 403, 500]


# =============================================================================
# CLI Config Security Tests
# =============================================================================

@pytest.mark.security
class TestCLIConfigSecurity:
    """Test CLI configuration security."""

    def test_keyring_storage_preferred(self):
        """Test that keyring storage is preferred when available."""
        try:
            from cli_config import KEYRING_AVAILABLE, get_storage_info
            info = get_storage_info()

            if KEYRING_AVAILABLE:
                assert info["method"] == "keyring"
                assert info["secure"] is True
            else:
                assert info["method"] == "file"
                assert info["secure"] is False
        except ImportError:
            pytest.skip("CLI config not found")

    def test_token_expiry_check_works(self):
        """Test that token expiry checking works correctly."""
        try:
            from cli_config import check_token_expiry
            # Should not raise an error
            result = check_token_expiry()
            assert result is None or isinstance(result, dict)
        except ImportError:
            pytest.skip("CLI config not found")


# =============================================================================
# Server Utils Security Tests
# =============================================================================

@pytest.mark.security
class TestServerUtilsSecurity:
    """Test server utility security functions."""

    def test_safe_join_prevents_traversal(self, temp_project_dir, path_traversal_payloads):
        """Test safe_join prevents path traversal."""
        try:
            from utils import safe_join, SecurityError
        except ImportError:
            pytest.skip("Server utils not found")

        for payload in path_traversal_payloads:
            with pytest.raises(SecurityError):
                safe_join(temp_project_dir, payload)

    def test_sanitize_filename_removes_dangerous_chars(self):
        """Test filename sanitization removes dangerous characters."""
        try:
            from utils import sanitize_filename
        except ImportError:
            pytest.skip("Server utils not found")

        dangerous_filenames = [
            "../../../etc/passwd",
            "file\x00.txt",
            "file<script>.txt",
            "CON",  # Windows reserved
            "file:stream.txt",  # NTFS alternate stream
        ]

        for filename in dangerous_filenames:
            result = sanitize_filename(filename)
            # Should not contain path separators or null bytes
            assert ".." not in result
            assert "\x00" not in result
            assert "/" not in result
            assert "\\" not in result

    def test_log_sanitization_prevents_injection(self):
        """Test log message sanitization prevents log injection."""
        try:
            from utils import sanitize_log_message
        except ImportError:
            pytest.skip("Server utils not found")

        injection_attempts = [
            "normal message\nFake log entry",
            "message\r\n[CRITICAL] Fake alert",
            "message\x00hidden",
        ]

        for msg in injection_attempts:
            result = sanitize_log_message(msg)
            # Should not contain newlines or control characters
            assert "\n" not in result
            assert "\r" not in result
            assert "\x00" not in result

    def test_project_id_validation(self):
        """Test project ID validation rejects invalid formats."""
        try:
            from utils import validate_project_id, SecurityError
        except ImportError:
            pytest.skip("Server utils not found")

        invalid_ids = [
            "not-a-valid-id",
            "../../../etc/passwd",
            "'; DROP TABLE projects; --",
            "a" * 100,  # Too long
            "",  # Empty
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(SecurityError):
                validate_project_id(invalid_id)

    def test_project_id_validation_accepts_valid_ids(self):
        """Test project ID validation accepts valid hex IDs."""
        try:
            from utils import validate_project_id
            import secrets
        except ImportError:
            pytest.skip("Server utils not found")

        valid_ids = [
            secrets.token_hex(16),
            "a" * 32,
            "0123456789abcdef" * 2,
        ]

        for valid_id in valid_ids:
            result = validate_project_id(valid_id)
            assert result is True
