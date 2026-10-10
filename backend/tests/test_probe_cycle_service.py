# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

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
    _normalize_tool_list,
    _read_results,
    _wait_until,
    collect_probe_results,
    poison_probe_macros,
    run_tool_length_batch,
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


def _results_client(range_values, single=lambda n: None):
    client = MagicMock()
    client.get_macro_variable_range = AsyncMock(return_value=range_values)
    client.get_macro_variable = AsyncMock(
        side_effect=lambda n, verbose=False: single(n)
    )
    return client


@pytest.mark.asyncio
async def test_read_results_full_range():
    client = _results_client([float(n) for n in range(100, 108)])
    results, warnings = await _read_results(client)
    assert results == {str(n): float(n) for n in range(100, 108)}
    assert warnings == []
    client.get_macro_variable_range.assert_awaited_with(
        100, 8, verbose=False, vacant_as_none=True
    )
    client.get_macro_variable.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_results_partial_vacant_is_trusted():
    client = _results_client([1.5, 2.5, None, None, None, None, None, None])
    results, warnings = await _read_results(client)
    assert results["100"] == 1.5
    assert results["102"] is None
    assert warnings == []
    client.get_macro_variable.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_results_all_vacant_falls_back_per_variable():
    client = _results_client([None] * 8, single=lambda n: float(n) + 0.5)
    results, warnings = await _read_results(client)
    assert results == {str(n): float(n) + 0.5 for n in range(100, 108)}
    assert warnings == []
    assert client.get_macro_variable.await_count == 8


@pytest.mark.asyncio
async def test_read_results_all_vacant_everywhere_warns_vacant():
    client = _results_client([None] * 8)
    results, warnings = await _read_results(client)
    assert all(v is None for v in results.values())
    assert len(warnings) == 1
    assert "vacant" in warnings[0]


@pytest.mark.asyncio
async def test_read_results_range_none_falls_back():
    client = _results_client(None, single=lambda n: float(n))
    results, warnings = await _read_results(client)
    assert results["107"] == 107.0
    assert len(warnings) == 1
    assert "0/8" in warnings[0]


@pytest.mark.asyncio
async def test_read_results_range_none_and_singles_fail_warns_read_failed():
    client = _results_client(None)
    results, warnings = await _read_results(client)
    assert all(v is None for v in results.values())
    assert len(warnings) == 1
    assert "read failed" in warnings[0].lower()


@pytest.mark.asyncio
async def test_read_results_short_range_reads_rest_individually():
    client = _results_client([1.0, 2.0, 3.0], single=lambda n: float(n))
    results, warnings = await _read_results(client)
    assert results["100"] == 1.0
    assert results["102"] == 3.0
    assert results["103"] == 103.0
    assert results["107"] == 107.0
    assert client.get_macro_variable.await_count == 5
    assert "3/8" in warnings[0]


@pytest.mark.asyncio
async def test_collect_surfaces_vacant_warning(monkeypatch):
    machine = SimpleNamespace(id=1, ip_address="10.0.0.1", control_version="C00")
    client = MagicMock()
    client.disconnect = AsyncMock()
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.get_macro_variable_range = AsyncMock(return_value=[None] * 8)
    client.get_macro_variable = AsyncMock(return_value=None)
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))
    client.get_status_description = MagicMock(return_value="OK")

    async def idle(c, cv):
        return _Snap(prd3_status="standby", operation_status=0)

    async def fake_create(*args, **kwargs):
        return client

    monkeypatch.setattr("app.clients.telnet_client.create_fresh_connection", fake_create)
    monkeypatch.setattr("app.services.probe_cycle_service._snapshot", idle)
    monkeypatch.setattr("app.services.probe_cycle_service.POST_CYCLE_SETTLE_S", 0)

    result = await collect_probe_results(
        db_machine=machine, machine_id=1, cycle_timeout_s=5, poll_s=0.01
    )
    assert result.ok is True
    assert all(v is None for v in result.results.values())
    assert result.warnings and "vacant" in result.warnings[0]


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


