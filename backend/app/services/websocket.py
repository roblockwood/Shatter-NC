"""WebSocket manager for real-time updates."""
import logging
from typing import List, Dict, Any
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from app.db.base import SessionLocal
from app.models.machine import Machine
from app.models.compressor import Compressor

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_status: Dict[int, Dict[str, Any]] = {}  # machine_id -> status
        self.last_compressor_status: Dict[int, Dict[str, Any]] = {}  # compressor_id -> status

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

                all_compressors = db.query(Compressor).all()
                all_cids = {c.id for c in all_compressors}
                for cid in list(self.last_compressor_status.keys()):
                    if cid not in all_cids:
                        del self.last_compressor_status[cid]
                        logger.info(f"Cleaned up cache for deleted compressor {cid}")

                machines_data = []

                for machine in all_machines:
                    # Start with database info
                    machine_info = {
                        "machine_id": machine.id,
                        "machine_name": machine.name,
                        "ip_address": machine.ip_address,
                        "enabled": machine.enabled,
                        "part_display_mode": getattr(machine, "part_display_mode", "parts"),
                        "poll_timestamp": datetime.utcnow().isoformat(),
                        "is_online": False,  # Default to offline
                        "program_name": None,  # Default program name
                    }

                    # Overlay cached polling data if available
                    if machine.id in self.last_status:
                        cached = self.last_status[machine.id]
                        machine_info.update(cached)
                        # Ensure program_name is included from cache
                        if "program_name" in cached:
                            machine_info["program_name"] = cached["program_name"]

                    machines_data.append(machine_info)

                compressors_data = []
                for comp in all_compressors:
                    cinfo = {
                        "asset_kind": "compressor",
                        "compressor_id": comp.id,
                        "compressor_name": comp.name,
                        "ip_address": comp.ip_address,
                        "enabled": comp.enabled,
                        "poll_interval_seconds": comp.poll_interval_seconds,
                        "layout_config": comp.layout_config,
                        "kaeser_connect_base_url": comp.kaeser_connect_base_url,
                        "kaeser_username": comp.kaeser_username,
                        "kaeser_credentials_configured": bool(
                            comp.kaeser_password
                            and comp.kaeser_username
                            and comp.kaeser_connect_base_url
                        ),
                        "poll_timestamp": datetime.utcnow().isoformat(),
                        "is_online": False,
                        "status": "offline",
                        "alarms": [],
                        "metrics": {},
                    }
                    if comp.id in self.last_compressor_status:
                        cinfo.update(self.last_compressor_status[comp.id])
                    compressors_data.append(cinfo)

                # Send all machines to new client
                await websocket.send_json(jsonable_encoder({
                    "type": "initial_status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "machines": machines_data,
                    "compressors": compressors_data,
                }))
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
        # Always cache the status, even if there are no active connections
        # This ensures the status is available for API queries
        machine_id = status_data.get("machine_id")
        if machine_id:
            # Preserve cached data that doesn't change frequently when not in new status
            # This ensures data persists even when connection is temporarily lost
            cached = self.last_status.get(machine_id, {})
            
            # Preserve program_name from cache if new status doesn't have it
            if "program_name" in cached and "program_name" not in status_data:
                status_data["program_name"] = cached["program_name"]
            
            # Preserve panel data from cache if new status doesn't have it
            if "panel" in cached and "panel" not in status_data:
                status_data["panel"] = cached["panel"]
            
            # Preserve alarms from cache if new status doesn't have it (but not if explicitly set to empty)
            if "alarms" in cached and "alarms" not in status_data:
                status_data["alarms"] = cached["alarms"]
            
            # Preserve machine display preferences from cache if not present in new status
            if "part_display_mode" in cached and "part_display_mode" not in status_data:
                status_data["part_display_mode"] = cached["part_display_mode"]

            # Preserve tool table and current tool from cache if new status doesn't have it
            if "tool_table" in cached and "tool_table" not in status_data:
                status_data["tool_table"] = cached["tool_table"]
            if "current_tool" in cached and "current_tool" not in status_data:
                status_data["current_tool"] = cached["current_tool"]
            # Preserve ATC tool list from cache when fast-poll updates omit it
            if "tools" in cached and "tools" not in status_data:
                status_data["tools"] = cached["tools"]
            if "tools_timestamp" in cached and "tools_timestamp" not in status_data:
                status_data["tools_timestamp"] = cached["tools_timestamp"]
            
            # Preserve macro variables from cache if new status doesn't have it
            if "macros" in cached and "macros" not in status_data:
                status_data["macros"] = cached["macros"]
            if "macros_timestamp" in cached and "macros_timestamp" not in status_data:
                status_data["macros_timestamp"] = cached["macros_timestamp"]
            # Preserve last successful fast poll time when partial updates omit it (e.g. tool-only broadcast)
            if "last_successful_poll_at" in cached and "last_successful_poll_at" not in status_data:
                status_data["last_successful_poll_at"] = cached["last_successful_poll_at"]
            
            self.last_status[machine_id] = status_data

        if not self.active_connections:
            return

        message = {
            "type": "status_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": status_data,
        }

        # Send to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(jsonable_encoder(message))
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_compressor_status(self, status_data: Dict[str, Any]):
        """Broadcast compressor status; cache by compressor_id (no CNC merge rules)."""
        cid = status_data.get("compressor_id")
        if cid is not None:
            self.last_compressor_status[cid] = status_data

        if not self.active_connections:
            return

        message = {
            "type": "compressor_status_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": status_data,
        }
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(jsonable_encoder(message))
            except Exception as e:
                logger.error(f"Error sending compressor status to WebSocket: {e}")
                disconnected.append(connection)
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
        """Get cached status for a specific machine (in-memory cache)."""
        return self.last_status.get(machine_id, {})
    
    def get_machine_status_from_cache(self, machine_id: int) -> Dict[str, Any]:
        """Get cached status for a specific machine (in-memory cache)."""
        return self.last_status.get(machine_id, {})

    def get_compressor_status(self, compressor_id: int) -> Dict[str, Any]:
        """Get cached compressor status (in-memory cache)."""
        return self.last_compressor_status.get(compressor_id, {})

    def pop_compressor_cache(self, compressor_id: int) -> None:
        self.last_compressor_status.pop(compressor_id, None)
