#!/usr/bin/env python3
"""Simple TCP relay for Brother CNC Telnet (Protocol Type 2).

Usage:
  python scripts/telnet_relay.py --listen-port 10000 --target-host 192.168.1.135 --target-port 10000

This runs on the host machine and lets Docker containers connect to host.docker.internal:10000,
which is then forwarded to the CNC telnet endpoint.
"""

import argparse
import asyncio
import contextlib


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        with contextlib.suppress(Exception):
            writer.close()
            await writer.wait_closed()


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    target_host: str,
    target_port: int,
) -> None:
    target_reader = None
    target_writer = None
    try:
        target_reader, target_writer = await asyncio.open_connection(target_host, target_port)

        await asyncio.gather(
            pipe(client_reader, target_writer),
            pipe(target_reader, client_writer),
        )
    except Exception:
        with contextlib.suppress(Exception):
            client_writer.close()
            await client_writer.wait_closed()
        if target_writer:
            with contextlib.suppress(Exception):
                target_writer.close()
                await target_writer.wait_closed()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Host-side TCP relay for Brother CNC Telnet")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--listen-port", type=int, default=10000, help="Local listen port (default: 10000)")
    parser.add_argument("--target-host", required=True, help="CNC target host/IP")
    parser.add_argument("--target-port", type=int, default=10000, help="CNC target port (default: 10000)")
    args = parser.parse_args()

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, args.target_host, args.target_port),
        host=args.listen_host,
        port=args.listen_port,
    )

    sockets = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
    print(f"Telnet relay listening on {sockets} -> {args.target_host}:{args.target_port}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
