#!/usr/bin/env python3
"""Live-machine test: write all v1-supported fields for a tool, verify, restore.

Table (TOLN / WRTTOFS / WRTTLLF): length H, diameter D, wear W, life
ATC (if tool is in magazine): color, type

Skips assignment unless --assign-to-pot is set (assignment is left in place by default).

Before running, stop the backend dev container:
    docker-compose -f docker-compose.dev.yml stop backend

Usage:
    cd backend && PYTHONPATH=. python3 scripts/test_tool_write_live.py --tool 7
    cd backend && PYTHONPATH=. python3 scripts/test_tool_write_live.py --tool 7 --assign-to-pot 12
    cd backend && PYTHONPATH=. python3 scripts/test_tool_write_live.py --tool 7 --assign-to-pot auto
    cd backend && PYTHONPATH=. python3 scripts/test_tool_write_live.py --tool 7 --read-only
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.parsers.atctl_parser_v2 import parse_atctl_v2
from app.parsers.mem_parser_v2 import parse_mem_v2
from app.parsers.prd3_parser_v2 import parse_prd3_v2
from app.parsers.tolni_parser_v2 import parse_tolni_v2


DEFAULT_IP = "192.168.86.89"


@dataclass
class WriteResult:
    name: str
    success: bool
    status: Optional[str] = None
    detail: str = ""


def _find_tool(tools: list[dict], tool_number: int) -> Optional[dict]:
    for tool in tools:
        if tool.get("tool_number") == tool_number:
            return tool
    return None


def _num(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _life_int(tool: dict) -> int:
    raw = tool.get("life") if tool.get("life") is not None else tool.get("tool_life")
    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        digits = "".join(ch for ch in raw if ch.isdigit())
        return int(digits) if digits else 0
    return int(raw)


async def _control_version(client: CNCTelnetClient) -> str:
    control = await client.detect_control_type()
    if not control:
        print("WARNING: control detection failed; using C00")
        return "C00"
    return control


async def read_tool_table(client: CNCTelnetClient, units: str) -> list[dict]:
    control = await _control_version(client)
    raw = await client.get_tool_table_data(units=units, verbose=False)
    if not raw:
        raise RuntimeError("Failed to read tool table (TOLN)")
    parsed = parse_tolni_v2(raw.encode("utf-8"), units=units, control_version=control)
    tools = parsed.get("tools", [])
    if not tools and control != "C00":
        parsed = parse_tolni_v2(raw.encode("utf-8"), units=units, control_version="C00")
        tools = parsed.get("tools", [])
    return tools


async def read_atc_tools(client: CNCTelnetClient) -> list[dict]:
    control = await _control_version(client)
    raw = await client.get_atc_magazine_data(control_version=control, verbose=False)
    if not raw:
        return []
    parsed = parse_atctl_v2(raw.encode("utf-8"), control_version=control)
    return parsed.get("tools", [])


async def print_machine_state(client: CNCTelnetClient) -> None:
    control = await _control_version(client)
    mem_data = await client.get_memory_data(verbose=False)
    if mem_data:
        mem = parse_mem_v2(mem_data.encode("utf-8"), control_version=control)
        print(
            f"  MEM mode={mem.get('mode')} operation_status={mem.get('operation_status')}"
        )
    prd3_data = await client.get_prd3_data(control_version=control, verbose=False)
    if prd3_data:
        prd3 = parse_prd3_v2(prd3_data.encode("utf-8"), control_version=control)
        st = (prd3.get("current_status") or {}).get("status")
        print(f"  PRD3 status={st!r}")


async def _write_and_report(
    name: str,
    write_fn: Callable,
    restore_fn: Callable,
) -> WriteResult:
    ok, status = await write_fn()
    if not ok:
        desc = CNCTelnetClient.get_status_description(status or "00")
        return WriteResult(name, False, status, desc)

    restore_ok, restore_status = await restore_fn()
    if not restore_ok:
        desc = CNCTelnetClient.get_status_description(restore_status or "00")
        return WriteResult(
            name,
            True,
            status,
            f"write ok but restore failed ({restore_status}: {desc})",
        )
    return WriteResult(name, True, status, "write + restore ok")


async def test_table_fields(
    client: CNCTelnetClient,
    tool_number: int,
    row: dict,
    units: str,
) -> list[WriteResult]:
    results: list[WriteResult] = []
    tn = tool_number

    orig_h = _num(row.get("length") or row.get("tool_length_offset"))
    orig_d = _num(row.get("diameter") or row.get("cutter_compensation"))
    orig_w = _num(row.get("tool_length_wear_offset"))
    orig_life = _life_int(row)

    new_h = round(orig_h + 0.0001, 4)
    new_d = round(orig_d + 0.0001, 4)
    new_w = round(orig_w + 0.0001, 4)
    new_life = min(999999, orig_life + 1)

    print(f"\n--- Table writes T{tn:02d} ---")
    print(f"  baseline: H={orig_h} D={orig_d} W={orig_w} life={orig_life}")

    for label, offset_type, orig, new in (
        ("length (H)", "H", orig_h, new_h),
        ("diameter (D)", "D", orig_d, new_d),
        ("wear (W)", "W", orig_w, new_w),
    ):
        print(f"  {label}: {orig} → {new} ...")
        result = await _write_and_report(
            label,
            lambda o=offset_type, n=new: client.write_tool_offset(tn, o, n, verbose=True),
            lambda o=offset_type, oorig=orig: client.write_tool_offset(
                tn, o, oorig, verbose=True
            ),
        )
        results.append(result)
        print(f"    {'OK' if result.success else 'FAIL'}: {result.detail}")

    print(f"  life: {orig_life} → {new_life} ...")
    life_result = await _write_and_report(
        "life",
        lambda: client.write_tool_life(tn, new_life, "TIME", verbose=True),
        lambda: client.write_tool_life(tn, orig_life, "TIME", verbose=True),
    )
    results.append(life_result)
    print(f"    {'OK' if life_result.success else 'FAIL'}: {life_result.detail}")

    print("\n  Re-read TOLN after table tests ...")
    after = _find_tool(await read_tool_table(client, units), tn)
    if after:
        print(
            f"  T{tn:02d} now: H={after.get('length')} D={after.get('diameter')} "
            f"W={after.get('tool_length_wear_offset')} life={_life_int(after)}"
        )

    return results


def _find_pot(atc: list[dict], pot_number: int) -> Optional[dict]:
    for row in atc:
        pot = row.get("pot_number")
        if pot is None:
            continue
        if str(pot).upper() == "SPINDLE":
            continue
        try:
            if int(pot) == pot_number:
                return row
        except (TypeError, ValueError):
            continue
    return None


def _find_empty_pot(atc: list[dict]) -> Optional[int]:
    """Return first pocket with no tool (tool_number 0)."""
    for row in atc:
        pot = row.get("pot_number")
        if pot is None or str(pot).upper() == "SPINDLE":
            continue
        if (row.get("tool_number") or 0) == 0:
            return int(pot)
    return None


def _find_cap_pot(atc: list[dict]) -> Optional[int]:
    """Return first pocket with cap setting (C00 tool_number 255)."""
    for row in atc:
        pot = row.get("pot_number")
        if pot is None or str(pot).upper() == "SPINDLE":
            continue
        if row.get("tool_number") == 255:
            return int(pot)
    return None


def _find_assignable_pot(atc: list[dict]) -> tuple[Optional[int], str]:
    """Prefer empty pocket; else cap pocket (clearable via CHGMAGD before assign)."""
    empty = _find_empty_pot(atc)
    if empty is not None:
        return empty, "empty"
    cap = _find_cap_pot(atc)
    if cap is not None:
        return cap, "cap"
    return None, "none"


async def test_atc_assignment(
    client: CNCTelnetClient,
    tool_number: int,
    pot_number: int,
    restore: bool,
) -> WriteResult:
    atc_before = await read_atc_tools(client)
    pot_row = _find_pot(atc_before, pot_number)
    prior_tool = (pot_row or {}).get("tool_number") or 0
    already = _find_tool(atc_before, tool_number)
    if already and int(already.get("pot_number") or 0) == pot_number:
        return WriteResult(
            "ATC assignment",
            True,
            "00",
            f"T{tool_number:02d} already in pot {pot_number}",
        )

    print(f"\n--- ATC assignment: T{tool_number:02d} → pot {pot_number} ---")
    print(f"  pot {pot_number} had tool {prior_tool}")
    if prior_tool == 255:
        print("  cap setting detected — will CHGMAGD clear before assign")
    if already:
        print(f"  T{tool_number:02d} currently in pot {already.get('pot_number')}")

    ok, status = await client.assign_tool_to_pot(pot_number, tool_number, verbose=True)
    if not ok:
        desc = CNCTelnetClient.get_status_description(status or "00")
        print(f"    FAIL: {desc}")
        return WriteResult("ATC assignment", False, status, desc)

    atc_after = await read_atc_tools(client)
    verify = _find_pot(atc_after, pot_number)
    verified_tn = (verify or {}).get("tool_number")
    print(f"  verify pot {pot_number}: tool_number={verified_tn}")

    if verified_tn != tool_number:
        return WriteResult(
            "ATC assignment",
            False,
            status,
            f"write ok but ATCTL shows tool {verified_tn}, expected {tool_number}",
        )

    if restore and prior_tool != tool_number:
        print(f"  restoring pot {pot_number} → T{prior_tool:02d} ...")
        restore_ok, restore_status = await client.assign_tool_to_pot(
            pot_number, prior_tool if prior_tool else 0, verbose=True
        )
        if not restore_ok:
            desc = CNCTelnetClient.get_status_description(restore_status or "00")
            return WriteResult(
                "ATC assignment",
                True,
                status,
                f"assigned ok; restore failed ({desc})",
            )
        print(f"    restored pot {pot_number} to tool {prior_tool}")

    detail = "assigned and verified" if not restore else "assign + restore ok"
    print(f"    OK: {detail}")
    return WriteResult("ATC assignment", True, status, detail)


async def test_atc_fields(
    client: CNCTelnetClient,
    tool_number: int,
    atc_row: dict,
) -> list[WriteResult]:
    results: list[WriteResult] = []
    pot = atc_row.get("pot_number")
    if pot is None or str(pot).upper() == "SPINDLE":
        print("\n--- ATC: skipped (tool on spindle or no pot) ---")
        return results

    pot_num = int(pot) if not isinstance(pot, int) else pot
    orig_color = int(atc_row.get("color") or 0)
    orig_type = int(atc_row.get("tool_type") or 1)
    new_color = 1 if orig_color != 1 else 2
    new_type = 2 if orig_type != 2 else 1

    print(f"\n--- ATC writes T{tool_number:02d} pot {pot_num} ---")
    print(f"  baseline: color={orig_color} type={orig_type}")

    print(f"  color: {orig_color} → {new_color} ...")
    color_result = await _write_and_report(
        "ATC color",
        lambda: client.change_atc_tool(
            "C", pot_num, tool_number, new_color, verbose=True
        ),
        lambda: client.change_atc_tool(
            "C", pot_num, tool_number, orig_color, verbose=True
        ),
    )
    results.append(color_result)
    print(f"    {'OK' if color_result.success else 'FAIL'}: {color_result.detail}")

    print(f"  type: {orig_type} → {new_type} ...")
    type_result = await _write_and_report(
        "ATC type",
        lambda: client.change_tool_type(pot_num, new_type, verbose=True),
        lambda: client.change_tool_type(pot_num, orig_type, verbose=True),
    )
    results.append(type_result)
    print(f"    {'OK' if type_result.success else 'FAIL'}: {type_result.detail}")

    return results


async def main() -> int:
    parser = argparse.ArgumentParser(description="Live test all writable tool fields")
    parser.add_argument("--ip", default=DEFAULT_IP)
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--tool", type=int, default=7)
    parser.add_argument("--units", choices=("in", "mm"), default="in")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument(
        "--assign-to-pot",
        metavar="POT",
        help="Assign tool to ATC pocket (1-99), or 'auto' for first empty pocket",
    )
    parser.add_argument(
        "--restore-assignment",
        action="store_true",
        help="After assign test, restore the pocket's previous tool number",
    )
    parser.add_argument(
        "--skip-table",
        action="store_true",
        help="Skip TOLN offset/life write tests",
    )
    args = parser.parse_args()

    if not 1 <= args.tool <= 99:
        print(f"ERROR: tool must be 1-99, got {args.tool}")
        return 1

    print(f"Connecting to {args.ip}:{args.port} ...")
    client = await create_fresh_connection(args.ip, args.port, timeout=30)
    if not client:
        print("ERROR: Could not connect")
        return 1

    try:
        print("Machine state:")
        await print_machine_state(client)

        table = await read_tool_table(client, args.units)
        row = _find_tool(table, args.tool)
        if not row:
            print(f"ERROR: T{args.tool:02d} not in tool table")
            return 1

        print(
            f"\nT{args.tool:02d} table: H={row.get('length')} D={row.get('diameter')} "
            f"W={row.get('tool_length_wear_offset')} life={_life_int(row)} "
            f"name={row.get('tool_name')!r}"
        )

        atc = await read_atc_tools(client)
        print(f"\nATC magazine: {len(atc)} entries")
        empty_pot = _find_empty_pot(atc)
        cap_pot = _find_cap_pot(atc)
        if empty_pot is not None:
            print(f"  first empty pocket: {empty_pot}")
        if cap_pot is not None:
            print(f"  first cap pocket (clearable): {cap_pot}")

        atc_row = _find_tool(atc, args.tool)
        if atc_row:
            print(
                f"T{args.tool:02d} ATC: pot={atc_row.get('pot_number')} "
                f"color={atc_row.get('color')} type={atc_row.get('tool_type')}"
            )
        else:
            print(f"T{args.tool:02d} not in ATC magazine")

        if args.read_only:
            return 0

        all_results: list[WriteResult] = []

        if args.assign_to_pot:
            if args.assign_to_pot.lower() == "auto":
                pot, kind = _find_assignable_pot(atc)
                if pot is None:
                    print("ERROR: no empty or cap ATC pocket found for auto assign")
                    return 1
                print(f"Auto-selected {kind} pot {pot}")
            else:
                pot = int(args.assign_to_pot)
            if not 1 <= pot <= 99:
                print(f"ERROR: pot must be 1-99, got {pot}")
                return 1
            all_results.append(
                await test_atc_assignment(
                    client,
                    args.tool,
                    pot,
                    restore=args.restore_assignment,
                )
            )
            atc = await read_atc_tools(client)
            atc_row = _find_tool(atc, args.tool)

        if not args.skip_table:
            all_results.extend(await test_table_fields(client, args.tool, row, args.units))
        if atc_row:
            all_results.extend(await test_atc_fields(client, args.tool, atc_row))

        print("\n" + "=" * 60)
        print("SUMMARY")
        for r in all_results:
            mark = "PASS" if r.success else "FAIL"
            print(f"  [{mark}] {r.name}: {r.detail}")

        failed = [r for r in all_results if not r.success]
        if failed:
            print(f"\n{len(failed)} field(s) failed — control may reject writes in current mode (status 05 = edit/operation)")
            return 2
        print("\nAll writable fields for T{:02d} passed (write + restore)".format(args.tool))
        return 0
    finally:
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
