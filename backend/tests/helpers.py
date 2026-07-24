"""Shared test helpers (importable from test modules)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional


class FakeReader:
    """Async stream reader that yields queued response chunks then EOF."""

    def __init__(self, response: bytes = b"", *extra: bytes) -> None:
        chunks: list[bytes] = []
        if response:
            chunks.append(response)
        chunks.extend(extra)
        self._chunks = chunks

    async def read(self, n: int) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)
        return b""


class FakeWriter:
    """Records writes; simulates a healthy, non-closing connection."""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self._closing = False

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        pass

    def is_closing(self) -> bool:
        return self._closing

    def close(self) -> None:
        self._closing = True

    async def wait_closed(self) -> None:
        pass


def make_brother_response(
    command: str,
    args: str = "",
    status: str = "00",
    data: str = "",
    checksum: str = "05",
) -> bytes:
    """Build a minimal valid Brother protocol response frame."""
    cmd_padded = command.ljust(7)[:7]
    args_padded = args.ljust(8)[:8]
    header = f"%R{cmd_padded}{args_padded}{status}\r\n"
    body = f"{data}\r\n" if data else ""
    return f"{header}{body}{checksum}%\r\n".encode("ascii")


def make_machine(
    *,
    id: int = 1,
    ip_address: str = "10.0.0.1",
    port: int = 10000,
    name: str = "Test Machine",
    control_version: str = "C00",
    ftp_enabled: bool = False,
    ftp_host: Optional[str] = None,
    ftp_username: Optional[str] = None,
    ftp_password: Optional[str] = None,
    **extra,
) -> SimpleNamespace:
    """Lightweight machine stand-in for service-level unit tests."""
    return SimpleNamespace(
        id=id,
        ip_address=ip_address,
        port=port,
        name=name,
        control_version=control_version,
        ftp_enabled=ftp_enabled,
        ftp_host=ftp_host,
        ftp_username=ftp_username,
        ftp_password=ftp_password,
        **extra,
    )
