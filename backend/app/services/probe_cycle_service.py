"""Orchestrate gated Blum probe cycles via O8099 only.

Shatter never MEMSTRTs Blum O81xx/O82xx/O8100 directly. It writes job macros,
sets #908 to the target helper O-number, and MEMSTRTs O8099 (preview + M0).
After the operator Cycle-Starts past M0, collect() waits for idle and reads results.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.models.machine import Machine
from app.parsers.mem_parser_v2 import parse_mem_v2
from app.parsers.prd3_parser_v2 import parse_prd3_v2
from app.services.machine_state_validator import (
    MachineStateValidator,
    macro_write_cache_max_age_seconds,
)
from app.services.probe_catalog import (
    ProbeCatalogError,
    get_gate_program,
    get_poison_values,
    get_result_macro_numbers,
    get_target_macro,
    validate_run_params,
)

logger = logging.getLogger(__name__)

DEFAULT_FOLDER = "PROGRAM"
DEFAULT_POLL_S = 0.5
DEFAULT_START_TIMEOUT_S = 30.0
DEFAULT_CYCLE_TIMEOUT_S = 180.0
DEFAULT_M0_TIMEOUT_S = 60.0

IDLE_STATUSES = frozenset({"standby", "stopped", "off"})
ACTIVE_STATUSES = frozenset({"operating"})
FATAL_STATUSES = frozenset({"error"})
# Brother MEM: 2=Temporary stop, 3=Block stop (typical at M0 / #3006)
M0_OPERATION_STATUSES = frozenset({2, 3})


@dataclass
class ProbeCycleResult:
    ok: bool
    program: Optional[int] = None
    gate_program: Optional[int] = None
    target_program: Optional[int] = None
    routine_id: Optional[str] = None
    mode: Optional[str] = None
    macros_written: Dict[int, float] = field(default_factory=dict)
    results: Dict[str, Optional[float]] = field(default_factory=dict)
    phase: str = "idle"
    error: Optional[str] = None
    status_data: Dict[str, Any] = field(default_factory=dict)
    elapsed_s: float = 0.0


def _cached_machine_status(machine_id: int) -> Dict[str, Any]:
    import app.api._status_state as status_state

    polling = status_state.polling_service
    if polling is None:
        return {}
    ws = getattr(polling, "websocket_manager", None)
    if ws is None:
        return {}
    return ws.get_machine_status(machine_id) or {}


@dataclass
class _Snap:
    prd3_status: Optional[str] = None
    operation_status: Optional[int] = None


def _is_idle(snap: _Snap) -> bool:
    if snap.prd3_status in FATAL_STATUSES:
        return False
    if snap.prd3_status in ACTIVE_STATUSES:
        return False
    if snap.operation_status in (1, 2, 3):
        return False
    if snap.prd3_status in IDLE_STATUSES:
        return True
    return snap.operation_status == 0


def _is_running(snap: _Snap) -> bool:
    return snap.prd3_status in ACTIVE_STATUSES or snap.operation_status == 1


def _is_m0_hold(snap: _Snap) -> bool:
    """True when NC has paused for operator (M0 / message stop)."""
    return snap.operation_status in M0_OPERATION_STATUSES


async def _snapshot(client: Any, control_version: str) -> _Snap:
    snap = _Snap()
    mem_raw = await client.get_memory_data(verbose=False)
    if mem_raw:
        mem = parse_mem_v2(mem_raw.encode("utf-8"), control_version=control_version)
        snap.operation_status = mem.get("operation_status")

    prd3_raw = await client.get_prd3_data(control_version=control_version, verbose=False)
    if prd3_raw:
        prd3 = parse_prd3_v2(prd3_raw.encode("utf-8"), control_version=control_version)
        snap.prd3_status = (prd3.get("current_status") or {}).get("status")
    return snap


async def _wait_until(
    client: Any,
    control_version: str,
    *,
    predicate,
    label: str,
    timeout_s: float,
    poll_s: float,
) -> _Snap:
    deadline = time.monotonic() + timeout_s
    last = _Snap()
    while True:
        last = await _snapshot(client, control_version)
        if predicate(last):
            return last
        if last.prd3_status in FATAL_STATUSES:
            raise RuntimeError(f"machine error while waiting for {label}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timeout waiting for {label}")
        await asyncio.sleep(poll_s)


async def _ensure_safety(
    db_machine: Machine,
    machine_id: int,
    telnet_client: Any,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    validator = MachineStateValidator()
    max_age = macro_write_cache_max_age_seconds(db_machine.poll_interval_seconds)
    cached = _cached_machine_status(machine_id)

    cache_safe, cache_error, status_data = validator.try_validate_macro_write_from_cache(
        cached_status=cached,
        machine_id=machine_id,
        machine_name=db_machine.name,
        max_age_seconds=max_age,
    )
    if cache_safe is True:
        return True, None, status_data

    return await validator.validate_macro_write_live_minimal(
        telnet_client=telnet_client,
        control_version=db_machine.control_version,
        machine_id=machine_id,
        machine_name=db_machine.name,
    )


async def _write_macros(client: Any, writes: Dict[int, float]) -> None:
    for macro, value in sorted(writes.items()):
        ok, status, _ = await client.write_macro_variable(
            macro_number=macro,
            value=value,
            verbose=False,
            verify=True,
        )
        if not ok:
            desc = client.get_status_description(status or "00")
            raise RuntimeError(f"macro #{macro} write failed: {status} ({desc})")


async def _poison_macros(client: Any, macros: Optional[List[int]] = None) -> Dict[int, float]:
    poison = get_poison_values()
    targets = macros if macros is not None else list(poison.keys())
    written: Dict[int, float] = {}
    for macro in targets:
        if macro not in poison:
            continue
        value = poison[macro]
        ok, status, _ = await client.write_macro_variable(
            macro_number=macro,
            value=value,
            verbose=False,
            verify=False,
        )
        if ok:
            written[macro] = value
        else:
            logger.warning("Failed to poison macro #%s: %s", macro, status)
    return written


async def _read_results(client: Any) -> Dict[str, Optional[float]]:
    results: Dict[str, Optional[float]] = {}
    for num in get_result_macro_numbers():
        value = await client.get_macro_variable(num, verbose=False)
        results[str(num)] = value
    return results


async def _memstrt_gate_only(client: Any, gate_program: int) -> None:
    """Hard allowlist: probing may only start the Shatter gate program."""
    allowed = get_gate_program()
    if int(gate_program) != int(allowed):
        raise RuntimeError(
            f"refusing MEMSTRT O{gate_program:04d}: probing allowlist is O{allowed:04d} only"
        )
    ok, status = await client.start_memory_program(gate_program, verbose=False)
    if not ok:
        desc = client.get_status_description(status or "00")
        raise RuntimeError(f"MEMSTRT {gate_program:04d} failed: {status} ({desc})")


async def poison_probe_macros(db_machine: Machine) -> ProbeCycleResult:
    """Write sentinel values to all probe job macros without starting a cycle."""
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    client = None
    try:
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )
        written = await _poison_macros(client)
        return ProbeCycleResult(
            ok=True,
            phase="poisoned",
            macros_written=written,
            gate_program=get_gate_program(),
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception("probe poison failed for machine %s", db_machine.id)
        return ProbeCycleResult(
            ok=False,
            phase="error",
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )
    finally:
        if client:
            await client.disconnect()


async def arm_probe_cycle(
    db_machine: Machine,
    machine_id: int,
    routine_id: str,
    mode: str,
    params: Dict[str, float],
    *,
    folder: str = DEFAULT_FOLDER,
    poll_s: float = DEFAULT_POLL_S,
    start_timeout_s: float = DEFAULT_START_TIMEOUT_S,
    m0_timeout_s: float = DEFAULT_M0_TIMEOUT_S,
) -> ProbeCycleResult:
    """
    Arm gated probe: write macros + #908 target, MEMSTRT O8099 only, wait for M0.

    Does **not** poison (operator must still Cycle Start past M0).
    Does **not** MEMSTRT Blum helpers directly.
    """
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    gate_program = get_gate_program()
    target_macro = get_target_macro()

    try:
        resolved, writes = validate_run_params(routine_id, mode, params)
    except ProbeCatalogError as e:
        return ProbeCycleResult(
            ok=False,
            routine_id=routine_id,
            mode=mode,
            gate_program=gate_program,
            phase="validate",
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )

    target_program = int(resolved["program"])
    writes[target_macro] = float(target_program)
    control_version = db_machine.control_version or "C00"
    client = None
    phase = "connect"

    try:
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )

        phase = "safety"
        safe, err, status_data = await _ensure_safety(db_machine, machine_id, client)
        if not safe:
            return ProbeCycleResult(
                ok=False,
                program=gate_program,
                gate_program=gate_program,
                target_program=target_program,
                routine_id=routine_id,
                mode=mode,
                phase=phase,
                error=err or "Machine not safe for probe arm",
                status_data=status_data,
                elapsed_s=time.perf_counter() - t0,
            )

        pwd = await client.get_working_folder(verbose=False)
        if pwd and pwd != "/":
            await client.change_folder("/", verbose=False)

        phase = "idle_wait"
        await _wait_until(
            client,
            control_version,
            predicate=_is_idle,
            label="idle before probe arm",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
        )

        phase = "writing"
        await _write_macros(client, writes)

        phase = "starting"
        ok, status = await client.change_mode("MEM", verbose=False)
        if not ok:
            desc = client.get_status_description(status or "00")
            raise RuntimeError(f"CHGMODE MEM failed: {status} ({desc})")

        ok, status = await client.change_folder(folder, verbose=False)
        if not ok:
            desc = client.get_status_description(status or "00")
            raise RuntimeError(f"FLDCHG {folder} failed: {status} ({desc})")

        try:
            await _memstrt_gate_only(client, gate_program)
        finally:
            await client.change_folder("/", verbose=False)

        phase = "running"
        await _wait_until(
            client,
            control_version,
            predicate=_is_running,
            label="gate program start",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
        )

        phase = "awaiting_m0"
        await _wait_until(
            client,
            control_version,
            predicate=_is_m0_hold,
            label="M0 / operator confirm",
            timeout_s=m0_timeout_s,
            poll_s=poll_s,
        )

        return ProbeCycleResult(
            ok=True,
            program=gate_program,
            gate_program=gate_program,
            target_program=target_program,
            routine_id=routine_id,
            mode=mode,
            macros_written=writes,
            phase="awaiting_m0",
            status_data=status_data,
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception(
            "probe arm failed machine=%s routine=%s phase=%s",
            machine_id,
            routine_id,
            phase,
        )
        if client is not None:
            try:
                await client.change_folder("/", verbose=False)
            except Exception:
                pass
            # Do not poison on arm failure after write — operator may still be reviewing.
            # Explicit POISON endpoint remains available.

        return ProbeCycleResult(
            ok=False,
            program=gate_program,
            gate_program=gate_program,
            target_program=target_program,
            routine_id=routine_id,
            mode=mode,
            macros_written=writes,
            phase=phase,
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )
    finally:
        if client:
            await client.disconnect()


# Back-compat alias used by older imports / tests
async def run_probe_cycle(*args: Any, **kwargs: Any) -> ProbeCycleResult:
    return await arm_probe_cycle(*args, **kwargs)


async def collect_probe_results(
    db_machine: Machine,
    machine_id: int,
    *,
    poll_s: float = DEFAULT_POLL_S,
    cycle_timeout_s: float = DEFAULT_CYCLE_TIMEOUT_S,
    poison: bool = True,
) -> ProbeCycleResult:
    """
    After operator confirms past M0 and probing finishes: wait idle, read #100+, poison.
    """
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    gate_program = get_gate_program()
    control_version = db_machine.control_version or "C00"
    client = None
    phase = "connect"

    try:
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )

        phase = "waiting_complete"
        await _wait_until(
            client,
            control_version,
            predicate=_is_idle,
            label="cycle complete after M0",
            timeout_s=cycle_timeout_s,
            poll_s=poll_s,
        )

        phase = "reading"
        results = await _read_results(client)

        macros_written: Dict[int, float] = {}
        if poison:
            phase = "poisoning"
            macros_written = await _poison_macros(client)

        return ProbeCycleResult(
            ok=True,
            program=gate_program,
            gate_program=gate_program,
            results=results,
            macros_written=macros_written,
            phase="complete",
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception("probe collect failed machine=%s phase=%s", machine_id, phase)
        if client is not None and poison:
            try:
                await _poison_macros(client)
            except Exception:
                logger.warning("post-collect poison failed for machine %s", machine_id)
        return ProbeCycleResult(
            ok=False,
            program=gate_program,
            gate_program=gate_program,
            phase=phase,
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )
    finally:
        if client:
            await client.disconnect()
