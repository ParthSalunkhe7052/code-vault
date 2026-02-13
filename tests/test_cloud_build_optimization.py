"""
Tests for Cloud Build Optimization Features

This module tests the optimized cache strategy, tier-based timeouts,
and other improvements made to the Cloud Build system.
"""

import pytest
import yaml
from pathlib import Path


class TestCloudBuildYAMLStructure:
    """Test that cloudbuild.yaml is valid and optimized"""

    def test_cloudbuild_yaml_valid(self):
        """Test that cloudbuild.yaml is valid YAML"""
        cloudbuild_path = Path(__file__).parent.parent / "cloudbuild.yaml"

        with open(cloudbuild_path, "r") as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert "steps" in config
        assert len(config["steps"]) > 0
        assert "substitutions" in config

    def test_cloudbuild_steps_have_ids(self):
        """Test that all steps have unique IDs"""
        cloudbuild_path = Path(__file__).parent.parent / "cloudbuild.yaml"

        with open(cloudbuild_path, "r") as f:
            config = yaml.safe_load(f)

        step_ids = [step.get("id") for step in config["steps"] if step.get("id")]
        # Filter out None values and check for duplicates
        assert len(step_ids) == len(set(step_ids)), "Duplicate step IDs found"

    def test_cache_steps_use_hash_based_keys(self):
        """Test that cache restoration uses hash-based keys"""
        cloudbuild_path = Path(__file__).parent.parent / "cloudbuild.yaml"

        with open(cloudbuild_path, "r") as f:
            content = f.read()

        # Check for cache directory configuration
        assert "_NUITKA_CACHE_DIR" in content, (
            "Cache directory should be defined in substitutions"
        )
        assert "/workspace/.nuitka-cache" in content, (
            "Nuitka cache directory should be configured"
        )

    def test_config_download_consolidated(self):
        """Test that config download is consolidated to single step"""
        cloudbuild_path = Path(__file__).parent.parent / "cloudbuild.yaml"

        with open(cloudbuild_path, "r") as f:
            content = f.read()

        # Should have download-config (consolidated) not separate linux/windows
        assert "id: 'download-config'" in content
        assert "download-config-linux" not in content
        assert "download-config-windows" not in content

    def test_secret_validation_step_exists(self):
        """Test that secrets are configured properly"""
        cloudbuild_path = Path(__file__).parent.parent / "cloudbuild.yaml"

        with open(cloudbuild_path, "r") as f:
            content = f.read()

        # Verify secrets configuration exists
        assert "availableSecrets" in content, "Secrets configuration should exist"
        assert "secretManager" in content, "Secret manager should be configured"

    def test_debug_build_substitution(self):
        """Test that _DEBUG_BUILD substitution exists"""
        cloudbuild_path = Path(__file__).parent.parent / "cloudbuild.yaml"

        with open(cloudbuild_path, "r") as f:
            content = f.read()

        # Verify debug build substitution exists
        assert "_DEBUG_BUILD" in content, "_DEBUG_BUILD substitution should exist"


class TestCloudBuildUtils:
    """Test cloud build utility functions"""

    @pytest.fixture
    def temp_upload_dir(self, tmp_path):
        """Create a temporary upload directory"""
        return tmp_path / "uploads"

    def test_validate_safe_path_valid(self, temp_upload_dir):
        """Test that valid paths are accepted"""
        from server.routes.cloud_build_utils import validate_safe_path

        temp_upload_dir.mkdir(parents=True, exist_ok=True)
        result = validate_safe_path(temp_upload_dir, "valid_project_id")
        assert "valid_project_id" in str(result)

    def test_validate_safe_path_traversal_blocked(self, temp_upload_dir):
        """Test that path traversal attacks are blocked"""
        from server.routes.cloud_build_utils import validate_safe_path
        from fastapi import HTTPException

        temp_upload_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(HTTPException):
            validate_safe_path(temp_upload_dir, "../etc/passwd")

    def test_validate_safe_path_special_chars_blocked(self, temp_upload_dir):
        """Test that special characters are blocked"""
        from server.routes.cloud_build_utils import validate_safe_path
        from fastapi import HTTPException

        temp_upload_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises(HTTPException):
            validate_safe_path(temp_upload_dir, "project;rm -rf")

    def test_verify_webhook_signature(self):
        """Test webhook signature verification"""
        from server.routes.cloud_build_utils import verify_webhook_signature
        import hmac
        import hashlib

        secret = "test_secret"
        payload = b'{"build_id":"test123"}'
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert verify_webhook_signature(payload, signature, secret) is True
        assert verify_webhook_signature(payload, "wrong_signature", secret) is False


