#!/usr/bin/env python3
"""Live-machine smoke test: optional stop (OP.STP) via CHGOPTS.

Validated on Brother C00:
  Command CHGOPTS (7-char), args ON / OFF (space-padded in 8-byte field).
  Same family as CHGMODE. Verify with LOD PANEL → mode_and_functions.opt_stop.

Before running, stop the backend so Telnet is free:
    docker-compose -f docker-compose.dev.yml stop backend

Usage:
    cd backend && PYTHONPATH=. python3 scripts/test_optstop.py --read-only
    cd backend && PYTHONPATH=. python3 scripts/test_optstop.py --toggle
    cd backend && PYTHONPATH=. python3 scripts/test_optstop.py --on
    cd backend && PYTHONPATH=. python3 scripts/test_optstop.py --off

After testing:
    docker-compose -f docker-compose.dev.yml start backend
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any, Optional

from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.parsers.panel_parser_v2 import parse_panel_v2

DEFAULT_IP = "192.168.86.89"


async def _ensure_root_cwd(client: CNCTelnetClient) -> None:
    ok, _, data = await client._send_command("FLDPWD", "", verbose=False)
    if not ok or not data:
        return
    pwd = data.split("\r")[0].split("\n")[0].strip()
    if pwd and pwd != "/":
        print(f"Restoring telnet cwd from {pwd!r} to '/'...")
        await client._send_multipart_command("FLDCHG", "", "/", verbose=False)


async def _read_panel(client: CNCTelnetClient) -> Optional[dict[str, Any]]:
    raw = await client.get_panel_data(verbose=False)
    if not raw:
        return None
    return parse_panel_v2(raw.encode("utf-8"))


def _mode_block(panel: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not panel:
        return {}
    block = panel.get("mode_and_functions")
    return block if isinstance(block, dict) else {}


def _opt_stop_state(panel: Optional[dict[str, Any]]) -> Optional[int]:
    if not panel:
        return None
    block = _mode_block(panel)
    if "opt_stop" in block:
        return block.get("opt_stop")
    return panel.get("opt_stop")


def _print_panel_opt(label: str, panel: Optional[dict[str, Any]]) -> Optional[int]:
    state = _opt_stop_state(panel)
    block = _mode_block(panel)
    print(
        f"{label}: opt_stop={state!r} mode={block.get('mode')!r} "
        f"single_block={block.get('single_block')!r} "
        f"dry_run={block.get('dry_run')!r} "
        f"block_skip={block.get('block_skip')!r} "
        f"machine_lock={block.get('machine_lock')!r}"
    )
    return state


async def _send(
    client: CNCTelnetClient, command: str, arguments: str
) -> tuple[bool, Optional[str]]:
    print(f"→ {command} args={arguments!r}")
    ok, status, _ = await client._send_command(command, arguments, verbose=True)
    desc = CNCTelnetClient.get_status_description(status or "00")
    print(f"← ok={ok} status={status!r} ({desc})")
    return ok, status


async def _set_optstop(client: CNCTelnetClient, on: bool) -> tuple[bool, Optional[str]]:
    return await _send(client, "CHGOPTS", "ON" if on else "OFF")


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Live test optional-stop (CHGOPTS) on Brother CNC"
    )
    parser.add_argument("--ip", default=DEFAULT_IP)
    parser.add_argument("--port", type=int, default=10000)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--on", action="store_true", help="Force optional stop ON")
    group.add_argument("--off", action="store_true", help="Force optional stop OFF")
    group.add_argument(
        "--toggle",
        action="store_true",
        help="Flip current PANEL opt_stop (default if no --on/--off/--read-only)",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Only print PANEL opt_stop; no writes",
    )
    parser.add_argument(
        "--skip-mem",
        action="store_true",
        help="Do not CHGMODE MEM before CHGOPTS",
    )
    args = parser.parse_args()

    print(f"Connecting to {args.ip}:{args.port}...")
    client = await create_fresh_connection(args.ip, args.port, timeout=15)
    if not client:
        print("ERROR: Could not connect")
        return 1

    try:
        await _ensure_root_cwd(client)
        before = await _read_panel(client)
        state = _print_panel_opt("PANEL before", before)

        if args.read_only:
            return 0 if state is not None else 2

        if args.on:
            want_on = True
        elif args.off:
            want_on = False
        else:
            if state is None:
                print("ERROR: cannot toggle; PANEL opt_stop unread")
                return 2
            want_on = state == 0
            print(f"Toggle: want opt_stop {'ON' if want_on else 'OFF'}")

        if not args.skip_mem:
            ok, status = await _send(client, "CHGMODE", "MEM")
            if not ok and status != "60":
                print(f"WARNING: CHGMODE MEM failed ({status}); continuing")

        ok, status = await _set_optstop(client, want_on)
        after = await _read_panel(client)
        after_state = _print_panel_opt("PANEL after", after)

        if not ok:
            return 2
        if after_state != (1 if want_on else 0):
            print(
                f"WARNING: command ok but opt_stop={after_state!r}, "
                f"expected {1 if want_on else 0}"
            )
            return 4

        print(f"OK: opt_stop {state!r} → {after_state!r}")
        return 0
    finally:
        await _ensure_root_cwd(client)
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
