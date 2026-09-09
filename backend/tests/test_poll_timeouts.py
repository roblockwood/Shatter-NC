"""Tests that hung telnet operations cannot block polling or hold locks indefinitely."""
import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients._telnet_state import _get_machine_lock
from app.core.config import settings
from app.services.polling import MachinePoller


def _discard_create_task(coro):
    if hasattr(coro, "close"):
        coro.close()
    return MagicMock()


def _machine(ip: str = "10.0.0.99"):
    return SimpleNamespace(
        id=42,
        name="timeout-test",
        ip_address=ip,
        units="in",
        part_display_mode="parts",
        control_version="C00",
        atc_pockets=21,
    )


def _montr_bytes():
    return (
        b"P01,2045,2046,'FOLDER  ','EDIT    '\r\n"
        b"T01,010203000,040506000,070809000\r\n"
        b"C01,001,000010,000100,000090\r\n"
    )


def _prd3_bytes(status_code: int = 2):
    return (
        f"A01,1,10,1\r\n"
        f"C01,20240101120000,{status_code},0,2045,'FOLDER  ',0\r\n"
    ).encode()


def _mem_bytes():
    return b"A01,'FOLDER  ',2045,0,0,0,0,0\r\n"


def _panel_bytes():
    return b"D01,0,0,0\r\nK01,2,6,0,0,0,0,0,1,0,1,0\r\nS01,4,100,100,1,0,0,1\r\n"


@pytest.fixture
def fast_poll_timeouts(monkeypatch):
    monkeypatch.setattr(settings, "TELNET_POLL_FAST_TIMEOUT_SECONDS", 0.5)
    monkeypatch.setattr(settings, "TELNET_MACRO_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(settings, "TELNET_POLL_SLOW_TIMEOUT_SECONDS", 0.5)


@pytest.mark.asyncio
async def test_poll_times_out_on_hung_montr(fast_poll_timeouts):
    poller = MachinePoller(_machine(), MagicMock())

    async def hang_forever(**_kwargs):
        await asyncio.sleep(3600)

    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(side_effect=hang_forever)
    fake.disconnect = AsyncMock()

    start = time.monotonic()
    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            result = await poller.poll()
    elapsed = time.monotonic() - start

    assert elapsed < 2.0
    assert result.get("consecutive_failures", 0) >= 1
    assert "timed out" in str(result.get("error", "")).lower()
    fake.disconnect.assert_awaited()


@pytest.mark.asyncio
async def test_poll_survives_hung_macro_fetch(fast_poll_timeouts):
    poller = MachinePoller(_machine(), None)

    async def hang_macros(*_args, **_kwargs):
        await asyncio.sleep(3600)

    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(return_value=_montr_bytes().decode())
    fake.get_prd3_data = AsyncMock(return_value=_prd3_bytes(2).decode())
    fake.get_memory_data = AsyncMock(return_value=_mem_bytes().decode())
    fake.get_alarm_data = AsyncMock(return_value="")
    fake.get_panel_data = AsyncMock(return_value=_panel_bytes().decode())
    fake.get_macro_variable_range = AsyncMock(side_effect=hang_macros)
    fake.disconnect = AsyncMock()

    start = time.monotonic()
    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            with patch("app.services._machine_poller.SessionLocal"):
                result = await poller.poll()
    elapsed = time.monotonic() - start

    assert elapsed < 2.0
    assert result["status"] == "standby"
    assert result.get("macros") == {}


@pytest.mark.asyncio
async def test_lock_released_after_poll_timeout(fast_poll_timeouts):
    """After a timed-out poll, the per-machine lock must not block a second poll."""
    ip = "10.0.0.100"
    poller = MachinePoller(_machine(ip=ip), None)
    call_count = 0

    async def montr_once_then_ok(**_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await asyncio.sleep(3600)
        return _montr_bytes().decode()

    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(side_effect=montr_once_then_ok)
    fake.get_prd3_data = AsyncMock(return_value=_prd3_bytes(2).decode())
    fake.get_memory_data = AsyncMock(return_value=_mem_bytes().decode())
    fake.get_alarm_data = AsyncMock(return_value="")
    fake.get_panel_data = AsyncMock(return_value=_panel_bytes().decode())
    fake.get_macro_variable_range = AsyncMock(return_value=[])
    fake.disconnect = AsyncMock()

    lock = await _get_machine_lock(ip, 10000)
    assert not lock.locked()

    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            fail_result = await poller.poll()
    assert fail_result.get("consecutive_failures", 0) >= 1
    assert not lock.locked()

    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            with patch("app.services._machine_poller.SessionLocal"):
                ok_result = await poller.poll()

    assert ok_result["status"] == "standby"
    assert ok_result["is_online"] is True


@pytest.mark.asyncio
async def test_tool_poll_skipped_when_offline():
    poller = MachinePoller(_machine(), None)
    poller.consecutive_failures = poller.offline_threshold

    with patch("app.services._machine_poller.CNCTelnetClient") as ctor:
        result = await poller.poll_tool_data()

    assert result == {}
    ctor.assert_not_called()
