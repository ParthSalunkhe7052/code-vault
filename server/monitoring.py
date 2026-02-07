"""
Monitoring and alerting system for CodeVault.
Provides health checks, metrics collection, and alerting capabilities.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Callable, List
import json

from database import get_db, release_db, check_database_health

logger = logging.getLogger(__name__)


class HealthMonitor:
    """System health monitoring and alerting."""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.alert_handlers: List[Callable] = []
        self.metrics: Dict[str, List[Dict]] = {}
        self.last_alert: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(
            minutes=5
        )  # Don't alert more than every 5 minutes

    def register_check(self, name: str, check_func: Callable, critical: bool = False):
        """Register a health check function."""
        self.checks[name] = {
            "func": check_func,
            "critical": critical,
            "last_status": None,
            "last_check": None,
        }

    def register_alert_handler(self, handler: Callable):
        """Register an alert handler (e.g., email, webhook, Slack)."""
        self.alert_handlers.append(handler)

    async def run_health_checks(self) -> Dict:
        """Run all registered health checks."""
        results = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for name, check in self.checks.items():
            try:
                start_time = time.time()
                status = await check["func"]()
                response_time = time.time() - start_time

                check["last_status"] = status
                check["last_check"] = datetime.now(timezone.utc)

                results["checks"][name] = {
                    "status": status.get("status", "unknown"),
                    "response_time_ms": round(response_time * 1000, 2),
                    "details": status,
                }

                # Check if status changed to unhealthy
                if status.get("status") != "healthy":
                    if check["critical"]:
                        results["status"] = "critical"
                    elif results["status"] == "healthy":
                        results["status"] = "degraded"

                    await self._trigger_alert(name, status)

            except Exception as e:
                logger.error(f"[HealthCheck] Error running check '{name}': {e}")
                results["checks"][name] = {"status": "error", "error": str(e)}
                if check["critical"]:
                    results["status"] = "critical"

        return results

    async def _trigger_alert(self, check_name: str, status: Dict):
        """Trigger alerts for failed health checks."""
        now = datetime.now(timezone.utc)

        # Check cooldown
        if check_name in self.last_alert:
            if now - self.last_alert[check_name] < self.alert_cooldown:
                return

        self.last_alert[check_name] = now

        alert_data = {
            "type": "health_check_failed",
            "check": check_name,
            "status": status,
            "timestamp": now.isoformat(),
            "message": f"Health check '{check_name}' failed: {status.get('message', 'Unknown error')}",
        }

        # Log the alert
        logger.error(f"[ALERT] {alert_data['message']}")

        # Send to all registered handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert_data)
            except Exception as e:
                logger.error(f"[ALERT] Failed to send alert via handler: {e}")

    def record_metric(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(
            {
                "value": value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tags": tags or {},
            }
        )

        # Keep only last 1000 data points per metric
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]

    def get_metrics(
        self, name: Optional[str] = None, duration_minutes: int = 60
    ) -> Dict:
        """Get recorded metrics."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)

        if name:
            return {
                name: [
                    m
                    for m in self.metrics.get(name, [])
                    if datetime.fromisoformat(m["timestamp"]) > cutoff
                ]
            }

        return {
            k: [m for m in v if datetime.fromisoformat(m["timestamp"]) > cutoff]
            for k, v in self.metrics.items()
        }


# Global health monitor instance
health_monitor = HealthMonitor()


async def database_health_check() -> Dict:
    """Check database health."""
    return await check_database_health()


async def redis_health_check() -> Dict:
    """Check Redis health."""
    from config import REDIS_URL

    if not REDIS_URL:
        return {"status": "degraded", "message": "Redis not configured"}

    try:
        # Try to connect to Redis
        import redis.asyncio as redis

        client = redis.from_url(REDIS_URL, socket_connect_timeout=5)
        await client.ping()
        await client.close()

        return {"status": "healthy", "message": "Redis connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Redis connection failed: {str(e)}"}


async def webhook_queue_health_check() -> Dict:
    """Check webhook retry queue health."""
    conn = await get_db()
    try:
        # Check pending retries
        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM webhook_retries WHERE status = 'pending'"
        )

        # Check failed retries in last hour
        failed = await conn.fetchval(
            """SELECT COUNT(*) FROM webhook_retries 
               WHERE status = 'failed' 
               AND updated_at > NOW() - INTERVAL '1 hour'"""
        )

        status = "healthy"
        if failed > 100:
            status = "degraded"
        if pending > 1000:
            status = "critical"

        return {
            "status": status,
            "pending_retries": pending,
            "failed_last_hour": failed,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await release_db(conn)


# Alert handlers
async def log_alert_handler(alert_data: Dict):
    """Simple logging alert handler."""
    logger.warning(f"[ALERT-HANDLER] {json.dumps(alert_data)}")


async def webhook_alert_handler(alert_data: Dict):
    """Send alerts to configured webhook."""
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()

    if not webhook_url:
        logger.warning(
            "[ALERT] ALERT_WEBHOOK_URL not configured, skipping webhook alert"
        )
        return

    if not webhook_url.startswith("http"):
        logger.warning(
            f"[ALERT] Invalid webhook URL (must start with http): {webhook_url[:20]}..."
        )
        return

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                webhook_url,
                json={"text": f"🚨 CodeVault Alert: {alert_data['message']}"},
            )
    except Exception as e:
        logger.error(f"[ALERT] Failed to send webhook alert: {e}")


def initialize_health_monitor():
    """Initialize health monitoring system."""
    # Register health checks
    health_monitor.register_check("database", database_health_check, critical=True)
    health_monitor.register_check("redis", redis_health_check)
    health_monitor.register_check("webhook_queue", webhook_queue_health_check)

    # Register alert handlers
    health_monitor.register_alert_handler(log_alert_handler)
    health_monitor.register_alert_handler(webhook_alert_handler)

    logger.info("[HealthMonitor] Health monitoring system initialized")


async def start_health_monitoring(interval_seconds: int = 60):
    """
    Start health monitoring background task.

    Usage:
        asyncio.create_task(start_health_monitoring())
    """
    initialize_health_monitor()

    while True:
        try:
            results = await health_monitor.run_health_checks()

            if results["status"] != "healthy":
                logger.warning(f"[HealthMonitor] System health: {results['status']}")

            # Record overall health metric
            health_monitor.record_metric(
                "system_health",
                1 if results["status"] == "healthy" else 0,
                {"status": results["status"]},
            )

        except Exception as e:
            logger.error(f"[HealthMonitor] Error in health monitoring: {e}")

        await asyncio.sleep(interval_seconds)


# API endpoint for health check
async def get_health_status() -> Dict:
    """Get current health status (for API endpoint)."""
    return await health_monitor.run_health_checks()
