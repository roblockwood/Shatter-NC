"""WebSocket manager for real-time updates."""
import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket
from datetime import datetime
from app.db.base import SessionLocal
from app.models.machine import Machine

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

        # Send initial status for all machines (from DB + cached polling data)
        try:
            db = SessionLocal()
            try:
                # Get all machines from database
                all_machines = db.query(Machine).all()

                # Clean up cache for deleted machines
                all_machine_ids = {m.id for m in all_machines}
                deleted_ids = [mid for mid in self.last_status.keys() if mid not in all_machine_ids]
                for mid in deleted_ids:
                    del self.last_status[mid]
                    logger.info(f"Cleaned up cache for deleted machine {mid}")

                machines_data = []

                for machine in all_machines:
                    # Start with database info
                    machine_info = {
                        "machine_id": machine.id,
                        "machine_name": machine.name,
                        "ip_address": machine.ip_address,
                        "enabled": machine.enabled,
                        "poll_timestamp": datetime.utcnow().isoformat(),
                    }

                    # Overlay cached polling data if available
                    if machine.id in self.last_status:
                        cached = self.last_status[machine.id]
                        machine_info.update(cached)
                    else:
                        # No polling data yet - assume offline until first poll
                        machine_info["is_online"] = False

                    machines_data.append(machine_info)

                # Send all machines to new client
                await websocket.send_json({
                    "type": "initial_status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "machines": machines_data,
                })
            finally:
                db.close()
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

    def get_machine_status(self, machine_id: int) -> Dict[str, Any]:
        """Get cached status for a specific machine."""
        return self.last_status.get(machine_id, {})
