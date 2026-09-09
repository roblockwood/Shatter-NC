#!/usr/bin/env python3
"""Live-machine smoke test: CHGMODE (MEM) and CHGPROG (select program).

Does NOT call MEMSTRT / MEMQTST / MEMSTOP — select and mode only.

Brother notes (validated on C00):
- CHGPROG args are 4-digit ASCII (e.g. '8112'), left in the 8-byte field.
- Selection is folder-scoped. Programs under /PROGRAM need multipart FLDCHG
  with payload 'PROGRAM' first. Root programs (e.g. O2000) work from '/'.
- Always FLDCHG back to '/' afterward — otherwise LOD MEM fails (status 07)
  because the telnet data cwd is no longer root.

Before running, stop the backend so Telnet is free:
    docker-compose -f docker-compose.dev.yml stop backend

Usage:
    cd backend && PYTHONPATH=. python3 scripts/test_chgprog.py --read-only
    cd backend && PYTHONPATH=. python3 scripts/test_chgprog.py --mode-only
    cd backend && PYTHONPATH=. python3 scripts/test_chgprog.py --program 2000
    cd backend && PYTHONPATH=. python3 scripts/test_chgprog.py --program 8112 --folder PROGRAM
    cd backend && PYTHONPATH=. python3 scripts/test_chgprog.py --program O8112 --folder PROGRAM

After testing:
    docker-compose -f docker-compose.dev.yml start backend
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from typing import Any, Optional

from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.parsers.mem_parser_v2 import parse_mem_v2

DEFAULT_IP = "192.168.86.89"

# Panel / MEM mode codes (see panel_schema.py)
MODE_LABELS = {
    0: "Manual",
    1: "MDI",
    2: "Memory",
    3: "Edit",
    4: "MDI manual",
    5: "Operating edit",
}

# MEM operation_status: 0=Reset, 1=Operation, 2=Temporary stop, 3=Block stop
UNSAFE_OPERATION_STATUSES = frozenset({1, 2, 3})


def _parse_program_number(raw: str) -> int:
    """Accept '2045', 'O2045', 'o42' → int program number."""
    text = raw.strip().upper()
    if text.startswith("O"):
        text = text[1:]
    if not re.fullmatch(r"\d{1,4}", text):
        raise argparse.ArgumentTypeError(
            f"program must be 1–4 digits (optional O prefix), got {raw!r}"
        )
    return int(text)


def _format_program_arg(program: int, padding: str) -> str:
    """Build the CHGPROG argument field (caller pads to 8 via _send_command)."""
    if padding == "zero4":
        return f"{program:04d}"
    if padding == "left":
        return f"{program}"
    if padding == "right":
        return f"{program:>4}"
    raise ValueError(f"unknown padding: {padding}")


async def _pwd(client: CNCTelnetClient) -> Optional[str]:
    ok, status, data = await client._send_command("FLDPWD", "", verbose=False)
    if not ok:
        desc = CNCTelnetClient.get_status_description(status or "00")
        print(f"FLDPWD failed: {status} ({desc})")
        return None
    # Response looks like '/\r\n06' or '/PROGRAM\r\n14'
    path = (data or "").split("\r")[0].split("\n")[0].strip()
    return path or None


async def _fldchg(client: CNCTelnetClient, folder: str) -> bool:
    """Change telnet data directory (multipart: empty args + folder payload)."""
    print(f"→ FLDCHG payload={folder!r} (multipart)")
    ok, status, _ = await client._send_multipart_command(
        "FLDCHG", "", folder, verbose=True
    )
    desc = CNCTelnetClient.get_status_description(status or "00")
    print(f"← ok={ok} status={status!r} ({desc})")
    pwd = await _pwd(client)
    print(f"  FLDPWD → {pwd!r}")
    return ok


async def _read_mem(client: CNCTelnetClient) -> Optional[dict[str, Any]]:
    raw = await client.get_memory_data(verbose=True)
    if not raw:
        return None
    return parse_mem_v2(raw.encode("utf-8"))


def _print_mem(label: str, mem: Optional[dict[str, Any]]) -> None:
    if not mem:
        print(f"{label}: (no MEM data)")
        return
    mode = mem.get("mode")
    mode_label = MODE_LABELS.get(mode, "?") if isinstance(mode, int) else "?"
    print(
        f"{label}: program={mem.get('program_name')!r} "
        f"folder={mem.get('operation_folder_name')!r} "
        f"mode={mode} ({mode_label}) "
        f"operation_status={mem.get('operation_status')}"
    )


async def _print_redprgn(client: CNCTelnetClient) -> None:
    info = await client.get_current_program_info(verbose=True)
    if not info:
        print("REDPRGN: (failed)")
        return
    print(
        f"REDPRGN: executed={info.get('currently_executed_program_number')!r} "
        f"main={info.get('main_program_number')!r} "
        f"block={info.get('currently_executed_block_number')!r}"
    )


async def _send(
    client: CNCTelnetClient,
    command: str,
    arguments: str,
) -> tuple[bool, Optional[str]]:
    print(f"→ {command} args={arguments!r} (len={len(arguments)})")
    ok, status, _ = await client._send_command(command, arguments, verbose=True)
    desc = CNCTelnetClient.get_status_description(status or "00")
    print(f"← ok={ok} status={status!r} ({desc})")
    return ok, status


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Live test CHGMODE/CHGPROG on a Brother CNC (no program start)"
    )
    parser.add_argument("--ip", default=DEFAULT_IP)
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument(
        "--program",
        type=_parse_program_number,
        help="Program number to select via CHGPROG (e.g. 2045 or O2045)",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Telnet data folder for FLDCHG before CHGPROG (e.g. PROGRAM). "
        "Omit for root '/'. Always restored to '/' on exit.",
    )
    parser.add_argument(
        "--padding",
        choices=("zero4", "left", "right"),
        default="zero4",
        help="How to format the 4-char program field (default: zero4 → '2045')",
    )
    parser.add_argument(
        "--mode-only",
        action="store_true",
        help="Only send CHGMODE MEM (no CHGPROG)",
    )
    parser.add_argument(
        "--skip-mode",
        action="store_true",
        help="Skip CHGMODE; only CHGPROG",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Only dump MEM + REDPRGN + FLDPWD; no writes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow CHGPROG even if MEM operation_status looks active",
    )
    args = parser.parse_args()

    if args.mode_only and args.skip_mode:
        print("ERROR: --mode-only and --skip-mode are mutually exclusive")
        return 1
    if not args.read_only and not args.mode_only and args.program is None:
        print("ERROR: --program is required unless --read-only or --mode-only")
        return 1

    print(f"Connecting to {args.ip}:{args.port}...")
    print("NOTE: Does not start a program (no MEMSTRT). Stop backend first if needed.")
    client = await create_fresh_connection(args.ip, args.port, timeout=15)
    if not client:
        print("ERROR: Could not connect")
        return 1

    folder_changed = False
    try:
        pwd = await _pwd(client)
        print(f"FLDPWD → {pwd!r}")
        # Ensure LOD MEM works even if a prior run left cwd elsewhere
        if pwd and pwd != "/":
            print("Restoring telnet cwd to '/' before reads...")
            if await _fldchg(client, "/"):
                folder_changed = False  # already at root

        before = await _read_mem(client)
        _print_mem("MEM before", before)
        await _print_redprgn(client)

        if args.read_only:
            return 0

        if before and before.get("operation_status") in UNSAFE_OPERATION_STATUSES:
            msg = (
                f"Machine operation_status={before.get('operation_status')} "
                "(not Reset). CHGPROG is blocked during operation."
            )
            if not args.force:
                print(f"ERROR: {msg} Use --force to try anyway.")
                return 3
            print(f"WARNING: {msg} Continuing because --force.")

        if not args.skip_mode:
            ok, status = await _send(client, "CHGMODE", "MEM")
            if not ok and status != "60":
                # 60 = already in requested mode
                return 2
            after_mode = await _read_mem(client)
            _print_mem("MEM after CHGMODE", after_mode)

        if args.mode_only:
            return 0

        if args.folder:
            folder_name = args.folder.strip().strip("/")
            if not await _fldchg(client, folder_name):
                return 2
            folder_changed = True

        assert args.program is not None
        prog_arg = _format_program_arg(args.program, args.padding)
        ok, status = await _send(client, "CHGPROG", prog_arg)
        if not ok:
            return 2

        # Restore cwd before MEM verify so LOD MEM succeeds
        if folder_changed:
            await _fldchg(client, "/")
            folder_changed = False

        after = await _read_mem(client)
        _print_mem("MEM after CHGPROG", after)
        await _print_redprgn(client)

        if after:
            raw_name = str(after.get("program_name") or "").strip().upper()
            digits = raw_name[1:] if raw_name.startswith("O") else raw_name
            digits = digits.strip()
            try:
                if digits and int(digits) != args.program:
                    print(
                        f"WARNING: MEM program_name={after.get('program_name')!r} "
                        f"does not match requested {args.program}"
                    )
                    return 4
            except ValueError:
                print(
                    f"WARNING: MEM program_name={after.get('program_name')!r} "
                    f"is not numeric; cannot verify vs {args.program}"
                )
                return 4

        print("OK: mode/select commands completed")
        return 0
    finally:
        if folder_changed:
            try:
                print("Cleanup: restoring telnet cwd to '/'...")
                await _fldchg(client, "/")
            except Exception as exc:
                print(f"WARNING: failed to restore cwd to '/': {exc}")
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
