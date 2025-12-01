"""WebSocket endpoints for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# WebSocket manager will be injected from main.py
websocket_manager = None


def set_websocket_manager(manager):
    """Set the WebSocket manager instance."""
    global websocket_manager
    websocket_manager = manager


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time machine status updates.

    Clients connect to this endpoint and receive:
    - Initial status for all machines
    - Real-time status updates as machines are polled

    Message format:
    {
        "type": "status_update" | "initial_status",
        "timestamp": "2024-01-01T00:00:00",
        "data": {...}  # or "machines": [...]
    }
    """
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not initialized")
        return

    await websocket_manager.connect(websocket)

    try:
        # Keep connection alive and handle client messages
        while True:
            # Receive messages from client (e.g., subscriptions, filters)
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")

            # For now, just acknowledge
            # Future: handle subscription to specific machines, etc.

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)
