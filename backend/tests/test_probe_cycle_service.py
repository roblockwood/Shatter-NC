"""Tests for stepped probe_cycle_service (write / start / collect)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.services.probe_cycle_service import (
    _Snap,
    _is_cycle_complete,
    _is_idle,
    _is_running,
    _memstrt_catalog_target,
    _wait_until,
    collect_probe_results,
    poison_probe_macros,
    start_probe_program,
    write_probe_macros,
)


def test_idle_running_predicates():
    assert _is_idle(_Snap(prd3_status="standby", operation_status=0))
    assert not _is_idle(_Snap(prd3_status="operating", operation_status=1))
    assert _is_running(_Snap(prd3_status="operating", operation_status=0))
    assert not _is_idle(_Snap(prd3_status=None, operation_status=None))
    assert _is_cycle_complete(_Snap(prd3_status="standby", operation_status=0))
    assert _is_cycle_complete(_Snap(prd3_status="operating", operation_status=2))
    assert not _is_cycle_complete(_Snap(prd3_status="operating", operation_status=1))
    assert not _is_cycle_complete(_Snap())


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
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.start_memory_program = AsyncMock(return_value=(True, "00"))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", 1.0))
    client.get_status_description = MagicMock(return_value="OK")

    async def fake_create(*args, **kwargs):
        return client

    async def fake_live(self, **kwargs):
        return True, None, {"status": "standby"}

    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        fake_create,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service._cached_machine_status",
        lambda _mid: {},
    )
    monkeypatch.setattr(
        "app.services.machine_state_validator.MachineStateValidator.validate_macro_write_live_minimal",
        fake_live,
    )

    result = await write_probe_macros(
        db_machine=machine,
        machine_id=1,
        routine_id="diameter_inside",
        mode="probe",
        params={"900": 54, "904": 50.8},
    )

    assert result.ok is True, result.error
    assert result.phase == "written"
    assert result.target_program == 8116
    assert 904 in result.macros_written
    client.start_memory_program.assert_not_awaited()
    client.change_folder.assert_awaited_with("/", verbose=False)


@pytest.mark.asyncio
async def test_wait_until_fails_fast_on_unreadable(monkeypatch):
    client = MagicMock()

    async def empty_snap(c, cv):
        return _Snap()

    monkeypatch.setattr(
        "app.services.probe_cycle_service._snapshot",
        empty_snap,
    )

    with pytest.raises(RuntimeError, match="Could not read MEM/PRD3"):
        await _wait_until(
            client,
            "C00",
            predicate=_is_idle,
            label="idle before macro write",
            timeout_s=30,
            poll_s=0.01,
            unreadable_limit=3,
        )


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
    client.change_mode = AsyncMock(return_value=(True, "00"))
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.start_memory_program = AsyncMock(return_value=(True, "00"))
    client.get_status_description = MagicMock(return_value="OK")

    snaps = [
        _Snap(prd3_status="standby", operation_status=0),  # idle before MEMSTRT
        _Snap(prd3_status="operating", operation_status=1),  # after MEMSTRT
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
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.get_macro_variable_range = AsyncMock(
        return_value=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
    )
    client.get_macro_variable = AsyncMock(side_effect=lambda n, verbose=False: float(n))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))
    client.get_status_description = MagicMock(return_value="OK")

    snaps = [
        _Snap(prd3_status="operating", operation_status=1),
        _Snap(prd3_status="standby", operation_status=0),
        _Snap(prd3_status="standby", operation_status=0),  # post-settle running check
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
        "app.services.probe_cycle_service.POST_CYCLE_SETTLE_S",
        0,
    )

    result = await collect_probe_results(
        db_machine=machine,
        machine_id=1,
        cycle_timeout_s=5,
        poll_s=0.01,
    )
    assert result.ok is True, result.error
    assert result.phase == "complete"
    assert result.results["100"] == 100.0
    client.get_macro_variable_range.assert_awaited()
    client.change_folder.assert_awaited_with("/", verbose=False)
    assert client.write_macro_variable.await_count >= 1


@pytest.mark.asyncio
async def test_collect_does_not_poison_on_wait_failure(monkeypatch):
    machine = SimpleNamespace(id=1, ip_address="10.0.0.1", control_version="C00")
    client = MagicMock()
    client.disconnect = AsyncMock()
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))
    client.get_status_description = MagicMock(return_value="OK")

    async def always_running(c, cv):
        return _Snap(prd3_status="operating", operation_status=1)

    async def fake_create(*args, **kwargs):
        return client

    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        fake_create,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service._snapshot",
        always_running,
    )

    result = await collect_probe_results(
        db_machine=machine,
        machine_id=1,
        cycle_timeout_s=0.05,
        poll_s=0.01,
    )
    assert result.ok is False
    assert result.phase == "waiting_complete"
    client.write_macro_variable.assert_not_awaited()


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
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))
    client.get_status_description = MagicMock(return_value="OK")

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
    assert call("/", verbose=False) in client.change_folder.await_args_list
