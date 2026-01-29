import httpx
import logging
from typing import Optional
from config import DODO_API_KEY, DODO_ENVIRONMENT

logger = logging.getLogger(__name__)


class DodoService:
    """
    Service for interacting with Dodo Payments API.
    Handles product creation and management for the marketplace.
    """

    def __init__(self):
        self.api_key = DODO_API_KEY
        self.base_url = (
            "https://test-api.dodopayments.com"
            if DODO_ENVIRONMENT == "test_mode"
            else "https://api.dodopayments.com"
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_product(
        self, name: str, description: str, price_cents: int, currency: str = "USD"
    ) -> Optional[str]:
        """
        Create a product in Dodo Payments.
        Returns the product_id.
        """
        if not self.api_key:
            logger.error("Dodo API Key not configured")
            return None

        # Convert cents to main currency unit (e.g. 1000 cents -> 10.00 USD)
        price_amount = price_cents / 100.0

        payload = {
            "name": name,
            "description": description,
            "amount": price_amount,
            "currency": currency.upper(),
            "billing_frequency": "one_time",  # Marketplace items are one-time purchases
            "tax_category": "digital_goods",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/products", json=payload, headers=self.headers
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    # Dodo returns 'product_id' or 'id' depending on endpoint version
                    return data.get("product_id") or data.get("id")
                else:
                    logger.error(f"Failed to create Dodo product: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Dodo API Error: {str(e)}")
            return None

    async def update_product(
        self,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price_cents: Optional[int] = None,
    ) -> bool:
        """
        Update a product in Dodo Payments.
        """
        if not self.api_key:
            return False

        payload = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if price_cents is not None:
            payload["amount"] = price_cents / 100.0

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/products/{product_id}",
                    json=payload,
                    headers=self.headers,
                )

                return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Dodo API Error: {str(e)}")
            return False

    async def create_checkout_session(
        self, product_id: str, metadata: dict
    ) -> Optional[str]:
        """
        Create a checkout session / payment link for a marketplace product.

        Args:
            product_id: The Dodo product ID (from projects.dodo_product_id)
            metadata: Dict with project_id, seller_id, buyer_email for webhook fulfillment

        Returns:
            Checkout URL string or None on failure
        """
        if not self.api_key:
            logger.error("Dodo API Key not configured")
            return None

        payload = {
            "product_id": product_id,
            "quantity": 1,
            "payment_link": True,  # Generate a shareable payment link
            "metadata": metadata,  # This gets passed back in webhook for fulfillment
        }

        # Add buyer email if provided (for pre-filled checkout)
        if metadata.get("buyer_email"):
            payload["customer"] = {"email": metadata["buyer_email"]}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments", json=payload, headers=self.headers
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    # Dodo returns 'payment_link' or 'url' depending on endpoint version
                    checkout_url = (
                        data.get("payment_link")
                        or data.get("url")
                        or data.get("checkout_url")
                    )

                    if checkout_url:
                        logger.info(f"Created Dodo checkout for product {product_id}")
                        return checkout_url
                    else:
                        logger.error(f"Dodo response missing checkout URL: {data}")
                        return None
                else:
                    logger.error(
                        f"Failed to create Dodo checkout: {response.status_code} - {response.text}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Dodo API Error creating checkout: {str(e)}")
            return None

    async def verify_webhook_signature(
        self, payload: bytes, signature: str, webhook_secret: str
    ) -> bool:
        """
        Verify Dodo webhook signature for security.

        Args:
            payload: Raw request body bytes
            signature: Value from 'dodo-signature' header
            webhook_secret: DODO_WEBHOOK_SECRET from config

        Returns:
            True if signature is valid, False otherwise
        """
        import hmac
        import hashlib

        if not webhook_secret:
            logger.warning(
                "DODO_WEBHOOK_SECRET not configured, skipping signature verification"
            )
            return True  # Allow in development, but log warning

        try:
            expected_signature = hmac.new(
                webhook_secret.encode(), payload, hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Webhook signature verification error: {str(e)}")
            return False


# Singleton instance
dodo_service = DodoService()
