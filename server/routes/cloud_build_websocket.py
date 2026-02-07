"""
CodeVault Cloud Build - WebSocket Module

Manages WebSocket connections for real-time build log streaming.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect

from database import get_db, release_db

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


def get_build_stage(build: dict) -> tuple:
    """Determine current build stage and progress."""
    status = build.get("status", "pending")
    progress = build.get("progress", 0)
    logs = build.get("logs", [])

    if status == "pending":
        return "Queued", 5
    elif status == "queued":
        return "Waiting for builder", 10
    elif status == "running":
        # Analyze logs for better progress
        if logs:
            log_text = " ".join(logs[-10:]).lower()
            if "compiling" in log_text or "nuitka" in log_text:
                return "Compiling", max(30, min(60, progress))
            elif "packaging" in log_text or "uploading" in log_text:
                return "Packaging", max(60, min(90, progress))
        return "Building", max(20, min(50, progress))
    elif status == "completed":
        return "Complete", 100
    elif status == "failed":
        return "Failed", progress
    elif status == "cancelled":
        return "Cancelled", progress
    else:
        return "Unknown", progress
