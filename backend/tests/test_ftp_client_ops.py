"""Tests for FTP client MLST helpers and download path."""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.clients.ftp_client import CNCFtpClient


def _client() -> CNCFtpClient:
    return CNCFtpClient("10.0.0.1", port=21, username="u", password="p")


def test_parse_mlst_response():
    client = _client()
    parsed = client._parse_mlst_response("size=123;modify=20240101120000;Type=file; O2000.NC")
    assert parsed["filename"] == "O2000.NC"
    assert parsed["metadata"]["size"] == "123"
    assert parsed["metadata"]["modify"] == "20240101120000"
    assert parsed["metadata"]["type"] == "file"


def test_parse_mlst_date_valid():
    client = _client()
    assert "2024-01-01T12:00:00" in client._parse_mlst_date("20240101120000")


def test_parse_mlst_date_invalid():
    client = _client()
    assert client._parse_mlst_date("") == ""
    assert client._parse_mlst_date("bad") == ""
    assert client._parse_mlst_date("20240101") == ""


@pytest.mark.asyncio
async def test_download_file_happy_path():
    client = _client()
    client._connected = True
    ftp = MagicMock()
    ftp.pwd.return_value = "/PROGRAM"
    ftp.cwd = MagicMock()

    def retrbinary(cmd, callback):
        assert "O2000.NC" in cmd
        callback(b"G90\n")

    ftp.retrbinary = retrbinary
    client.ftp = ftp

    with patch.object(client, "_ensure_connection"):
        data = await client.download_file("/PROGRAM/O2000.NC")

    assert data == b"G90\n"
    ftp.cwd.assert_any_call("/PROGRAM")


@pytest.mark.asyncio
async def test_download_file_returns_none_on_error():
    client = _client()
    client._connected = True
    ftp = MagicMock()
    ftp.pwd.side_effect = RuntimeError("down")
    client.ftp = ftp
    with patch.object(client, "_ensure_connection"):
        assert await client.download_file("O1.NC") is None
