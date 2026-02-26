"""
Webhook routes for CodeVault API.
Extracted from main.py for modularity.
"""

import json
import time
import secrets
import hashlib
import hmac
import ipaddress
import logging
import socket
import asyncio
from typing import Optional, List
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import httpx

from utils import get_current_user, utc_now, sanitize_log_message, get_user_tier_limits
from database import get_db, release_db
from models import WebhookCreateRequest
from middleware.tier_enforcement import requires_feature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

WEBHOOK_EVENTS = [
    "license.created",
    "license.validated",
    "license.revoked",
    "license.expired",
    "hwid.bound",
    "hwid.reset",
    "hwid.suspicious",  # O9 FIX: fired when HWID heuristics flag a suspicious pattern
    "compilation.started",
    "compilation.completed",
    "compilation.failed",
    "tamper.alert",  # Fired when license validation fails due to tampering
]

# Blocked hostnames and IP ranges for SSRF protection
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",  # GCP metadata
    "169.254.169.254",  # AWS/Azure/GCP metadata service
}


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_reserved
            or ip.is_link_local
            or ip.is_multicast
        )
    except ValueError:
        return False


async def validate_webhook_url(url: str) -> tuple[bool, str]:
    """Validate webhook URL with immediate IP resolution.

    H2 FIX: socket.getaddrinfo is a blocking syscall. Calling it directly
    from an async handler stalls the entire event loop for the DNS RTT
    (typically 10-100ms, up to seconds on slow resolvers). We offload it
    to the default thread-pool executor via run_in_executor so the event
    loop remains unblocked while waiting for DNS.

    Returns:
        Tuple of (is_valid, error_message)
    """
    import asyncio
    from urllib.parse import urlparse

    if not url:
        return False, "URL cannot be empty"

    # Must be http or https
    if not url.startswith(("http://", "https://")):
        return False, "Webhook URL must start with http:// or https://"

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        return False, "Invalid URL: no hostname"

    # Check .local TLD
    hostname_lower = hostname.lower()
    if hostname_lower.endswith(".local"):
        return False, "Webhook URL cannot target .local domains"

    # Check known dangerous hostnames
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, f"Webhook URL cannot target {hostname_lower}"

    # Reasonable length limit (check before DNS to fail fast)
    if len(url) > 2000:
        return False, "URL is too long (max 2000 characters)"

    # H2 FIX: Offload blocking DNS resolution to thread pool executor
    port = parsed.port or 443
    loop = asyncio.get_event_loop()
    try:
        resolved = await loop.run_in_executor(
            None,
            lambda: socket.getaddrinfo(hostname, port, socket.AF_UNSPEC),
        )
    except socket.gaierror as e:
        return False, f"Cannot resolve hostname '{hostname}': {e}"

    # Check each resolved IP
    for family, _, _, _, sockaddr in resolved:
        ip_str = sockaddr[0]
        if is_private_ip(ip_str):
            return False, f"Webhook resolves to private IP: {ip_str}"

    return True, "Valid"


