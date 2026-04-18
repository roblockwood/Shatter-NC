"""Tests for WebSocket manager in-memory cache."""
import asyncio
import pytest
from app.services.websocket import WebSocketManager


def test_broadcast_preserves_cached_program_name_when_new_is_placeholder():
    manager = WebSocketManager()
    mid = 7
    manager.last_status[mid] = {"machine_id": mid, "program_name": "O2045", "status": "operating"}

    async def run():
        await manager.broadcast_status({"machine_id": mid, "status": "operating", "program_name": "----"})

    asyncio.run(run())
    assert manager.last_status[mid]["program_name"] == "O2045"


def test_broadcast_preserves_cached_program_name_when_new_key_omitted():
    manager = WebSocketManager()
    mid = 8
    manager.last_status[mid] = {"machine_id": mid, "program_name": "O2045"}

    async def run():
        await manager.broadcast_status({"machine_id": mid, "status": "standby"})

    asyncio.run(run())
    assert manager.last_status[mid]["program_name"] == "O2045"


def test_broadcast_preserves_snapshot_fields_when_omitted():
    manager = WebSocketManager()
    mid = 11
    manager.last_status[mid] = {
        "machine_id": mid,
        "cycle_time": "0012:34.567",
        "power_on_hours": "0100:00.000",
        "mem_mode": 1,
        "mem_operation_status": 2,
    }

    async def run():
        await manager.broadcast_status({"machine_id": mid, "status": "operating"})

    asyncio.run(run())
    assert manager.last_status[mid]["cycle_time"] == "0012:34.567"
    assert manager.last_status[mid]["power_on_hours"] == "0100:00.000"
    assert manager.last_status[mid]["mem_mode"] == 1
    assert manager.last_status[mid]["mem_operation_status"] == 2


def test_broadcast_updates_program_name_when_new_is_meaningful():
    manager = WebSocketManager()
    mid = 9
    manager.last_status[mid] = {"machine_id": mid, "program_name": "O2045"}

    async def run():
        await manager.broadcast_status({"machine_id": mid, "program_name": "O2099"})

    asyncio.run(run())
    assert manager.last_status[mid]["program_name"] == "O2099"


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
