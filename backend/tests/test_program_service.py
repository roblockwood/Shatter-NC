"""Tests for ProgramService upload/deploy with mocked DB."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.program_service import ProgramService


def test_upload_program_dedupe_hit():
    existing = SimpleNamespace(id=1, original_filename="A.NC", content_hash="abc")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    service = ProgramService(db)

    with patch("app.services.program_service.parse_gcode", return_value={"tools": []}):
        with patch("app.models.program.Program.compute_hash", return_value="abc"):
            result = service.upload_program("%\nO1\n%", "A.NC")

    assert result["is_new_version"] is False
    assert result["program"] is existing
    assert result["deployment"] is None
    db.add.assert_not_called()


def test_upload_program_parse_failure_creates_new():
    db = MagicMock()
    # First query (by hash) -> None; scalar for max version -> None
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.scalar.return_value = None

    service = ProgramService(db)
    with patch("app.services.program_service.parse_gcode", side_effect=RuntimeError("boom")):
        with patch("app.models.program.Program.compute_hash", return_value="hash1"):
            with patch("app.services.program_service.Program") as Prog:
                prog_inst = MagicMock()
                Prog.return_value = prog_inst
                Prog.compute_hash = MagicMock(return_value="hash1")
                result = service.upload_program("G90\n", "MACRO.NC")

    assert result["is_new_version"] is True
    db.add.assert_called()
    db.commit.assert_called()


def test_deploy_program_missing_program():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    service = ProgramService(db)
    with pytest.raises(ValueError):
        service.deploy_program(1, 1, "O1000.NC")


def test_deploy_program_success():
    program = SimpleNamespace(id=1, deployed_count=0)
    machine = SimpleNamespace(id=2, name="M1")
    db = MagicMock()

    def first_side_effect():
        # program then machine then existing deployment
        yield program
        yield machine
        yield None

    # query().filter().first() called multiple times
    db.query.return_value.filter.return_value.first.side_effect = [program, machine, None]

    service = ProgramService(db)
    with patch("app.services.program_service.ProgramDeployment") as Dep:
        dep_inst = MagicMock()
        Dep.return_value = dep_inst
        result = service.deploy_program(
            program_id=1,
            machine_id=2,
            deployed_filename="O1000.NC",
            deployed_path="/PROGRAM/O1000.NC",
            validation_results={"valid": True},
        )
    assert result is dep_inst
    db.add.assert_called()
    db.commit.assert_called()
