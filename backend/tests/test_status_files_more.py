"""Mocked file-management route tests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api import _status_files as files


def _db(machine):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = machine
    return db


def _machine():
    return SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        ftp_port=2121,
        ftp_username="operator",
        ftp_password="secret",
        units="in",
    )


@pytest.mark.asyncio
async def test_list_programs_returns_ftp_listing(monkeypatch):
    ftp_client = MagicMock()
    ftp_client.get_programs = AsyncMock(return_value=[{"name": "O1000.NC"}, {"name": "PARTS", "is_dir": True}])
    monkeypatch.setattr(files, "CNCFtpClient", MagicMock(return_value=ftp_client))
    monkeypatch.setattr(
        files,
        "_attach_program_notes",
        MagicMock(return_value=[
            {"name": "O1000.NC", "program_note": None},
            {"name": "PARTS", "is_dir": True, "program_note": None},
        ]),
    )

    result = await files.list_programs(1, "/PROGRAMS", _db(_machine()))

    assert result == {
        "machine_id": 1,
        "machine_name": "Mill",
        "current_path": "/PROGRAMS",
        "programs": [
            {"name": "O1000.NC", "program_note": None},
            {"name": "PARTS", "is_dir": True, "program_note": None},
        ],
        "total_count": 2,
    }
    ftp_client.get_programs.assert_awaited_once_with("/PROGRAMS")


@pytest.mark.asyncio
async def test_list_programs_rejects_unknown_machine():
    with pytest.raises(HTTPException) as exc_info:
        await files.list_programs(99, "/", _db(None))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Machine with id 99 not found"


@pytest.mark.asyncio
async def test_download_file_returns_attachment_response(monkeypatch):
    ftp_client = MagicMock()
    ftp_client.download_file = AsyncMock(return_value=b"G01 X1")
    monkeypatch.setattr(files, "CNCFtpClient", MagicMock(return_value=ftp_client))

    response = await files.download_file(1, "/PROGRAMS/O1000.NC", _db(_machine()))

    assert response.media_type == "application/octet-stream"
    assert response.headers["content-disposition"] == "attachment; filename=O1000.NC"
    ftp_client.download_file.assert_awaited_once_with("/PROGRAMS/O1000.NC")


@pytest.mark.asyncio
async def test_file_metadata_parses_tools_and_runtime(monkeypatch):
    ftp_client = MagicMock()
    ftp_client.download_file = AsyncMock(return_value=b"T1 M06\nT7 M06")
    monkeypatch.setattr(files, "CNCFtpClient", MagicMock(return_value=ftp_client))
    monkeypatch.setattr(
        files,
        "parse_gcode",
        MagicMock(return_value={"tools": [{"tool_number": 1}, {"tool_number": 7}], "estimated_runtime_seconds": 91.9}),
    )
    persist = MagicMock(return_value="FACE OP")
    monkeypatch.setattr(
        files,
        "ProgramService",
        MagicMock(return_value=MagicMock(persist_comment_for_machine_file=persist)),
    )

    result = await files.get_file_metadata(1, "/O1000.NC", _db(_machine()))

    assert result == {
        "file_path": "/O1000.NC",
        "tools": [1, 7],
        "runtime_seconds": 91,
        "has_errors": False,
        "program_note": "FACE OP",
    }
    persist.assert_called_once()


@pytest.mark.asyncio
async def test_view_file_rejects_missing_ftp_file(monkeypatch):
    ftp_client = MagicMock()
    ftp_client.download_file = AsyncMock(return_value=None)
    monkeypatch.setattr(files, "CNCFtpClient", MagicMock(return_value=ftp_client))

    with pytest.raises(HTTPException) as exc_info:
        await files.view_file(1, "/MISSING.NC", db=_db(_machine()))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Failed to read file: /MISSING.NC"
