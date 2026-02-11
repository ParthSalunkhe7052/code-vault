"""
Audit logging for CodeVault CLI build operations.

Sends build events to the server for security monitoring and analytics.
All logging failures are silent to avoid blocking builds.
"""

import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import requests

from cli_config import get_api_base, get_headers


class AuditLogger:
    """Handles audit logging for build operations."""

    # Singleton instance
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._event_queue = []
        self._lock = threading.Lock()
        self._max_queue_size = 50

    def log_build_start(
        self,
        project_id: Optional[str],
        language: str,
        license_mode: str,
        obfuscate_enabled: bool,
        lease_enabled: bool,
        source_file: Optional[str] = None,
    ) -> None:
        """Log the start of a build operation."""
        self._queue_event(
            {
                "event_type": "build_start",
                "project_id": project_id,
                "language": language,
                "license_mode": license_mode,
                "obfuscate_enabled": obfuscate_enabled,
                "lease_enabled": lease_enabled,
                "source_file": source_file,
                "timestamp": time.time(),
            }
        )

    def log_build_success(
        self,
        project_id: Optional[str],
        language: str,
        duration_ms: int,
        output_size_bytes: int,
        license_mode: str,
    ) -> None:
        """Log a successful build."""
        self._queue_event(
            {
                "event_type": "build_success",
                "project_id": project_id,
                "language": language,
                "duration_ms": duration_ms,
                "output_size_bytes": output_size_bytes,
                "license_mode": license_mode,
                "timestamp": time.time(),
            }
        )

    def log_build_failure(
        self,
        project_id: Optional[str],
        language: str,
        error_message: str,
        error_type: str,
        license_mode: str,
    ) -> None:
        """Log a failed build."""
        # Truncate very long error messages
        if len(error_message) > 500:
            error_message = error_message[:500] + "... (truncated)"

        self._queue_event(
            {
                "event_type": "build_failure",
                "project_id": project_id,
                "language": language,
                "error_message": error_message,
                "error_type": error_type,
                "license_mode": license_mode,
                "timestamp": time.time(),
            }
        )

    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log a security-related event (e.g., path traversal attempt)."""
        self._queue_event(
            {
                "event_type": f"security_{event_type}",
                "details": details,
                "timestamp": time.time(),
            }
        )

    def log_obfuscation_stats(
        self, files_processed: int, files_failed: int, duration_ms: int
    ) -> None:
        """Log obfuscation statistics."""
        self._queue_event(
            {
                "event_type": "obfuscation_stats",
                "files_processed": files_processed,
                "files_failed": files_failed,
                "duration_ms": duration_ms,
                "timestamp": time.time(),
            }
        )

    def _queue_event(self, event: Dict[str, Any]) -> None:
        """Add event to queue for async sending."""
        with self._lock:
            if len(self._event_queue) >= self._max_queue_size:
                # Drop oldest event to prevent memory issues
                self._event_queue.pop(0)
            self._event_queue.append(event)

        # Try to send immediately in background
        self._try_send_events()

    def _try_send_events(self) -> None:
        """Attempt to send queued events to server (non-blocking)."""
        # Get a copy of events to send
        with self._lock:
            if not self._event_queue:
                return
            events_to_send = self._event_queue.copy()
            self._event_queue.clear()

        # Try to send (with timeout to avoid blocking)
        try:
            thread = threading.Thread(
                target=self._send_events_sync, args=(events_to_send,), daemon=True
            )
            thread.start()
        except Exception:
            # Silently fail - never block the user's workflow
            pass

    def _send_events_sync(self, events: list) -> None:
        """Send events synchronously (runs in background thread)."""
        try:
            api_url = get_api_base()
            headers = get_headers()

            if not headers:
                return  # Not logged in, can't send

            # Filter out None values and prepare payload
            payload = {
                "events": events,
                "client_time": datetime.now(timezone.utc).isoformat(),
            }

            # Use short timeout to avoid hanging (fire-and-forget)
            requests.post(
                f"{api_url}/build/audit",
                json=payload,
                headers=headers,
                timeout=5,
            )

            # Don't care about response, just that it was sent
            # If it fails, we silently drop the events

        except requests.exceptions.Timeout:
            # Server too slow, drop events
            pass
        except requests.exceptions.ConnectionError:
            # Can't reach server, drop events
            pass
        except Exception:
            # Any other error, drop events silently
            pass


# Convenience module-level functions
def log_build_start(
    project_id: Optional[str] = None,
    language: str = "python",
    license_mode: str = "GENERIC_BUILD",
    obfuscate_enabled: bool = False,
    lease_enabled: bool = False,
    source_file: Optional[str] = None,
) -> None:
    """Log build start."""
    AuditLogger().log_build_start(
        project_id,
        language,
        license_mode,
        obfuscate_enabled,
        lease_enabled,
        source_file,
    )


def log_build_success(
    project_id: Optional[str],
    language: str,
    duration_ms: int,
    output_size_bytes: int,
    license_mode: str,
) -> None:
    """Log build success."""
    AuditLogger().log_build_success(
        project_id, language, duration_ms, output_size_bytes, license_mode
    )


def log_build_failure(
    project_id: Optional[str],
    language: str,
    error_message: str,
    error_type: str,
    license_mode: str,
) -> None:
    """Log build failure."""
    AuditLogger().log_build_failure(
        project_id, language, error_message, error_type, license_mode
    )


def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log security event."""
    AuditLogger().log_security_event(event_type, details)


def log_obfuscation_stats(
    files_processed: int, files_failed: int, duration_ms: int
) -> None:
    """Log obfuscation statistics."""
    AuditLogger().log_obfuscation_stats(files_processed, files_failed, duration_ms)
