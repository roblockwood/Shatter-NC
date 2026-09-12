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
DEFAULT_COLLECT_POLL_S = 1.0
DEFAULT_START_TIMEOUT_S = 30.0
DEFAULT_CYCLE_TIMEOUT_S = 180.0
POST_CYCLE_SETTLE_S = 0.75

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


@dataclass
class ProbeProgressCtx:
    machine_id: int
    api_step: str
    client_run_id: Optional[str] = None
    t0: float = field(default_factory=time.perf_counter)


def _cached_machine_status(machine_id: int) -> Dict[str, Any]:
    import app.api._status_state as status_state

    polling = status_state.polling_service
    if polling is None:
        return {}
    ws = getattr(polling, "websocket_manager", None)
    if ws is None:
        return {}
    return ws.get_machine_status(machine_id) or {}


async def emit_probe_progress(
    ctx: Optional[ProbeProgressCtx],
    phase: str,
    message: str,
    *,
    snap: Optional["_Snap"] = None,
    final: bool = False,
) -> None:
    if ctx is None:
        return
    import app.api._status_state as status_state

    polling = status_state.polling_service
    ws = getattr(polling, "websocket_manager", None) if polling else None
    if ws is None or not hasattr(ws, "broadcast_probe_progress"):
        return
    payload: Dict[str, Any] = {
        "machine_id": ctx.machine_id,
        "api_step": ctx.api_step,
        "phase": phase,
        "message": message,
        "elapsed_s": round(time.perf_counter() - ctx.t0, 3),
        "final": final,
    }
    if ctx.client_run_id:
        payload["client_run_id"] = ctx.client_run_id
    if snap is not None:
        payload["snap"] = {
            "prd3_status": snap.prd3_status,
            "operation_status": snap.operation_status,
        }
    try:
        await ws.broadcast_probe_progress(payload)
    except Exception:
        logger.debug("probe_progress broadcast failed", exc_info=True)


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


def _is_cycle_complete(snap: _Snap) -> bool:
    """True when probe motion has stopped enough to read #100+ / salt.

    Stricter than "not operating": still blocks active cutting (op=1), but
    allows M0/temp-stop/block-stop so results can be collected after a pause.
    """
    if snap.prd3_status is None and snap.operation_status is None:
        return False
    if snap.prd3_status in FATAL_STATUSES:
        return False
    if snap.operation_status == 1:
        return False
    if snap.prd3_status in ACTIVE_STATUSES and snap.operation_status in (None, 1):
        return False
    return True


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


def _snap_unreadable(snap: _Snap) -> bool:
    return snap.prd3_status is None and snap.operation_status is None


async def _ensure_root_folder(client: Any) -> None:
    """LOD MEM/PRD3 fail with status 07 unless telnet cwd is `/`."""
    ok, status = await client.change_folder("/", verbose=False)
    if not ok:
        desc = client.get_status_description(status or "00")
        raise RuntimeError(f"FLDCHG / failed: {status} ({desc})")


async def _wait_until(
    client: Any,
    control_version: str,
    *,
    predicate,
    label: str,
    timeout_s: float,
    poll_s: float,
    unreadable_limit: int = 5,
    progress: Optional[ProbeProgressCtx] = None,
    progress_phase: str = "waiting_complete",
) -> _Snap:
    deadline = time.perf_counter() + timeout_s
    last = _Snap()
    unreadable_streak = 0
    while time.perf_counter() < deadline:
        last = await _snapshot(client, control_version)
        await emit_probe_progress(
            progress,
            progress_phase,
            f"Waiting for {label} (prd3={last.prd3_status!r} op={last.operation_status!r})",
            snap=last,
        )
        if _snap_unreadable(last):
            unreadable_streak += 1
            if unreadable_streak >= unreadable_limit:
                raise RuntimeError(
                    f"Could not read MEM/PRD3 while waiting for {label} "
                    f"(prd3={last.prd3_status!r} op={last.operation_status!r}). "
                    "Ensure telnet folder is / and the machine responds to LOD."
                )
        else:
            unreadable_streak = 0
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


