"""
Configuration settings for CodeVault API Server.
Loads environment variables from data/.env or local .env fallback.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Try to load from data/.env first (production), fallback to local .env (development)
_env_file = Path(__file__).parent.parent.parent / "data" / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
    print(f"[Config] Loaded environment from: {_env_file}")
else:
    load_dotenv()  # Fallback to default behavior
    print("[Config] Using default .env loading")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Validate critical secrets in production
if ENVIRONMENT == "production":
    if SECRET_KEY == "dev-secret-key-change-in-production":
        raise ValueError("CRITICAL: SECRET_KEY must be set in production! Set it in .env file.")
    if JWT_SECRET == "jwt-secret-change-in-production":
        raise ValueError("CRITICAL: JWT_SECRET must be set in production! Set it in .env file.")


# Admin
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# License Server URL - Used by compiled applications to validate licenses
# Set this to your production API URL, e.g. "https://api.codevault.com/api/v1"
LICENSE_SERVER_URL = os.getenv("LICENSE_SERVER_URL", "http://localhost:8000/api/v1")

# CLI Tool
CLI_VERSION = "1.0.0"
CLI_DOWNLOAD_URLS = {
    "windows": os.getenv("CLI_DOWNLOAD_WINDOWS", ""),
    "macos": os.getenv("CLI_DOWNLOAD_MACOS", ""),
    "linux": os.getenv("CLI_DOWNLOAD_LINUX", "")
}

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price IDs
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_ENTERPRISE = os.getenv("STRIPE_PRICE_ENTERPRISE", "")

# Subscription Tier Limits
# -1 means unlimited
TIER_LIMITS = {
    "free": {
        "_tier_name": "Free",
        "max_projects": 1,
        "max_licenses_per_project": 5,
        "can_sell_licenses": False,
        "cloud_compilation": False,
        "analytics": False,
        "webhooks": False,
        "team_seats": 1,
        "node_support": False,
    },
    "pro": {
        "_tier_name": "Pro",
        "max_projects": 10,
        "max_licenses_per_project": 100,
        "can_sell_licenses": True,
        "cloud_compilation": True,
        "analytics": True,
        "webhooks": True,
        "team_seats": 1,
        "node_support": True,
    },
    "enterprise": {
        "_tier_name": "Enterprise",
        "max_projects": -1,  # unlimited
        "max_licenses_per_project": -1,  # unlimited
        "can_sell_licenses": True,
        "cloud_compilation": True,
        "analytics": True,
        "webhooks": True,
        "team_seats": 5,
        "team_seats": 5,
        "white_labeling": True,
        "node_support": True,
    }
}

# Pricing Configuration
PRICING_CONFIG = {
    "free": {
        "name": "Free",
        "price": 0,
        "currency": "USD",
        "features": ["1 Project", "5 Licenses/Project", "Basic Support"]
    },
    "pro": {
        "name": "Pro",
        "price": 20,
        "currency": "USD",
        "price_id": STRIPE_PRICE_PRO,
        "features": ["10 Projects", "100 Licenses/Project", "Sell Licenses", "Cloud Compilation", "Analytics"]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 50,
        "currency": "USD",
        "price_id": STRIPE_PRICE_ENTERPRISE,
        "features": ["Unlimited Projects", "Unlimited Licenses", "Priority Support", "White Labeling"]
    }
}

# Webhook Events
WEBHOOK_EVENTS = [
    "license.created",
    "license.validated", 
    "license.revoked",
    "license.expired",
    "hwid.bound",
    "hwid.reset",
    "compilation.started",
    "compilation.completed",
    "compilation.failed",
    "subscription.created",
    "subscription.updated",
    "subscription.canceled",
    "license.purchased",
]
