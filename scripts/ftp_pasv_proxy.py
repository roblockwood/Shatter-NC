#!/usr/bin/env python3
"""Minimal FTP passive-mode proxy.

Designed for environments where containers cannot directly reach CNC FTP servers
but can reach the host machine. This proxy rewrites PASV responses so the FTP
client connects data channels to the proxy, which then bridges to the CNC server.
"""

import argparse
import re
import socket
import sys
import threading
from typing import List, Optional, Tuple

BUFFER_SIZE = 65536

PASV_RE = re.compile(r"\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)")


def read_ftp_response_lines(file_obj) -> List[bytes]:
    """Read one FTP response (single or multiline)."""
    first = file_obj.readline()
    if not first:
        return []

    lines = [first]
    if len(first) >= 4 and first[3:4] == b"-":
        code = first[:3]
        while True:
            line = file_obj.readline()
            if not line:
                break
            lines.append(line)
            if line.startswith(code + b" "):
                break
    return lines


def pump(src: socket.socket, dst: socket.socket) -> None:
    """Forward bytes from src to dst until EOF/error."""
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


def bridge_pair(a: socket.socket, b: socket.socket) -> None:
    """Bridge two established sockets until closed."""
    t1 = threading.Thread(target=pump, args=(a, b), daemon=True)
    t2 = threading.Thread(target=pump, args=(b, a), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


class PassiveDataBridge:
    """Single-use passive data bridge for one PASV operation."""

    def __init__(
        self,
        target_host: str,
        target_port: int,
        listen_host: str,
        advertise_host: str,
        timeout: float,
    ):
        self.target_host = target_host
        self.target_port = target_port
        self.listen_host = listen_host
        self.advertise_host = advertise_host
        self.timeout = timeout

        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((self.listen_host, 0))
        self.listener.listen(1)

        self.bound_port = self.listener.getsockname()[1]

    def start(self) -> None:
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self) -> None:
        client_data = None
        upstream_data = None
        try:
            print(
                f"ftp-proxy: data bridge waiting on {self.listener.getsockname()[0]}:{self.bound_port} "
                f"for upstream {self.target_host}:{self.target_port}",
                flush=True,
            )
            self.listener.settimeout(self.timeout)
            client_data, _ = self.listener.accept()
            print("ftp-proxy: data bridge accepted client data connection", flush=True)
            upstream_data = socket.create_connection(
                (self.target_host, self.target_port), timeout=self.timeout
            )
            print("ftp-proxy: data bridge connected to upstream passive endpoint", flush=True)

            client_data.settimeout(None)
            upstream_data.settimeout(None)
            bridge_pair(client_data, upstream_data)
            print("ftp-proxy: data bridge transfer complete", flush=True)
        except Exception as exc:
            print(f"ftp-proxy: data bridge error: {exc}", flush=True)
        finally:
            for sock in (client_data, upstream_data, self.listener):
                if sock is None:
                    continue
                try:
                    sock.close()
                except Exception:
                    pass


def parse_pasv_endpoint(resp_line: bytes) -> Optional[Tuple[str, int]]:
    """Extract host/port from a 227 PASV response line."""
    text = resp_line.decode("latin-1", errors="ignore")
    match = PASV_RE.search(text)
    if not match:
        return None

    h1, h2, h3, h4, p1, p2 = (int(match.group(i)) for i in range(1, 7))
    host = f"{h1}.{h2}.{h3}.{h4}"
    port = p1 * 256 + p2
    return host, port


def build_pasv_response(advertise_host: str, port: int) -> bytes:
    """Build a 227 response line that points client data channel at proxy."""
    octets = advertise_host.split(".")
    if len(octets) != 4:
        raise ValueError(f"Invalid advertise host for PASV: {advertise_host}")

    p1 = port // 256
    p2 = port % 256
    payload = ",".join(octets + [str(p1), str(p2)])
    return f"227 Entering Passive Mode ({payload})\r\n".encode("ascii")


