"""
CodeVault Cloud Build - WebSocket Module

Manages WebSocket connections for real-time build log streaming.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for build log streaming."""

    def __init__(self):
        # build_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, build_id: str):
        await websocket.accept()
        if build_id not in self.active_connections:
            self.active_connections[build_id] = []
        self.active_connections[build_id].append(websocket)
        logger.debug(f"[WS] Client connected to build {build_id}")

    def disconnect(self, websocket: WebSocket, build_id: str):
        if build_id in self.active_connections:
            if websocket in self.active_connections[build_id]:
                self.active_connections[build_id].remove(websocket)
            if not self.active_connections[build_id]:
                del self.active_connections[build_id]
        logger.debug(f"[WS] Client disconnected from build {build_id}")

    async def broadcast(self, build_id: str, message: dict):
        """Broadcast a message to all connected clients for a build."""
        if build_id not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[build_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn, build_id)


# Global connection manager instance
ws_manager = ConnectionManager()


async def broadcast_build_update(build_id: str, update_type: str, data: dict):
    """Helper function to broadcast updates to all connected WebSocket clients."""
    await ws_manager.broadcast(
        build_id,
        {
            "type": update_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def get_build_stage(build: dict) -> tuple[str, int]:
    """Calculate build stage and detailed progress from build status, logs, and timing."""
    status = build.get("status", "pending")
    logs = build.get("logs") or []
    started_at = build.get("started_at")
    current_progress = build.get("progress", 0)

    if isinstance(logs, str):
        try:
            logs = json.loads(logs)
        except Exception:
            logs = []

    if status == "pending":
        return "Queued", 5
    elif status == "queued":
        return "Waiting for runner", 8
    elif status == "running":
        # Check logs for stage keywords
        logs_str = " ".join(str(log).lower() for log in logs)
        log_based_progress = 15  # Default
        stage = "Processing"

        if "upload" in logs_str:
            stage = "Uploading artifact"
            log_based_progress = 90
        elif "compil" in logs_str or "nuitka" in logs_str or "pkg" in logs_str:
            stage = "Compiling binary"
            log_based_progress = 55
        elif "inject" in logs_str or "wrapper" in logs_str:
            stage = "Injecting license protection"
            log_based_progress = 35
        elif (
            "dependenc" in logs_str
            or "install" in logs_str
            or "pip" in logs_str
            or "npm" in logs_str
        ):
            stage = "Installing dependencies"
            log_based_progress = 20
        elif "download" in logs_str or "source" in logs_str:
            stage = "Downloading source"
            log_based_progress = 12

        # Time-based progress interpolation for smoother updates
        if started_at:
            try:
                elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
                # Estimate ~3-4 minutes for typical build (180-240 seconds)
                estimated_duration = 210  # 3.5 minutes average
                time_progress = min(85, int((elapsed / estimated_duration) * 85) + 10)

                # Use the maximum of time-based and log-based progress
                # But never exceed current_progress from webhooks if available
                if current_progress and current_progress > 0:
                    # Webhooks provide more accurate progress
                    final_progress = max(
                        current_progress, time_progress, log_based_progress
                    )
                else:
                    final_progress = max(time_progress, log_based_progress)

                return stage, min(
                    95, final_progress
                )  # Cap at 95% until actually complete
            except Exception:
                pass

        # Fallback to log-based or webhook progress
        return stage, max(current_progress or 0, log_based_progress)

    elif status == "completed":
        return "Complete", 100
    elif status == "failed":
        return "Failed", 100
    elif status == "cancelling":
        return "Cancelling", build.get("progress", 0)
    elif status == "cancelled":
        return "Cancelled", 100
    else:
        return "Unknown", 0
