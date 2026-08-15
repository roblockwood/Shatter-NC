"""Tests for MachineStateValidator with mocked telnet / DB."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.machine_state_validator import MachineStateValidator


def _db_with_machine(machine=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = machine
    return db


def _telnet_mock(*, mem=None, prd3=None, alarms=None, control="C00"):
    client = MagicMock()
    client.detect_control_type = AsyncMock(return_value=control)
    client.get_memory_data = AsyncMock(return_value=mem)
    client.get_prd3_data = AsyncMock(return_value=prd3)
    client.get_alarm_data = AsyncMock(return_value=alarms)
    client.disconnect = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_machine_not_found():
    validator = MachineStateValidator()
    ok, msg, data = await validator.validate_safe_for_write(99, "tool_color", _db_with_machine(None))
    assert ok is False
    assert "not found" in msg
    assert data is None


@pytest.mark.asyncio
async def test_blocks_when_prd3_operating():
    machine = SimpleNamespace(id=1, name="M1", ip_address="10.0.0.1")
    client = _telnet_mock(
        mem="A01,'F',2045,0,0,0,0,0",
        prd3="A01,1,2,1\nC01,20240101120000,3,0,2045,'F',0",
    )
    with patch("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client)):
        ok, msg, data = await MachineStateValidator().validate_safe_for_write(
            1, "tool_color", _db_with_machine(machine)
        )
    assert ok is False
    assert "running" in msg.lower()
    assert data["status"] == "operating"
    client.disconnect.assert_awaited()


@pytest.mark.asyncio
async def test_blocks_mem_mode_2_when_operation_active():
    machine = SimpleNamespace(id=1, name="M1", ip_address="10.0.0.1")
    client = _telnet_mock(
        mem="A01,'F',2045,1,0,0,2,0",  # operation_status=1, mode=2
        prd3="A01,1,2,1\nC01,20240101120000,2,0,2045,'F',0",
    )
    with patch("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client)):
        ok, msg, _ = await MachineStateValidator().validate_safe_for_write(
            1, "tool_color", _db_with_machine(machine)
        )
    assert ok is False
    assert "running" in msg.lower()


@pytest.mark.asyncio
async def test_mem_mode_2_idle_allows_tool_life():
    machine = SimpleNamespace(id=1, name="M1", ip_address="10.0.0.1")
    client = _telnet_mock(
        mem="A01,'F',2045,0,0,0,2,0",  # operation_status=0, mode=2 (memory selected, not running)
        prd3="A01,1,2,1\nC01,20240101120000,2,0,2045,'F',0",
    )
    with patch("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client)):
        ok, msg, _ = await MachineStateValidator().validate_safe_for_write(
            1, "tool_life", _db_with_machine(machine)
        )
    assert ok is True
    assert msg is None


@pytest.mark.asyncio
async def test_edit_mode_blocks_tool_assignment_allows_color():
    machine = SimpleNamespace(id=1, name="M1", ip_address="10.0.0.1")
    # mode=3 (Edit), operation_status=0
    mem = "A01,'F',2045,0,0,0,3,0"
    prd3 = "A01,1,2,1\nC01,20240101120000,2,0,2045,'F',0"
    client = _telnet_mock(mem=mem, prd3=prd3)
    with patch("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client)):
        ok_assign, msg, _ = await MachineStateValidator().validate_safe_for_write(
            1, "tool_assignment", _db_with_machine(machine)
        )
        ok_color, _, _ = await MachineStateValidator().validate_safe_for_write(
            1, "tool_color", _db_with_machine(machine)
        )
    assert ok_assign is False
    assert "Edit" in msg
    assert ok_color is True


@pytest.mark.asyncio
async def test_operation_status_blocks_delete_allows_color():
    machine = SimpleNamespace(id=1, name="M1", ip_address="10.0.0.1")
    # operation_status=2 (Temporary stop), mode=0
    mem = "A01,'F',2045,2,0,0,0,0"
    prd3 = "A01,1,2,1\nC01,20240101120000,2,0,2045,'F',0"
    client = _telnet_mock(mem=mem, prd3=prd3)
    with patch("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client)):
        ok_del, msg, _ = await MachineStateValidator().validate_safe_for_write(
            1, "tool_delete", _db_with_machine(machine)
        )
        ok_color, _, _ = await MachineStateValidator().validate_safe_for_write(
            1, "tool_color", _db_with_machine(machine)
        )
    assert ok_del is False
    assert "Temporary stop" in msg
    assert ok_color is True


@pytest.mark.asyncio
async def test_missing_mem_and_prd3_allows():
    machine = SimpleNamespace(id=1, name="M1", ip_address="10.0.0.1")
    client = _telnet_mock(mem=None, prd3=None, alarms=None)
    with patch("app.clients.telnet_client.create_fresh_connection", AsyncMock(return_value=client)):
        ok, msg, data = await MachineStateValidator().validate_safe_for_write(
            1, "tool_assignment", _db_with_machine(machine)
        )
    assert ok is True
    assert msg is None
    assert data["machine_id"] == 1


@pytest.mark.asyncio
async def test_connection_error():
    machine = SimpleNamespace(id=1, name="M1", ip_address="10.0.0.1")
    with patch(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(side_effect=RuntimeError("down")),
    ):
        ok, msg, data = await MachineStateValidator().validate_safe_for_write(
            1, "tool_color", _db_with_machine(machine)
        )
    assert ok is False
    assert "Error checking machine state" in msg
    assert data is None
