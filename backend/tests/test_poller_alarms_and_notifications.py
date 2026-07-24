"""Additional poller tick + notification helper coverage."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.notification_service import (
    _format_pacific_time,
    _format_runtime_hms,
    _normalize_alarm_code,
)
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


def test_normalize_alarm_code():
    assert _normalize_alarm_code(None) == ""
    assert _normalize_alarm_code("om0500]") == "OM0500"
    assert _normalize_alarm_code("  NC1234  ") == "NC1234"


def test_format_runtime_hms():
    assert _format_runtime_hms(None) == ""
    assert _format_runtime_hms(3661) == "01:01:01"
    assert _format_runtime_hms(-5) == "00:00:00"


def test_format_pacific_time():
    assert _format_pacific_time(None) == ""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    formatted = _format_pacific_time(dt)
    assert "JAN" in formatted.upper() or "24" in formatted
    assert "PST" in formatted or "PDT" in formatted


@pytest.mark.asyncio
async def test_poll_halting_alarm_sets_error():
    poller = MachinePoller(_machine(), None)
    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(
        return_value="P01,2045,2046,'F','E'\r\nT01,010203000,040506000,070809000\r\n"
    )
    fake.get_prd3_data = AsyncMock(
        return_value="A01,1,10,1\r\nC01,20240101120000,2,0,2045,'F',0\r\n"
    )
    fake.get_memory_data = AsyncMock(return_value="A01,'F',2045,0,0,0,0,0\r\n")
    fake.get_alarm_data = AsyncMock(return_value="E01,0412340000\r\n")
    fake.get_panel_data = AsyncMock(return_value=None)
    fake.get_macro_variable_range = AsyncMock(return_value=None)
    fake.disconnect = AsyncMock()

    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            with patch("app.services._machine_poller.SessionLocal"):
                with patch(
                    "app.services._machine_poller.enrich_alarm_with_lookup",
                    side_effect=lambda a, *_args, **_k: {**a, "stop_level": 4},
                ):
                    result = await poller.poll()

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_poll_operating_not_overridden_by_alarms():
    poller = MachinePoller(_machine(), None)
    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(
        return_value="P01,2045,2046,'F','E'\r\nT01,010203000,040506000,070809000\r\n"
    )
    fake.get_prd3_data = AsyncMock(
        return_value="A01,1,10,1\r\nC01,20240101120000,3,0,2045,'F',0\r\n"
    )
    fake.get_memory_data = AsyncMock(return_value="A01,'F',2045,0,0,0,0,0\r\n")
    fake.get_alarm_data = AsyncMock(return_value="E01,0412340000\r\n")
    fake.get_panel_data = AsyncMock(return_value=None)
    fake.get_macro_variable_range = AsyncMock(return_value=None)
    fake.disconnect = AsyncMock()

    with patch("app.services._machine_poller.CNCTelnetClient", return_value=fake):
        with patch("app.services._machine_poller.asyncio.create_task", _discard_create_task):
            with patch("app.services._machine_poller.SessionLocal"):
                with patch(
                    "app.services._machine_poller.enrich_alarm_with_lookup",
                    side_effect=lambda a, *_args, **_k: {**a, "stop_level": 5},
                ):
                    result = await poller.poll()

    assert result["status"] == "operating"


def test_import_tool_instance_model():
    from app.models import tool_instance

    assert tool_instance.ToolInstance.__tablename__
