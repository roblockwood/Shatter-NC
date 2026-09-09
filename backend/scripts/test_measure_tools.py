#!/usr/bin/env python3
"""Live-machine: measure a sequence of tools via macro #920 + MEMSTRT O8100.

For each tool number:
  1. Wait until the machine is idle
  2. Write measurement-tool macro #920
  3. CHGMODE MEM → FLDCHG PROGRAM → MEMSTRT <program>
  4. Restore telnet cwd to '/'
  5. Wait until the cycle starts, then until it completes
  6. Proceed to the next tool

THIS STARTS THE MACHINE. Keep eyes on the spindle / doors.

Before running, stop the backend so Telnet is free:
    docker-compose -f docker-compose.dev.yml stop backend

Usage:
    cd backend && PYTHONPATH=. python3 scripts/test_measure_tools.py --tools 5,7,12
    cd backend && PYTHONPATH=. python3 scripts/test_measure_tools.py --tools 5 7 12 --program 8100 --folder PROGRAM
    cd backend && PYTHONPATH=. python3 scripts/test_measure_tools.py --tools 5 --dry-run
    cd backend && PYTHONPATH=. python3 scripts/test_measure_tools.py --tools 5 --yes

After testing:
    docker-compose -f docker-compose.dev.yml start backend
"""
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any, Optional

from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.parsers.mem_parser_v2 import parse_mem_v2
from app.parsers.prd3_parser_v2 import parse_prd3_v2

DEFAULT_IP = "192.168.86.89"
MEASUREMENT_TOOL_MACRO = 920
DEFAULT_PROGRAM = 8100
DEFAULT_FOLDER = "PROGRAM"

IDLE_STATUSES = frozenset({"standby", "stopped", "off"})
ACTIVE_STATUSES = frozenset({"operating"})
FATAL_STATUSES = frozenset({"error"})


@dataclass
class MachineSnapshot:
    prd3_status: Optional[str] = None
    operation_status: Optional[int] = None
    program_name: Optional[str] = None
    folder: Optional[str] = None
    mode: Optional[int] = None
    executed_program: Optional[str] = None
    main_program: Optional[str] = None
    block: Optional[str] = None


@dataclass
class ToolResult:
    tool: int
    ok: bool
    detail: str
    elapsed_s: float = 0.0


class AbortRequested(Exception):
    """Raised when the operator hits Ctrl+C."""


def _parse_tools(values: list[str]) -> list[int]:
    """Accept --tools 5,7,12 and/or --tools 5 7 12."""
    tools: list[int] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            n = int(part)
            if not 1 <= n <= 999:
                raise argparse.ArgumentTypeError(f"tool out of range 1–999: {n}")
            tools.append(n)
    if not tools:
        raise argparse.ArgumentTypeError("at least one tool number is required")
    return tools


async def _pwd(client: CNCTelnetClient) -> Optional[str]:
    ok, _, data = await client._send_command("FLDPWD", "", verbose=False)
    if not ok or not data:
        return None
    return data.split("\r")[0].split("\n")[0].strip() or None


async def _fldchg(client: CNCTelnetClient, folder: str) -> bool:
    ok, status, _ = await client._send_multipart_command(
        "FLDCHG", "", folder, verbose=False
    )
    if not ok:
        desc = CNCTelnetClient.get_status_description(status or "00")
        print(f"  FLDCHG {folder!r} failed: {status} ({desc})")
    return ok


async def _ensure_root_cwd(client: CNCTelnetClient) -> None:
    pwd = await _pwd(client)
    if pwd and pwd != "/":
        await _fldchg(client, "/")


async def _snapshot(client: CNCTelnetClient, control_version: str) -> MachineSnapshot:
    snap = MachineSnapshot()

    mem_raw = await client.get_memory_data(verbose=False)
    if mem_raw:
        mem = parse_mem_v2(mem_raw.encode("utf-8"), control_version=control_version)
        snap.operation_status = mem.get("operation_status")
        snap.program_name = mem.get("program_name")
        snap.folder = mem.get("operation_folder_name")
        snap.mode = mem.get("mode")

    prd3_raw = await client.get_prd3_data(
        control_version=control_version, verbose=False
    )
    if prd3_raw:
        prd3 = parse_prd3_v2(prd3_raw.encode("utf-8"), control_version=control_version)
        snap.prd3_status = (prd3.get("current_status") or {}).get("status")

    info = await client.get_current_program_info(verbose=False)
    if info:
        snap.executed_program = info.get("currently_executed_program_number")
        snap.main_program = info.get("main_program_number")
        snap.block = info.get("currently_executed_block_number")

    return snap


