"""
Polar Webhook Tests for CodeVault.

Coverage includes:
- Signature verification (Standard Webhooks)
- Event handling and error behavior
- Checkout endpoint auth
"""

import pytest
import sys
import os
import json

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


@pytest.mark.integration
class TestPolarWebhookSignature:
    """Test Polar webhook signature verification."""

    def test_signature_verification_accepts_valid_signature(self, mock_polar_signature):
        try:
            from routes.polar_routes import _verify_webhook_signature
        except ImportError:
            pytest.skip("Polar routes not found")

        payload = '{"type": "subscription.created"}'
        webhook_id = "wh_123"
        webhook_timestamp = "1700000000"
        secret = "dGVzdF9zZWNyZXQ="  # base64("test_secret")
        signature = mock_polar_signature(payload, secret, webhook_id, webhook_timestamp)

        assert _verify_webhook_signature(
            payload.encode("utf-8"),
            webhook_id,
            webhook_timestamp,
            signature,
            secret,
        )

    def test_signature_verification_rejects_tampered_payload(self, mock_polar_signature):
        try:
            from routes.polar_routes import _verify_webhook_signature
        except ImportError:
            pytest.skip("Polar routes not found")

        original_payload = '{"type": "subscription.created"}'
        tampered_payload = '{"type": "subscription.created", "hacked": true}'
        webhook_id = "wh_456"
        webhook_timestamp = "1700000001"
        secret = "dGVzdF9zZWNyZXQ="
        signature = mock_polar_signature(
            original_payload, secret, webhook_id, webhook_timestamp
        )

        assert not _verify_webhook_signature(
            tampered_payload.encode("utf-8"),
            webhook_id,
            webhook_timestamp,
            signature,
            secret,
        )


@pytest.mark.integration
class TestPolarWebhookEndpoint:
    """Test Polar webhook endpoint behavior."""

    def test_webhook_requires_signature_in_production(self, client):
        try:
            from config import ENVIRONMENT
        except ImportError:
            pytest.skip("Config not found")

        if ENVIRONMENT != "production":
            pytest.skip("Signature enforcement only required in production")

        response = client.post(
            "/api/v1/polar/webhook",
            content=b'{"type": "subscription.created"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_unknown_event_type_ignored(self, client, mock_polar_event, monkeypatch):
        try:
            from routes import polar_routes
        except ImportError:
            pytest.skip("Polar routes not found")

        class _DummyTx:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class _DummyConn:
            async def fetchval(self, *args, **kwargs):
                return None

            async def execute(self, *args, **kwargs):
                return None

            def transaction(self):
                return _DummyTx()

        async def _get_db():
            return _DummyConn()

        async def _release_db(conn):
            return None

        # Force development behavior to avoid signature dependency
        monkeypatch.setattr(polar_routes, "ENVIRONMENT", "development", raising=False)
        monkeypatch.setattr(polar_routes, "POLAR_WEBHOOK_SECRET", None, raising=False)
        monkeypatch.setattr(polar_routes, "get_db", _get_db, raising=False)
        monkeypatch.setattr(polar_routes, "release_db", _release_db, raising=False)

        mock_polar_event["type"] = "unknown.event.type"
        response = client.post(
            "/api/v1/polar/webhook",
            content=json.dumps(mock_polar_event).encode(),
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [200, 202]


@pytest.mark.integration
class TestPolarCheckoutFlow:
    """Test Polar checkout session creation."""

    def test_checkout_requires_authentication(self, client, monkeypatch):
        try:
            from routes import polar_routes
        except ImportError:
            pytest.skip("Polar routes not found")

        class _DummyConn:
            async def fetchrow(self, *args, **kwargs):
                return None

        async def _get_db():
            return _DummyConn()

        async def _release_db(conn):
            return None

        monkeypatch.setattr(polar_routes, "get_db", _get_db, raising=False)
        monkeypatch.setattr(polar_routes, "release_db", _release_db, raising=False)

        response = client.post(
            "/api/v1/polar/create-checkout",
            json={"product_id": "prod_test_pro"},
        )

        assert response.status_code in [401, 403]
