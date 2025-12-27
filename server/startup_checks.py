import os
import logging
from config import ENVIRONMENT

logger = logging.getLogger(__name__)


def run_startup_checks():
    """
    Run critical startup checks to ensure security and configuration.
    Raises ValueError if critical environment variables are missing in production.
    """
    logger.info("Running startup checks...")

    missing = []

    # 1. Stripe Secrets
    if not os.getenv("STRIPE_SECRET_KEY"):
        missing.append("STRIPE_SECRET_KEY")

    # 2. Webhook Secret (Critical for security)
    if not os.getenv("STRIPE_WEBHOOK_SECRET"):
        if ENVIRONMENT == "production":
            missing.append("STRIPE_WEBHOOK_SECRET")
        else:
            logger.warning(
                "STRIPE_WEBHOOK_SECRET is missing. Webhooks signatures might not be verified properly in dev mode."
            )

    # 3. Price IDs
    if not os.getenv("STRIPE_PRICE_PRO"):
        # Warning only, might not have Pro plan
        logger.warning("STRIPE_PRICE_PRO is not set. Pro plan might not work.")

    if not os.getenv("STRIPE_PRICE_ENTERPRISE"):
        logger.warning(
            "STRIPE_PRICE_ENTERPRISE is not set. Enterprise plan might not work."
        )

    if missing:
        error_msg = (
            f"CRITICAL: Missing required environment variables: {', '.join(missing)}"
        )
        logger.error(error_msg)
        # In production, we should fail hard
        if ENVIRONMENT == "production":
            raise ValueError(error_msg)

    logger.info("Startup checks passed.")
