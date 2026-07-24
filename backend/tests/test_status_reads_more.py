"""Mocked read-route tests for machine status data."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api import _status_reads as reads


def _db(machine):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = machine
    return db


def _machine():
    return SimpleNamespace(id=1, name="Mill", ip_address="10.0.0.1", units="in", http_port=80)


@pytest.mark.asyncio
async def test_running_log_rejects_unknown_machine():
    db = _db(None)

    with pytest.raises(HTTPException) as exc_info:
        await reads.get_running_log(99, db)

    assert exc_info.value.status_code == 404
    assert "Machine with id 99 not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_running_log_formats_parser_time_data(monkeypatch):
    client = SimpleNamespace(
        detect_control_type=AsyncMock(return_value="C00"),
        get_monitor_data=AsyncMock(return_value="MONTR"),
        disconnect=AsyncMock(),
    )
    monkeypatch.setattr("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client))
    monkeypatch.setattr(
        "app.parsers.montr_parser_v2.parse_montr_v2",
        lambda *_args, **_kwargs: {"time_info": {"total_operation_time": "000001000", "operation_time": "000000500"}},
    )

    result = await reads.get_running_log(1, _db(_machine()))

    assert result["machine_id"] == 1
    assert result["cycle_time"] == "0000:01.000"
    assert result["cutting_time"] == "0000:00.500"
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_work_counters_supplies_defaults_for_missing_fields(monkeypatch):
    client = SimpleNamespace(
        detect_control_type=AsyncMock(return_value="D00"),
        get_monitor_data=AsyncMock(return_value="MONTR"),
        disconnect=AsyncMock(),
    )
    monkeypatch.setattr("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client))
    monkeypatch.setattr(
        "app.parsers.montr_parser_v2.parse_montr_v2",
        lambda *_args, **_kwargs: {"counters": [{"count": 9}, {"counter_number": 7, "current": 2, "end": 10}]},
    )

    result = await reads.get_work_counters(1, _db(_machine()))

    assert result["counters"] == [
        {"counter_number": 1, "count": 9, "current": 0, "end": 0, "end_warning": 0},
        {"counter_number": 7, "count": 0, "current": 2, "end": 10, "end_warning": 0},
    ]
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_alarms_returns_empty_lists_when_machine_returns_none(monkeypatch):
    client = SimpleNamespace(get_alarm_data=AsyncMock(return_value=None), disconnect=AsyncMock())
    monkeypatch.setattr("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client))

    result = await reads.get_alarms_live(1, _db(_machine()))

    assert result["machine_id"] == 1
    assert result["alarms"] == []
    assert result["loading_alarms"] == []
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_tools_raw_html_uses_http_client_without_telnet(monkeypatch):
    http_client = MagicMock()
    http_client._send_request.return_value = "<html>tools</html>"
    monkeypatch.setattr(reads, "CNCHttpClient", MagicMock(return_value=http_client))

    result = await reads.get_tools(1, source="atc", raw_html=True, db=_db(_machine()))

    assert result == {"machine_id": 1, "source": "atc", "raw_html": "<html>tools</html>"}
    http_client._send_request.assert_called_once_with("/tool")


@pytest.mark.asyncio
async def test_machine_status_combines_telnet_data_and_mem(monkeypatch):
    client = SimpleNamespace(
        detect_control_type=AsyncMock(return_value="C00"),
        get_monitor_data=AsyncMock(return_value="MONTR"),
        get_prd3_data=AsyncMock(return_value="PRD3"),
        get_memory_data=AsyncMock(return_value="MEM"),
        get_alarm_data=AsyncMock(return_value=None),
        disconnect=AsyncMock(),
    )
    monkeypatch.setattr("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client))
    monkeypatch.setattr(
        "app.parsers.montr_parser_v2.parse_montr_v2",
        lambda *_args, **_kwargs: {
            "program_info": {"operation_program_no": "O1234"},
            "time_info": {"total_operation_time": "000001000", "operation_time": "000000500", "power_on_time": "000002000"},
            "counters": [{"count": 3}],
        },
    )
    monkeypatch.setattr(
        "app.parsers.prd3_parser_v2.parse_prd3_v2",
        lambda *_args, **_kwargs: {"current_status": {"current_status": 1, "status": "running"}},
    )
    monkeypatch.setattr(
        "app.parsers.mem_parser_v2.parse_mem_v2",
        lambda *_args, **_kwargs: {
            "mode": "AUTO",
            "operation_status": "RUN",
            "operation_folder_name": "PROGRAMS",
        },
    )

    result = await reads.get_machine_status(1, include_mem=True, db=_db(_machine()))

    assert result["machine_id"] == 1
    assert result["machine_name"] == "Mill"
    assert result["program_name"] == "O1234"
    assert result["status"] == "running"
    assert result["counters"] == [{"counter_number": 1, "count": 3, "current": 0, "end": 0, "end_warning": 0}]
    assert result["mode"] == "AUTO"
    assert result["operation_folder_name"] == "PROGRAMS"
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_machine_status_rejects_unknown_machine():
    with pytest.raises(HTTPException) as exc_info:
        await reads.get_machine_status(99, db=_db(None))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Machine with id 99 not found"


@pytest.mark.asyncio
async def test_live_alarms_reject_unknown_machine():
    with pytest.raises(HTTPException) as exc_info:
        await reads.get_alarms_live(99, _db(None))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Machine with id 99 not found"