def _fmt_snap(snap: MachineSnapshot) -> str:
    return (
        f"prd3={snap.prd3_status!r} op={snap.operation_status} "
        f"prog={snap.program_name!r} folder={snap.folder!r} "
        f"exec={snap.executed_program!r}/{snap.main_program!r} blk={snap.block!r}"
    )


def _is_idle(snap: MachineSnapshot) -> bool:
    if snap.prd3_status in FATAL_STATUSES:
        return False
    if snap.prd3_status in ACTIVE_STATUSES:
        return False
    if snap.operation_status in (1, 2, 3):
        return False
    if snap.prd3_status in IDLE_STATUSES:
        return True
    # Unknown PRD3 but MEM says reset
    return snap.operation_status == 0


def _is_running(snap: MachineSnapshot) -> bool:
    return snap.prd3_status in ACTIVE_STATUSES or snap.operation_status == 1


async def _wait_until(
    client: CNCTelnetClient,
    control_version: str,
    *,
    predicate,
    label: str,
    timeout_s: float,
    poll_s: float,
    abort_event: asyncio.Event,
) -> MachineSnapshot:
    deadline = time.monotonic() + timeout_s
    last: Optional[MachineSnapshot] = None
    while True:
        if abort_event.is_set():
            raise AbortRequested()
        last = await _snapshot(client, control_version)
        if predicate(last):
            return last
        if last.prd3_status in FATAL_STATUSES:
            raise RuntimeError(f"machine entered error while waiting for {label}: {_fmt_snap(last)}")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timeout waiting for {label}: {_fmt_snap(last)}")
        print(f"  … waiting {label}: {_fmt_snap(last)} ({remaining:.0f}s left)")
        await asyncio.sleep(min(poll_s, remaining))


async def _memstop_hold(client: CNCTelnetClient) -> None:
    """Latch feed-hold via MEMSTOP ON (does not auto-release)."""
    print("→ MEMSTOP ON (feed hold latch)")
    ok, status, _ = await client._send_command("MEMSTOP", "ON", verbose=True)
    desc = CNCTelnetClient.get_status_description(status or "00")
    print(f"← MEMSTOP ON ok={ok} status={status!r} ({desc})")
    print("NOTE: Feed hold is latched ON. Clear on the panel or send MEMSTOP OFF to resume.")


