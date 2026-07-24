"""Mocked one-tick MachinePoller.poll() coverage."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.polling import MachinePoller


def _discard_create_task(coro):
    if hasattr(coro, "close"):
        coro.close()
    return MagicMock()


def _machine():
    return SimpleNamespace(
        id=1,
        name="test-machine",
        ip_address="10.0.0.1",
        units="in",
        part_display_mode="parts",
        control_version="C00",
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


@pytest.mark.asyncio
async def test_poll_standby_happy_path():
    poller = MachinePoller(_machine(), None)
    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(return_value=_montr_bytes().decode())
    fake.get_prd3_data = AsyncMock(return_value=_prd3_bytes(2).decode())
    fake.get_memory_data = AsyncMock(return_value=_mem_bytes().decode())
    fake.get_alarm_data = AsyncMock(return_value=b"E01,\r\n".decode())
    fake.get_panel_data = AsyncMock(return_value=_panel_bytes().decode())
    fake.get_macro_variable_range = AsyncMock(return_value=None)
    fake.disconnect = AsyncMock()

    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            with patch("app.services._machine_poller.SessionLocal") as session_cls:
                session_cls.return_value = MagicMock()
                result = await poller.poll()

    assert result["status"] == "standby"
    assert result["is_online"] is True
    assert poller.consecutive_failures == 0
    assert poller.last_known_prd3_status == "standby"
    fake.disconnect.assert_awaited()


@pytest.mark.asyncio
async def test_poll_off_becomes_standby_when_active():
    poller = MachinePoller(_machine(), None)
    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(return_value=_montr_bytes().decode())
    fake.get_prd3_data = AsyncMock(return_value=_prd3_bytes(1).decode())  # off
    fake.get_memory_data = AsyncMock(return_value=_mem_bytes().decode())
    fake.get_alarm_data = AsyncMock(return_value="")
    fake.get_panel_data = AsyncMock(return_value=None)
    fake.get_macro_variable_range = AsyncMock(return_value=[])
    fake.disconnect = AsyncMock()

    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            with patch("app.services._machine_poller.SessionLocal"):
                result = await poller.poll()

    assert result["status"] == "standby"


@pytest.mark.asyncio
async def test_poll_missing_montr_finalizes_failure():
    poller = MachinePoller(_machine(), MagicMock())
    poller.last_successful_fast_poll_at = None
    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(return_value=None)
    fake.disconnect = AsyncMock()

    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            result = await poller.poll()

    assert result["is_online"] is False or result.get("consecutive_failures", 0) >= 1
