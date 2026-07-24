"""Tests for ftp_sync_service helpers and retry paths."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ftp_sync_service import FtpSyncService


def test_max_nested_folder_depth():
    assert FtpSyncService._max_nested_folder_depth("C00") == 0
    assert FtpSyncService._max_nested_folder_depth("D00") == 2
    assert FtpSyncService._max_nested_folder_depth(None) == 0


def test_join_remote():
    assert FtpSyncService._join_remote("/PROGRAM", "A/O1.NC") == "/PROGRAM/A/O1.NC"
    assert FtpSyncService._join_remote("/", "O1.NC") == "/O1.NC"
    assert FtpSyncService._join_remote("", "O1.NC") == "/O1.NC"


def test_relative_remote_path():
    assert FtpSyncService._relative_remote_path("/PROGRAM", "/PROGRAM/A/O1.NC") == "A/O1.NC"
    assert FtpSyncService._relative_remote_path("/", "/O1.NC") == "O1.NC"
    assert FtpSyncService._relative_remote_path("/PROGRAM", "/OTHER/O1.NC") == "OTHER/O1.NC"


def test_detect_changed_files_seed_then_change(tmp_path):
    service = FtpSyncService(websocket_manager=None)
    folder = tmp_path / "src"
    folder.mkdir()
    f = folder / "O1000.NC"
    f.write_text("%\nO1000\n%")

    config = SimpleNamespace(
        id=1,
        source_folder=str(folder),
        include_pattern="*.NC",
        debounce_seconds=0.0,
    )

    # First scan seeds cache
    assert service._detect_changed_files(config) == []
    # Touch mtime past debounce
    import os
    import time

    time.sleep(0.05)
    os.utime(f, None)
    changed = service._detect_changed_files(config)
    assert changed == ["O1000.NC"]


@pytest.mark.asyncio
async def test_upload_with_retry_succeeds_second_try():
    service = FtpSyncService(websocket_manager=None)
    ftp = MagicMock()
    ftp.upload_file = AsyncMock(
        side_effect=[{"success": False, "error": "busy"}, {"success": True}]
    )
    with patch("app.services.ftp_sync_service.asyncio.sleep", AsyncMock()):
        with patch("app.services.ftp_sync_service.settings") as settings:
            settings.FTP_SYNC_REMOTE_DIR_CREATE_RETRIES = 2
            settings.FTP_SYNC_REMOTE_DIR_CREATE_DELAY_SECONDS = 0
            result = await service._upload_with_retry(ftp, b"data", "/PROGRAM/O1.NC")
    assert result["success"] is True
    assert ftp.upload_file.await_count == 2


@pytest.mark.asyncio
async def test_download_with_retry_returns_none():
    service = FtpSyncService(websocket_manager=None)
    ftp = MagicMock()
    ftp.download_file = AsyncMock(return_value=None)
    with patch("app.services.ftp_sync_service.asyncio.sleep", AsyncMock()):
        with patch("app.services.ftp_sync_service.settings") as settings:
            settings.FTP_SYNC_REMOTE_DIR_CREATE_RETRIES = 1
            settings.FTP_SYNC_REMOTE_DIR_CREATE_DELAY_SECONDS = 0
            result = await service._download_with_retry(ftp, "/PROGRAM/O1.NC")
    assert result is None
    assert ftp.download_file.await_count == 2