def handle_client(
    client_sock: socket.socket,
    target_host: str,
    target_port: int,
    data_listen_host: str,
    data_timeout: float,
    advertise_host_override: Optional[str],
) -> None:
    """Handle one FTP control connection proxy session."""
    upstream = None
    client_file = None
    upstream_file = None

    try:
        upstream = socket.create_connection((target_host, target_port), timeout=10)
        client_file = client_sock.makefile("rb", buffering=0)
        upstream_file = upstream.makefile("rb", buffering=0)

        # Forward server greeting first.
        for line in read_ftp_response_lines(upstream_file):
            client_sock.sendall(line)

        while True:
            cmd_line = client_file.readline()
            if not cmd_line:
                break

            cmd = cmd_line.strip().upper()

            # Intercept PASV only; client uses passive mode in current backend.
            if cmd == b"PASV" or cmd.startswith(b"PASV "):
                upstream.sendall(cmd_line)
                resp_lines = read_ftp_response_lines(upstream_file)
                if not resp_lines:
                    break

                last = resp_lines[-1]
                endpoint = parse_pasv_endpoint(last)
                if endpoint is None or not last.startswith(b"227"):
                    for line in resp_lines:
                        client_sock.sendall(line)
                    continue

                data_target_host, data_target_port = endpoint
                control_local_host = client_sock.getsockname()[0]
                advertise_host = advertise_host_override or control_local_host
                print(
                    f"ftp-proxy: PASV rewrite upstream={data_target_host}:{data_target_port} "
                    f"advertise={advertise_host}",
                    flush=True,
                )
                bridge = PassiveDataBridge(
                    target_host=data_target_host,
                    target_port=data_target_port,
                    listen_host=data_listen_host,
                    advertise_host=advertise_host,
                    timeout=data_timeout,
                )
                bridge.start()

                for line in resp_lines[:-1]:
                    client_sock.sendall(line)
                client_sock.sendall(build_pasv_response(advertise_host, bridge.bound_port))
                continue

            # Pass-through for all other commands.
            upstream.sendall(cmd_line)
            resp_lines = read_ftp_response_lines(upstream_file)
            if not resp_lines:
                break
            for line in resp_lines:
                client_sock.sendall(line)

            # Data transfer commands often send a preliminary 1xx response
            # followed by a final 2xx/4xx/5xx completion response.
            while resp_lines and resp_lines[-1][:1] == b"1":
                resp_lines = read_ftp_response_lines(upstream_file)
                if not resp_lines:
                    break
                for line in resp_lines:
                    client_sock.sendall(line)

            if cmd.startswith(b"QUIT"):
                break

    except Exception as exc:
        print(f"ftp-proxy: control connection error: {exc}", flush=True)
    finally:
        for fobj in (client_file, upstream_file):
            if fobj is None:
                continue
            try:
                fobj.close()
            except Exception:
                pass
        for sock in (upstream, client_sock):
            if sock is None:
                continue
            try:
                sock.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="FTP passive-mode proxy")
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, default=21)
    parser.add_argument("--data-listen-host", default="0.0.0.0")
    parser.add_argument("--data-timeout", type=float, default=30.0)
    parser.add_argument("--advertise-host", default="")
    args = parser.parse_args()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        listener.bind((args.listen_host, args.listen_port))
        listener.listen(64)
    except Exception as exc:
        print(
            f"ftp-proxy: failed to bind {args.listen_host}:{args.listen_port} -> {exc}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print(
        f"ftp-proxy: listening on {args.listen_host}:{args.listen_port} -> {args.target_host}:{args.target_port}",
        flush=True,
    )

    advertise_host = args.advertise_host.strip() or None

    try:
        while True:
            client, addr = listener.accept()
            print(f"ftp-proxy: accepted control {addr[0]}:{addr[1]}", flush=True)
            threading.Thread(
                target=handle_client,
                args=(
                    client,
                    args.target_host,
                    args.target_port,
                    args.data_listen_host,
                    args.data_timeout,
                    advertise_host,
                ),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print("ftp-proxy: stopping", flush=True)
        return 0
    finally:
        try:
            listener.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
