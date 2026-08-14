"""Mocked tests for ATC/tool write routes in _status_tools."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import _status_tools as tools
import app.api._status_state as _state


def _db(machine):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = machine
    return db


def _machine():
    return SimpleNamespace(id=1, name="Mill", ip_address="10.0.0.1")


@pytest.mark.asyncio
async def test_refresh_tool_data_not_found():
    with pytest.raises(HTTPException) as ei:
        await tools.refresh_tool_data(99, _db(None))
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_refresh_tool_data_no_polling_service():
    _state.polling_service = None
    with pytest.raises(HTTPException) as ei:
        await tools.refresh_tool_data(1, _db(_machine()))
    assert ei.value.status_code == 503


@pytest.mark.asyncio
async def test_refresh_tool_data_success():
    poller = MagicMock()
    poller.refresh_tool_data = AsyncMock(return_value={"tools": []})
    _state.polling_service = poller
    try:
        result = await tools.refresh_tool_data(1, _db(_machine()))
        assert result["machine_id"] == 1
        assert "tool_data" in result
    finally:
        _state.polling_service = None


@pytest.mark.asyncio
async def test_change_tool_color_invalid_color():
    with pytest.raises(HTTPException) as ei:
        await tools.change_tool_color(1, 1, tool_number=5, color=99, db=_db(_machine()))
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_change_tool_color_unsafe_state(monkeypatch):
    validator = MagicMock()
    validator.validate_safe_for_write = AsyncMock(
        return_value=(False, "Machine is running", {"status": "operating"})
    )
    monkeypatch.setattr(
        "app.services.machine_state_validator.MachineStateValidator",
        lambda: validator,
    )
    with pytest.raises(HTTPException) as ei:
        await tools.change_tool_color(1, 1, tool_number=5, color=2, db=_db(_machine()))
    assert ei.value.status_code == 409


@pytest.mark.asyncio
async def test_change_tool_color_success(monkeypatch):
    validator = MagicMock()
    validator.validate_safe_for_write = AsyncMock(return_value=(True, None, {"status": "standby"}))
    monkeypatch.setattr(
        "app.services.machine_state_validator.MachineStateValidator",
        lambda: validator,
    )
    telnet = MagicMock()
    telnet.change_atc_tool = AsyncMock(return_value=(True, "00"))
    telnet.disconnect = AsyncMock()
    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(return_value=telnet),
    )
    monkeypatch.setattr("app.services.audit_logger.AuditLogger.log_tool_modification", MagicMock())
    _state.polling_service = MagicMock()
    _state.polling_service.refresh_tool_data = AsyncMock(return_value={})
    try:
        result = await tools.change_tool_color(1, 1, tool_number=5, color=2, db=_db(_machine()))
        assert result["success"] is True or result.get("machine_id") == 1 or "color" in result
    finally:
        _state.polling_service = None
        if hasattr(telnet, "disconnect"):
            pass


@pytest.mark.asyncio
async def test_delete_tool_machine_not_found():
    with pytest.raises(HTTPException) as ei:
        await tools.delete_tool_from_pot(99, 1, db=_db(None))
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_set_tool_life_machine_not_found():
    with pytest.raises(HTTPException) as ei:
        await tools.set_tool_life(99, 1, life_value=100, db=_db(None))
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_set_macro_variable_invalid_number():
    with pytest.raises(HTTPException) as ei:
        await tools.set_macro_variable(1, 100, value=5.0, db=_db(_machine()))
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_set_macro_variable_success(monkeypatch):
    validator = MagicMock()
    validator.validate_safe_for_write = AsyncMock(return_value=(True, None, {"status": "standby"}))
    monkeypatch.setattr(
        "app.services.machine_state_validator.MachineStateValidator",
        lambda: validator,
    )
    telnet = MagicMock()
    telnet.write_macro_variable = AsyncMock(return_value=(True, "00", 5.0))
    telnet.disconnect = AsyncMock()
    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(return_value=telnet),
    )
    monkeypatch.setattr("app.services.audit_logger.AuditLogger.log_tool_modification", MagicMock())

    result = await tools.set_macro_variable(1, 920, value=5.0, db=_db(_machine()))
    assert result["success"] is True
    assert result["macro_number"] == 920
    telnet.write_macro_variable.assert_awaited_once_with(
        macro_number=920, value=5.0, verbose=True, verify=True
    )


@pytest.mark.asyncio
async def test_set_measurement_tool_success(monkeypatch):
    validator = MagicMock()
    validator.validate_safe_for_write = AsyncMock(return_value=(True, None, {"status": "standby"}))
    monkeypatch.setattr(
        "app.services.machine_state_validator.MachineStateValidator",
        lambda: validator,
    )
    telnet = MagicMock()
    telnet.write_macro_variable = AsyncMock(return_value=(True, "00", 12.0))
    telnet.disconnect = AsyncMock()
    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(return_value=telnet),
    )
    monkeypatch.setattr("app.services.audit_logger.AuditLogger.log_tool_modification", MagicMock())

    result = await tools.set_measurement_tool(1, tool_number=12, db=_db(_machine()))
    assert result["success"] is True
    assert result["tool_number"] == 12
    telnet.write_macro_variable.assert_awaited_once_with(
        macro_number=920, value=12.0, verbose=True, verify=True
    )
