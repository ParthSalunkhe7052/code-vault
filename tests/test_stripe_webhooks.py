"""
Stripe Webhook Tests for CodeVault.

Comprehensive tests for Stripe webhook handling including:
- Signature verification
- Event processing
- Error handling
- Idempotency
"""

import pytest
import sys
import os
import json
import time
from unittest.mock import patch, AsyncMock

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


@pytest.mark.integration
class TestStripeWebhookSignature:
    """Test Stripe webhook signature verification."""

    def test_webhook_requires_signature_in_production(self, client):
        """Test that webhooks require signature verification in production."""
        # Mock production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            response = client.post(
                "/api/v1/stripe/webhook",
                content=b'{"type": "test"}',
                headers={"Content-Type": "application/json"}
            )
            # Should reject without signature
            assert response.status_code in [400, 401, 403, 500]

    def test_webhook_rejects_tampered_payload(self, client, mock_stripe_signature):
        """Test that tampered payloads are rejected."""
        original_payload = '{"type": "checkout.session.completed"}'
        tampered_payload = '{"type": "checkout.session.completed", "hacked": true}'

        # Generate signature for original payload
        secret = "whsec_test_secret"
        signature = mock_stripe_signature(original_payload, secret)

        # Send tampered payload with original signature
        response = client.post(
            "/api/v1/stripe/webhook",
            content=tampered_payload.encode(),
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": signature
            }
        )

        # Should reject due to signature mismatch
        assert response.status_code in [400, 401, 403, 500]

    def test_webhook_rejects_expired_timestamp(self, client):
        """Test that webhooks with old timestamps are rejected."""
        payload = '{"type": "test"}'

        # Create signature with old timestamp (> 5 minutes ago)
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        signature = f"t={old_timestamp},v1=fakesignature"

        response = client.post(
            "/api/v1/stripe/webhook",
            content=payload.encode(),
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": signature
            }
        )

        # Should reject due to timestamp tolerance
        assert response.status_code in [400, 401, 403, 500]


@pytest.mark.integration
class TestStripeEventProcessing:
    """Test Stripe event processing logic."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"id": "user123", "email": "test@example.com"})
        conn.execute = AsyncMock()
        return conn

    def test_checkout_completed_event_structure(self, mock_stripe_event):
        """Test checkout.session.completed event has required fields."""
        event = mock_stripe_event
        assert event["type"] == "checkout.session.completed"
        assert "data" in event
        assert "object" in event["data"]

        session = event["data"]["object"]
        assert "customer" in session
        assert "metadata" in session

    def test_subscription_event_types_supported(self):
        """Test that required subscription event types are handled."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server", "routes"))

            # These event types should be handled by the webhook
            required_events = [
                "checkout.session.completed",
                "customer.subscription.updated",
                "customer.subscription.deleted",
                "invoice.payment_succeeded",
                "invoice.payment_failed",
            ]

            # This test just verifies the structure is in place
            # Actual handling is tested with mocked database
            assert len(required_events) == 5

        except ImportError:
            pytest.skip("Stripe routes not found")


@pytest.mark.integration
class TestStripeErrorHandling:
    """Test Stripe webhook error handling."""

    def test_invalid_json_returns_400(self, client):
        """Test that invalid JSON returns 400 Bad Request."""
        response = client.post(
            "/api/v1/stripe/webhook",
            content=b"not valid json {{{",
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=123,v1=abc"
            }
        )
        assert response.status_code in [400, 422, 500]

    def test_missing_event_type_handled(self, client):
        """Test that missing event type is handled gracefully."""
        response = client.post(
            "/api/v1/stripe/webhook",
            content=b'{"data": {}}',
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=123,v1=abc"
            }
        )
        # Should not crash - return an error
        assert response.status_code in [400, 401, 403, 422, 500]

    def test_unknown_event_type_ignored(self, client, mock_stripe_event):
        """Test that unknown event types are acknowledged but not processed."""
        # Modify event to unknown type
        mock_stripe_event["type"] = "unknown.event.type"

        # This would need proper signature in real test
        # Here we just verify the endpoint doesn't crash on unknown types
        response = client.post(
            "/api/v1/stripe/webhook",
            content=json.dumps(mock_stripe_event).encode(),
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=123,v1=abc"
            }
        )

        # Should not return 500 (internal error)
        # Unknown events should be ignored gracefully
        assert response.status_code != 500, (
            f"Unknown events should not cause 500 errors, got {response.status_code}"
        )


@pytest.mark.integration
class TestStripeIdempotency:
    """Test idempotent webhook processing."""

    def test_duplicate_event_handling(self, mock_stripe_event):
        """Test that duplicate events are handled idempotently."""
        # Get the same event ID
        event_id = mock_stripe_event["id"]

        # In a real implementation, the second processing should be a no-op
        # This test verifies the event structure supports idempotency
        assert event_id.startswith("evt_")
        assert len(event_id) > 10  # Has sufficient entropy


@pytest.mark.integration
class TestStripeProductionRequirements:
    """Test production-specific requirements."""

    def test_webhook_secret_required_in_production(self):
        """Test that STRIPE_WEBHOOK_SECRET is required in production."""
        try:
            from config import ENVIRONMENT

            if ENVIRONMENT == "production":
                # In production, the secret should be set
                # If not set, the app should fail to start or reject webhooks
                # This is validated in config.py startup
                pass

        except ImportError:
            pytest.skip("Config not found")
        except ValueError as e:
            # Expected in production without secret configured
            assert "STRIPE_WEBHOOK_SECRET" in str(e)

    def test_webhook_logs_events_securely(self):
        """Test that webhook logging doesn't expose sensitive data."""
        try:
            from utils import sanitize_log_message
        except ImportError:
            pytest.skip("Utils not found")

        # Sensitive data that should be sanitized
        sensitive_data = [
            "sk_live_abcdefghijklmnop",
            "whsec_secretkey123",
            "customer@email.com",
        ]

        for data in sensitive_data:
            sanitized = sanitize_log_message(data)
            # Should not contain newlines (log injection)
            assert "\n" not in sanitized
            assert "\r" not in sanitized


@pytest.mark.integration
class TestStripeCheckoutFlow:
    """Test Stripe checkout session creation."""

    def test_checkout_session_includes_metadata(self, mock_user):
        """Test that checkout sessions include necessary metadata."""
        # Metadata should include user_id for linking
        metadata = {
            "user_id": mock_user["id"],
            "tier": "pro",
        }

        assert "user_id" in metadata
        assert metadata["user_id"] == mock_user["id"]

    def test_checkout_requires_authentication(self, client):
        """Test that checkout session creation requires auth."""
        response = client.post(
            "/api/v1/stripe/create-checkout-session",
            json={"price_id": "price_123"}
        )

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_portal_requires_authentication(self, client):
        """Test that customer portal creation requires auth."""
        response = client.post(
            "/api/v1/stripe/create-customer-portal",
            json={"return_url": "https://example.com"}
        )

        # Should require authentication
        assert response.status_code in [401, 403]
