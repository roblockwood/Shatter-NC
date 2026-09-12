"""Tests for probe exclusive hold and polling pause."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.polling import PollingService
from app.services.probe_cycle_service import (
    ProbeProgressCtx,
    _Snap,
    _is_cycle_complete,
    _wait_until,
    emit_probe_progress,
)
from app.services import probe_exclusive


@pytest.fixture(autouse=True)
def _reset_exclusive():
    probe_exclusive._reset_for_tests()
    yield
    probe_exclusive._reset_for_tests()


def test_pause_machine_polling_refcount():
    svc = PollingService(websocket_manager=MagicMock())
    assert svc.is_machine_polling_paused(7) is False
    assert svc.pause_machine_polling(7, reason="probe") == 1
    assert svc.is_machine_polling_paused(7) is True
    assert svc.pause_machine_polling(7, reason="probe") == 2
    assert svc.resume_machine_polling(7) == 1
    assert svc.is_machine_polling_paused(7) is True
    assert svc.resume_machine_polling(7) == 0
    assert svc.is_machine_polling_paused(7) is False


@pytest.mark.asyncio
async def test_refresh_tool_data_skipped_when_paused():
    svc = PollingService(websocket_manager=MagicMock())
    poller = MagicMock()
    poller.poll_tool_data = AsyncMock(return_value={"tools": []})
    svc.pollers[3] = poller
    svc.pause_machine_polling(3)
    result = await svc.refresh_tool_data(3)
    assert result == {}
    poller.poll_tool_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_exclusive_begin_end_pauses_polling(monkeypatch):
    polling = PollingService(websocket_manager=MagicMock())
    monkeypatch.setattr(
        "app.api._status_state.polling_service",
        polling,
        raising=False,
    )
    import app.api._status_state as status_state

    status_state.polling_service = polling

    out = await probe_exclusive.begin_exclusive(11)
    assert out["active"] is True
    assert polling.is_machine_polling_paused(11) is True
    assert probe_exclusive.is_exclusive_active(11) is True
    assert probe_exclusive.collect_poll_seconds(11, 1.0) == 0.25

    out = await probe_exclusive.end_exclusive(11)
    assert out["active"] is False
    assert polling.is_machine_polling_paused(11) is False
    assert probe_exclusive.collect_poll_seconds(11, 1.0) == 1.0


@pytest.mark.asyncio
async def test_exclusive_stale_timeout_auto_resume(monkeypatch):
    polling = PollingService(websocket_manager=MagicMock())
    import app.api._status_state as status_state

    status_state.polling_service = polling

    await probe_exclusive.begin_exclusive(5)
    hold = probe_exclusive._holds[5]
    hold["last_activity_at"] = hold["last_activity_at"] - 400
    await probe_exclusive.sweep_stale_holds(timeout_s=300)
    assert probe_exclusive.is_exclusive_active(5) is False
    assert polling.is_machine_polling_paused(5) is False


@pytest.mark.asyncio
async def test_wait_until_emits_progress_ticks(monkeypatch):
    client = MagicMock()
    ticks = {"n": 0}

    async def fake_snapshot(*_a, **_k):
        ticks["n"] += 1
        if ticks["n"] >= 2:
            return _Snap(prd3_status="standby", operation_status=0)
        return _Snap(prd3_status="operating", operation_status=1)

    emitted = []

    async def fake_emit(ctx, phase, message, *, snap=None, final=False):
        emitted.append({"phase": phase, "message": message, "snap": snap, "final": final})

    monkeypatch.setattr(
        "app.services.probe_cycle_service._snapshot",
        fake_snapshot,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service.emit_probe_progress",
        fake_emit,
    )
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    ctx = ProbeProgressCtx(machine_id=1, api_step="collect", client_run_id="run-1")
    snap = await _wait_until(
        client,
        "C00",
        predicate=_is_cycle_complete,
        label="cycle complete",
        timeout_s=5,
        poll_s=0.25,
        progress=ctx,
        progress_phase="waiting_complete",
    )
    assert snap.prd3_status == "standby"
    assert len(emitted) >= 2
    assert emitted[0]["phase"] == "waiting_complete"


@pytest.mark.asyncio
async def test_broadcast_probe_progress_not_in_last_status():
    from app.services.websocket import WebSocketManager

    ws = WebSocketManager()
    conn = MagicMock()
    conn.send_json = AsyncMock()
    ws.active_connections = [conn]
    await ws.broadcast_probe_progress(
        {
            "machine_id": 9,
            "api_step": "collect",
            "phase": "waiting_complete",
            "message": "Waiting",
            "final": False,
        }
    )
    assert 9 not in ws.last_status
    conn.send_json.assert_awaited()
    msg = conn.send_json.await_args.args[0]
    assert msg["type"] == "probe_progress"


@pytest.mark.asyncio
async def test_emit_probe_progress_uses_manager(monkeypatch):
    ws = MagicMock()
    ws.broadcast_probe_progress = AsyncMock()
    polling = SimpleNamespace(websocket_manager=ws)
    import app.api._status_state as status_state

    status_state.polling_service = polling

    ctx = ProbeProgressCtx(machine_id=2, api_step="write", client_run_id="abc")
    await emit_probe_progress(ctx, "writing", "Writing…")
    ws.broadcast_probe_progress.assert_awaited()
    payload = ws.broadcast_probe_progress.await_args.args[0]
    assert payload["machine_id"] == 2
    assert payload["client_run_id"] == "abc"
    assert payload["phase"] == "writing"
