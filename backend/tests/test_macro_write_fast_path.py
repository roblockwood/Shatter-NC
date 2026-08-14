"""Tests for macro write fast path and cache validation."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.machine_state_validator import (
    MachineStateValidator,
    cache_age_seconds,
    evaluate_macro_write_safety,
    macro_write_cache_max_age_seconds,
)
from app.services.macro_write_service import execute_macro_write


def test_macro_write_cache_max_age():
    assert macro_write_cache_max_age_seconds(5) == 15
    assert macro_write_cache_max_age_seconds(20) == 40


def test_cache_age_seconds_from_last_successful_poll():
    ts = (datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat()
    cached = {"last_successful_poll_at": ts}
    age = cache_age_seconds(cached)
    assert age is not None
    assert 2 <= age <= 6


def test_evaluate_macro_write_blocks_operating():
    ok, msg, data = evaluate_macro_write_safety(
        machine_status="operating",
        mem_mode=0,
        machine_id=1,
        machine_name="Mill",
    )
    assert ok is False
    assert "running" in msg.lower()
    assert data["status"] == "operating"


def test_evaluate_macro_write_blocks_mem_mode_2():
    ok, msg, _ = evaluate_macro_write_safety(
        machine_status="standby",
        mem_mode=2,
        machine_id=1,
        machine_name="Mill",
    )
    assert ok is False
    assert "running" in msg.lower()


def test_try_validate_from_fresh_cache():
    ts = datetime.now(timezone.utc).isoformat()
    cached = {
        "status": "standby",
        "mem_mode": 0,
        "last_successful_poll_at": ts,
    }
    safe, err, data = MachineStateValidator.try_validate_macro_write_from_cache(
        cached, machine_id=1, machine_name="Mill", max_age_seconds=15
    )
    assert safe is True
    assert err is None
    assert data["status"] == "standby"


def test_try_validate_stale_cache_returns_none():
    ts = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    cached = {"status": "standby", "mem_mode": 0, "last_successful_poll_at": ts}
    safe, err, _ = MachineStateValidator.try_validate_macro_write_from_cache(
        cached, machine_id=1, machine_name="Mill", max_age_seconds=15
    )
    assert safe is None
    assert err is None


@pytest.mark.asyncio
async def test_execute_macro_write_uses_cache_only(monkeypatch):
    machine = SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        poll_interval_seconds=5,
        control_version="D00",
    )
    ts = datetime.now(timezone.utc).isoformat()
    ws = MagicMock()
    ws.get_machine_status.return_value = {
        "status": "standby",
        "mem_mode": 0,
        "last_successful_poll_at": ts,
    }
    polling = MagicMock(websocket_manager=ws)
    monkeypatch.setattr("app.api._status_state.polling_service", polling)

    telnet = MagicMock()
    telnet.write_macro_variable = AsyncMock(return_value=(True, "00", 12.0))
    telnet.disconnect = AsyncMock()
    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(return_value=telnet),
    )

    outcome = await execute_macro_write(machine, machine_id=1, macro_number=920, value=12.0)
    assert outcome.success is True
    assert outcome.verified_value == 12.0
    assert not telnet.get_memory_data.called
    telnet.write_macro_variable.assert_awaited_once_with(
        macro_number=920, value=12.0, verbose=False, verify=True
    )


@pytest.mark.asyncio
async def test_execute_macro_write_live_fallback_when_cache_stale(monkeypatch):
    machine = SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        poll_interval_seconds=5,
        control_version="D00",
    )
    ts = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    ws = MagicMock()
    ws.get_machine_status.return_value = {
        "status": "standby",
        "mem_mode": 0,
        "last_successful_poll_at": ts,
    }
    polling = MagicMock(websocket_manager=ws)
    monkeypatch.setattr("app.api._status_state.polling_service", polling)

    telnet = MagicMock()
    telnet.get_memory_data = AsyncMock(return_value="A01,'F',2045,0,0,0,0,0")
    telnet.get_prd3_data = AsyncMock(
        return_value="A01,1,2,1\nC01,20240101120000,2,0,2045,'F',0"
    )
    telnet.write_macro_variable = AsyncMock(return_value=(True, "00", 5.0))
    telnet.disconnect = AsyncMock()
    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(return_value=telnet),
    )

    outcome = await execute_macro_write(machine, machine_id=1, macro_number=920, value=5.0)
    assert outcome.success is True
    telnet.get_memory_data.assert_awaited_once()
    telnet.get_prd3_data.assert_awaited_once()