async def _write_macros(
    client: Any,
    writes: Dict[int, float],
    *,
    progress: Optional[ProbeProgressCtx] = None,
) -> None:
    items = list(writes.items())
    total = len(items)
    for i, (macro, value) in enumerate(items, start=1):
        await emit_probe_progress(
            progress,
            "writing",
            f"WRTMCNM #{macro}={value:g} ({i}/{total})…",
        )
        ok, status, verified = await client.write_macro_variable(
            macro_number=macro,
            value=value,
            verbose=False,
            verify=True,
        )
        if not ok:
            desc = client.get_status_description(status or "00")
            detail = f"Failed writing #{macro}={value}: {status} ({desc})"
            if status == "verify_mismatch" and verified is not None:
                detail += f" read_back={verified}"
            raise RuntimeError(detail)
        await emit_probe_progress(
            progress,
            "writing",
            f"Wrote #{macro}={value:g} ({i}/{total})",
        )


async def _poison_macros(
    client: Any,
    targets: Optional[Set[int]] = None,
    *,
    progress: Optional[ProbeProgressCtx] = None,
) -> Dict[int, float]:
    poison = get_poison_values()
    if targets is None:
        targets = set(poison.keys())
    ordered = sorted(m for m in targets if m in poison)
    written: Dict[int, float] = {}
    await _ensure_root_folder(client)
    total = len(ordered)
    for i, macro in enumerate(ordered, start=1):
        value = poison[macro]
        await emit_probe_progress(
            progress,
            "poisoning",
            f"WRTMCNM #{macro}={value:g} ({i}/{total})…",
        )
        ok, status, _ = await client.write_macro_variable(
            macro_number=macro,
            value=value,
            verbose=False,
            verify=False,
        )
        if ok:
            written[macro] = value
            await emit_probe_progress(
                progress,
                "poisoning",
                f"Wrote #{macro}={value:g} ({i}/{total})",
            )
        else:
            desc = client.get_status_description(status or "00")
            logger.warning("Failed to poison macro #%s: %s (%s)", macro, status, desc)
            await emit_probe_progress(
                progress,
                "poisoning",
                f"Failed #{macro}={value:g}: {status} ({desc}) ({i}/{total})",
            )
        await asyncio.sleep(0.05)
    return written


async def _read_results(client: Any) -> Dict[str, Optional[float]]:
    """Read Blum result macros (#100–#107) via one REDMCNM range when possible."""
    nums = get_result_macro_numbers()
    results: Dict[str, Optional[float]] = {str(n): None for n in nums}
    if not nums:
        return results

    start = min(nums)
    size = max(nums) - start + 1
    values = await client.get_macro_variable_range(start, size, verbose=False)
    if values is not None:
        for num in nums:
            idx = num - start
            if 0 <= idx < len(values):
                results[str(num)] = values[idx]
        return results

    for num in nums:
        results[str(num)] = await client.get_macro_variable(num, verbose=False)
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


