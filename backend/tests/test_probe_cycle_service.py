"""Tests for gated probe_cycle_service (O8099 only)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.probe_cycle_service import (
    _Snap,
    _is_idle,
    _is_m0_hold,
    _is_running,
    arm_probe_cycle,
    collect_probe_results,
    poison_probe_macros,
)


def test_idle_running_m0_predicates():
    assert _is_idle(_Snap(prd3_status="standby", operation_status=0))
    assert not _is_idle(_Snap(prd3_status="operating", operation_status=1))
    assert _is_running(_Snap(prd3_status="operating", operation_status=0))
    assert _is_m0_hold(_Snap(prd3_status="operating", operation_status=2))
    assert _is_m0_hold(_Snap(prd3_status="stopped", operation_status=3))
    assert not _is_m0_hold(_Snap(prd3_status="operating", operation_status=1))


@pytest.mark.asyncio
async def test_arm_validation_error():
    machine = SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        poll_interval_seconds=5,
        control_version="C00",
    )
    result = await arm_probe_cycle(
        db_machine=machine,
        machine_id=1,
        routine_id="corner_xyz",
        mode="probe",
        params={"900": 0, "901": 1, "902": 1, "903": 1},
    )
    assert result.ok is False
    assert result.phase == "validate"


@pytest.mark.asyncio
async def test_arm_probe_waits_for_m0_and_only_starts_gate(monkeypatch):
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
    client.get_status_description = MagicMock(return_value="OK")

    snaps = [
        _Snap(prd3_status="standby", operation_status=0),  # idle before
        _Snap(prd3_status="operating", operation_status=1),  # started
        _Snap(prd3_status="operating", operation_status=2),  # M0 hold
    ]

    async def fake_snapshot(c, cv):
        if snaps:
            return snaps.pop(0)
        return _Snap(prd3_status="operating", operation_status=2)

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

    result = await arm_probe_cycle(
        db_machine=machine,
        machine_id=1,
        routine_id="diameter_inside",
        mode="probe",
        params={"900": 54, "904": 50.8},
        start_timeout_s=5,
        m0_timeout_s=5,
        poll_s=0.01,
    )

    assert result.ok is True
    assert result.phase == "awaiting_m0"
    assert result.gate_program == 8099
    assert result.target_program == 8116
    assert result.macros_written[908] == 8116.0
    client.start_memory_program.assert_awaited_with(8099, verbose=False)
    # Never start Blum helper directly
    for call in client.start_memory_program.await_args_list:
        assert call.args[0] == 8099


@pytest.mark.asyncio
async def test_memstrt_refuse_non_gate(monkeypatch):
    from app.services.probe_cycle_service import _memstrt_gate_only

    client = MagicMock()
    client.start_memory_program = AsyncMock(return_value=(True, "00"))
    with pytest.raises(RuntimeError, match="allowlist"):
        await _memstrt_gate_only(client, 8116)
    client.start_memory_program.assert_not_awaited()


@pytest.mark.asyncio
async def test_collect_probe_results(monkeypatch):
    machine = SimpleNamespace(id=1, ip_address="10.0.0.1", control_version="C00")
    client = MagicMock()
    client.disconnect = AsyncMock()
    client.get_macro_variable = AsyncMock(side_effect=lambda n, verbose=False: float(n))
    client.write_macro_variable = AsyncMock(return_value=(True, "00", None))

    snaps = [
        _Snap(prd3_status="standby", operation_status=0),
    ]

    async def fake_snapshot(c, cv):
        return snaps[0]

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

    result = await collect_probe_results(machine, machine_id=1, poll_s=0.01, cycle_timeout_s=5)
    assert result.ok is True
    assert result.phase == "complete"
    assert "100" in result.results
    assert client.write_macro_variable.await_count >= 1


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