@pytest.mark.asyncio
async def test_poison_emits_per_macro_progress(monkeypatch):
    machine = SimpleNamespace(id=7, ip_address="10.0.0.1", control_version="C00")
    client = MagicMock()
    client.disconnect = AsyncMock()
    client.change_folder = AsyncMock(return_value=(True, "00"))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))
    client.get_status_description = MagicMock(return_value="OK")

    messages = []

    async def capture_progress(ctx, phase, message, **kwargs):
        messages.append((phase, message))

    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        AsyncMock(return_value=client),
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service.emit_probe_progress",
        capture_progress,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service.asyncio.sleep",
        AsyncMock(),
    )

    result = await poison_probe_macros(machine, client_run_id="run-1")
    assert result.ok is True
    poison_msgs = [m for phase, m in messages if phase == "poisoning"]
    # Banner + one start/finish pair per poison macro (#900–908, #920)
    assert any("Writing sentinel" in m for m in poison_msgs)
    assert any("WRTMCNM #900=" in m for m in poison_msgs)
    assert any("Wrote #900=" in m for m in poison_msgs)
    assert any("WRTMCNM #920=" in m for m in poison_msgs)
    assert any("Wrote #920=" in m for m in poison_msgs)
    assert sum(1 for m in poison_msgs if m.startswith("WRTMCNM #")) == 10
    assert sum(1 for m in poison_msgs if m.startswith("Wrote #")) == 10
    assert messages[-1][0] == "complete"


def test_normalize_tool_list_dedupes_and_rejects():
    assert _normalize_tool_list([3, 1, 3, 2]) == [3, 1, 2]
    with pytest.raises(ValueError, match="Invalid"):
        _normalize_tool_list([0])
    with pytest.raises(ValueError, match="Invalid"):
        _normalize_tool_list([255])
    with pytest.raises(ValueError, match="at least one"):
        _normalize_tool_list([])


@pytest.mark.asyncio
async def test_tool_length_batch_validate_error():
    machine = SimpleNamespace(id=1, ip_address="10.0.0.1", control_version="C00")
    result = await run_tool_length_batch(
        db_machine=machine,
        machine_id=1,
        tools=[],
    )
    assert result.ok is False
    assert result.phase == "validate"


@pytest.mark.asyncio
async def test_tool_length_batch_aborts_on_first_failure(monkeypatch):
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

    writes = []

    async def fake_write(macro_number, value, verbose=False, verify=True):
        writes.append((macro_number, int(value)))
        if int(value) == 2:
            return False, "30", None
        return True, "00", float(value)

    client.write_macro_variable = AsyncMock(side_effect=fake_write)

    async def fake_create(*args, **kwargs):
        return client

    monkeypatch.setattr(
        "app.clients.telnet_client.create_fresh_connection",
        fake_create,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service._ensure_safety",
        AsyncMock(return_value=(True, None, {"status": "standby"})),
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service._wait_until",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service._snapshot",
        AsyncMock(
            return_value=_Snap(prd3_status="operating", operation_status=1)
        ),
    )
    monkeypatch.setattr(
        "app.services.probe_exclusive.collect_poll_seconds",
        lambda mid, default: 0.01,
    )
    monkeypatch.setattr(
        "app.services.probe_cycle_service.asyncio.sleep",
        AsyncMock(),
    )

    result = await run_tool_length_batch(
        db_machine=machine,
        machine_id=1,
        tools=[1, 2, 3],
        start_timeout_s=5,
        cycle_timeout_s=5,
        poll_s=0.01,
    )

    assert result.ok is False
    assert result.aborted is True
    assert [item.tool for item in result.tools] == [1, 2]
    assert result.tools[0].ok is True
    assert result.tools[1].ok is False
    assert writes == [(920, 1), (920, 2)]
    # First tool completed MEMSTRT; second failed before start
    assert client.start_memory_program.await_count == 1
