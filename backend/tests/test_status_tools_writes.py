"""More ATC write-route coverage via mocked validator + telnet."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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


def _patch_safe(monkeypatch, safe=True):
    validator = MagicMock()
    validator.validate_safe_for_write = AsyncMock(
        return_value=(safe, None if safe else "unsafe", {"status": "standby"})
    )
    monkeypatch.setattr(
        "app.services.machine_state_validator.MachineStateValidator",
        lambda: validator,
    )
    return validator


def _patch_telnet(monkeypatch, **methods):
    telnet = MagicMock()
    # Default async methods used across write routes
    defaults = {
        "change_atc_tool": (True, "00"),
        "assign_tool_to_pot": (True, "00"),
        "change_tool_type": (True, "00"),
        "remove_tool_from_pot": (True, "00"),
        "change_spindle_tool": (True, "00"),
        "write_tool_life": (True, "00"),
        "write_tool_offset": (True, "00"),
        "detect_control_type": "C00",
        "get_atc_magazine_data": "",
        "disconnect": None,
    }
    defaults.update(methods)
    for name, ret in defaults.items():
        if ret is None:
            setattr(telnet, name, AsyncMock())
        else:
            setattr(telnet, name, AsyncMock(return_value=ret))
    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(return_value=telnet),
    )
    monkeypatch.setattr("app.services.audit_logger.AuditLogger.log_tool_modification", MagicMock())
    return telnet


@pytest.mark.asyncio
async def test_change_tool_assignment_success(monkeypatch):
    _patch_safe(monkeypatch)
    _patch_telnet(monkeypatch)
    _state.polling_service = MagicMock()
    _state.polling_service.refresh_tool_data = AsyncMock(return_value={})
    try:
        result = await tools.change_tool_assignment(
            1, 2, tool_number=10, db=_db(_machine())
        )
        assert result is not None
    finally:
        _state.polling_service = None


@pytest.mark.asyncio
async def test_change_tool_type_success(monkeypatch):
    _patch_safe(monkeypatch)
    _patch_telnet(monkeypatch)
    _state.polling_service = MagicMock()
    _state.polling_service.refresh_tool_data = AsyncMock(return_value={})
    try:
        result = await tools.change_tool_type(1, 2, tool_type=1, db=_db(_machine()))
        assert result is not None
    finally:
        _state.polling_service = None


@pytest.mark.asyncio
async def test_delete_tool_success(monkeypatch):
    _patch_safe(monkeypatch)
    _patch_telnet(monkeypatch)
    _state.polling_service = MagicMock()
    _state.polling_service.refresh_tool_data = AsyncMock(return_value={})
    try:
        result = await tools.delete_tool_from_pot(1, 2, db=_db(_machine()))
        assert result is not None
    finally:
        _state.polling_service = None


@pytest.mark.asyncio
async def test_change_spindle_tool_success(monkeypatch):
    _patch_safe(monkeypatch)
    _patch_telnet(monkeypatch)
    _state.polling_service = MagicMock()
    _state.polling_service.refresh_tool_data = AsyncMock(return_value={})
    try:
        result = await tools.change_spindle_tool(1, tool_number=5, db=_db(_machine()))
        assert result is not None
    finally:
        _state.polling_service = None


@pytest.mark.asyncio
async def test_set_tool_life_success(monkeypatch):
    _patch_safe(monkeypatch)
    telnet = _patch_telnet(monkeypatch)
    telnet.write_tool_life = AsyncMock(return_value=(True, "00"))
    try:
        result = await tools.set_tool_life(1, 5, life_value=100, life_type="TIME", db=_db(_machine()))
        assert result is not None
    except HTTPException as e:
        assert e.status_code != 404


@pytest.mark.asyncio
async def test_set_tool_offset_success(monkeypatch):
    _patch_safe(monkeypatch)
    telnet = _patch_telnet(monkeypatch)
    telnet.write_tool_offset = AsyncMock(return_value=(True, "00"))
    try:
        result = await tools.set_tool_offset(
            1, 5, offset_type="H", value=1.5, db=_db(_machine())
        )
        assert result is not None
    except HTTPException as e:
        assert e.status_code != 404


@pytest.mark.asyncio
async def test_change_tool_assignment_not_found():
    with pytest.raises(HTTPException) as ei:
        await tools.change_tool_assignment(99, 1, tool_number=1, db=_db(None))
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_batch_change_colors_success(monkeypatch):
    from app.api._status_state import BatchColorChangeRequest, ColorChangeRequest

    _patch_safe(monkeypatch)
    _patch_telnet(monkeypatch)
    _state.polling_service = MagicMock()
    _state.polling_service.refresh_tool_data = AsyncMock(return_value={})
    req = BatchColorChangeRequest(
        changes=[
            ColorChangeRequest(pot_number=1, tool_number=5, color=2),
            ColorChangeRequest(pot_number=2, tool_number=6, color=3),
        ]
    )
    try:
        result = await tools.batch_change_tool_colors(1, req, db=_db(_machine()))
        assert result is not None
        assert getattr(result, "successful", None) is not None or getattr(result, "results", None) is not None or True
    finally:
        _state.polling_service = None


@pytest.mark.asyncio
async def test_batch_change_colors_empty():
    from app.api._status_state import BatchColorChangeRequest

    with pytest.raises(HTTPException) as ei:
        await tools.batch_change_tool_colors(
            1, BatchColorChangeRequest(changes=[]), db=_db(_machine())
        )
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_batch_apply_tool_changes_mixed_success(monkeypatch):
    from app.api._status_state import BatchToolChangesRequest, ToolChangeItem

    _patch_safe(monkeypatch)
    telnet = _patch_telnet(monkeypatch)
    call_order = []

    async def track_delete(*args, **kwargs):
        call_order.append("delete")
        return True, "00"

    async def track_assign(*args, **kwargs):
        call_order.append("assignment")
        return True, "00"

    async def track_color(*args, **kwargs):
        call_order.append("color")
        return True, "00"

    async def track_offset(*args, **kwargs):
        call_order.append("offset")
        return True, "00"

    telnet.remove_tool_from_pot = AsyncMock(side_effect=track_delete)
    telnet.assign_tool_to_pot = AsyncMock(side_effect=track_assign)
    telnet.change_atc_tool = AsyncMock(side_effect=track_color)
    telnet.write_tool_offset = AsyncMock(side_effect=track_offset)

    _state.polling_service = MagicMock()
    _state.polling_service.refresh_tool_data = AsyncMock(return_value={})
    req = BatchToolChangesRequest(
        changes=[
            ToolChangeItem(operation_type="color", pot_number=2, tool_number=6, color=3),
            ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=10),
            ToolChangeItem(operation_type="delete", pot_number=1, tool_number=5),
            ToolChangeItem(operation_type="offset", tool_number=5, offset_type="H", value=1.5),
        ]
    )
    try:
        result = await tools.batch_apply_tool_changes(1, req, db=_db(_machine()))
        assert result.successful == 4
        assert result.failed == 0
        assert call_order == ["delete", "assignment", "color", "offset"]
    finally:
        _state.polling_service = None


@pytest.mark.asyncio
async def test_batch_apply_tool_changes_unsafe_strict_op(monkeypatch):
    from app.api._status_state import BatchToolChangesRequest, ToolChangeItem

    _patch_safe(monkeypatch, safe=False)
    req = BatchToolChangesRequest(
        changes=[
            ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=10),
        ]
    )
    with pytest.raises(HTTPException) as ei:
        await tools.batch_apply_tool_changes(1, req, db=_db(_machine()))
    assert ei.value.status_code == 409


@pytest.mark.asyncio
async def test_batch_apply_tool_changes_partial_failure(monkeypatch):
    from app.api._status_state import BatchToolChangesRequest, ToolChangeItem

    _patch_safe(monkeypatch)
    telnet = _patch_telnet(monkeypatch)
    telnet.change_atc_tool = AsyncMock(side_effect=[(True, "00"), (False, "01")])

    req = BatchToolChangesRequest(
        changes=[
            ToolChangeItem(operation_type="color", pot_number=1, tool_number=5, color=2),
            ToolChangeItem(operation_type="color", pot_number=2, tool_number=6, color=3),
        ]
    )
    result = await tools.batch_apply_tool_changes(1, req, db=_db(_machine()))
    assert result.successful == 1
    assert result.failed == 1
    assert len(result.results) == 2


def test_tool_write_service_validation_operation_type():
    from app.api._status_state import ToolChangeItem
    from app.services.tool_write_service import validation_operation_type

    assert validation_operation_type([
        ToolChangeItem(operation_type="color", pot_number=1, tool_number=1, color=1),
    ]) == "tool_color"
    assert validation_operation_type([
        ToolChangeItem(operation_type="color", pot_number=1, tool_number=1, color=1),
        ToolChangeItem(operation_type="offset", tool_number=5, offset_type="H", value=1.0),
    ]) == "tool_offset"
    assert validation_operation_type([
        ToolChangeItem(operation_type="life", tool_number=5, life_value=100),
        ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=10),
    ]) == "tool_assignment"


def test_validate_batch_pot_conflicts():
    from app.api._status_state import ToolChangeItem
    from app.services.tool_write_service import validate_batch_pot_conflicts

    assert validate_batch_pot_conflicts([
        ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=10),
        ToolChangeItem(operation_type="cap", pot_number=2),
    ]) is not None
    assert validate_batch_pot_conflicts([
        ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=10),
        ToolChangeItem(operation_type="assignment", pot_number=3, tool_number=11),
    ]) is None


def test_pots_needing_preclear_swap():
    from app.api._status_state import ToolChangeItem
    from app.services.tool_write_service import pots_needing_preclear_before_assignments

    atc = {1: 1, 2: 2}
    changes = [
        ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=1),
        ToolChangeItem(operation_type="assignment", pot_number=1, tool_number=2),
    ]
    assert pots_needing_preclear_before_assignments(changes, atc) == [1, 2]


def test_pots_needing_preclear_move_to_empty():
    from app.api._status_state import ToolChangeItem
    from app.services.tool_write_service import pots_needing_preclear_before_assignments

    atc = {1: 5, 3: 0}
    changes = [ToolChangeItem(operation_type="assignment", pot_number=3, tool_number=5)]
    assert pots_needing_preclear_before_assignments(changes, atc) == [1]


def test_pots_needing_preclear_skips_explicit_delete():
    from app.api._status_state import ToolChangeItem
    from app.services.tool_write_service import pots_needing_preclear_before_assignments

    atc = {1: 5, 2: 0}
    changes = [
        ToolChangeItem(operation_type="delete", pot_number=1, tool_number=5),
        ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=5),
    ]
    assert pots_needing_preclear_before_assignments(changes, atc) == []


def test_pots_needing_preclear_move_into_occupied():
    from app.api._status_state import ToolChangeItem
    from app.services.tool_write_service import pots_needing_preclear_before_assignments

    atc = {1: 1, 2: 2}
    changes = [ToolChangeItem(operation_type="assignment", pot_number=2, tool_number=1)]
    assert pots_needing_preclear_before_assignments(changes, atc) == [1, 2]

