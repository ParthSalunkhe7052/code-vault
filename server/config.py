"""
Configuration settings for CodeVault API Server.
Loads environment variables from multiple possible locations.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Try multiple .env locations in order of priority
_server_dir = Path(__file__).parent
_project_root = _server_dir.parent
_env_locations = [
    _project_root / "data" / ".env",  # Production: data/.env
    _project_root / ".env",            # Development: project root .env
    _server_dir / ".env",              # Fallback: server/.env
]

_env_loaded = False
for _env_file in _env_locations:
    if _env_file.exists():
        load_dotenv(_env_file)
        print(f"[Config] Loaded environment from: {_env_file}")
        _env_loaded = True
        break

if not _env_loaded:
    load_dotenv()  # Last resort: default behavior
    print("[Config] Using default .env loading")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# =============================================================================
# Load All Environment Variables FIRST (before validation)
# =============================================================================

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Redis (Upstash)
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

# Redis URL for rate limiting (use standard Redis URL format)
# For Upstash, convert UPSTASH_REDIS_REST_URL + token to standard format
REDIS_URL = os.getenv("REDIS_URL", "")

# If REDIS_URL is not set but UPSTASH credentials are available, construct the URL
if not REDIS_URL and UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
    # Upstash REST API URL format: https://unique-name.upstash.io
    # Convert to standard Redis URL format: rediss://default:{token}@{endpoint}:6379
    endpoint = UPSTASH_REDIS_REST_URL.replace("https://", "").replace("http://", "")
    REDIS_URL = f"rediss://default:{UPSTASH_REDIS_REST_TOKEN}@{endpoint}:6379"
    print(f"[Config] Using Upstash Redis: {endpoint}")
elif not REDIS_URL:
    # For local development, suggest localhost Redis
    print("[Config] No Redis configured. Rate limiting disabled.")
    print("[Config] Install local Redis for rate limiting: https://redis.io/download")
    print("[Config] Or add REDIS_URL=redis://localhost:6379 to .env")

# Admin
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


# GitHub Actions (Cloud Build)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
BUILD_CALLBACK_SECRET = os.getenv("BUILD_CALLBACK_SECRET", "")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://localhost:8000")


# CLI Tool
CLI_VERSION = "1.0.0"
LICENSE_SERVER_URL = os.getenv("LICENSE_SERVER_URL", "http://localhost:8000")
CLI_DOWNLOAD_URLS = {
    "windows": os.getenv("CLI_DOWNLOAD_WINDOWS", ""),
    "macos": os.getenv("CLI_DOWNLOAD_MACOS", ""),
    "linux": os.getenv("CLI_DOWNLOAD_LINUX", ""),
}

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price IDs
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_ENTERPRISE = os.getenv("STRIPE_PRICE_ENTERPRISE", "")

# =============================================================================
# SECURITY VALIDATION (Startup Checks)
# =============================================================================

# Track configuration issues
config_issues = []

# Validate ENVIRONMENT setting
valid_environments = {"development", "staging", "production"}
if ENVIRONMENT not in valid_environments:
    config_issues.append(
        f"ENVIRONMENT must be one of {valid_environments}, got '{ENVIRONMENT}'"
    )

# Validate database URL
if not DATABASE_URL:
    config_issues.append("DATABASE_URL is not set")

# Validate secrets in production
if ENVIRONMENT == "production":
    if SECRET_KEY == "dev-secret-key-change-in-production":
        config_issues.append(
            "SECRET_KEY must be changed from default in production!"
        )
    if JWT_SECRET == "jwt-secret-change-in-production":
        config_issues.append(
            "JWT_SECRET must be changed from default in production!"
        )
    if not STRIPE_WEBHOOK_SECRET:
        config_issues.append(
            "STRIPE_WEBHOOK_SECRET must be set in production for secure webhooks!"
        )

    # Additional production security checks
    if CORS_ALLOW_ALL:
        config_issues.append(
            "CORS_ALLOW_ALL=true is insecure in production. Use specific origins."
        )

# Warn in development, fail in production
if config_issues:
    if ENVIRONMENT == "production":
        error_msg = "\n".join([
            "CRITICAL CONFIGURATION ERRORS:",
            *config_issues,
            "",
            "Server cannot start in production with these issues."
        ])
        raise ValueError(error_msg)
    else:
        print("\n[Config] ⚠️  DEVELOPMENT MODE: Configuration warnings:")
        for issue in config_issues:
            print(f"  - {issue}")
        print()

# Log current environment for visibility
print(f"[Config] Environment: {ENVIRONMENT}")

# Build Credit Costs
BUILD_COST_STANDARD = 1
BUILD_COST_FAST = 0  # Free for now to encourage testing

# Subscription Tier Limits
# -1 means unlimited
TIER_LIMITS = {
    "free": {
        "_tier_name": "Free",
        "max_projects": 1,
        "max_licenses_per_project": 50,
        "can_sell_licenses": False,
        "cloud_compilation": False,
        "cloud_builds_per_month": 0,
        "cloud_platforms": ["windows"],
        "analytics": False,
        "webhooks": False,
        "team_seats": 1,
        "node_support": False,
    },
    "pro": {
        "_tier_name": "Pro",
        "max_projects": -1,  # unlimited
        "max_licenses_per_project": 200,
        "can_sell_licenses": True,
        "cloud_compilation": True,
        "cloud_builds_per_month": 10,
        "cloud_platforms": ["windows", "macos", "linux"],
        "analytics": True,
        "webhooks": True,
        "team_seats": 1,
        "node_support": True,
    },
    "enterprise": {
        "_tier_name": "Agency",
        "max_projects": -1,  # unlimited
        "max_licenses_per_project": -1,  # unlimited
        "can_sell_licenses": True,
        "cloud_compilation": True,
        "cloud_builds_per_month": 50,  # 50 credits
        "cloud_platforms": ["windows", "macos", "linux"],
        "analytics": True,
        "webhooks": True,
        "team_seats": 5,
        "white_labeling": True,
        "node_support": True,
    },
}

# Pricing Configuration
PRICING_CONFIG = {
    "free": {
        "name": "Free",
        "price": 0,
        "currency": "USD",
        "features": ["1 Project", "50 Licenses", "Local Compilation Only"],
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "currency": "USD",
        "price_id": STRIPE_PRICE_PRO,
        "features": [
            "Unlimited Projects",
            "500 Licenses",
            "15 Cloud Builds/mo",
            "Whop Integration",
            "Analytics",
        ],
    },
    "enterprise": {
        "name": "Agency",
        "price": 99,
        "currency": "USD",
        "price_id": STRIPE_PRICE_ENTERPRISE,
        "features": [
            "Unlimited Licenses",
            "50 Cloud Builds/mo",
            "Priority Support",
            "White Labeling",
        ],
    },
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