async def poison_probe_macros(
    db_machine: Machine,
    *,
    client_run_id: Optional[str] = None,
) -> ProbeCycleResult:
    """Write sentinel values to all probe job macros without starting a cycle."""
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    progress = ProbeProgressCtx(
        machine_id=db_machine.id,
        api_step="poison",
        client_run_id=client_run_id,
        t0=t0,
    )
    client = None
    try:
        await emit_probe_progress(progress, "connect", "Connecting for poison…")
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )
        await emit_probe_progress(progress, "poisoning", "Writing sentinel macros…")
        written = await _poison_macros(client, progress=progress)
        if not written:
            await emit_probe_progress(
                progress,
                "error",
                "No poison macros were written (WRTMCNM failed)",
                final=True,
            )
            return ProbeCycleResult(
                ok=False,
                phase="poisoning",
                error="No poison macros were written (WRTMCNM failed)",
                elapsed_s=time.perf_counter() - t0,
            )
        await emit_probe_progress(
            progress,
            "complete",
            f"Poisoned {len(written)} macros",
            final=True,
        )
        return ProbeCycleResult(
            ok=True,
            phase="poisoned",
            macros_written=written,
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception("probe poison failed for machine %s", db_machine.id)
        await emit_probe_progress(progress, "error", str(e), final=True)
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
    client_run_id: Optional[str] = None,
) -> ProbeCycleResult:
    """Validate + write job macros only. Does not MEMSTRT / cause motion."""
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    progress = ProbeProgressCtx(
        machine_id=machine_id,
        api_step="write",
        client_run_id=client_run_id,
        t0=t0,
    )
    try:
        resolved, writes = validate_run_params(routine_id, mode, params)
    except ProbeCatalogError as e:
        await emit_probe_progress(progress, "error", str(e), final=True)
        return ProbeCycleResult(
            ok=False,
            routine_id=routine_id,
            mode=mode,
            phase="validate",
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )

    target_program = int(resolved["program"])
    client = None
    phase = "connect"

    try:
        await emit_probe_progress(progress, "connect", "Connecting for macro write…")
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )

        phase = "safety"
        await emit_probe_progress(progress, "safety", "Checking machine safety…")
        safe, err, status_data = await _ensure_safety(db_machine, machine_id, client)
        if not safe:
            await emit_probe_progress(
                progress,
                "error",
                err or "Machine not safe for macro write",
                final=True,
            )
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

        # Same gate as execute_macro_write: safety already blocks operating.
        # Do not idle-poll here — empty MEM/PRD3 reads never look "idle" and hang.
        phase = "writing"
        await emit_probe_progress(progress, "writing", "Writing job macros…")
        await _ensure_root_folder(client)
        await _write_macros(client, writes, progress=progress)

        await emit_probe_progress(
            progress,
            "complete",
            f"Wrote {len(writes)} macros",
            final=True,
        )
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
        await emit_probe_progress(progress, "error", str(e), final=True)
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
    client_run_id: Optional[str] = None,
) -> ProbeCycleResult:
    """
    MEMSTRT the catalog target program (motion). Allowlisted O-numbers only.

    Does not rewrite macros — call write_probe_macros first. Waits until the
    program is observed running, then returns so the UI can COLLECT later.
    """
    from app.clients.telnet_client import create_fresh_connection

    t0 = time.perf_counter()
    progress = ProbeProgressCtx(
        machine_id=machine_id,
        api_step="start",
        client_run_id=client_run_id,
        t0=t0,
    )
    try:
        resolved, _writes = validate_run_params(routine_id, mode, params)
    except ProbeCatalogError as e:
        await emit_probe_progress(progress, "error", str(e), final=True)
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
        await emit_probe_progress(progress, "connect", "Connecting for MEMSTRT…")
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )

        phase = "safety"
        await emit_probe_progress(progress, "safety", "Checking machine safety…")
        safe, err, status_data = await _ensure_safety(db_machine, machine_id, client)
        if not safe:
            await emit_probe_progress(
                progress,
                "error",
                err or "Machine not safe for probe start",
                final=True,
            )
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

        await _ensure_root_folder(client)

        phase = "idle_wait"
        await emit_probe_progress(progress, "idle_wait", "Waiting for idle before MEMSTRT…")
        await _wait_until(
            client,
            control_version,
            predicate=_is_idle,
            label="idle before MEMSTRT",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
            progress=progress,
            progress_phase="idle_wait",
        )

        phase = "starting"
        await emit_probe_progress(
            progress,
            "starting",
            f"MEMSTRT O{target_program:04d}…",
        )
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
        await emit_probe_progress(progress, "running", "Waiting for program start…")
        # Short Blum cycles can finish before the first poll sees "operating".
        # Wait at least 1s before treating idle as "already done" so we don't
        # race the MEMSTRT start latch.
        memstrt_at = time.perf_counter()
        start_deadline = memstrt_at + start_timeout_s
        saw_running = False
        last = _Snap()
        while time.perf_counter() < start_deadline:
            last = await _snapshot(client, control_version)
            await emit_probe_progress(
                progress,
                "running",
                f"Waiting for start (prd3={last.prd3_status!r} op={last.operation_status!r})",
                snap=last,
            )
            if _snap_unreadable(last):
                await asyncio.sleep(poll_s)
                continue
            if last.prd3_status in FATAL_STATUSES:
                raise RuntimeError("Machine error while waiting for probe program start")
            if _is_running(last):
                saw_running = True
                break
            if (
                _is_cycle_complete(last)
                and (time.perf_counter() - memstrt_at) >= 1.0
            ):
                saw_running = True
                break
            await asyncio.sleep(poll_s)
        if not saw_running:
            raise TimeoutError(
                "Timeout waiting for probe program start "
                f"(prd3={last.prd3_status!r} op={last.operation_status!r})"
            )

        await emit_probe_progress(
            progress,
            "complete",
            f"O{target_program:04d} started",
            snap=last,
            final=True,
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
        await emit_probe_progress(progress, "error", str(e), final=True)
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
    poll_s: Optional[float] = None,
    cycle_timeout_s: float = DEFAULT_CYCLE_TIMEOUT_S,
    poison: bool = True,
    client_run_id: Optional[str] = None,
) -> ProbeCycleResult:
    """Wait for cycle complete, read #100+, optionally poison.

    Does not poison on wait/read failure — that previously blasted WRTMCNM while
    the control was busy and could trigger CM7522 (abnormal end command).
    """
    from app.clients.telnet_client import create_fresh_connection
    from app.services.probe_exclusive import collect_poll_seconds

    t0 = time.perf_counter()
    progress = ProbeProgressCtx(
        machine_id=machine_id,
        api_step="collect",
        client_run_id=client_run_id,
        t0=t0,
    )
    if poll_s is None:
        poll_s = collect_poll_seconds(machine_id, DEFAULT_COLLECT_POLL_S)
    control_version = db_machine.control_version or "C00"
    client = None
    phase = "connect"
    results: Dict[str, Optional[float]] = {}

    try:
        await emit_probe_progress(progress, "connect", "Connecting for collect…")
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )

        await _ensure_root_folder(client)

        phase = "waiting_complete"
        await emit_probe_progress(
            progress,
            "waiting_complete",
            f"Waiting for cycle complete (poll {poll_s:.2f}s)…",
        )
        await _wait_until(
            client,
            control_version,
            predicate=_is_cycle_complete,
            label="cycle complete",
            timeout_s=cycle_timeout_s,
            poll_s=poll_s,
            progress=progress,
            progress_phase="waiting_complete",
        )

        # Let M30 / mode settle before REDMCNM / WRTMCNM bursts.
        await asyncio.sleep(POST_CYCLE_SETTLE_S)
        await _ensure_root_folder(client)

        phase = "reading"
        await emit_probe_progress(progress, "reading", "Reading result macros #100+…")
        results = await _read_results(client)

        macros_written: Dict[int, float] = {}
        if poison:
            phase = "poisoning"
            await emit_probe_progress(progress, "poisoning", "Salting job macros…")
            # Refuse salt while still cutting — avoids CM7522 / status 32 storms.
            snap = await _snapshot(client, control_version)
            if _is_running(snap):
                await emit_probe_progress(
                    progress,
                    "error",
                    "Results read, but machine still running — skipped salt",
                    snap=snap,
                    final=True,
                )
                return ProbeCycleResult(
                    ok=False,
                    results=results,
                    phase=phase,
                    error=(
                        "Results read, but machine still running — "
                        "skipped salt/poison. Retry when idle."
                    ),
                    elapsed_s=time.perf_counter() - t0,
                )
            macros_written = await _poison_macros(client, progress=progress)
            if not macros_written:
                await emit_probe_progress(
                    progress,
                    "error",
                    "Results read, but salt/poison wrote no macros",
                    final=True,
                )
                return ProbeCycleResult(
                    ok=False,
                    results=results,
                    phase=phase,
                    error="Results read, but salt/poison wrote no macros",
                    elapsed_s=time.perf_counter() - t0,
                )

        await emit_probe_progress(
            progress,
            "complete",
            "Collect complete",
            final=True,
        )
        return ProbeCycleResult(
            ok=True,
            results=results,
            macros_written=macros_written,
            phase="complete",
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception("probe collect failed machine=%s phase=%s", machine_id, phase)
        await emit_probe_progress(progress, "error", str(e), final=True)
        return ProbeCycleResult(
            ok=False,
            results=results or {},
            phase=phase,
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )
    finally:
        if client:
            await client.disconnect()


MEASUREMENT_TOOL_MACRO = 920
TOOL_LENGTH_PROGRAM = 8100


@dataclass
class ToolBatchItemResult:
    tool: int
    ok: bool
    detail: str
    elapsed_s: float = 0.0
    index: int = 0


@dataclass
class ToolBatchResult:
    ok: bool
    tools: list = field(default_factory=list)
    phase: str = "idle"
    error: Optional[str] = None
    elapsed_s: float = 0.0
    aborted: bool = False


def _normalize_tool_list(tools: list) -> list:
    out = []
    seen: Set[int] = set()
    for raw in tools:
        t = int(raw)
        if t <= 0 or t in (255, 999):
            raise ValueError(f"Invalid tool number {t}")
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    if not out:
        raise ValueError("Select at least one tool")
    if len(out) > 99:
        raise ValueError("Too many tools in one batch (max 99)")
    return out


async def run_tool_length_batch(
    db_machine: Machine,
    machine_id: int,
    tools: list,
    *,
    folder: str = DEFAULT_FOLDER,
    poll_s: float = DEFAULT_POLL_S,
    start_timeout_s: float = DEFAULT_START_TIMEOUT_S,
    cycle_timeout_s: float = DEFAULT_CYCLE_TIMEOUT_S,
    client_run_id: Optional[str] = None,
) -> ToolBatchResult:
    """Measure multiple tools by sequencing O8100 (write #920 → MEMSTRT → wait).

    Aborts remaining tools on the first failure.
    """
    from app.clients.telnet_client import create_fresh_connection
    from app.services.probe_exclusive import collect_poll_seconds

    t0 = time.perf_counter()
    progress = ProbeProgressCtx(
        machine_id=machine_id,
        api_step="tool_batch",
        client_run_id=client_run_id,
        t0=t0,
    )
    try:
        tool_list = _normalize_tool_list(list(tools))
    except ValueError as e:
        await emit_probe_progress(progress, "error", str(e), final=True)
        return ToolBatchResult(ok=False, phase="validate", error=str(e), elapsed_s=0.0)

    wait_poll = collect_poll_seconds(machine_id, poll_s)
    control_version = db_machine.control_version or "C00"
    client = None
    items: list = []
    phase = "connect"

    try:
        await emit_probe_progress(
            progress,
            "connect",
            f"Connecting for multi-tool measure ({len(tool_list)} tools)…",
        )
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=15,
        )

        phase = "safety"
        await emit_probe_progress(progress, "safety", "Checking machine safety…")
        safe, err, _status = await _ensure_safety(db_machine, machine_id, client)
        if not safe:
            msg = err or "Machine not safe for tool measure"
            await emit_probe_progress(progress, "error", msg, final=True)
            return ToolBatchResult(
                ok=False,
                phase=phase,
                error=msg,
                elapsed_s=time.perf_counter() - t0,
            )

        await _ensure_root_folder(client)

        for idx, tool in enumerate(tool_list):
            item_t0 = time.perf_counter()
            label = f"Tool {idx + 1}/{len(tool_list)} · T{tool:02d}"
            await emit_probe_progress(
                progress,
                "writing",
                f"{label} — writing #920 and waiting idle…",
            )
            try:
                await _wait_until(
                    client,
                    control_version,
                    predicate=_is_idle,
                    label=f"idle before T{tool}",
                    timeout_s=start_timeout_s,
                    poll_s=wait_poll,
                    progress=progress,
                    progress_phase="idle_wait",
                )

                await emit_probe_progress(
                    progress,
                    "writing",
                    f"{label} — WRTMCNM #920={tool}",
                )
                ok, status, _verified = await client.write_macro_variable(
                    macro_number=MEASUREMENT_TOOL_MACRO,
                    value=float(tool),
                    verbose=False,
                    verify=True,
                )
                if not ok:
                    desc = client.get_status_description(status or "00")
                    raise RuntimeError(f"Failed writing #920={tool}: {status} ({desc})")

                phase = "starting"
                await emit_probe_progress(
                    progress,
                    "starting",
                    f"{label} — MEMSTRT O{TOOL_LENGTH_PROGRAM:04d}",
                )
                ok, status = await client.change_mode("MEM", verbose=False)
                if not ok and status != "60":
                    desc = client.get_status_description(status or "00")
                    raise RuntimeError(f"CHGMODE MEM failed: {status} ({desc})")

                ok, status = await client.change_folder(folder, verbose=False)
                if not ok:
                    desc = client.get_status_description(status or "00")
                    raise RuntimeError(f"FLDCHG {folder} failed: {status} ({desc})")

                try:
                    await _memstrt_catalog_target(client, TOOL_LENGTH_PROGRAM)
                finally:
                    await client.change_folder("/", verbose=False)

                phase = "running"
                memstrt_at = time.perf_counter()
                start_deadline = memstrt_at + start_timeout_s
                saw_running = False
                last = _Snap()
                while time.perf_counter() < start_deadline:
                    last = await _snapshot(client, control_version)
                    await emit_probe_progress(
                        progress,
                        "running",
                        f"{label} — waiting start "
                        f"(prd3={last.prd3_status!r} op={last.operation_status!r})",
                        snap=last,
                    )
                    if _snap_unreadable(last):
                        await asyncio.sleep(wait_poll)
                        continue
                    if last.prd3_status in FATAL_STATUSES:
                        raise RuntimeError(
                            "Machine error while waiting for tool measure start"
                        )
                    if _is_running(last):
                        saw_running = True
                        break
                    if (
                        _is_cycle_complete(last)
                        and (time.perf_counter() - memstrt_at) >= 1.0
                    ):
                        saw_running = True
                        break
                    await asyncio.sleep(wait_poll)
                if not saw_running:
                    raise TimeoutError(
                        f"Timeout waiting for O{TOOL_LENGTH_PROGRAM:04d} start "
                        f"(prd3={last.prd3_status!r} op={last.operation_status!r})"
                    )

                phase = "waiting_complete"
                await emit_probe_progress(
                    progress,
                    "waiting_complete",
                    f"{label} — waiting cycle complete…",
                )
                await _wait_until(
                    client,
                    control_version,
                    predicate=_is_cycle_complete,
                    label=f"T{tool} cycle complete",
                    timeout_s=cycle_timeout_s,
                    poll_s=wait_poll,
                    progress=progress,
                    progress_phase="waiting_complete",
                )
                await asyncio.sleep(POST_CYCLE_SETTLE_S)
                await _ensure_root_folder(client)

                items.append(
                    ToolBatchItemResult(
                        tool=tool,
                        ok=True,
                        detail="measured",
                        elapsed_s=time.perf_counter() - item_t0,
                        index=idx,
                    )
                )
                await emit_probe_progress(
                    progress,
                    "complete",
                    f"{label} — ok ({items[-1].elapsed_s:.1f}s)",
                )
            except Exception as tool_err:
                logger.exception(
                    "tool batch aborted machine=%s tool=%s index=%s",
                    machine_id,
                    tool,
                    idx,
                )
                items.append(
                    ToolBatchItemResult(
                        tool=tool,
                        ok=False,
                        detail=str(tool_err),
                        elapsed_s=time.perf_counter() - item_t0,
                        index=idx,
                    )
                )
                remaining = len(tool_list) - idx - 1
                msg = (
                    f"{label} failed: {tool_err}"
                    + (f" — aborted {remaining} remaining" if remaining else "")
                )
                await emit_probe_progress(progress, "error", msg, final=True)
                return ToolBatchResult(
                    ok=False,
                    tools=items,
                    phase=phase,
                    error=msg,
                    elapsed_s=time.perf_counter() - t0,
                    aborted=remaining > 0,
                )

        await emit_probe_progress(
            progress,
            "complete",
            f"Measured {len(items)} tools",
            final=True,
        )
        return ToolBatchResult(
            ok=True,
            tools=items,
            phase="complete",
            elapsed_s=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception(
            "tool length batch failed machine=%s phase=%s", machine_id, phase
        )
        await emit_probe_progress(progress, "error", str(e), final=True)
        return ToolBatchResult(
            ok=False,
            tools=items,
            phase=phase,
            error=str(e),
            elapsed_s=time.perf_counter() - t0,
        )
    finally:
        if client:
            try:
                await client.change_folder("/", verbose=False)
            except Exception:
                pass
            await client.disconnect()
