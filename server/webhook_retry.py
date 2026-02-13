"""
Webhook retry system for CodeVault API.
Implements exponential backoff retry mechanism for failed webhooks.
"""

import json
import time
import secrets
import hashlib
import hmac
import asyncio
from datetime import timedelta
from typing import Optional, Dict, Any
import logging

import httpx

from database import get_db, release_db
from utils import utc_now
from routes.webhook_routes import validate_webhook_url

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAYS = [60, 300, 900]  # 1 minute, 5 minutes, 15 minutes (exponential backoff)
MAX_FAILURE_COUNT = 10  # Disable webhook after this many consecutive failures
WEBHOOK_TIMEOUT = 10.0  # seconds


class WebhookRetryQueue:
    """Manages retry queue for failed webhooks."""

    @staticmethod
    async def add_to_retry_queue(
        webhook_id: str,
        event: str,
        payload: Dict[str, Any],
        attempt: int = 1,
        last_error: Optional[str] = None,
    ) -> bool:
        """
        Add a failed webhook delivery to the retry queue.

        Args:
            webhook_id: The webhook ID
            event: The event type
            payload: The webhook payload
            attempt: Current retry attempt number (1 = first retry)
            last_error: Error message from last attempt

        Returns:
            True if added to queue, False if max attempts reached
        """
        if attempt > MAX_RETRY_ATTEMPTS:
            logger.warning(
                f"[WebhookRetry] Max retry attempts ({MAX_RETRY_ATTEMPTS}) reached for webhook {webhook_id}. "
                f"Disabling webhook."
            )
            await WebhookRetryQueue._disable_webhook(
                webhook_id, "Max retry attempts exceeded"
            )
            return False

        # Calculate next retry time
        delay_seconds = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
        next_retry_at = utc_now() + timedelta(seconds=delay_seconds)

        conn = await get_db()
        try:
            await conn.execute(
                """
                INSERT INTO webhook_retries (
                    id, webhook_id, event, payload, attempt, next_retry_at, 
                    last_error, created_at, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), 'pending')
                ON CONFLICT (webhook_id, event, payload) DO UPDATE SET
                    attempt = EXCLUDED.attempt,
                    next_retry_at = EXCLUDED.next_retry_at,
                    last_error = EXCLUDED.last_error,
                    status = 'pending',
                    updated_at = NOW()
            """,
                secrets.token_hex(16),
                webhook_id,
                event,
                json.dumps(payload),
                attempt,
                next_retry_at,
                last_error[:500] if last_error else None,
            )

            logger.info(
                f"[WebhookRetry] Added webhook {webhook_id} to retry queue. "
                f"Attempt {attempt}/{MAX_RETRY_ATTEMPTS}, next retry at {next_retry_at}"
            )
            return True

        except Exception as e:
            logger.error(f"[WebhookRetry] Failed to add to retry queue: {e}")
            return False
        finally:
            await release_db(conn)

    @staticmethod
    async def _disable_webhook(webhook_id: str, reason: str):
        """Disable a webhook after too many failures."""
        conn = await get_db()
        try:
            await conn.execute(
                """
                UPDATE webhooks 
                SET is_active = FALSE, disabled_at = NOW(), disabled_reason = $2
                WHERE id = $1
            """,
                webhook_id,
                reason,
            )
            logger.warning(f"[WebhookRetry] Webhook {webhook_id} disabled: {reason}")
        finally:
            await release_db(conn)

    @staticmethod
    async def get_pending_retries(limit: int = 100) -> list:
        """Get pending retries that are due for processing."""
        conn = await get_db()
        try:
            rows = await conn.fetch(
                """
                SELECT r.id, r.webhook_id, r.event, r.payload, r.attempt, r.last_error,
                       w.url, w.secret, w.user_id
                FROM webhook_retries r
                JOIN webhooks w ON r.webhook_id = w.id
                WHERE r.status = 'pending' 
                AND r.next_retry_at <= NOW()
                AND w.is_active = TRUE
                ORDER BY r.next_retry_at ASC
                LIMIT $1
            """,
                limit,
            )
            return [dict(row) for row in rows]
        finally:
            await release_db(conn)

    @staticmethod
    async def mark_retry_completed(
        retry_id: str, success: bool, error_message: Optional[str] = None
    ):
        """Mark a retry as completed or failed."""
        conn = await get_db()
        try:
            if success:
                await conn.execute(
                    """
                    UPDATE webhook_retries 
                    SET status = 'completed', completed_at = NOW(), updated_at = NOW()
                    WHERE id = $1
                """,
                    retry_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE webhook_retries 
                    SET status = 'failed', error_message = $2, updated_at = NOW()
                    WHERE id = $1
                """,
                    retry_id,
                    error_message[:500] if error_message else None,
                )
        finally:
            await release_db(conn)

    @staticmethod
    async def cleanup_old_retries(days: int = 7):
        """Clean up old completed/failed retry records."""
        # Validate days is an integer
        days = int(days)

        conn = await get_db()
        try:
            await conn.execute(
                """
                DELETE FROM webhook_retries 
                WHERE status IN ('completed', 'failed') 
                AND updated_at < NOW() - ($1 * INTERVAL '1 day')
            """,
                days,
            )
            logger.info("[WebhookRetry] Cleaned up old retry records")
        finally:
            await release_db(conn)


async def deliver_webhook_with_retry(
    webhook_id: str,
    url: str,
    secret: Optional[str],
    event: str,
    payload: Dict[str, Any],
    attempt: int = 0,
) -> tuple[bool, Optional[str]]:
    """
    Deliver a webhook with retry logic.

    Args:
        webhook_id: The webhook ID
        url: Target URL
        secret: Webhook secret for signature
        event: Event type
        payload: Payload to send
        attempt: Current attempt number (0 = initial delivery)

    Returns:
        Tuple of (success, error_message)
    """
    # Validate URL before attempting
    is_valid, message = await validate_webhook_url(url)
    if not is_valid:
        error_msg = f"URL validation failed: {message}"
        logger.error(f"[WebhookRetry] {error_msg}")
        return False, error_msg

    # Build payload
    webhook_payload = {
        "event": event,
        "timestamp": utc_now().isoformat(),
        "data": payload,
        "attempt": attempt + 1,  # 1-based for recipient
    }

    # Build headers
    headers = {"Content-Type": "application/json"}
    body_bytes = json.dumps(webhook_payload, sort_keys=True).encode()
    if secret:
        signature = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = signature

    start_time = time.time()
    delivery_id = secrets.token_hex(16)

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
            response = await client.post(url, content=body_bytes, headers=headers)
            delivery_time_ms = int((time.time() - start_time) * 1000)

            success = 200 <= response.status_code < 300

            # Log delivery result
            conn = await get_db()
            try:
                await conn.execute(
                    """
                    INSERT INTO webhook_deliveries (
                        id, webhook_id, event_type, payload, response_status, 
                        response_body, delivery_time_ms, success, created_at, is_retry
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
                """,
                    delivery_id,
                    webhook_id,
                    event,
                    json.dumps(webhook_payload),
                    response.status_code,
                    response.text[:1000] if response.text else None,
                    delivery_time_ms,
                    success,
                    attempt > 0,
                )

                if success:
                    # Reset failure count on success
                    await conn.execute(
                        """
                        UPDATE webhooks 
                        SET last_triggered_at = NOW(), failure_count = 0 
                        WHERE id = $1
                    """,
                        webhook_id,
                    )
                    logger.info(
                        f"[WebhookRetry] Successfully delivered {event} to webhook {webhook_id} "
                        f"(attempt {attempt + 1}, {delivery_time_ms}ms)"
                    )
                    return True, None
                else:
                    # Increment failure count
                    await conn.execute(
                        """
                        UPDATE webhooks 
                        SET last_triggered_at = NOW(), failure_count = failure_count + 1 
                        WHERE id = $1
                    """,
                        webhook_id,
                    )
                    error_msg = f"HTTP {response.status_code}"
                    logger.warning(
                        f"[WebhookRetry] Failed to deliver {event} to webhook {webhook_id} "
                        f"(attempt {attempt + 1}): {error_msg}"
                    )
                    return False, error_msg

            finally:
                await release_db(conn)

    except httpx.TimeoutException:
        error_msg = "Request timeout"
        await _log_delivery_failure(
            webhook_id, delivery_id, event, webhook_payload, error_msg, attempt
        )
        return False, error_msg

    except Exception as e:
        error_msg = str(e)
        await _log_delivery_failure(
            webhook_id, delivery_id, event, webhook_payload, error_msg, attempt
        )
        return False, error_msg


async def _log_delivery_failure(
    webhook_id: str,
    delivery_id: str,
    event: str,
    payload: Dict,
    error: str,
    attempt: int,
):
    """Log a delivery failure to the database."""
    conn = await get_db()
    try:
        await conn.execute(
            """
            INSERT INTO webhook_deliveries (
                id, webhook_id, event_type, payload, response_status, 
                response_body, delivery_time_ms, success, created_at, is_retry
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
        """,
            delivery_id,
            webhook_id,
            event,
            json.dumps(payload),
            0,
            error[:1000],
            0,
            False,
            attempt > 0,
        )

        await conn.execute(
            """
            UPDATE webhooks 
            SET failure_count = failure_count + 1 
            WHERE id = $1
        """,
            webhook_id,
        )

        # Check if we should disable the webhook
        row = await conn.fetchrow(
            "SELECT failure_count FROM webhooks WHERE id = $1", webhook_id
        )
        if row and row["failure_count"] >= MAX_FAILURE_COUNT:
            await WebhookRetryQueue._disable_webhook(
                webhook_id, f"Too many consecutive failures ({MAX_FAILURE_COUNT})"
            )
    finally:
        await release_db(conn)


async def process_retry_queue():
    """
    Background task to process pending webhook retries.
    Should be run periodically (e.g., every minute via cron or asyncio task).
    """
    retries = await WebhookRetryQueue.get_pending_retries(limit=100)

    if not retries:
        return

    logger.info(f"[WebhookRetry] Processing {len(retries)} pending retries")

    tasks = [_process_single_retry(retry) for retry in retries]
    await asyncio.gather(*tasks, return_exceptions=True)


async def _process_single_retry(retry: Dict[str, Any]):
    """Process a single retry from the queue."""
    retry_id = retry["id"]
    webhook_id = retry["webhook_id"]
    attempt = retry["attempt"]

    try:
        payload = (
            json.loads(retry["payload"])
            if isinstance(retry["payload"], str)
            else retry["payload"]
        )

        success, error = await deliver_webhook_with_retry(
            webhook_id=webhook_id,
            url=retry["url"],
            secret=retry["secret"],
            event=retry["event"],
            payload=payload,
            attempt=attempt,
        )

        if success:
            await WebhookRetryQueue.mark_retry_completed(retry_id, success=True)
        else:
            # Schedule next retry
            await WebhookRetryQueue.mark_retry_completed(
                retry_id, success=False, error_message=error
            )

            # Add to queue for next attempt
            await WebhookRetryQueue.add_to_retry_queue(
                webhook_id=webhook_id,
                event=retry["event"],
                payload=payload,
                attempt=attempt + 1,
                last_error=error,
            )

    except Exception as e:
        logger.error(f"[WebhookRetry] Error processing retry {retry_id}: {e}")
        await WebhookRetryQueue.mark_retry_completed(
            retry_id, success=False, error_message=str(e)
        )


async def start_retry_processor(interval_seconds: int = 60):
    """
    Start the background retry processor.
    Runs indefinitely until cancelled.

    Usage:
        asyncio.create_task(start_retry_processor())
    """
    logger.info(
        f"[WebhookRetry] Starting retry processor (interval: {interval_seconds}s)"
    )

    while True:
        try:
            await process_retry_queue()
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("[WebhookRetry] Retry processor stopped")
            break
        except Exception as e:
            logger.error(f"[WebhookRetry] Error in retry processor: {e}")
            await asyncio.sleep(interval_seconds)
