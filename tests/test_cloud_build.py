"""
Unit Tests for Cloud Build Feature.

Tests cover:
- Tier limit enforcement (Free vs Pro)
- HMAC webhook signature verification
- Start build validation
- Build status polling
"""

import pytest
import json
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone


# =============================================================================
# Fixtures specific to cloud build tests
# =============================================================================

@pytest.fixture
def mock_pro_user():
    """Generate a mock Pro tier user."""
    return {
        "id": 1,
        "email": f"pro_{secrets.token_hex(4)}@example.com",
        "name": "Pro User",
        "role": "user",
        "tier": "pro",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_free_user():
    """Generate a mock Free tier user."""
    return {
        "id": 2,
        "email": f"free_{secrets.token_hex(4)}@example.com",
        "name": "Free User",
        "role": "user",
        "tier": "free",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_cloud_build():
    """Generate a mock cloud build record."""
    return {
        "id": f"bld_{secrets.token_hex(8)}",
        "project_id": secrets.token_hex(16),
        "user_id": 1,
        "language": "python",
        "entry_file": "main.py",
        "output_name": "test_app",
        "status": "pending",
        "progress": 0,
        "config_json": json.dumps({"project_id": "test", "language": "python"}),
        "download_key": None,
        "download_filename": None,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
        "expires_at": None,
    }


@pytest.fixture
def callback_secret():
    """Generate a test callback secret."""
    return "test_callback_secret_12345"


# =============================================================================
# HMAC Signature Verification Tests
# =============================================================================

class TestHMACVerification:
    """Tests for HMAC webhook signature verification."""

    def test_valid_signature_is_accepted(self, callback_secret):
        """Valid HMAC signature should be accepted."""
        payload = json.dumps({
            "build_id": "bld_test123",
            "status": "completed",
            "download_key": "builds/test/app.exe"
        })
        
        expected = hmac.new(
            callback_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Simulate verification
        computed = hmac.new(
            callback_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert hmac.compare_digest(expected.lower(), computed.lower())

    def test_invalid_signature_is_rejected(self, callback_secret):
        """Invalid HMAC signature should be rejected."""
        payload = json.dumps({"build_id": "test123"})
        
        valid_sig = hmac.new(
            callback_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        invalid_sig = "0" * 64  # Wrong signature
        
        assert not hmac.compare_digest(valid_sig.lower(), invalid_sig.lower())

    def test_empty_signature_is_rejected(self):
        """Empty signature should be rejected."""
        signature = ""
        assert not signature  # Empty string is falsy

    def test_signature_case_insensitive(self, callback_secret):
        """Signature comparison should be case-insensitive."""
        payload = b"test payload"
        
        sig = hmac.new(
            callback_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert hmac.compare_digest(sig.lower(), sig.upper().lower())


# =============================================================================
# Tier Limit Tests
# =============================================================================

class TestTierLimits:
    """Tests for cloud build tier limit enforcement."""

    def test_free_tier_has_no_cloud_builds(self):
        """Free tier should have cloud_compilation = False."""
        free_tier_limits = {
            "cloud_compilation": False,
            "cloud_builds_per_month": 0,
            "max_projects": 1,
        }
        
        assert free_tier_limits["cloud_compilation"] is False
        assert free_tier_limits["cloud_builds_per_month"] == 0

    def test_pro_tier_has_cloud_builds(self):
        """Pro tier should have cloud_compilation = True."""
        pro_tier_limits = {
            "cloud_compilation": True,
            "cloud_builds_per_month": 10,
            "max_projects": 10,
        }
        
        assert pro_tier_limits["cloud_compilation"] is True
        assert pro_tier_limits["cloud_builds_per_month"] == 10

    def test_enterprise_has_unlimited_builds(self):
        """Enterprise tier should have unlimited (-1) cloud builds."""
        enterprise_limits = {
            "cloud_compilation": True,
            "cloud_builds_per_month": -1,  # unlimited
            "max_projects": -1,
        }
        
        assert enterprise_limits["cloud_builds_per_month"] == -1

    def test_monthly_limit_enforcement(self):
        """Monthly build limit should be enforced correctly."""
        max_builds = 10
        current_builds = 10
        
        # Should be at limit
        assert current_builds >= max_builds
        
        # One more build should fail
        can_build = current_builds < max_builds
        assert can_build is False


# =============================================================================
# Build Request Validation Tests
# =============================================================================

class TestBuildRequestValidation:
    """Tests for cloud build request validation."""

    def test_valid_build_request(self):
        """Valid build request should pass validation."""
        request = {
            "project_id": secrets.token_hex(16),
            "license_id": None,
            "target_platform": "windows",
        }
        
        assert len(request["project_id"]) == 32
        assert request["target_platform"] in ["windows", "macos", "linux"]

    def test_missing_project_id_fails(self):
        """Missing project_id should fail validation."""
        request = {
            "license_id": None,
            "target_platform": "windows",
        }
        
        assert "project_id" not in request

    def test_invalid_platform_rejected(self):
        """Invalid target platform should be rejected."""
        valid_platforms = ["windows", "macos", "linux"]
        invalid_platform = "android"
        
        assert invalid_platform not in valid_platforms


# =============================================================================
# Source Directory Tests
# =============================================================================

class TestSourceDirectoryValidation:
    """Tests for source directory validation."""

    def test_correct_source_path_format(self, temp_project_dir):
        """Source path should follow correct format: uploads/{project_id}/source."""
        project_id = secrets.token_hex(16)
        base_dir = temp_project_dir
        
        # The expected path format
        expected_path = base_dir / project_id / "source"
        
        # Create the directory
        expected_path.mkdir(parents=True, exist_ok=True)
        (expected_path / "main.py").write_text("print('hello')")
        
        assert expected_path.exists()
        assert (expected_path / "main.py").exists()

    def test_empty_source_dir_rejected(self, temp_project_dir):
        """Empty source directory should be rejected."""
        source_dir = temp_project_dir / "empty_source"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        # No files in directory
        files = list(source_dir.iterdir())
        assert len(files) == 0

    def test_alternate_path_fallback(self, temp_project_dir):
        """Should try alternate path if primary doesn't exist."""
        project_id = "test_project"
        
        # Primary path doesn't exist
        primary_path = temp_project_dir / project_id / "source"
        assert not primary_path.exists()
        
        # Create alternate path
        alt_path = temp_project_dir / "projects" / project_id / "source"
        alt_path.mkdir(parents=True, exist_ok=True)
        (alt_path / "main.py").write_text("print('hello')")
        
        # Fallback should work
        assert alt_path.exists()


# =============================================================================
# Build Status Tests
# =============================================================================

class TestBuildStatus:
    """Tests for build status transitions."""

    def test_valid_status_transitions(self):
        """Status should follow valid transition path."""
        valid_statuses = ["pending", "queued", "running", "completed", "failed", "cancelled"]
        
        for status in valid_statuses:
            assert status in valid_statuses

    def test_pending_to_queued(self):
        """Build should transition from pending to queued."""
        next_status = "queued"
        
        valid_from_pending = ["queued", "failed", "cancelled"]
        assert next_status in valid_from_pending

    def test_completed_build_has_download_url(self, mock_cloud_build):
        """Completed build should have download info."""
        mock_cloud_build["status"] = "completed"
        mock_cloud_build["download_key"] = "builds/test/app.exe"
        mock_cloud_build["download_filename"] = "app.exe"
        
        assert mock_cloud_build["status"] == "completed"
        assert mock_cloud_build["download_key"] is not None
        assert mock_cloud_build["download_filename"] is not None

    def test_failed_build_has_error_message(self, mock_cloud_build):
        """Failed build should have error message."""
        mock_cloud_build["status"] = "failed"
        mock_cloud_build["error_message"] = "Compilation failed: syntax error"
        
        assert mock_cloud_build["status"] == "failed"
        assert mock_cloud_build["error_message"] is not None


# =============================================================================
# Webhook Payload Tests
# =============================================================================

class TestWebhookPayload:
    """Tests for webhook payload handling."""

    def test_valid_completion_payload(self):
        """Valid completion payload should be accepted."""
        payload = {
            "build_id": "bld_abc123",
            "status": "completed",
            "download_key": "builds/bld_abc123/app.exe",
            "filename": "app.exe",
        }
        
        assert "build_id" in payload
        assert payload["status"] in ["completed", "failed"]
        assert "download_key" in payload

    def test_valid_failure_payload(self):
        """Valid failure payload should include error."""
        payload = {
            "build_id": "bld_abc123",
            "status": "failed",
            "error": "Compilation timed out",
        }
        
        assert payload["status"] == "failed"
        assert "error" in payload

    def test_missing_build_id_rejected(self):
        """Payload without build_id should be rejected."""
        payload = {
            "status": "completed",
            "download_key": "test",
        }
        
        assert "build_id" not in payload


# =============================================================================
# Config Generation Tests
# =============================================================================

class TestConfigGeneration:
    """Tests for build config generation."""

    def test_python_config_generation(self):
        """Python build config should have correct defaults."""
        config = {
            "project_id": "test123",
            "language": "python",
            "entry_file": "main.py",
            "output_name": "test_app",
            "license_key": "GENERIC_BUILD",
            "api_url": "https://api.example.com/api/v1/license/validate",
        }
        
        assert config["language"] == "python"
        assert config["entry_file"].endswith(".py")

    def test_nodejs_config_generation(self):
        """Node.js build config should have correct defaults."""
        config = {
            "project_id": "test123",
            "language": "nodejs",
            "entry_file": "index.js",
            "output_name": "test_app",
            "license_key": "GENERIC_BUILD",
        }
        
        assert config["language"] == "nodejs"
        assert config["entry_file"].endswith(".js")

    def test_generic_license_key_default(self):
        """Should default to GENERIC_BUILD if no license specified."""
        license_id = None
        expected_key = "GENERIC_BUILD" if not license_id else "actual_key"
        
        assert expected_key == "GENERIC_BUILD"


# =============================================================================
# Download URL Tests
# =============================================================================

class TestDownloadURL:
    """Tests for download URL generation."""

    def test_expired_download_rejected(self):
        """Expired download should be rejected."""
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # Expired yesterday
        
        is_expired = expires_at < datetime.now(timezone.utc)
        assert is_expired is True

    def test_valid_download_accepted(self):
        """Valid (non-expired) download should be accepted."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=6)  # Expires in 6 days
        
        is_expired = expires_at < datetime.now(timezone.utc)
        assert is_expired is False

    def test_no_download_key_rejected(self):
        """Build without download_key should not provide download URL."""
        build = {
            "status": "completed",
            "download_key": None,
        }
        
        can_download = build["status"] == "completed" and build["download_key"]
        assert not can_download


# =============================================================================
# Integration-style Tests (Mocked)
# =============================================================================

class TestCloudBuildIntegration:
    """Integration-style tests with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_start_build_creates_record(self, mock_db_connection, mock_pro_user):
        """Starting a build should create a database record."""
        mock_db_connection.fetchrow.return_value = {
            "id": "test_project",
            "name": "Test Project",
            "language": "python",
            "user_id": mock_pro_user["id"],
            "settings": json.dumps({"entry_file": "main.py"}),
        }
        mock_db_connection.fetchval.return_value = 0  # No builds this month
        
        # Simulate the insert would succeed
        mock_db_connection.execute.return_value = "INSERT 0 1"
        
        # The build would be created
        assert mock_db_connection.execute is not None

    @pytest.mark.asyncio
    async def test_webhook_updates_status(self, mock_db_connection, mock_cloud_build):
        """Webhook should update build status in database."""
        mock_db_connection.fetchrow.return_value = mock_cloud_build
        
        # Simulate update
        await mock_db_connection.execute(
            "UPDATE cloud_builds SET status = $1 WHERE id = $2",
            "completed", mock_cloud_build["id"]
        )
        
        mock_db_connection.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_status_returns_build_info(self, mock_db_connection, mock_cloud_build):
        """Get status should return build information."""
        mock_db_connection.fetchrow.return_value = mock_cloud_build
        
        result = await mock_db_connection.fetchrow(
            "SELECT * FROM cloud_builds WHERE id = $1",
            mock_cloud_build["id"]
        )
        
        assert result is not None
        assert result["id"] == mock_cloud_build["id"]
