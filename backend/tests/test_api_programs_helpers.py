"""Unit tests for program validation and upload API helpers."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import programs


def _machine(**overrides):
    values = {
        "id": 1,
        "ip_address": "10.0.0.1",
        "ftp_port": 21,
        "ftp_username": "user",
        "ftp_password": "secret",
        "units": "in",
        "control_version": "C00",
        "use_machine_tool_tolerances": False,
        "validate_tool_diameter": True,
        "validate_tool_length": True,
        "diameter_tolerance": 0.01,
        "length_tolerance_plus": 0.02,
        "length_tolerance_minus": 0.0,
        "use_machine_wcs_tolerances": False,
        "tolerance_x": 0.01,
        "tolerance_y": 0.01,
        "tolerance_z": 0.01,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _program(**overrides):
    values = {
        "id": 10,
        "original_filename": "part.NC",
        "content_hash": "hash",
        "posted_date": None,
        "version_number": 1,
        "program_metadata": {},
        "file_size_bytes": 10,
        "line_count": 1,
        "estimated_runtime_seconds": None,
        "first_seen_at": datetime(2024, 1, 1),
        "last_deployed_at": None,
        "deployed_count": 0,
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_validate_tool_matches_string_tool_number_and_reports_mismatch():
    result = programs._validate_tool(
        {"tool_number": 7, "diameter": 0.25, "length_total": 2.0},
        {"tools": [{"tool_number": "7", "tool_name": "EM", "diameter": 0.251, "length": 1.5}]},
    )

    assert result.available is True
    assert result.machine_tool_data["tool_name"] == "EM"
    assert result.diameter_match is False
    assert result.length_sufficient is False
    assert "exact match required" in result.warnings[0]
    assert "must be ≥ required" in result.warnings[1]


def test_validate_tool_call_without_requirements_does_not_fail_dimensions():
    result = programs._validate_tool(
        {"tool_number": 9, "from_tool_call": True},
        {"tools": [{"tool_number": 9, "diameter": 0.5, "length": 1.0}]},
    )

    assert result.available is True
    assert result.requirements_complete is False
    assert result.diameter_match is True
    assert result.length_sufficient is True
    assert result.warnings == []


def test_validate_wcs_uses_per_axis_machine_tolerances(monkeypatch):
    monkeypatch.setattr(
        "app.parsers.posni_parser_v2.parse_posni_v2",
        lambda *_args, **_kwargs: {"work_offsets": {54: {"x": 1.005, "y": 2.02, "z": 3.001}}},
    )

    result = programs._validate_wcs_offset(
        {"work_offset": 54, "x": 1.0, "y": 2.0, "z": 3.0},
        "POSNI",
        use_machine_tolerances=True,
        tolerance_x=0.01,
        tolerance_y=0.01,
        tolerance_z=0.01,
    )

    assert result.valid is False
    assert result.difference["y"] == pytest.approx(0.02)
    assert result.warnings == ['Y axis difference 0.0200" exceeds tolerance ±0.01"']


@pytest.mark.asyncio
async def test_validate_program_uses_prefetched_tools_without_telnet():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _machine()
    parsed = {
        "tools": [{"tool_number": 4, "diameter": 0.25, "length_total": 1.0}],
        "posted_date": None,
        "estimated_runtime_seconds": 12.0,
        "wcs_offset": None,
        "line_count": 2,
        "file_size": 8,
    }

    with patch.object(programs, "parse_gcode", return_value=parsed):
        result = await programs.validate_program(
            1,
            programs.ProgramValidateRequest(
                gcode_content="T4 M6",
                prefetched_tool_data={"tools": [{"tool_number": 4, "diameter": 0.25, "length": 1.5}]},
            ),
            db,
        )

    assert result.valid is True
    assert result.tools[4].available is True
    assert result.metadata["tool_count"] == 1


@pytest.mark.asyncio
async def test_upload_program_returns_bad_request_for_service_value_error():
    request = programs.ProgramUploadRequest(gcode_content="G90", original_filename="A.NC")
    service = MagicMock()
    service.upload_program.side_effect = ValueError("duplicate name")

    with patch.object(programs, "ProgramService", return_value=service):
        with pytest.raises(HTTPException) as exc_info:
            await programs.upload_program(request, MagicMock())

    assert exc_info.value.status_code == 400
    assert "Upload failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_program_returns_not_found_for_unknown_machine():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await programs.validate_program(99, programs.ProgramValidateRequest(gcode_content="G90"), db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Machine 99 not found"


@pytest.mark.asyncio
async def test_validate_program_handles_unparseable_content_without_machine_calls():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _machine()

    with patch.object(programs, "parse_gcode", side_effect=ValueError("macro")):
        result = await programs.validate_program(
            1,
            programs.ProgramValidateRequest(
                gcode_content="nonstandard macro",
                prefetched_tool_data={"tools": []},
            ),
            db,
        )

    assert result.valid is True
    assert result.tools == {}
    assert result.metadata["line_count"] == 1
    assert result.warnings == ["No tool data in NC program and machine data unavailable"]


@pytest.mark.asyncio
async def test_validate_program_marks_missing_required_tool_invalid():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _machine()
    parsed = {
        "tools": [{"tool_number": 8, "diameter": 0.25, "length_total": 1.0}],
        "posted_date": None,
        "estimated_runtime_seconds": 0.0,
        "wcs_offset": None,
        "line_count": 1,
        "file_size": 5,
    }

    with patch.object(programs, "parse_gcode", return_value=parsed):
        result = await programs.validate_program(
            1,
            programs.ProgramValidateRequest(gcode_content="T8", prefetched_tool_data={"tools": []}),
            db,
        )

    assert result.valid is False
    assert result.tools[8].available is False
    assert result.errors == ["Tool T08 not found in machine tool table"]


def test_validate_wcs_requires_program_tolerance_when_machine_tolerances_disabled():
    result = programs._validate_wcs_offset(
        {"work_offset": 54, "x": 1.0, "y": 2.0, "z": 3.0},
        "unused",
    )

    assert result.valid is False
    assert result.tolerance == 0.0
    assert "No E parameter" in result.warnings[0]


def test_validate_wcs_reports_missing_machine_offset(monkeypatch):
    monkeypatch.setattr(
        "app.parsers.posni_parser_v2.parse_posni_v2",
        lambda *_args, **_kwargs: {"work_offsets": {}},
    )

    result = programs._validate_wcs_offset(
        {"work_offset": 55, "x": 1.0, "y": 2.0, "z": 3.0, "tolerance": 0.01},
        "POSNI",
    )

    assert result.valid is False
    assert result.actual == {}
    assert result.warnings == ["G55 offset not found in machine data"]


@pytest.mark.asyncio
async def test_validate_file_normalizes_path_and_returns_content():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _machine()
    ftp_client = MagicMock()
    ftp_client.download_file = AsyncMock(return_value=b"G90\nM30")
    validation = programs.ProgramValidationResponse(
        valid=True, tools={}, wcs_offset=None, warnings=[], errors=[], metadata={}
    )

    with (
        patch.object(programs, "CNCFtpClient", return_value=ftp_client),
        patch.object(programs, "validate_program", new=AsyncMock(return_value=validation)) as validate,
    ):
        result = await programs.validate_file_on_machine(1, r"//PROGRAM\\O0003.NC", db)

    ftp_client.download_file.assert_awaited_once_with("/PROGRAM/O0003.NC")
    validate.assert_awaited_once()
    assert result.gcode_content == "G90\nM30"
    assert result.validation.valid is True


@pytest.mark.asyncio
async def test_validate_file_returns_not_found_for_empty_download():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _machine()
    ftp_client = MagicMock()
    ftp_client.download_file = AsyncMock(return_value=b"")

    with patch.object(programs, "CNCFtpClient", return_value=ftp_client):
        with pytest.raises(HTTPException) as exc_info:
            await programs.validate_file_on_machine(1, "/O0003.NC", db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "File not found on machine: /O0003.NC"


@pytest.mark.asyncio
async def test_upload_program_validates_then_passes_result_to_service():
    request = programs.ProgramUploadRequest(
        gcode_content="G90",
        original_filename="part.NC",
        machine_id=1,
        deployed_filename="O2000.nc",
    )
    validation = programs.ProgramValidationResponse(
        valid=True, tools={}, wcs_offset=None, warnings=[], errors=[], metadata={}
    )
    service = MagicMock()
    service.upload_program.return_value = {
        "program": _program(),
        "is_new_version": True,
        "deployment": None,
        "validation_results": {"valid": True},
    }

    with (
        patch.object(programs, "ProgramService", return_value=service),
        patch.object(programs, "validate_program", new=AsyncMock(return_value=validation)) as validate,
    ):
        result = await programs.upload_program(request, MagicMock())

    validate.assert_awaited_once()
    assert service.upload_program.call_args.kwargs["validation_results"] is validation
    assert service.upload_program.call_args.kwargs["deployed_filename"] == "O2000.nc"
    assert result.is_new_version is True
    assert result.program.original_filename == "part.NC"


@pytest.mark.asyncio
async def test_upload_program_returns_internal_error_for_unexpected_failure():
    request = programs.ProgramUploadRequest(gcode_content="G90", original_filename="A.NC")
    service = MagicMock()
    service.upload_program.side_effect = RuntimeError("database unavailable")

    with patch.object(programs, "ProgramService", return_value=service):
        with pytest.raises(HTTPException) as exc_info:
            await programs.upload_program(request, MagicMock())

    assert exc_info.value.status_code == 500
    assert "Upload failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_next_onumber_returns_first_gap_in_fifo_range():
    machine_query = MagicMock()
    machine_query.filter.return_value.first.return_value = _machine()
    deployments_query = MagicMock()
    deployments_query.filter.return_value.order_by.return_value.all.return_value = [
        SimpleNamespace(deployed_filename="O2000.nc"),
        SimpleNamespace(deployed_filename="O2002.nc"),
    ]
    db = MagicMock()
    db.query.side_effect = [machine_query, deployments_query]

    result = await programs.get_next_onumber_fifo(1, db=db)

    assert result == {
        "next_onumber": "O2001.nc",
        "onumber_int": 2001,
        "is_replacing": False,
        "replacement_info": None,
        "is_redeployment": False,
    }


@pytest.mark.asyncio
async def test_get_deployment_by_onumber_rejects_invalid_format():
    with pytest.raises(HTTPException) as exc_info:
        await programs.get_deployment_by_onumber(1, "not-an-onumber", db=MagicMock())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid O-number format"


@pytest.mark.asyncio
async def test_get_program_returns_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await programs.get_program(123, db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Program not found"
