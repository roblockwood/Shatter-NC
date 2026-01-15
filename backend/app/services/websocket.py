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
            
            # Preserve tool table and current tool from cache if new status doesn't have it
            if "tool_table" in cached and "tool_table" not in status_data:
                status_data["tool_table"] = cached["tool_table"]
            if "current_tool" in cached and "current_tool" not in status_data:
                status_data["current_tool"] = cached["current_tool"]
            
            # Preserve macro variables from cache if new status doesn't have it
            if "macros" in cached and "macros" not in status_data:
                status_data["macros"] = cached["macros"]
            if "macros_timestamp" in cached and "macros_timestamp" not in status_data:
                status_data["macros_timestamp"] = cached["macros_timestamp"]
            
            self.last_status[machine_id] = status_data
            
            # Write to Redis cache for persistence across workers and restarts
            try:
                from app.utils.redis_client import get_redis
                redis = get_redis()
                
                # Write full status cache (60s TTL)
                cache_key = f"machine:status:{machine_id}"
                redis.setex(
                    cache_key,
                    60,  # 60 second TTL
                    json.dumps(status_data).encode('utf-8')
                )
                
                # Write extended caches with longer TTLs for stable data
                if "tool_table" in status_data and status_data["tool_table"] is not None:
                    tool_table_key = f"machine:tool_table:{machine_id}"
                    redis.setex(
                        tool_table_key,
                        300,  # 5 minutes
                        json.dumps(status_data["tool_table"]).encode('utf-8')
                    )
                
                if "panel" in status_data and status_data["panel"] is not None:
                    panel_key = f"machine:panel:{machine_id}"
                    redis.setex(
                        panel_key,
                        120,  # 2 minutes
                        json.dumps(status_data["panel"]).encode('utf-8')
                    )
                
                if "program_name" in status_data and status_data["program_name"] is not None:
                    program_name_key = f"machine:program_name:{machine_id}"
                    redis.setex(
                        program_name_key,
                        300,  # 5 minutes
                        status_data["program_name"].encode('utf-8') if isinstance(status_data["program_name"], str) else str(status_data["program_name"]).encode('utf-8')
                    )
            except Exception as e:
                # Log but don't fail if Redis write fails
                logger.warning(f"Failed to write status to Redis cache for machine {machine_id}: {e}")

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
        """Get cached status for a specific machine (in-memory cache)."""
        return self.last_status.get(machine_id, {})
    
    def get_machine_status_from_cache(self, machine_id: int) -> Dict[str, Any]:
        """
        Get cached status for a specific machine from Redis (with fallback to in-memory cache).
        
        This method checks Redis cache first (persists across workers and restarts),
        then falls back to in-memory cache if Redis is unavailable or has cache miss.
        """
        try:
            from app.utils.redis_client import get_redis
            import json
            redis = get_redis()
            cache_key = f"machine:status:{machine_id}"
            cached_data = redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data.decode('utf-8'))
        except Exception as e:
            logger.debug(f"Failed to read from Redis cache for machine {machine_id}, falling back to in-memory cache: {e}")
        
        # Fall back to in-memory cache
        return self.last_status.get(machine_id, {})
