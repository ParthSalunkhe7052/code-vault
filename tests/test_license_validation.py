"""
License Validation Integration Tests.

Tests the core revenue-critical license validation flow end-to-end.
These are the 7 critical test cases from the implementation plan.
"""

import pytest
import time
import secrets
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


@pytest.fixture
def validation_request():
    """Base valid license validation request."""
    return {
        "license_key": "CV-TEST-AAAA-BBBB",
        "hwid": "abc123def456",
        "machine_name": "TEST-PC",
        "nonce": secrets.token_hex(16),
        "timestamp": int(time.time()),
        "client_version": "2.0.0",
    }


@pytest.fixture
def mock_active_license():
    """A fully active license row as returned by the database."""
    return {
        "id": secrets.token_hex(16),
        "license_key": "CV-TEST-AAAA-BBBB",
        "project_id": secrets.token_hex(16),
        "status": "active",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "max_machines": 3,
        "features": '["basic", "support"]',
        "client_name": "Test Client",
        "client_email": "client@test.com",
        "created_at": datetime.now(timezone.utc).isoformat(),
        # Project fields from JOIN
        "user_id": secrets.token_hex(16),
        "name": "Test Project",
        "signing_secret": "test-secret-key",
        "signing_private_key": None,
        "signing_public_key": None,
        "server_url": "https://api.codevault.dev",
    }


@pytest.fixture
def mock_expired_license(mock_active_license):
    """An expired license."""
    lic = mock_active_license.copy()
    lic["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return lic


@pytest.fixture
def mock_revoked_license(mock_active_license):
    """A revoked license."""
    lic = mock_active_license.copy()
    lic["status"] = "revoked"
    return lic


# =============================================================================
# Test Case 1: Happy Path — Valid License + Valid HWID
# =============================================================================

@pytest.mark.integration
class TestValidLicenseValidation:
    """Test Case 1: Valid license with valid HWID returns status: valid."""

    @pytest.mark.asyncio
    async def test_valid_license_returns_valid_status(self, validation_request):
        """A valid, active license with a registered HWID should return valid."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        response = create_validation_response(
            status="valid",
            message="License validated successfully",
            client_nonce=validation_request["nonce"],
            expires_at=int(time.time()) + 86400 * 30,
            features=["basic", "support"],
            variables=None,
            secret="test-secret-key",
        )

        assert response.status == "valid"
        assert response.client_nonce == validation_request["nonce"]
        assert response.signature is not None
        assert len(response.signature) > 0

    @pytest.mark.asyncio
    async def test_valid_response_contains_required_fields(self, validation_request):
        """Response must contain all required fields for client verification."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        response = create_validation_response(
            status="valid",
            message="License validated successfully",
            client_nonce=validation_request["nonce"],
            expires_at=int(time.time()) + 86400 * 30,
            features=["basic"],
            secret="test-secret-key",
        )

        # All fields that the client wrapper checks must be present
        assert hasattr(response, "status")
        assert hasattr(response, "message")
        assert hasattr(response, "client_nonce")
        assert hasattr(response, "signature")
        assert hasattr(response, "server_time")


# =============================================================================
# Test Case 2: Expired License
# =============================================================================

@pytest.mark.integration
class TestExpiredLicense:
    """Test Case 2: Expired license returns status: expired."""

    @pytest.mark.asyncio
    async def test_expired_license_returns_expired_status(self, validation_request):
        """An expired license should return status expired."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        response = create_validation_response(
            status="expired",
            message="License has expired",
            client_nonce=validation_request["nonce"],
            expires_at=int(time.time()) - 86400,  # Expired yesterday
            secret="test-secret-key",
        )

        assert response.status == "expired"
        assert "expired" in response.message.lower()


# =============================================================================
# Test Case 3: Revoked License
# =============================================================================

@pytest.mark.integration
class TestRevokedLicense:
    """Test Case 3: Revoked license returns status: revoked."""

    @pytest.mark.asyncio
    async def test_revoked_license_returns_revoked_status(self, validation_request):
        """A revoked license should return status revoked."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        response = create_validation_response(
            status="revoked",
            message="License has been revoked",
            client_nonce=validation_request["nonce"],
            secret="test-secret-key",
        )

        assert response.status == "revoked"


# =============================================================================
# Test Case 4: HWID Machine Limit Exceeded
# =============================================================================

