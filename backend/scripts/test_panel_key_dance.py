#!/usr/bin/env python3
"""Live demo: dance B.SKIP / OP.STP / SINGL / M.LCK for ~30s via CHG* keys.

Validated CHGOPTS layout (C00): command CHGxxxx + args ON/OFF.
Siblings assumed same family:
  CHGBLKS  — block skip
  CHGOPTS  — optional stop
  CHGSNGL  — single block
  CHGMACL  — machine lock

Restores all four to OFF on exit (including Ctrl+C).

    cd backend && PYTHONPATH=. python3 scripts/test_panel_key_dance.py
    cd backend && PYTHONPATH=. python3 scripts/test_panel_key_dance.py --seconds 30 --interval 0.4
"""
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
from typing import Optional

from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.parsers.panel_parser_v2 import parse_panel_v2

DEFAULT_IP = "192.168.86.89"

# (command, PANEL mode_and_functions field, label)
KEYS = (
    ("CHGBLKS", "block_skip", "B.SKIP"),
    ("CHGOPTS", "opt_stop", "OP.STP"),
    ("CHGSNGL", "single_block", "SINGL"),
    ("CHGMACL", "machine_lock", "M.LCK"),
)


async def _ensure_root_cwd(client: CNCTelnetClient) -> None:
    ok, _, data = await client._send_command("FLDPWD", "", verbose=False)
    if not ok or not data:
        return
    pwd = data.split("\r")[0].split("\n")[0].strip()
    if pwd and pwd != "/":
        await client._send_multipart_command("FLDCHG", "", "/", verbose=False)


async def _set_key(client: CNCTelnetClient, command: str, on: bool) -> bool:
    ok, status, _ = await client._send_command(
        command, "ON" if on else "OFF", verbose=False
    )
    if not ok:
        desc = CNCTelnetClient.get_status_description(status or "00")
        print(f"  ! {command} {'ON' if on else 'OFF'} → {status} ({desc})")
    return ok


async def _read_keys(client: CNCTelnetClient) -> dict[str, Optional[int]]:
    raw = await client.get_panel_data(verbose=False)
    out: dict[str, Optional[int]] = {field: None for _, field, _ in KEYS}
    if not raw:
        return out
    panel = parse_panel_v2(raw.encode("utf-8"))
    block = panel.get("mode_and_functions") or {}
    for _, field, _ in KEYS:
        out[field] = block.get(field)
    return out


def _fmt(state: dict[str, Optional[int]]) -> str:
    parts = []
    for _, field, label in KEYS:
        v = state.get(field)
        mark = "●" if v == 1 else ("○" if v == 0 else "?")
        parts.append(f"{label}:{mark}")
    return "  ".join(parts)


async def _all_off(client: CNCTelnetClient) -> None:
    print("Restoring all keys OFF…")
    for command, _, label in KEYS:
        await _set_key(client, command, False)
    state = await _read_keys(client)
    print(f"Final: {_fmt(state)}")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Dance panel MEM-mode keys for N seconds")
    parser.add_argument("--ip", default=DEFAULT_IP)
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument(
        "--interval",
        type=float,
        default=0.35,
        help="Seconds between each key toggle",
    )
    parser.add_argument(
        "--skip-mem",
        action="store_true",
        help="Skip CHGMODE MEM at start",
    )
    args = parser.parse_args()

    print(f"Connecting to {args.ip}:{args.port}…")
    client = await create_fresh_connection(args.ip, args.port, timeout=15)
    if not client:
        print("ERROR: Could not connect")
        return 1

    abort = asyncio.Event()
    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, abort.set)
    except NotImplementedError:
        signal.signal(signal.SIGINT, lambda *_: abort.set())

    try:
        await _ensure_root_cwd(client)
        if not args.skip_mem:
            ok, status, _ = await client._send_command("CHGMODE", "MEM", verbose=False)
            if not ok and status != "60":
                print(f"WARNING: CHGMODE MEM → {status}")

        start = await _read_keys(client)
        print(f"Start: {_fmt(start)}")
        print(f"Dancing for {args.seconds:.0f}s (Ctrl+C to stop)…\n")

        deadline = time.monotonic() + args.seconds
        step = 0
        # Chase pattern: walk ON through keys, then walk OFF
        while time.monotonic() < deadline and not abort.is_set():
            idx = step % len(KEYS)
            phase = (step // len(KEYS)) % 2  # 0 = turn ON, 1 = turn OFF
            command, field, label = KEYS[idx]
            want_on = phase == 0
            await _set_key(client, command, want_on)
            state = await _read_keys(client)
            print(f"[{step:03d}] {label} → {'ON ' if want_on else 'OFF'}  {_fmt(state)}")
            step += 1
            await asyncio.sleep(args.interval)

        if abort.is_set():
            print("\nInterrupted.")
        else:
            print("\nDone.")
        return 0
    finally:
        try:
            await _all_off(client)
            await _ensure_root_cwd(client)
        except Exception as exc:
            print(f"Cleanup warning: {exc}")
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
