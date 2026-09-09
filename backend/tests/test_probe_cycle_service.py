"""Tests for probe_cycle_service with mocked telnet client."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.probe_cycle_service import (
    ProbeCycleResult,
    _is_idle,
    _is_running,
    _Snap,
    poison_probe_macros,
    run_probe_cycle,
)


def test_idle_running_predicates():
    assert _is_idle(_Snap(prd3_status="standby", operation_status=0))
    assert not _is_idle(_Snap(prd3_status="operating", operation_status=1))
    assert _is_running(_Snap(prd3_status="operating", operation_status=0))
    assert _is_running(_Snap(prd3_status="standby", operation_status=1))


@pytest.mark.asyncio
async def test_run_probe_cycle_validation_error():
    machine = SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        poll_interval_seconds=5,
        control_version="C00",
    )
    result = await run_probe_cycle(
        db_machine=machine,
        machine_id=1,
        routine_id="corner_xyz",
        mode="probe",
        params={"900": 0, "901": 1, "902": 1, "903": 1},
    )
    assert result.ok is False
    assert result.phase == "validate"
    assert result.error


@pytest.mark.asyncio
async def test_run_probe_cycle_success(monkeypatch):
    machine = SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        poll_interval_seconds=5,
        control_version="C00",
    )

    client = MagicMock()
    client.disconnect = AsyncMock()
    client.get_working_folder = AsyncMock(return_value="/")
    client.change_mode = AsyncMock(return_value=(True, "00"))
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.start_memory_program = AsyncMock(return_value=(True, "00"))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", 1.0))
    client.get_macro_variable = AsyncMock(side_effect=lambda n, verbose=False: float(n))
    client.get_status_description = MagicMock(return_value="OK")
    client.get_memory_data = AsyncMock(return_value=None)
    client.get_prd3_data = AsyncMock(return_value=None)

    # Drive idle → running → idle via snapshot side effects
    snaps = [
        _Snap(prd3_status="standby", operation_status=0),  # idle before
        _Snap(prd3_status="operating", operation_status=1),  # started
        _Snap(prd3_status="standby", operation_status=0),  # complete
    ]

    async def fake_snapshot(c, cv):
        if snaps:
            return snaps.pop(0)
        return _Snap(prd3_status="standby", operation_status=0)

    async def fake_create(*args, **kwargs):
        return client

    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        fake_create,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service._snapshot",
        fake_snapshot,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service._ensure_safety",
        AsyncMock(return_value=(True, None, {"status": "standby"})),
    )

    result = await run_probe_cycle(
        db_machine=machine,
        machine_id=1,
        routine_id="diameter_inside",
        mode="probe",
        params={"900": 54, "904": 50.8},
        start_timeout_s=5,
        cycle_timeout_s=5,
        poll_s=0.01,
    )

    assert result.ok is True
    assert result.program == 8116
    assert result.phase == "complete"
    assert result.macros_written[900] == 54.0
    assert "100" in result.results
    client.change_mode.assert_awaited()
    client.start_memory_program.assert_awaited_with(8116, verbose=False)
    # Folder restored to /
    assert any(
        call.args and call.args[0] == "/"
        for call in client.change_folder.await_args_list
    )


@pytest.mark.asyncio
async def test_poison_probe_macros(monkeypatch):
    machine = SimpleNamespace(id=1, ip_address="10.0.0.1")
    client = MagicMock()
    client.disconnect = AsyncMock()
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))

    async def fake_create(*args, **kwargs):
        return client

    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        fake_create,
    )

    result = await poison_probe_macros(machine)
    assert result.ok is True
    assert result.phase == "poisoned"
    assert client.write_macro_variable.await_count >= 5