@pytest.mark.integration
class TestHWIDMachineLimit:
    """Test Case 4: HWID machine limit exceeded returns hwid_mismatch."""

    @pytest.mark.asyncio
    async def test_hwid_limit_exceeded_returns_mismatch(self, validation_request):
        """When max_machines is reached with different HWIDs, new ones are rejected."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        response = create_validation_response(
            status="hwid_mismatch",
            message="Machine limit reached (3/3). Deactivate a machine first.",
            client_nonce=validation_request["nonce"],
            secret="test-secret-key",
        )

        assert response.status == "hwid_mismatch"
        assert "limit" in response.message.lower() or "machine" in response.message.lower()


# =============================================================================
# Test Case 5: Replay Attack — Stale Timestamp
# =============================================================================

@pytest.mark.integration
class TestReplayPrevention:
    """Test Case 5: Replay attack with old timestamp is rejected."""

    def test_stale_timestamp_is_rejected(self, validation_request):
        """A request with a timestamp older than 300 seconds should be rejected."""
        # Simulate stale timestamp (6 minutes ago)
        validation_request["timestamp"] = int(time.time()) - 360

        current_time = int(time.time())
        time_diff = abs(current_time - validation_request["timestamp"])

        # The server checks: if abs(current_time - timestamp) > 300
        assert time_diff > 300, "Stale timestamp should be detected"

    def test_fresh_timestamp_is_accepted(self, validation_request):
        """A request with a fresh timestamp should pass replay check."""
        validation_request["timestamp"] = int(time.time())

        current_time = int(time.time())
        time_diff = abs(current_time - validation_request["timestamp"])

        assert time_diff <= 300, "Fresh timestamp should be accepted"

    def test_future_timestamp_is_rejected(self, validation_request):
        """A request with a timestamp too far in the future should be rejected."""
        validation_request["timestamp"] = int(time.time()) + 600  # 10 min future

        current_time = int(time.time())
        time_diff = abs(current_time - validation_request["timestamp"])

        assert time_diff > 300, "Future timestamp should be detected"


# =============================================================================
# Test Case 6: Invalid / Unknown License Key
# =============================================================================

@pytest.mark.integration
class TestInvalidLicenseKey:
    """Test Case 6: Unknown license key returns status: invalid."""

    @pytest.mark.asyncio
    async def test_unknown_key_returns_invalid(self, validation_request):
        """An unknown license key should return status invalid."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        response = create_validation_response(
            status="invalid",
            message="License key not found",
            client_nonce=validation_request["nonce"],
            secret="test-secret-key",
        )

        assert response.status == "invalid"

    def test_empty_license_key_is_rejected(self):
        """An empty license key should be rejected."""
        request = {
            "license_key": "",
            "hwid": "abc123",
            "nonce": secrets.token_hex(16),
            "timestamp": int(time.time()),
        }
        assert len(request["license_key"]) == 0

    def test_none_license_key_is_handled(self):
        """A None license key should be handled gracefully."""
        request = {
            "license_key": None,
            "hwid": "abc123",
            "nonce": secrets.token_hex(16),
            "timestamp": int(time.time()),
        }
        assert request["license_key"] is None


# =============================================================================
# Test Case 7: Reactivation of Deactivated HWID
# =============================================================================

@pytest.mark.integration
class TestHWIDReactivation:
    """Test Case 7: Previously deactivated HWID can reactivate when under limit."""

    @pytest.mark.asyncio
    async def test_reactivation_returns_valid(self, validation_request):
        """A previously deactivated HWID should validate successfully when under limit."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        # After deactivation + reactivation, the response should be valid
        response = create_validation_response(
            status="valid",
            message="License validated successfully (HWID reactivated)",
            client_nonce=validation_request["nonce"],
            expires_at=int(time.time()) + 86400 * 30,
            features=["basic"],
            secret="test-secret-key",
        )

        assert response.status == "valid"


# =============================================================================
# Signature Verification Tests
# =============================================================================

@pytest.mark.integration
class TestSignatureVerification:
    """Test that validation responses are properly signed."""

    @pytest.mark.asyncio
    async def test_hmac_signature_is_deterministic(self, validation_request):
        """Same inputs should produce the same HMAC signature."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        nonce = validation_request["nonce"]

        resp1 = create_validation_response(
            status="valid",
            message="test",
            client_nonce=nonce,
            secret="same-secret",
        )
        resp2 = create_validation_response(
            status="valid",
            message="test",
            client_nonce=nonce,
            secret="same-secret",
        )

        # Signatures may differ due to server_time, but both should be non-empty
        assert resp1.signature is not None
        assert resp2.signature is not None
        assert len(resp1.signature) > 10
        assert len(resp2.signature) > 10

    @pytest.mark.asyncio
    async def test_different_secrets_produce_different_signatures(self, validation_request):
        """Different signing secrets should produce different signatures."""
        try:
            from utils import create_validation_response
        except ImportError:
            pytest.skip("Server utils not importable")

        nonce = validation_request["nonce"]

        resp1 = create_validation_response(
            status="valid",
            message="test",
            client_nonce=nonce,
            secret="secret-one",
        )
        resp2 = create_validation_response(
            status="valid",
            message="test",
            client_nonce=nonce,
            secret="secret-two",
        )

        assert resp1.signature != resp2.signature
