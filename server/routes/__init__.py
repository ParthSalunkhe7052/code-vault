"""
Routes package for CodeVault API.
Contains all endpoint definitions organized by feature area.
"""

from routes.stripe_routes import router as stripe_router
from routes.auth_routes import router as auth_router
from routes.webhook_routes import router as webhook_router, trigger_webhook
from routes.license_routes import router as license_router
from routes.admin_routes import router as admin_router
from routes.analytics_routes import router as analytics_router

__all__ = [
    "stripe_router",
    "auth_router",
    "webhook_router",
    "trigger_webhook",
    "license_router",
    "admin_router",
    "analytics_router",
]
