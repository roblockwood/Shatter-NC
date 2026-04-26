"""Tests for remote candidate collection in FTP download mode."""

from types import SimpleNamespace

import pytest

from app.services.ftp_sync_service import FtpSyncService


@pytest.mark.asyncio
async def test_collect_remote_candidates_filters_and_maps(tmp_path):
    service = FtpSyncService(websocket_manager=None)

    async def fake_list(_ftp_client, _remote_folder):
        return [
            {"name": "O2000.NC", "path": "/PROGRAM/O2000.NC", "is_directory": False},
            {"name": "README.TXT", "path": "/PROGRAM/README.TXT", "is_directory": False},
            {"name": "ALARM.NC", "path": "/PROGRAM/ALARM.NC", "is_directory": False},
            {"name": "SUB", "path": "/PROGRAM/SUB", "is_directory": True},
        ]

    service._list_remote_files_with_retry = fake_list

    config = SimpleNamespace(
        source_folder=str(tmp_path),
        remote_folder="/PROGRAM",
        include_pattern="*",
        exclude_patterns="",
        control_type="C00",
        strict_brother_naming=True,
        require_onumber_filename=True,
    )

    files, excluded = await service._collect_remote_candidate_files(config, ftp_client=None, relative_paths=None)

    assert len(files) == 1
    assert files[0][0] == "O2000.NC"
    assert files[0][1].endswith("O2000.NC")
    assert files[0][2] == "/PROGRAM/O2000.NC"

    excluded_reasons = {row[3] for row in excluded}
    assert "unsupported_extension" in excluded_reasons or "requires_onumber_filename" in excluded_reasons
    assert "reserved_system_filename" in excluded_reasons


@pytest.mark.asyncio
async def test_collect_remote_candidates_respects_relative_filter(tmp_path):
    service = FtpSyncService(websocket_manager=None)

    async def fake_list(_ftp_client, _remote_folder):
        return [
            {"name": "O2001.NC", "path": "/PROGRAM/O2001.NC", "is_directory": False},
            {"name": "O2002.NC", "path": "/PROGRAM/O2002.NC", "is_directory": False},
        ]

    service._list_remote_files_with_retry = fake_list

    config = SimpleNamespace(
        source_folder=str(tmp_path),
        remote_folder="/PROGRAM",
        include_pattern="*.NC",
        exclude_patterns="",
        control_type="C00",
        strict_brother_naming=True,
        require_onumber_filename=True,
    )

    files, excluded = await service._collect_remote_candidate_files(
        config,
        ftp_client=None,
        relative_paths=["O2002.NC"],
    )

    assert len(files) == 1
    assert files[0][0] == "O2002.NC"
    assert excluded == []
