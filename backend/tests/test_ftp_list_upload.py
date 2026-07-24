"""FTP list_files and upload success path with mocked ftplib."""
from unittest.mock import MagicMock, patch

import pytest

from app.clients.ftp_client import CNCFtpClient


@pytest.mark.asyncio
async def test_list_files_returns_entries():
    client = CNCFtpClient("10.0.0.1", username="u", password="p")
    client._connected = True
    ftp = MagicMock()
    ftp.pwd.return_value = "/PROGRAM"
    ftp.nlst.return_value = ["O1000.NC", "SUBDIR"]
    ftp.size.side_effect = lambda name: 128 if name.endswith(".NC") else (_ for _ in ()).throw(Exception("dir"))
    ftp.cwd = MagicMock()
    client.ftp = ftp

    with patch.object(client, "_ensure_connection"):
        files = await client.list_files("/PROGRAM")

    assert isinstance(files, list)
    names = [f.get("name") or f.get("filename") for f in files]
    assert "O1000.NC" in names or any("O1000" in str(f) for f in files)


@pytest.mark.asyncio
async def test_upload_file_success():
    client = CNCFtpClient("10.0.0.1", username="u", password="p")
    client._connected = True
    ftp = MagicMock()
    ftp.pwd.return_value = "/"
    ftp.cwd = MagicMock()
    ftp.storbinary = MagicMock()
    client.ftp = ftp

    with patch.object(client, "ensure_directory", return_value={"success": True}):
        with patch.object(client, "_ensure_connection"):
            result = await client.upload_file(b"%\nO1\n%", "/PROGRAM/O1.NC")

    assert result.get("success") is True