async def measure_tool(
    client: CNCTelnetClient,
    *,
    tool: int,
    program: int,
    folder: str,
    control_version: str,
    poll_s: float,
    start_timeout_s: float,
    cycle_timeout_s: float,
    dry_run: bool,
    abort_event: asyncio.Event,
) -> ToolResult:
    t0 = time.perf_counter()
    print(f"\n=== Tool {tool} ===")

    try:
        await _ensure_root_cwd(client)
        idle = await _wait_until(
            client,
            control_version,
            predicate=_is_idle,
            label="idle before measure",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
            abort_event=abort_event,
        )
        print(f"  idle: {_fmt_snap(idle)}")

        print(f"  → WRTMCNM #{MEASUREMENT_TOOL_MACRO} = {tool}")
        ok, status, verified = await client.write_macro_variable(
            macro_number=MEASUREMENT_TOOL_MACRO,
            value=float(tool),
            verbose=False,
            verify=True,
        )
        desc = CNCTelnetClient.get_status_description(status or "00")
        print(f"  ← macro write ok={ok} status={status!r} ({desc}) verified={verified!r}")
        if not ok:
            return ToolResult(tool, False, f"macro write failed: {status} ({desc})", time.perf_counter() - t0)

        if dry_run:
            return ToolResult(tool, True, "dry-run: macro set, skipped MEMSTRT", time.perf_counter() - t0)

        ok, status, _ = await client._send_command("CHGMODE", "MEM", verbose=False)
        if not ok and status != "60":
            desc = CNCTelnetClient.get_status_description(status or "00")
            return ToolResult(tool, False, f"CHGMODE failed: {status} ({desc})", time.perf_counter() - t0)

        if not await _fldchg(client, folder):
            return ToolResult(tool, False, f"FLDCHG {folder} failed", time.perf_counter() - t0)

        prog_arg = f"{program:04d}"
        print(f"  → MEMSTRT {prog_arg}  (STARTS PROGRAM)")
        ok, status, _ = await client._send_command("MEMSTRT", prog_arg, verbose=True)
        desc = CNCTelnetClient.get_status_description(status or "00")
        print(f"  ← MEMSTRT ok={ok} status={status!r} ({desc})")

        # Always restore cwd so PRD3/MEM polls work
        await _fldchg(client, "/")

        if not ok:
            return ToolResult(tool, False, f"MEMSTRT failed: {status} ({desc})", time.perf_counter() - t0)

        started = await _wait_until(
            client,
            control_version,
            predicate=_is_running,
            label="cycle start",
            timeout_s=start_timeout_s,
            poll_s=poll_s,
            abort_event=abort_event,
        )
        print(f"  started: {_fmt_snap(started)}")

        finished = await _wait_until(
            client,
            control_version,
            predicate=_is_idle,
            label="cycle complete",
            timeout_s=cycle_timeout_s,
            poll_s=poll_s,
            abort_event=abort_event,
        )
        print(f"  complete: {_fmt_snap(finished)}")
        return ToolResult(tool, True, "ok", time.perf_counter() - t0)

    except AbortRequested:
        raise
    except Exception as exc:
        await _ensure_root_cwd(client)
        return ToolResult(tool, False, str(exc), time.perf_counter() - t0)


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sequentially measure tools via #920 + MEMSTRT (live Brother CNC)"
    )
    parser.add_argument("--ip", default=DEFAULT_IP)
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument(
        "--tools",
        nargs="+",
        required=True,
        help="Tool numbers (space- and/or comma-separated), e.g. --tools 5,7,12",
    )
    parser.add_argument("--program", type=int, default=DEFAULT_PROGRAM, help="O-number to MEMSTRT")
    parser.add_argument(
        "--folder",
        default=DEFAULT_FOLDER,
        help="Telnet folder containing the program (default: PROGRAM)",
    )
    parser.add_argument("--poll", type=float, default=1.0, help="Status poll interval seconds")
    parser.add_argument(
        "--start-timeout",
        type=float,
        default=60.0,
        help="Seconds to wait for idle before start / for cycle to begin",
    )
    parser.add_argument(
        "--cycle-timeout",
        type=float,
        default=600.0,
        help="Seconds to wait for each measure cycle to finish",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write #920 only; do not MEMSTRT",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep going if one tool fails",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation",
    )
    args = parser.parse_args()

    try:
        tools = _parse_tools(args.tools)
    except (argparse.ArgumentTypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Connecting to {args.ip}:{args.port}...")
    print(
        f"Plan: tools={tools} program=O{args.program:04d} folder={args.folder!r} "
        f"macro=#{MEASUREMENT_TOOL_MACRO} dry_run={args.dry_run}"
    )
    if not args.dry_run:
        print("WARNING: This will START memory operation on the machine for each tool.")

    if not args.yes and not args.dry_run:
        try:
            reply = input("Type 'start' to proceed: ").strip().lower()
        except EOFError:
            reply = ""
        if reply != "start":
            print("Aborted.")
            return 1

    client = await create_fresh_connection(args.ip, args.port, timeout=20)
    if not client:
        print("ERROR: Could not connect")
        return 1

    abort_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _on_sigint() -> None:
        print("\nCtrl+C — aborting after current poll…")
        abort_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, _on_sigint)
    except NotImplementedError:
        # Windows / limited environments
        signal.signal(signal.SIGINT, lambda *_: abort_event.set())

    results: list[ToolResult] = []
    try:
        control_version = await client.detect_control_type()
        print(f"Control version: {control_version}")
        await _ensure_root_cwd(client)
        snap = await _snapshot(client, control_version)
        print(f"Initial: {_fmt_snap(snap)}")

        for tool in tools:
            if abort_event.is_set():
                raise AbortRequested()
            result = await measure_tool(
                client,
                tool=tool,
                program=args.program,
                folder=args.folder.strip().strip("/"),
                control_version=control_version,
                poll_s=args.poll,
                start_timeout_s=args.start_timeout,
                cycle_timeout_s=args.cycle_timeout,
                dry_run=args.dry_run,
                abort_event=abort_event,
            )
            results.append(result)
            print(
                f"=== Tool {tool}: {'OK' if result.ok else 'FAIL'} "
                f"({result.elapsed_s:.1f}s) — {result.detail}"
            )
            if not result.ok and not args.continue_on_error:
                break

    except AbortRequested:
        print("Abort requested — attempting MEMSTOP ON…")
        try:
            await _ensure_root_cwd(client)
            await _memstop_hold(client)
        except Exception as exc:
            print(f"MEMSTOP failed: {exc}")
        return 130
    finally:
        try:
            await _ensure_root_cwd(client)
        except Exception:
            pass
        await client.disconnect()

    print("\nSummary:")
    for r in results:
        flag = "OK" if r.ok else "FAIL"
        print(f"  T{r.tool:03d}  {flag:4}  {r.elapsed_s:6.1f}s  {r.detail}")

    return 0 if results and all(r.ok for r in results) else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
