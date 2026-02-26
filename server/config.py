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
    _project_root / ".env",  # Development: project root .env
    _server_dir / ".env",  # Fallback: server/.env
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
# Heroku uses postgres:// but asyncpg requires postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Supabase requires SSL - add sslmode=require if not present
if DATABASE_URL and "supabase.co" in DATABASE_URL and "sslmode=" not in DATABASE_URL:
    # Check if URL already has query parameters
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

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

# API Documentation (OpenAPI/Swagger)
# Set ENABLE_PUBLIC_DOCS=false in production to disable /docs and /redoc
ENABLE_PUBLIC_DOCS = os.getenv("ENABLE_PUBLIC_DOCS", "false").lower() == "true"

# Redis (Upstash)
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

# Redis URL for rate limiting (use standard Redis URL format)
# For Upstash, convert UPSTASH_REDIS_REST_URL + token to standard format
REDIS_URL = os.getenv("REDIS_URL", "")

# If REDIS_URL is not set but UPSTASH credentials are available, construct the URL
if not REDIS_URL and UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
    # Upstash REST API URL format: https://unique-name.upstash.io
    # Convert to standard Redis URL format
    # Using redis:// instead of rediss:// to avoid SSL handshake issues in some environments
    endpoint = UPSTASH_REDIS_REST_URL.replace("https://", "").replace("http://", "")
    REDIS_URL = f"redis://default:{UPSTASH_REDIS_REST_TOKEN}@{endpoint}:6379"
    print(f"[Config] Using Upstash Redis: {endpoint}")
elif not REDIS_URL:
    # For local development, suggest localhost Redis
    print("[Config] No Redis configured. Rate limiting disabled.")
    print("[Config] Install local Redis for rate limiting: https://redis.io/download")
    print("[Config] Or add REDIS_URL=redis://localhost:6379 to .env")

# Admin
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# Google Cloud Storage
GCS_BUILDS_BUCKET = os.getenv("GCS_BUILDS_BUCKET", "codevault-builds")


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

# Polar Payment Configuration
POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN", "")
POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET", "")

# Polar Product IDs
POLAR_PRODUCT_PRO = os.getenv("POLAR_PRODUCT_PRO", "")
POLAR_PRODUCT_BUSINESS = os.getenv("POLAR_PRODUCT_BUSINESS", "")

# Google Cloud Build
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cloudbuild-486309")

# Note: Stripe removed - using Polar for payments

# =============================================================================
# SECURITY VALIDATION (Startup Checks)
# =============================================================================

