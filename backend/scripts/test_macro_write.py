#!/usr/bin/env python3
"""Ad-hoc WRTMCNM test against a live Brother CNC (measurement tool macro #920)."""
import argparse
import asyncio
import sys
from typing import Optional

from app.clients._telnet_write_ops import format_macro_set_value
from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection


async def read_macro(client: CNCTelnetClient, macro: int) -> Optional[float]:
    return await client.get_macro_variable(macro, verbose=True)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Test WRTMCNM macro write on a Brother CNC")
    parser.add_argument("--ip", default="192.168.86.89")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--macro", type=int, default=920)
    parser.add_argument("--tool", type=int, default=5, help="Tool number to write to macro #920")
    parser.add_argument("--read-only", action="store_true", help="Only read macro, no write")
    args = parser.parse_args()

    print(f"Connecting to {args.ip}:{args.port}...")
    client = await create_fresh_connection(args.ip, args.port, timeout=15)
    if not client:
        print("ERROR: Could not connect")
        return 1

    try:
        before = await read_macro(client, args.macro)
        print(f"Macro #{args.macro} before: {before!r}")

        if args.read_only:
            return 0

        value = float(args.tool)
        payload = format_macro_set_value(value)
        print(f"Writing macro #{args.macro} = {value} (payload={payload!r}, len={len(payload)})")

        ok, status, verified = await client.write_macro_variable(
            macro_number=args.macro,
            value=value,
            verbose=True,
            verify=True,
        )
        print(f"Write result: ok={ok} status={status!r} verified={verified!r}")

        if not ok:
            desc = CNCTelnetClient.get_status_description(status or "00")
            print(f"Status description: {desc}")
            return 2

        after = await read_macro(client, args.macro)
        print(f"Macro #{args.macro} after:  {after!r}")
        return 0
    finally:
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
