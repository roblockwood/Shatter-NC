"""Tests for program comment persistence and list attachment."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api import _status_files as files
from app.models.program import Program, ProgramDeployment
from app.services.program_service import ProgramService, program_comment_from_content


def test_program_comment_from_content_strips_onumber_prefix():
    content = "(O1234 — BRACKET POCKET)\nG90\n"
    assert program_comment_from_content(content, "O1234.NC") == "BRACKET POCKET"


def test_attach_program_notes_uses_deployment_metadata():
    db = MagicMock()
    program = SimpleNamespace(program_metadata={"program_comment": "FACE OP"})
    deployment = SimpleNamespace(
        deployed_path="/O2000.NC",
        deployed_filename="O2000.NC",
        program=program,
    )
    query = MagicMock()
    query.options.return_value.filter.return_value.all.return_value = [deployment]
    db.query.return_value = query

    rows = [{"name": "O2000.NC", "path": "/O2000.NC", "is_directory": False}]
    enriched = files._attach_program_notes(db, 1, rows)

    assert enriched[0]["program_note"] == "FACE OP"


def test_attach_program_notes_leaves_unmanaged_files_empty():
    db = MagicMock()
    query = MagicMock()
    query.options.return_value.filter.return_value.all.return_value = []
    db.query.return_value = query

    rows = [{"name": "O9999.NC", "path": "/O9999.NC", "is_directory": False}]
    enriched = files._attach_program_notes(db, 1, rows)

    assert enriched[0]["program_note"] is None


@pytest.mark.asyncio
async def test_list_programs_does_not_download_nc_files(monkeypatch):
    machine = SimpleNamespace(
        id=1,
        name="Mill",
        ip_address="10.0.0.1",
        ftp_port=2121,
        ftp_username="operator",
        ftp_password="secret",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = machine

    ftp_client = MagicMock()
    ftp_client.get_programs = AsyncMock(
        return_value=[{"name": "O1000.NC", "path": "/O1000.NC", "is_directory": False}]
    )
    monkeypatch.setattr(files, "CNCFtpClient", MagicMock(return_value=ftp_client))
    monkeypatch.setattr(
        files,
        "_attach_program_notes",
        MagicMock(return_value=[{"name": "O1000.NC", "path": "/O1000.NC", "program_note": "TEST"}]),
    )

    result = await files.list_programs(1, "/", db)

    assert result["programs"][0]["program_note"] == "TEST"
    ftp_client.get_programs.assert_awaited_once_with("/")
    ftp_client.download_file.assert_not_called()


def test_upload_program_stores_program_comment_in_metadata():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.scalar.return_value = 0

    service = ProgramService(db)
    content = "(O2000 — FACE OP)\nG90\nM30\n"

    with patch.object(db, "add"), patch.object(db, "commit"), patch.object(db, "refresh"):
        with patch("app.services.program_service.parse_gcode") as parse_gcode:
            parse_gcode.return_value = {
                "tools": [],
                "posted_date": None,
                "estimated_runtime_seconds": 0.0,
                "wcs_offset": None,
                "stock_size": None,
                "line_count": 3,
                "file_size": len(content.encode()),
            }
            result = service.upload_program(
                gcode_content=content,
                original_filename="O2000.NC",
            )

    metadata = result["program"].program_metadata
    assert metadata["program_comment"] == "FACE OP"


def test_persist_comment_creates_deployment_for_list_lookup():
    db = MagicMock()
    service = ProgramService(db)
    content = "(O2000 — FACE OP)\nG90\nM30\n"
    program = SimpleNamespace(id=42, program_metadata={})

    deployment_query = MagicMock()
    deployment_query.filter.return_value.first.return_value = None
    program_query = MagicMock()
    program_query.filter.return_value.first.return_value = program

    def query_side_effect(model):
        if model is ProgramDeployment:
            return deployment_query
        if model is Program:
            return program_query
        return MagicMock()

    db.query.side_effect = query_side_effect

    with patch.object(service, "_set_program_comment", return_value="FACE OP") as set_comment:
        with patch.object(service, "upload_program") as upload:
            with patch.object(service, "_ensure_comment_deployment") as ensure_deployment:
                result = service.persist_comment_for_machine_file(
                    machine_id=1,
                    file_path="/O2000.NC",
                    gcode_content=content,
                    filename="O2000.NC",
                )

    assert result == "FACE OP"
    upload.assert_not_called()
    set_comment.assert_called_once_with(program, content, "O2000.NC")
    ensure_deployment.assert_called_once_with(
        program_id=42,
        machine_id=1,
        filename="O2000.NC",
        deployed_path="/O2000.NC",
    )
