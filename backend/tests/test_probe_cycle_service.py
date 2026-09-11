"""Tests for stepped probe_cycle_service (write / start / collect)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.probe_cycle_service import (
    _Snap,
    _is_idle,
    _is_running,
    _memstrt_catalog_target,
    collect_probe_results,
    poison_probe_macros,
    start_probe_program,
    write_probe_macros,
)


def test_idle_running_predicates():
    assert _is_idle(_Snap(prd3_status="standby", operation_status=0))
    assert not _is_idle(_Snap(prd3_status="operating", operation_status=1))
    assert _is_running(_Snap(prd3_status="operating", operation_status=0))


@pytest.mark.asyncio
async def test_write_validation_error():
    machine = SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        poll_interval_seconds=5,
        control_version="C00",
    )
    result = await write_probe_macros(
        db_machine=machine,
        machine_id=1,
        routine_id="corner_xyz",
        mode="probe",
        params={"900": 0, "901": 1, "902": 1, "903": 1},
    )
    assert result.ok is False
    assert result.phase == "validate"


@pytest.mark.asyncio
async def test_write_macros_no_memstrt(monkeypatch):
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
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.start_memory_program = AsyncMock(return_value=(True, "00"))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", 1.0))
    client.get_status_description = MagicMock(return_value="OK")

    async def fake_snapshot(c, cv):
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

    result = await write_probe_macros(
        db_machine=machine,
        machine_id=1,
        routine_id="diameter_inside",
        mode="probe",
        params={"900": 54, "904": 50.8},
        start_timeout_s=5,
        poll_s=0.01,
    )

    assert result.ok is True
    assert result.phase == "written"
    assert result.target_program == 8116
    assert 904 in result.macros_written
    client.start_memory_program.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_memstrt_catalog_target(monkeypatch):
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
    client.get_status_description = MagicMock(return_value="OK")

    snaps = [
        _Snap(prd3_status="standby", operation_status=0),
        _Snap(prd3_status="operating", operation_status=1),
    ]

    async def fake_snapshot(c, cv):
        if snaps:
            return snaps.pop(0)
        return _Snap(prd3_status="operating", operation_status=1)

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

    result = await start_probe_program(
        db_machine=machine,
        machine_id=1,
        routine_id="diameter_inside",
        mode="probe",
        params={"900": 54, "904": 50.8},
        start_timeout_s=5,
        poll_s=0.01,
    )

    assert result.ok is True
    assert result.phase == "running"
    assert result.target_program == 8116
    client.start_memory_program.assert_awaited_with(8116, verbose=False)


@pytest.mark.asyncio
async def test_memstrt_refuse_non_catalog(monkeypatch):
    client = MagicMock()
    client.start_memory_program = AsyncMock(return_value=(True, "00"))
    with pytest.raises(RuntimeError, match="allowlist"):
        await _memstrt_catalog_target(client, 1234)
    client.start_memory_program.assert_not_awaited()


@pytest.mark.asyncio
async def test_collect_probe_results(monkeypatch):
    machine = SimpleNamespace(id=1, ip_address="10.0.0.1", control_version="C00")
    client = MagicMock()
    client.disconnect = AsyncMock()
    client.get_macro_variable = AsyncMock(side_effect=lambda n, verbose=False: float(n))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))

    async def fake_snapshot(c, cv):
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

    result = await collect_probe_results(
        db_machine=machine,
        machine_id=1,
        cycle_timeout_s=5,
        poll_s=0.01,
    )
    assert result.ok is True
    assert result.phase == "complete"
    assert result.results["100"] == 100.0


@pytest.mark.asyncio
async def test_ensure_safety_uses_validator_no_ctor_args(monkeypatch):
    """Regression: MachineStateValidator() takes no args; no validate_for_macro_write."""
    from app.services.probe_cycle_service import _ensure_safety

    machine = SimpleNamespace(
        id=1,
        name="Mill",
        poll_interval_seconds=5,
        control_version="C00",
    )
    client = MagicMock()

    monkeypatch.setattr(
        "app.services.probe_cycle_service._cached_machine_status",
        lambda _mid: {},
    )

    async def fake_live(self, **kwargs):
        assert kwargs["telnet_client"] is client
        return True, None, {"status": "standby"}

    monkeypatch.setattr(
        "app.services.machine_state_validator.MachineStateValidator.validate_macro_write_live_minimal",
        fake_live,
    )

    ok, err, data = await _ensure_safety(machine, 1, client)
    assert ok is True
    assert err is None
    assert data.get("status") == "standby"


@pytest.mark.asyncio
async def test_poison_probe_macros(monkeypatch):
    machine = SimpleNamespace(id=1, ip_address="10.0.0.1", control_version="C00")
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
    assert client.write_macro_variable.await_count >= 1
