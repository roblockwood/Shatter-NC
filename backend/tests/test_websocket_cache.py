"""Tests for WebSocket manager in-memory cache."""
import pytest
from app.services.websocket import WebSocketManager


def test_get_machine_status_from_cache_returns_updated_status():
    """After broadcast_status, get_machine_status_from_cache returns that data."""
    manager = WebSocketManager()
    machine_id = 42
    status_data = {
        "machine_id": machine_id,
        "status": "running",
        "program_name": "O0001",
    }
    # broadcast_status is async but we only need to update last_status
    manager.last_status[machine_id] = status_data
    out = manager.get_machine_status_from_cache(machine_id)
    assert out == status_data
    assert manager.get_machine_status(machine_id) == status_data


def test_get_machine_status_from_cache_miss_returns_empty():
    """Cache miss returns empty dict."""
    manager = WebSocketManager()
    out = manager.get_machine_status_from_cache(999)
    assert out == {}