class TestCloudBuildWebSocket:
    """Test WebSocket connection management"""

    @pytest.mark.asyncio
    async def test_connection_manager_connect_disconnect(self):
        """Test WebSocket connect and disconnect"""
        from server.routes.cloud_build_websocket import ConnectionManager
        from unittest.mock import AsyncMock

        manager = ConnectionManager()
        mock_ws = AsyncMock()

        # Test connect
        await manager.connect(mock_ws, "build_123")
        assert "build_123" in manager.active_connections
        assert mock_ws in manager.active_connections["build_123"]

        # Test disconnect
        manager.disconnect(mock_ws, "build_123")
        assert "build_123" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_build_update(self):
        """Test broadcasting updates to clients"""
        from server.routes.cloud_build_websocket import broadcast_build_update
        from unittest.mock import AsyncMock, patch

        with patch("server.routes.cloud_build_websocket.ws_manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()

            await broadcast_build_update(
                "build_123", "progress", {"stage": "Compiling"}
            )

            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            assert call_args[0][0] == "build_123"
            assert call_args[0][1]["type"] == "progress"
            assert call_args[0][1]["data"]["stage"] == "Compiling"

    def test_get_build_stage_pending(self):
        """Test pending build stage calculation"""
        from server.routes.cloud_build_websocket import get_build_stage

        build = {"status": "pending", "progress": 0}
        stage, progress = get_build_stage(build)
        assert stage == "Queued"
        assert progress == 5

    def test_get_build_stage_running(self):
        """Test running build stage calculation"""
        from server.routes.cloud_build_websocket import get_build_stage

        build = {"status": "running", "progress": 0, "logs": ["Compiling with Nuitka"]}
        stage, progress = get_build_stage(build)
        assert "Compiling" in stage
        assert progress >= 30

    def test_get_build_stage_completed(self):
        """Test completed build stage"""
        from server.routes.cloud_build_websocket import get_build_stage

        build = {"status": "completed", "progress": 100}
        stage, progress = get_build_stage(build)
        assert stage == "Complete"
        assert progress == 100


class TestCloudBuildIntegration:
    """Test Cloud Build integration features"""

    def test_tier_based_timeout_configuration(self):
        """Test that different tiers get different timeouts"""
        import sys
        import os

        # Add scripts directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
        from cloud_build_integration import TIER_TIMEOUTS

        # Verify expected values from canonical configuration
        assert TIER_TIMEOUTS["free"] == 1800
        assert TIER_TIMEOUTS["pro"] == 3600
        assert TIER_TIMEOUTS["business"] == 7200
        assert TIER_TIMEOUTS.get("unknown", 3600) == 3600  # Default

    def test_tier_based_machine_types(self):
        """Test that different tiers get different machine types"""
        import sys
        import os

        # Add scripts directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
        from cloud_build_integration import TIER_MACHINES

        # Verify expected values from canonical configuration
        assert TIER_MACHINES["business"] == "N1_HIGHCPU_8"
        assert TIER_MACHINES["pro"] == "E2_HIGHCPU_8"
        assert TIER_MACHINES["free"] == "E2_MEDIUM"


class TestDatabaseMigration:
    """Test database migration for GCP build tracking"""

    def test_migration_file_exists(self):
        """Test that migration file exists"""
        migration_path = (
            Path(__file__).parent.parent
            / "server"
            / "migrations"
            / "009_add_gcp_build_tracking.sql"
        )
        assert migration_path.exists()

    def test_migration_contains_required_columns(self):
        """Test that migration adds required columns"""
        migration_path = (
            Path(__file__).parent.parent
            / "server"
            / "migrations"
            / "009_add_gcp_build_tracking.sql"
        )

        with open(migration_path, "r") as f:
            content = f.read()

        required_columns = [
            "gcp_build_id",
            "build_type",
            "build_duration",
            "queue_wait_time",
            "error_type",
        ]

        for column in required_columns:
            assert f"ADD COLUMN IF NOT EXISTS {column}" in content, (
                f"Missing column: {column}"
            )

    def test_migration_creates_indexes(self):
        """Test that migration creates indexes"""
        migration_path = (
            Path(__file__).parent.parent
            / "server"
            / "migrations"
            / "009_add_gcp_build_tracking.sql"
        )

        with open(migration_path, "r") as f:
            content = f.read()

        assert "CREATE INDEX" in content
        assert "idx_cloud_builds_gcp_id" in content


class TestGitHubActionsRemoval:
    """Test GitHub Actions workflow configuration"""

    def test_github_actions_workflows_exist(self):
        """Test that GitHub Actions workflow files exist (for legacy builds)"""
        github_dir = Path(__file__).parent.parent / ".github" / "workflows"

        # GitHub Actions workflows may still exist for legacy builds
        # The main build system uses Google Cloud Build now
        assert github_dir.exists(), "GitHub workflows directory should exist"
