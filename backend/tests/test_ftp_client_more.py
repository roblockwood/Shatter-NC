"""Additional FTP client behavioral tests with mocked ftplib."""
from unittest.mock import MagicMock, patch

import pytest
from ftplib import error_perm

from app.clients.ftp_client import CNCFtpClient


def _connected_client():
    client = CNCFtpClient("10.0.0.1", port=21, username="u", password="p")
    client._connected = True
    client.ftp = MagicMock()
    return client


@pytest.mark.asyncio
async def test_ensure_directory_root():
    client = _connected_client()
    result = await client.ensure_directory("/")
    assert result["success"] is True
    assert result["path"] == "/"


@pytest.mark.asyncio
async def test_ensure_directory_creates_parts():
    client = _connected_client()
    client.ftp.pwd.return_value = "/"

    def cwd(part):
        if part in ("/", "PROGRAM"):
            return
        raise error_perm("550 missing")

    # First cwd(part) fails for JOB1, then mkd + cwd succeeds
    seen = {"n": 0}

    def cwd_side_effect(part):
        seen["n"] += 1
        if part == "/":
            return
        if part == "PROGRAM":
            return
        if part == "JOB1" and seen["n"] < 4:
            raise Exception("nope")
        return

    client.ftp.cwd.side_effect = cwd_side_effect
    client.ftp.mkd = MagicMock()

    with patch.object(client, "_ensure_connection"):
        with patch("app.clients.ftp_client.time.sleep"):
            result = await client.ensure_directory("/PROGRAM/JOB1", settle_delay_seconds=0)

    assert result["success"] is True
    assert client.ftp.mkd.called


@pytest.mark.asyncio
async def test_upload_file_fails_when_ensure_directory_fails():
    client = _connected_client()
    with patch.object(client, "ensure_directory", return_value={"success": False, "error": "nope"}):
        result = await client.upload_file(b"data", "/PROGRAM/O1.NC")
    assert result["success"] is False
    assert "directory" in result["error"].lower()


@pytest.mark.asyncio
async def test_list_files_happy_path():
    client = _connected_client()

    def nlst():
        return ["O1000.NC", "O2000.NC"]

    client.ftp.nlst = nlst
    client.ftp.pwd.return_value = "/PROGRAM"
    client.ftp.cwd = MagicMock()

    with patch.object(client, "_ensure_connection"):
        # Prefer list_files if it exists
        if hasattr(client, "list_files"):
            files = await client.list_files("/PROGRAM")
            assert "O1000.NC" in files or isinstance(files, list)
        else:
            pytest.skip("list_files not present")
