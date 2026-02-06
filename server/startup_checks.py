import logging
from config import (
    ENVIRONMENT,
    POLAR_ACCESS_TOKEN,
    POLAR_WEBHOOK_SECRET,
    POLAR_PRODUCT_PRO,
    POLAR_PRODUCT_BUSINESS,
)

logger = logging.getLogger(__name__)


def run_startup_checks():
    """
    Run critical startup checks to ensure security and configuration.
    Raises ValueError if critical environment variables are missing in production.
    """
    logger.info("Running startup checks...")

    missing = []

    # 1. Polar Access Token (required for payment processing)
    if not POLAR_ACCESS_TOKEN:
        if ENVIRONMENT == "production":
            missing.append("POLAR_ACCESS_TOKEN")
        else:
            logger.warning(
                "POLAR_ACCESS_TOKEN is missing. Payment processing will not work."
            )

    # 2. Polar Webhook Secret (needed for webhook verification)
    if not POLAR_WEBHOOK_SECRET:
        logger.warning(
            "POLAR_WEBHOOK_SECRET is missing. Polar webhook endpoints will reject incoming webhooks."
        )

    # 3. Polar Product IDs
    if not POLAR_PRODUCT_PRO:
        logger.warning("POLAR_PRODUCT_PRO is not set. Pro plan checkout will not work.")

    if not POLAR_PRODUCT_BUSINESS:
        logger.warning(
            "POLAR_PRODUCT_BUSINESS is not set. Business plan checkout will not work."
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
