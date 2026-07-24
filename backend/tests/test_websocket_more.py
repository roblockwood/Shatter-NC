"""Extended WebSocket manager behavioral tests."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.websocket import WebSocketManager


@pytest.mark.asyncio
async def test_broadcast_preserves_all_cached_fields():
    mgr = WebSocketManager()
    mid = 1
    mgr.last_status[mid] = {
        "machine_id": mid,
        "program_name": "O1",
        "panel": {"a": 1},
        "alarms": [{"code": "1"}],
        "part_display_mode": "parts",
        "tool_table": [1],
        "current_tool": 2,
        "tools": [3],
        "tools_timestamp": "t1",
        "macros": {"x": 1},
        "macros_timestamp": "t2",
        "last_successful_poll_at": "t3",
        "cycle_time": "c",
    }
    await mgr.broadcast_status({"machine_id": mid, "status": "standby"})
    cached = mgr.last_status[mid]
    assert cached["panel"] == {"a": 1}
    assert cached["alarms"] == [{"code": "1"}]
    assert cached["part_display_mode"] == "parts"
    assert cached["tool_table"] == [1]
    assert cached["current_tool"] == 2
    assert cached["tools"] == [3]
    assert cached["tools_timestamp"] == "t1"
    assert cached["macros"] == {"x": 1}
    assert cached["macros_timestamp"] == "t2"
    assert cached["last_successful_poll_at"] == "t3"
    assert cached["cycle_time"] == "c"


@pytest.mark.asyncio
async def test_broadcast_with_connection_and_disconnect_on_error():
    mgr = WebSocketManager()
    good = AsyncMock()
    bad = AsyncMock()
    bad.send_json.side_effect = RuntimeError("gone")
    mgr.active_connections = [good, bad]
    await mgr.broadcast_status({"machine_id": 5, "status": "ok"})
    good.send_json.assert_awaited()
    assert bad not in mgr.active_connections
    assert good in mgr.active_connections


@pytest.mark.asyncio
async def test_broadcast_compressor_and_getters():
    mgr = WebSocketManager()
    await mgr.broadcast_compressor_status({"compressor_id": 9, "status": "load"})
    assert mgr.get_compressor_status(9)["status"] == "load"
    assert mgr.get_connection_count() == 0
    mgr.pop_compressor_cache(9)
    assert mgr.get_compressor_status(9) == {}


@pytest.mark.asyncio
async def test_send_message_disconnect_on_error():
    mgr = WebSocketManager()
    ws = AsyncMock()
    ws.send_json.side_effect = RuntimeError("x")
    mgr.active_connections = [ws]
    await mgr.send_message(ws, {"hi": 1})
    assert ws not in mgr.active_connections


@pytest.mark.asyncio
async def test_connect_sends_initial_status():
    mgr = WebSocketManager()
    ws = AsyncMock()
    machine = MagicMock(id=1, name="M", ip_address="1.1.1.1", enabled=True)
    machine.part_display_mode = "parts"
    comp = MagicMock(id=2, name="C", ip_address="2.2.2.2", enabled=True, poll_interval_seconds=10)
    comp.layout_config = None
    db = MagicMock()
    db.query.side_effect = [
        MagicMock(all=MagicMock(return_value=[machine])),
        MagicMock(all=MagicMock(return_value=[comp])),
    ]
    with patch("app.services.websocket.SessionLocal", return_value=db):
        await mgr.connect(ws)
    ws.accept.assert_awaited()
    ws.send_json.assert_awaited()
    assert ws in mgr.active_connections
    mgr.disconnect(ws)
    assert ws not in mgr.active_connections
