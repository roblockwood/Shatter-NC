#!/usr/bin/env python3
"""Time each step of the measurement-tool API telnet path (validate → write → verify)."""
import argparse
import asyncio
import time

from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.parsers.mem_parser_v2 import parse_mem_v2
from app.parsers.prd3_parser_v2 import parse_prd3_v2
from app.services.machine_state_validator import MachineStateValidator


MEASUREMENT_TOOL_MACRO = 920


def ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


async def benchmark_validator_path(ip: str, port: int) -> dict[str, int]:
    """Mirror MachineStateValidator telnet work (no DB)."""
    timings: dict[str, int] = {}
    t0 = time.perf_counter()
    client = await create_fresh_connection(ip, port, timeout=10)
    timings["validate_connect"] = ms(t0)

    t = time.perf_counter()
    control_version = await client.detect_control_type()
    timings["validate_detect_control"] = ms(t)

    t = time.perf_counter()
    mem_data = await client.get_memory_data(verbose=False)
    if mem_data:
        parse_mem_v2(mem_data.encode("utf-8"), control_version=control_version)
    timings["validate_mem_lod"] = ms(t)

    t = time.perf_counter()
    prd3_data = await client.get_prd3_data(control_version=control_version, verbose=False)
    if prd3_data:
        parse_prd3_v2(prd3_data.encode("utf-8"), control_version=control_version)
    timings["validate_prd3_lod"] = ms(t)

    t = time.perf_counter()
    await client.get_alarm_data(verbose=False)
    timings["validate_alarm_lod"] = ms(t)

    t = time.perf_counter()
    await client.disconnect()
    timings["validate_disconnect"] = ms(t)

    return timings


async def benchmark_write_path(ip: str, port: int, tool: int, post_validate_delay_ms: int) -> dict[str, int]:
    timings: dict[str, int] = {}

    t = time.perf_counter()
    await asyncio.sleep(post_validate_delay_ms / 1000.0)
    timings["post_validate_sleep"] = ms(t)

    t = time.perf_counter()
    client = await create_fresh_connection(ip, port, timeout=10)
    timings["write_connect"] = ms(t)

    t = time.perf_counter()
    ok, status, verified = await client.write_macro_variable(
        macro_number=MEASUREMENT_TOOL_MACRO,
        value=float(tool),
        verbose=False,
        verify=True,
    )
    timings["write_and_verify"] = ms(t)

    t = time.perf_counter()
    await client.disconnect()
    timings["write_disconnect"] = ms(t)

    timings["write_ok"] = 1 if ok else 0
    timings["write_status"] = int(status) if status and status.isdigit() else -1
    timings["verified_tool"] = int(verified) if verified is not None else -1
    return timings


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="192.168.86.89")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--tool", type=int, default=12)
    parser.add_argument("--delay-ms", type=int, default=250, help="Post-validation sleep (API default)")
    args = parser.parse_args()

    print(f"Benchmarking measurement-tool path → {args.ip}:{args.port} (T{args.tool:02d})")
    print("=" * 60)

    validate = await benchmark_validator_path(args.ip, args.port)
    write = await benchmark_write_path(args.ip, args.port, args.tool, args.delay_ms)

    rows = [
        ("Validation TCP connect", validate["validate_connect"]),
        ("detect_control_type", validate["validate_detect_control"]),
        ("LOD MEM (+ parse)", validate["validate_mem_lod"]),
        ("LOD PRD3 (+ parse)", validate["validate_prd3_lod"]),
        ("LOD ALARM (not used for blocking)", validate["validate_alarm_lod"]),
        ("Validation disconnect", validate["validate_disconnect"]),
        ("Post-validation sleep (fixed)", write["post_validate_sleep"]),
        ("Write TCP connect", write["write_connect"]),
        ("WRTMCNM + REDMCNM verify", write["write_and_verify"]),
        ("Write disconnect", write["write_disconnect"]),
    ]

    total = sum(ms for _, ms in rows)
    for label, duration in rows:
        pct = (duration / total * 100) if total else 0
        bar = "█" * max(1, int(pct / 5))
        print(f"{label:40} {duration:5d} ms  ({pct:4.0f}%)  {bar}")

    print("-" * 60)
    print(f"{'TOTAL (telnet path only)':40} {total:5d} ms")
    print(f"Write ok={bool(write['write_ok'])} verified=#{write['verified_tool']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