def validate_webhook_url_legacy(url: str) -> tuple[bool, str]:
    """Validate webhook URL for SSRF protection (synchronous version for non-async contexts).

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    # Must be http or https
    if not url.startswith(("http://", "https://")):
        return False, "Webhook URL must start with http:// or https://"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a valid hostname"

    # Block known dangerous hostnames
    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, f"Webhook URL cannot target {hostname_lower} (internal address)"

    # Check if hostname is an IP address
    try:
        if is_private_ip(hostname):
            return False, f"Webhook URL cannot target private IP address: {hostname}"
    except ValueError:
        # It's a hostname, not an IP - try to resolve it
        try:
            # Resolve hostname to check if it points to a private IP
            resolved_ips = socket.getaddrinfo(
                hostname, parsed.port or 443, socket.AF_UNSPEC
            )
            for family, _, _, _, sockaddr in resolved_ips:
                ip_str = sockaddr[0]
                if is_private_ip(ip_str):
                    return (
                        False,
                        f"Webhook URL hostname resolves to private IP: {ip_str}",
                    )
        except socket.gaierror:
            # Can't resolve - let it fail at request time
            pass

    # Block .local TLD explicitly
    if hostname_lower.endswith(".local"):
        return False, "Webhook URL cannot target .local domains"

    # Reasonable length limit
    if len(url) > 2000:
        return False, "URL is too long (max 2000 characters)"

    return True, ""


class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=500)
    events: Optional[List[str]] = None
    secret: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


async def _deliver_webhook(
    client: httpx.AsyncClient, webhook: dict, event: str, payload: dict, conn
):
    """Internal helper to deliver a single webhook and log results."""
    webhook_id = webhook["id"]
    url = webhook["url"]
    secret = webhook["secret"]

    # RE-VALIDATE immediately before making the HTTP request
    is_valid, message = await validate_webhook_url(url)
    if not is_valid:
        logger.error(
            f"[Webhook] Pre-request validation failed for {webhook_id}: {message}"
        )
        return

    webhook_payload = {
        "event": event,
        "timestamp": utc_now().isoformat(),
        "data": payload,
    }

    headers = {"Content-Type": "application/json"}
    if secret:
        payload_str = json.dumps(webhook_payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(), payload_str.encode(), hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = signature

    start_time = time.time()
    delivery_id = secrets.token_hex(16)

    try:
        response = await client.post(url, json=webhook_payload, headers=headers)
        delivery_time_ms = int((time.time() - start_time) * 1000)

        success = 200 <= response.status_code < 300
        await conn.execute(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at, is_retry)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
        """,
            delivery_id,
            webhook_id,
            event,
            json.dumps(webhook_payload),
            response.status_code,
            response.text[:1000] if response.text else None,
            delivery_time_ms,
            success,
            False,
        )

        if success:
            await conn.execute(
                "UPDATE webhooks SET last_triggered_at = NOW(), failure_count = 0 WHERE id = $1",
                webhook_id,
            )
        else:
            await conn.execute(
                "UPDATE webhooks SET last_triggered_at = NOW(), failure_count = failure_count + 1 WHERE id = $1",
                webhook_id,
            )
            # Schedule retry for non-2xx responses
            from webhook_retry import WebhookRetryQueue

            await WebhookRetryQueue.add_to_retry_queue(
                webhook_id=webhook_id,
                event=event,
                payload=payload,
                attempt=1,
                last_error=f"HTTP {response.status_code}",
            )

    except Exception as e:
        delivery_time_ms = int((time.time() - start_time) * 1000)
        error_str = str(e)
        await conn.execute(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at, is_retry)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
        """,
            delivery_id,
            webhook_id,
            event,
            json.dumps(webhook_payload),
            0,
            error_str[:1000],
            delivery_time_ms,
            False,
            False,
        )

        await conn.execute(
            "UPDATE webhooks SET failure_count = failure_count + 1 WHERE id = $1",
            webhook_id,
        )
        safe_url = sanitize_log_message(url)
        safe_error = sanitize_log_message(error_str)
        logger.error(f"[Webhook] Failed to deliver {event} to {safe_url}: {safe_error}")

        # Schedule retry for failed deliveries
        from webhook_retry import WebhookRetryQueue

        await WebhookRetryQueue.add_to_retry_queue(
            webhook_id=webhook_id,
            event=event,
            payload=payload,
            attempt=1,
            last_error=error_str,
        )


async def trigger_webhook(user_id: str, event: str, payload: dict):
    """
    Send webhook notifications for an event.
    Fetches all active webhooks for the user subscribed to this event,
    sends HTTP POST requests in parallel, and logs delivery results.
    """
    conn = await get_db()
    try:
        rows = await conn.fetch(
            """
            SELECT id, url, secret, events FROM webhooks
            WHERE user_id = $1 AND is_active = TRUE
        """,
            user_id,
        )

        to_trigger = []
        for webhook in rows:
            events = webhook["events"]
            if isinstance(events, str):
                try:
                    events = json.loads(events)
                except Exception:
                    events = []

            if event in events:
                to_trigger.append(webhook)

        if not to_trigger:
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
                _deliver_webhook(client, webhook, event, payload, conn)
                for webhook in to_trigger
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        safe_event = sanitize_log_message(event)
        safe_error = sanitize_log_message(str(e))
        logger.error(
            f"[Webhook] Error triggering webhooks for {safe_event}: {safe_error}"
        )
    finally:
        await release_db(conn)


@router.get("")
async def list_webhooks(user: dict = Depends(get_current_user)):
    """List all webhooks for the current user."""
    conn = await get_db()
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, url, events, is_active, last_triggered_at, failure_count, created_at,
                   disabled_at, disabled_reason
            FROM webhooks WHERE user_id = $1 ORDER BY created_at DESC
        """,
            user["id"],
        )

        result = []
        for w in rows:
            events = w["events"]
            if isinstance(events, str):
                try:
                    events = json.loads(events)
                except Exception:
                    events = []
            result.append(
                {
                    "id": w["id"],
                    "name": w["name"],
                    "url": w["url"],
                    "events": events,
                    "is_active": bool(w["is_active"]),
                    "last_triggered_at": w["last_triggered_at"].isoformat()
                    if w["last_triggered_at"]
                    else None,
                    "failure_count": w["failure_count"] or 0,
                    "created_at": w["created_at"].isoformat()
                    if w["created_at"]
                    else None,
                    "disabled_at": w["disabled_at"].isoformat()
                    if w["disabled_at"]
                    else None,
                    "disabled_reason": w["disabled_reason"],
                }
            )
        return result
    finally:
        await release_db(conn)


