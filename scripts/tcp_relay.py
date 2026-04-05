#!/usr/bin/env python3
"""Simple TCP relay for local-host to target-host forwarding.

This is intended for machine protocols that use a single TCP stream
(such as Brother Telnet on port 10000).
"""

import argparse
import socket
import sys
import threading
from typing import Tuple

BUFFER_SIZE = 65536


def pump(src: socket.socket, dst: socket.socket) -> None:
    """Forward bytes from src to dst until EOF or error."""
    try:
        while True:
            data = src.recv(BUFFER_SIZE)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def handle_client(client: socket.socket, target: Tuple[str, int]) -> None:
    """Bridge a single client connection to target."""
    upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upstream.settimeout(10)

    try:
        upstream.connect(target)
        upstream.settimeout(None)
        client.settimeout(None)

        t1 = threading.Thread(target=pump, args=(client, upstream), daemon=True)
        t2 = threading.Thread(target=pump, args=(upstream, client), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as exc:
        print(f"relay: connection error to {target[0]}:{target[1]} -> {exc}", flush=True)
    finally:
        try:
            upstream.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="TCP relay")
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, required=True)
    args = parser.parse_args()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        listener.bind((args.listen_host, args.listen_port))
        listener.listen(128)
    except Exception as exc:
        print(
            f"relay: failed to bind {args.listen_host}:{args.listen_port} -> {exc}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print(
        f"relay: listening on {args.listen_host}:{args.listen_port} -> {args.target_host}:{args.target_port}",
        flush=True,
    )

    target = (args.target_host, args.target_port)
    try:
        while True:
            client, addr = listener.accept()
            print(f"relay: accepted {addr[0]}:{addr[1]}", flush=True)
            threading.Thread(target=handle_client, args=(client, target), daemon=True).start()
    except KeyboardInterrupt:
        print("relay: stopping", flush=True)
        return 0
    finally:
        try:
            listener.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
