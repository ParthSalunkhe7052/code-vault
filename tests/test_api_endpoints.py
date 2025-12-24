"""
API Endpoint Tests for CodeVault.
Tests health check, authentication, and basic API functionality.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


class TestHealthEndpoints:
    """Test health check and basic endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client."""
        try:
            from main import app
            self.client = TestClient(app)
        except ImportError:
            pytest.skip("Could not import main app - server may not be configured")

    def test_health_check(self):
        """Test the /health endpoint returns OK."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"

    def test_root_endpoint(self):
        """Test the root / endpoint returns welcome message."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "CodeVault" in data.get("message", "")

    def test_api_health(self):
        """Test the /api/v1/health endpoint."""
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client."""
        try:
            from main import app
            self.client = TestClient(app)
        except ImportError:
            pytest.skip("Could not import main app")

    def test_login_missing_credentials(self):
        """Test login fails without credentials."""
        response = self.client.post("/api/v1/auth/login", json={})
        # Should return 422 (validation error) or 401
        assert response.status_code in [401, 422]

    def test_login_invalid_credentials(self):
        """Test login fails with invalid credentials."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "fake@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_without_auth(self):
        """Test protected endpoints return 401 without token."""
        response = self.client.get("/api/v1/projects")
        assert response.status_code in [401, 403]

    def test_me_endpoint_without_auth(self):
        """Test /auth/me returns 401 without authentication."""
        response = self.client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]


class TestLicenseValidation:
    """Test license validation endpoint (public API)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client."""
        try:
            from main import app
            self.client = TestClient(app)
        except ImportError:
            pytest.skip("Could not import main app")

    def test_validate_missing_key(self):
        """Test validation fails without license key."""
        response = self.client.post(
            "/api/v1/license/validate",
            json={"hwid": "test-hwid"}
        )
        # Should return 422 (missing required field) or 400
        assert response.status_code in [400, 422]

    def test_validate_invalid_key(self):
        """Test validation fails with invalid license key."""
        response = self.client.post(
            "/api/v1/license/validate",
            json={
                "license_key": "FAKE-LICENSE-KEY-1234",
                "hwid": "test-hwid-12345"
            }
        )
        # Should return 404 (license not found) or 401/403
        assert response.status_code in [401, 403, 404]


class TestBuildEndpoints:
    """Test build/compilation endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client."""
        try:
            from main import app
            self.client = TestClient(app)
        except ImportError:
            pytest.skip("Could not import main app")

    def test_build_prerequisites_endpoint(self):
        """Test prerequisites check endpoint exists."""
        response = self.client.get("/api/v1/build/prerequisites")
        # Should return 200 with prerequisite status
        assert response.status_code == 200
        data = response.json()
        assert "python" in data or "prerequisites" in str(data).lower()
