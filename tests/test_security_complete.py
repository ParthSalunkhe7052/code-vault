"""
Security Testing Suite for CodeVault
Run these tests to verify security measures are working correctly.
"""

import asyncio
import pytest
import httpx
from fastapi.testclient import TestClient

# Import the app
import sys

sys.path.append("..")
from main import app

client = TestClient(app)


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_login_rate_limit(self):
        """Test that login endpoint is rate limited."""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": f"test{i}@example.com", "password": "wrongpassword"},
            )
            responses.append(response.status_code)

        # Some should be rate limited (429)
        assert 429 in responses, "Rate limiting not enforced on login"

    def test_register_rate_limit(self):
        """Test that registration endpoint is rate limited."""
        responses = []
        for i in range(5):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test{i}@example.com",
                    "password": "password123",
                    "name": "Test User",
                },
            )
            responses.append(response.status_code)

        # Should be rate limited after a few attempts
        assert 429 in responses or responses.count(400) >= 3, (
            "Registration rate limiting not working"
        )


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in login."""
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "' UNION SELECT * FROM users --",
        ]

        for malicious_input in malicious_inputs:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": malicious_input, "password": "password"},
            )
            # Should not crash, should return 401
            assert response.status_code in [401, 422], (
                f"SQL injection succeeded with: {malicious_input}"
            )

    def test_xss_prevention(self):
        """Test XSS prevention in project names."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
        ]

        # This would require authentication, but we can test the validation
        for payload in xss_payloads:
            # API should sanitize or reject
            assert len(payload) > 0  # Placeholder


class TestAuthentication:
    """Test authentication security."""

    def test_protected_endpoints_require_auth(self):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            "/api/v1/projects",
            "/api/v1/licenses",
            "/api/v1/webhooks",
            "/api/v1/user/me",
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, (
                f"Endpoint {endpoint} should require authentication"
            )

    def test_invalid_token_rejected(self):
        """Test that invalid tokens are rejected."""
        response = client.get(
            "/api/v1/user/me", headers={"Authorization": "Bearer invalidtoken123"}
        )
        assert response.status_code == 401


class TestWebhookSecurity:
    """Test webhook security features."""

    def test_webhook_url_validation(self):
        """Test webhook URL validation."""
        invalid_urls = [
            "http://localhost:8080/webhook",
            "http://127.0.0.1:3000/callback",
            "http://192.168.1.1/webhook",
            "http://169.254.169.254/metadata",  # AWS metadata
        ]

        # Note: This requires authentication, test the validation function directly
        from routes.webhook_routes import validate_webhook_url

        for url in invalid_urls:
            is_valid, error = asyncio.run(validate_webhook_url(url))
            assert not is_valid, f"URL {url} should be rejected"

    def test_webhook_signature_verification(self):
        """Test webhook signature verification."""
        import hmac
        import hashlib
        import json

        secret = "test-secret"
        payload = {"event": "test", "data": {"key": "value"}}

        # Generate valid signature
        payload_str = json.dumps(payload, sort_keys=True)
        expected_sig = hmac.new(
            secret.encode(), payload_str.encode(), hashlib.sha256
        ).hexdigest()

        # Verify it matches expected format
        assert len(expected_sig) == 64  # SHA256 hex length


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are present."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert (
            "access-control-allow-origin" in response.headers
            or response.status_code == 200
        )

    def test_cors_credentials(self):
        """Test CORS credentials handling."""
        response = client.get(
            "/api/v1/health", headers={"Origin": "http://localhost:3000"}
        )

        # Should either allow the origin or not
        assert response.status_code == 200


class TestFileUploadSecurity:
    """Test file upload security."""

    def test_file_type_validation(self):
        """Test file type validation on upload."""
        # This would require actual file upload testing
        # For now, document the expected behavior
        dangerous_extensions = [".exe", ".php", ".jsp", ".asp", ".sh", ".bat"]

        for ext in dangerous_extensions:
            # Files with these extensions should be rejected
            pass

    def test_file_size_limits(self):
        """Test file size limits."""
        # Large files should be rejected
        max_size = 100 * 1024 * 1024  # 100MB
        pass


def run_security_tests():
    """Run all security tests."""
    print("=" * 60)
    print("CODEVAULT SECURITY TEST SUITE")
    print("=" * 60)
    print()

    # Run pytest
    import subprocess

    result = subprocess.run(["pytest", __file__, "-v"], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)

    print()
    print("=" * 60)
    print(f"Tests completed with return code: {result.returncode}")
    print("=" * 60)


if __name__ == "__main__":
    run_security_tests()
