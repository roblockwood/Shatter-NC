"""WebSocket manager for real-time updates."""
import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_status: Dict[int, Dict[str, Any]] = {}  # machine_id -> status

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send initial status for all machines
        if self.last_status:
            try:
                await websocket.send_json({
                    "type": "initial_status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "machines": list(self.last_status.values()),
                })
            except Exception as e:
                logger.error(f"Error sending initial status: {e}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast_status(self, status_data: Dict[str, Any]):
        """Broadcast machine status to all connected clients."""
        if not self.active_connections:
            return

        machine_id = status_data.get("machine_id")
        if machine_id:
            self.last_status[machine_id] = status_data

        message = {
            "type": "status_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": status_data,
        }

        # Send to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