@router.post("")
async def create_webhook(
    data: WebhookCreateRequest, user: dict = Depends(get_current_user)
):
    """Create a new webhook. Requires 'webhooks' feature on tier.

    H9 FIX: Tier check and INSERT are now performed inside a single transaction
    with pg_advisory_xact_lock to prevent TOCTOU races where two concurrent
    requests both pass the tier check before either has written the row.
    """
    invalid_events = [e for e in data.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid_events}")

    # SSRF protection: Validate webhook URL before acquiring DB connection
    is_valid, error_msg = await validate_webhook_url(data.url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    conn = await get_db()
    try:
        async with conn.transaction():
            # Advisory lock keyed on the user_id to serialize concurrent webhook creations
            # for the same user. hash() is deterministic within a process; use sha256 for
            # a stable 63-bit integer that fits in pg_advisory_xact_lock's bigint param.
            import hashlib as _hl
            lock_key = int(_hl.sha256(user["id"].encode()).hexdigest()[:15], 16)
            await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

            # Tier check inside the lock — prevents TOCTOU
            limits = await get_user_tier_limits(user["id"], conn)
            if not limits.get("webhooks", False):
                raise HTTPException(
                    status_code=403,
                    detail="Webhooks are not available on your current plan. Please upgrade."
                )

            webhook_id = secrets.token_hex(16)
            events_json = json.dumps(data.events)

            await conn.execute(
                """
                INSERT INTO webhooks (id, user_id, name, url, secret, events, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """,
                webhook_id,
                user["id"],
                data.name,
                data.url,
                data.secret,
                events_json,
            )

        return {
            "id": webhook_id,
            "name": data.name,
            "url": data.url,
            "events": data.events,
            "is_active": True,
            "last_triggered_at": None,
            "failure_count": 0,
            "created_at": utc_now().isoformat(),
        }
    finally:
        await release_db(conn)


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Get a specific webhook."""
    conn = await get_db()
    try:
        row = await conn.fetchrow(
            """
            SELECT id, name, url, events, secret, is_active, last_triggered_at, failure_count, created_at
            FROM webhooks WHERE id = $1 AND user_id = $2
        """,
            webhook_id,
            user["id"],
        )

        if not row:
            raise HTTPException(status_code=404, detail="Webhook not found")

        events = row["events"]
        if isinstance(events, str):
            try:
                events = json.loads(events)
            except Exception:
                events = []

        return {
            "id": row["id"],
            "name": row["name"],
            "url": row["url"],
            "events": events,
            "secret": row["secret"],
            "is_active": bool(row["is_active"]),
            "last_triggered_at": row["last_triggered_at"].isoformat()
            if row["last_triggered_at"]
            else None,
            "failure_count": row["failure_count"] or 0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
    finally:
        await release_db(conn)


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str, data: WebhookUpdateRequest, user: dict = Depends(get_current_user)
):
    """Update a webhook.

    O6 FIX: Removed unreachable dead-code ALLOWED_COLUMNS branches.
    The set was static and the membership checks could never be False, so the
    'Security error' branches were dead code. The actual injection guard is the
    use of parameterised queries — column names are hardcoded literals, not
    interpolated from user input.
    """
    conn = await get_db()
    try:
        exists = await conn.fetchrow(
            "SELECT id FROM webhooks WHERE id = $1 AND user_id = $2",
            webhook_id,
            user["id"],
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")

        updates = []
        params = []
        param_count = 1

        if data.name is not None:
            updates.append("name = $" + str(param_count))
            params.append(data.name)
            param_count += 1
        if data.url is not None:
            # SSRF protection: Validate webhook URL
            is_valid, error_msg = await validate_webhook_url(data.url)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            updates.append("url = $" + str(param_count))
            params.append(data.url)
            param_count += 1
        if data.events is not None:
            invalid_events = [e for e in data.events if e not in WEBHOOK_EVENTS]
            if invalid_events:
                raise HTTPException(
                    status_code=400, detail=f"Invalid events: {invalid_events}"
                )
            updates.append("events = $" + str(param_count))
            params.append(json.dumps(data.events))
            param_count += 1
        if data.secret is not None:
            updates.append("secret = $" + str(param_count))
            params.append(data.secret)
            param_count += 1
        if data.is_active is not None:
            updates.append("is_active = $" + str(param_count))
            params.append(data.is_active)
            param_count += 1

        if updates:
            updates.append("updated_at = NOW()")
            params.append(webhook_id)
            query = (
                f"UPDATE webhooks SET {', '.join(updates)} WHERE id = ${param_count}"
            )
            await conn.execute(query, *params)

        return await get_webhook(webhook_id, user)
    finally:
        await release_db(conn)


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Delete a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow(
            "SELECT id FROM webhooks WHERE id = $1 AND user_id = $2",
            webhook_id,
            user["id"],
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")

        await conn.execute("DELETE FROM webhooks WHERE id = $1", webhook_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)


@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """Get delivery history for a webhook."""
    conn = await get_db()
    try:
        exists = await conn.fetchrow(
            "SELECT id FROM webhooks WHERE id = $1 AND user_id = $2",
            webhook_id,
            user["id"],
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Webhook not found")

        rows = await conn.fetch(
            """
            SELECT id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at
            FROM webhook_deliveries WHERE webhook_id = $1
            ORDER BY created_at DESC LIMIT $2
        """,
            webhook_id,
            limit,
        )

        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload"]) if row["payload"] else None,
                "response_status": row["response_status"],
                "response_body": row["response_body"],
                "delivery_time_ms": row["delivery_time_ms"],
                "success": row["success"],
                "created_at": row["created_at"].isoformat()
                if row["created_at"]
                else None,
            }
            for row in rows
        ]
    finally:
        await release_db(conn)


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Test a webhook by sending a test payload."""
    conn = await get_db()
    try:
        webhook = await conn.fetchrow(
            "SELECT id, url, secret FROM webhooks WHERE id = $1 AND user_id = $2",
            webhook_id,
            user["id"],
        )
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        url = webhook["url"]
        secret = webhook["secret"]

        # RE-VALIDATE immediately before making the HTTP request
        is_valid, message = await validate_webhook_url(url)
        if not is_valid:
            logger.error(
                f"[Webhook Test] Pre-request validation failed for {webhook_id}: {message}"
            )
            raise HTTPException(
                status_code=400, detail=f"Webhook URL validation failed: {message}"
            )

        test_payload = {
            "event": "test",
            "timestamp": utc_now().isoformat(),
            "data": {
                "message": "This is a test webhook from CodeVault",
                "webhook_id": webhook_id,
            },
        }

        headers = {"Content-Type": "application/json"}
        if secret:
            payload_str = json.dumps(test_payload, sort_keys=True)
            signature = hmac.new(
                secret.encode(), payload_str.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        start_time = time.time()
        delivery_id = secrets.token_hex(16)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=test_payload, headers=headers)
                delivery_time_ms = int((time.time() - start_time) * 1000)
                success = 200 <= response.status_code < 300

                await conn.execute(
                    """
                    INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """,
                    delivery_id,
                    webhook_id,
                    "test",
                    json.dumps(test_payload),
                    response.status_code,
                    response.text[:1000] if response.text else None,
                    delivery_time_ms,
                    success,
                )

                await conn.execute(
                    "UPDATE webhooks SET last_triggered_at = NOW(), failure_count = 0 WHERE id = $1",
                    webhook_id,
                )

                if success:
                    return {
                        "status": "success",
                        "message": f"Test webhook sent successfully! Response: {response.status_code}",
                        "delivery_time_ms": delivery_time_ms,
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Webhook returned non-2xx status: {response.status_code}",
                        "delivery_time_ms": delivery_time_ms,
                    }

        except Exception as e:
            delivery_time_ms = int((time.time() - start_time) * 1000)
            await conn.execute(
                """
                INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, response_status, response_body, delivery_time_ms, success, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """,
                delivery_id,
                webhook_id,
                "test",
                json.dumps(test_payload),
                0,
                str(e)[:1000],
                delivery_time_ms,
                False,
            )

            await conn.execute(
                "UPDATE webhooks SET failure_count = failure_count + 1 WHERE id = $1",
                webhook_id,
            )
            # Security: Log error details server-side, return generic message to client
            logger.error(
                f"[Webhook Test] Failed to send webhook {webhook_id}: {sanitize_log_message(str(e))}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to send test webhook. Please check the URL and try again.",
            )
    finally:
        await release_db(conn)


@router.get("/events/list")
async def get_webhook_events():
    """Get list of available webhook events with descriptions."""
    descriptions = {
        "license.created": "Triggered when a new license is created",
        "license.validated": "Triggered when a license is successfully validated",
        "license.revoked": "Triggered when a license is revoked",
        "license.expired": "Triggered when a license expires during validation",
        "hwid.bound": "Triggered when a new hardware ID is bound to a license",
        "hwid.reset": "Triggered when hardware bindings are reset for a license",
        "hwid.suspicious": "Triggered when a hardware ID matches suspicious/VM patterns",
        "compilation.started": "Triggered when a compilation job starts",
        "compilation.completed": "Triggered when a compilation job completes successfully",
        "compilation.failed": "Triggered when a compilation job fails",
    }
    return {"events": WEBHOOK_EVENTS, "descriptions": descriptions}