# CRITICAL: Production Security Validation (Fail Fast)
if ENVIRONMENT == "production":
    # Validate secrets are not using default values
    if SECRET_KEY == "dev-secret-key-change-in-production":
        raise ValueError(
            "CRITICAL: SECRET_KEY is using default value in production! "
            "Set SECRET_KEY environment variable to a secure random value. "
            "Generate one with: openssl rand -hex 32"
        )
    if JWT_SECRET == "jwt-secret-change-in-production":
        raise ValueError(
            "CRITICAL: JWT_SECRET is using default value in production! "
            "Set JWT_SECRET environment variable to a secure random value. "
            "Generate one with: openssl rand -hex 32"
        )

    # Validate minimum length
    if len(SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")
    if len(JWT_SECRET) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")

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
        config_issues.append("SECRET_KEY must be changed from default in production!")
    if JWT_SECRET == "jwt-secret-change-in-production":
        config_issues.append("JWT_SECRET must be changed from default in production!")

    if not BUILD_CALLBACK_SECRET:
        config_issues.append(
            "BUILD_CALLBACK_SECRET must be set in production for Cloud Build security!"
        )

    if not PUBLIC_API_URL or "localhost" in PUBLIC_API_URL:
        config_issues.append(
            "PUBLIC_API_URL must be set to your production domain (e.g., https://api.codevault.parth7.me)"
        )

    if not POLAR_WEBHOOK_SECRET:
        # Warn but don't block startup — webhook endpoint will reject unsigned payloads
        print(
            "[Config] WARNING: POLAR_WEBHOOK_SECRET is not set. Polar webhooks will be rejected until configured."
        )

    # Validate Redis is configured in production for rate limiting
    if not REDIS_URL:
        config_issues.append(
            "REDIS_URL not configured. Rate limiting and webhook retries will not work in production!"
        )
        print("[Config] CRITICAL: Redis not configured in production environment!")
        print("[Config] Rate limiting and webhook retry functionality are DISABLED.")

    # Additional production security checks
    if CORS_ALLOW_ALL:
        config_issues.append(
            "CORS_ALLOW_ALL=true is insecure in production. Use specific origins."
        )

# O7 FIX: Also warn loudly in staging — staging environments often share
# production-equivalent secrets or data, so wildcard CORS is equally dangerous.
if ENVIRONMENT == "staging" and CORS_ALLOW_ALL:
    import logging as _cfg_log
    _cfg_log.getLogger(__name__).warning(
        "[Config] CORS_ALLOW_ALL=true in staging is insecure. "
        "Staging may share secrets with production — use specific origins."
    )

# Warn in development, fail in production
if config_issues:
    if ENVIRONMENT == "production":
        error_msg = "\n".join(
            [
                "CRITICAL CONFIGURATION ERRORS:",
                *config_issues,
                "",
                "Server cannot start in production with these issues.",
            ]
        )
        raise ValueError(error_msg)
    else:
        print("\n[Config] ⚠️  DEVELOPMENT MODE: Configuration warnings:")
        for issue in config_issues:
            print(f"  - {issue}")
        print()

# Log current environment for visibility
print(f"[Config] Environment: {ENVIRONMENT}")

# Production environment guard
if ENVIRONMENT != "production":
    import logging

    # Check if we're running on a production host
    import socket

    hostname = socket.gethostname().lower()
    production_hosts = ["heroku", "aws", "prod", "production", "codevault"]

    is_production_host = any(host in hostname for host in production_hosts)

    if is_production_host:
        logging.critical(
            "[Config] CRITICAL WARNING: Running with ENVIRONMENT='{}' on what appears to be "
            "a production host ('{}'). Set ENVIRONMENT=production for production deployments!".format(
                ENVIRONMENT, hostname
            )
        )

    # Additional check: Heroku-specific
    import os

    if os.getenv("DYNO") and ENVIRONMENT != "production":
        logging.critical(
            "[Config] CRITICAL: Running on Heroku (DYNO environment variable detected) "
            "but ENVIRONMENT is not set to 'production'. This is a security risk!"
        )

# Build Credit Costs
# Credits are consumed per cloud build. Cost varies by platform and language.
# Linux builds are cheapest (native); Windows builds use Wine cross-compilation (heavier).
BUILD_COST_LINUX_PYTHON = 1       # Linux native Nuitka build
BUILD_COST_LINUX_NODE = 1         # Linux native yao-pkg build
BUILD_COST_WINDOWS_PYTHON = 2     # Windows cross-compile via Wine (heavier)
BUILD_COST_WINDOWS_NODE = 2       # Windows cross-compile via Wine (heavier)
BUILD_COST_DUAL_PLATFORM = 3      # Windows + Linux in a single job

# Legacy constant — kept for backward-compat references; prefer per-platform constants above
BUILD_COST_STANDARD = 1


def get_build_credit_cost(target_platforms: list, language: str) -> int:
    """Calculate credit cost for a cloud build job.

    Args:
        target_platforms: List of platforms, e.g. ['windows'], ['linux'], ['windows', 'linux']
        language: 'python' or 'nodejs'

    Returns:
        Integer credit cost for this build job.
    """
    platforms = [p.lower() for p in (target_platforms or [])]
    lang = (language or "python").lower()

    has_windows = "windows" in platforms
    has_linux = "linux" in platforms

    # Dual-platform: flat rate regardless of language
    if has_windows and has_linux:
        return BUILD_COST_DUAL_PLATFORM

    if has_windows:
        return BUILD_COST_WINDOWS_NODE if lang == "nodejs" else BUILD_COST_WINDOWS_PYTHON

    if has_linux:
        return BUILD_COST_LINUX_NODE if lang == "nodejs" else BUILD_COST_LINUX_PYTHON

    # Fallback: single credit
    return BUILD_COST_STANDARD


# Subscription Tier Limits
# -1 means unlimited
TIER_LIMITS = {
    "free": {
        "_tier_name": "Free",
        "max_projects": 1,
        "max_licenses_per_project": 50,
        "max_licenses_total": 50,
        "can_sell_licenses": False,
        "cloud_compilation": False,
        "cloud_builds_per_month": 0,
        "credits_per_month": 0,
        "cloud_platforms": ["windows"],
        "webhooks": False,
        "node_support": False,
    },
    "pro": {
        "_tier_name": "Pro",
        "max_projects": -1,
        "max_licenses_per_project": 500,
        "max_licenses_total": 500,
        "can_sell_licenses": True,
        "cloud_compilation": True,
        "cloud_builds_per_month": 25,
        "credits_per_month": 25,
        "cloud_platforms": ["windows", "linux"],
        "webhooks": True,
        "node_support": True,
    },
    "business": {
        "_tier_name": "Business",
        "max_projects": -1,
        "max_licenses_per_project": 5000,
        "max_licenses_total": 5000,
        "can_sell_licenses": True,
        "cloud_compilation": True,
        "cloud_builds_per_month": 100,
        "credits_per_month": 100,
        "cloud_platforms": ["windows", "linux"],
        "webhooks": True,
        "white_label_branding": True,
        "node_support": True,
    },
    "enterprise": {
        "_tier_name": "Enterprise",
        "max_projects": -1,
        "max_licenses_per_project": -1,
        "max_licenses_total": -1,
        "can_sell_licenses": True,
        "cloud_compilation": True,
        "cloud_builds_per_month": -1,
        "credits_per_month": -1,
        "cloud_platforms": ["windows", "linux"],
        "webhooks": True,
        "white_label_branding": True,
        "node_support": True,
    },
}

# Pricing Configuration
PRICING_CONFIG = {
    "free": {
        "name": "Free",
        "price": 0,
        "currency": "USD",
        "features": [
            "1 Project",
            "50 Licenses Total",
            "Local Compilation Only",
            "Python Support",
        ],
    },
    "pro": {
        "name": "Pro",
        "price": 15,
        "currency": "USD",
        "product_id": POLAR_PRODUCT_PRO,
        "features": [
            "Unlimited Projects",
            "500 Licenses",
            "25 Cloud Build Credits/mo",
            "Windows & Linux Cloud Builds",
            "Node.js Support",
            "Offline Leases",
            "No Branding / Splash Screen",
        ],
    },
    "business": {
        "name": "Business",
        "price": 39,
        "currency": "USD",
        "product_id": POLAR_PRODUCT_BUSINESS,
        "features": [
            "5,000 Licenses",
            "100 Cloud Build Credits/mo",
            "Priority Build Queue",
            "White Label Branding",
            "Priority Support",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": "Custom",
        "currency": "USD",
        "features": [
            "Unlimited Licenses",
            "Unlimited Cloud Build Credits",
            "Dedicated Build Runners",
            "White Label Branding",
            "Dedicated Support",
            "Custom SLAs",
            "Security Reviews",
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
    "hwid.suspicious",
    "compilation.started",
    "compilation.completed",
    "compilation.failed",
    "subscription.created",
    "subscription.updated",
    "subscription.canceled",
    "license.purchased",
]
