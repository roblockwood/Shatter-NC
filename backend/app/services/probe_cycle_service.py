"""Stepped Blum probe cycles — Shatter confirms each stage before motion.

Flow (each step is a separate API call / UI GO):
  1. write  — validate + write job macros only (no MEMSTRT)
  2. start  — MEMSTRT catalog target O-number only (allowlisted)
  3. collect — wait idle, read #100+, poison

O8099 gate / M98 is abandoned. Motion only happens on an explicit start call.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from app.models.machine import Machine
from app.parsers.mem_parser_v2 import parse_mem_v2
from app.parsers.prd3_parser_v2 import parse_prd3_v2
from app.services.machine_state_validator import (
    MachineStateValidator,
    macro_write_cache_max_age_seconds,
)
from app.services.probe_catalog import (
    ProbeCatalogError,
    get_allowed_start_programs,
    get_poison_values,
    get_result_macro_numbers,
    validate_run_params,
)

logger = logging.getLogger(__name__)

DEFAULT_FOLDER = "PROGRAM"
DEFAULT_POLL_S = 0.5
DEFAULT_START_TIMEOUT_S = 30.0
DEFAULT_CYCLE_TIMEOUT_S = 180.0

IDLE_STATUSES = frozenset({"standby", "stopped", "off"})
ACTIVE_STATUSES = frozenset({"operating"})
FATAL_STATUSES = frozenset({"error"})


@dataclass
class ProbeCycleResult:
    ok: bool
    program: Optional[int] = None
    target_program: Optional[int] = None
    routine_id: Optional[str] = None
    mode: Optional[str] = None
    macros_written: Dict[int, float] = field(default_factory=dict)
    results: Dict[str, Optional[float]] = field(default_factory=dict)
    phase: str = "idle"
    error: Optional[str] = None
    status_data: Dict[str, Any] = field(default_factory=dict)
    elapsed_s: float = 0.0
    # Deprecated — kept for API compatibility with older clients
    gate_program: Optional[int] = None


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
    deadline = time.perf_counter() + timeout_s
    last = _Snap()
    while time.perf_counter() < deadline:
        last = await _snapshot(client, control_version)
        if last.prd3_status in FATAL_STATUSES:
            raise RuntimeError(f"Machine error while waiting for {label}")
        if predicate(last):
            return last
        await asyncio.sleep(poll_s)
    raise TimeoutError(
        f"Timeout waiting for {label} "
        f"(prd3={last.prd3_status!r} op={last.operation_status!r})"
    )


async def _ensure_safety(
    db_machine: Machine, machine_id: int, client: Any
) -> tuple[bool, Optional[str], Dict[str, Any]]:
    """Cache-then-live macro-write safety check on an open telnet session."""
    cached = _cached_machine_status(machine_id)
    max_age = macro_write_cache_max_age_seconds(db_machine.poll_interval_seconds or 5)
    validator = MachineStateValidator()
    cache_safe, cache_error, status_data = validator.try_validate_macro_write_from_cache(
        cached_status=cached,
        machine_id=machine_id,
        machine_name=db_machine.name,
        max_age_seconds=max_age,
    )
    if cache_safe is True:
        return True, None, status_data

    is_safe, live_error, status_data = await validator.validate_macro_write_live_minimal(
        telnet_client=client,
        control_version=db_machine.control_version,
        machine_id=machine_id,
        machine_name=db_machine.name,
    )
    if not is_safe:
        return False, live_error or cache_error or "Machine not safe for macro write", status_data
    return True, None, status_data


async def _write_macros(client: Any, writes: Dict[int, float]) -> None:
    for macro, value in writes.items():
        ok, status, _ = await client.write_macro_variable(
            macro_number=macro,
            value=value,
            verbose=False,
            verify=True,
        )
        if not ok:
            desc = client.get_status_description(status or "00")
            raise RuntimeError(f"Failed writing #{macro}={value}: {status} ({desc})")


async def _poison_macros(
    client: Any, targets: Optional[Set[int]] = None
) -> Dict[int, float]:
    poison = get_poison_values()
    if targets is None:
        targets = set(poison.keys())
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


async def _memstrt_catalog_target(client: Any, program: int) -> None:
    """Hard allowlist: only MEMSTRT O-numbers that appear in the probe catalog."""
    allowed = get_allowed_start_programs()
    if int(program) not in allowed:
        raise RuntimeError(
            f"refusing MEMSTRT O{program:04d}: not in probe catalog allowlist"
        )
    ok, status = await client.start_memory_program(program, verbose=False)
    if not ok:
        desc = client.get_status_description(status or "00")
        raise RuntimeError(f"MEMSTRT {program:04d} failed: {status} ({desc})")


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


async def write_probe_macros(
    db_machine: Machine,
    machine_id: int,
    routine_id: str,
    mode: str,
    params: Dict[str, float],
    *,
    start_timeout_s: float = DEFAULT_START_TIMEOUT_S,
    poll_s: float = DEFAULT_POLL_S,
) -> ProbeCycleResult:
    """Validate + write job macros only. Does not MEMSTRT / cause motion."""
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    try:
        resolved, writes = validate_run_params(routine_id, mode, params)
    except ProbeCatalogError as e:
        return ProbeCycleResult(
            ok=False,
            routine_id=routine_id,
            mode=mode,
            phase="validate",
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )

    target_program = int(resolved["program"])
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
                target_program=target_program,
                routine_id=routine_id,
                mode=mode,
                phase=phase,
                error=err or "Machine not safe for macro write",
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
            label="idle before macro write",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
        )

        phase = "writing"
        await _write_macros(client, writes)

        return ProbeCycleResult(
            ok=True,
            program=target_program,
            target_program=target_program,
            routine_id=routine_id,
            mode=mode,
            macros_written=writes,
            phase="written",
            status_data=status_data,
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception(
            "probe write failed machine=%s routine=%s phase=%s",
            machine_id,
            routine_id,
            phase,
        )
        return ProbeCycleResult(
            ok=False,
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


async def start_probe_program(
    db_machine: Machine,
    machine_id: int,
    routine_id: str,
    mode: str,
    params: Dict[str, float],
    *,
    folder: str = DEFAULT_FOLDER,
    poll_s: float = DEFAULT_POLL_S,
    start_timeout_s: float = DEFAULT_START_TIMEOUT_S,
) -> ProbeCycleResult:
    """
    MEMSTRT the catalog target program (motion). Allowlisted O-numbers only.

    Does not rewrite macros — call write_probe_macros first. Waits until the
    program is observed running, then returns so the UI can COLLECT later.
    """
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    try:
        resolved, _writes = validate_run_params(routine_id, mode, params)
    except ProbeCatalogError as e:
        return ProbeCycleResult(
            ok=False,
            routine_id=routine_id,
            mode=mode,
            phase="validate",
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )

    target_program = int(resolved["program"])
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
                program=target_program,
                target_program=target_program,
                routine_id=routine_id,
                mode=mode,
                phase=phase,
                error=err or "Machine not safe for probe start",
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
            label="idle before MEMSTRT",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
        )

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
            await _memstrt_catalog_target(client, target_program)
        finally:
            await client.change_folder("/", verbose=False)

        phase = "running"
        await _wait_until(
            client,
            control_version,
            predicate=_is_running,
            label="probe program start",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
        )

        return ProbeCycleResult(
            ok=True,
            program=target_program,
            target_program=target_program,
            routine_id=routine_id,
            mode=mode,
            phase="running",
            status_data=status_data,
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception(
            "probe start failed machine=%s routine=%s phase=%s",
            machine_id,
            routine_id,
            phase,
        )
        if client is not None:
            try:
                await client.change_folder("/", verbose=False)
            except Exception:
                pass
        return ProbeCycleResult(
            ok=False,
            program=target_program,
            target_program=target_program,
            routine_id=routine_id,
            mode=mode,
            phase=phase,
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )
    finally:
        if client:
            await client.disconnect()


async def collect_probe_results(
    db_machine: Machine,
    machine_id: int,
    *,
    poll_s: float = DEFAULT_POLL_S,
    cycle_timeout_s: float = DEFAULT_CYCLE_TIMEOUT_S,
    poison: bool = True,
) -> ProbeCycleResult:
    """Wait for idle after motion, read #100+, optionally poison."""
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
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
            label="cycle complete",
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
            phase=phase,
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )
    finally:
        if client:
            await client.disconnect()
