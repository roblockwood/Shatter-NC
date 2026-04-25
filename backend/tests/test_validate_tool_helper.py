"""Behavioral tests for _validate_tool and the gcode parser → validation pipeline.

These tests exist to prevent regressions introduced during refactoring:
  - length_total (gcode parser key) must feed required_length in _validate_tool
  - from_tool_call flag must suppress dimension validation (requirements_complete)
  - tool number comparison must be type-safe (str "1" == int 1)
  - use_machine_tolerances must gate tolerance mode correctly
  - validate_program and upload_program must be importable from app.api.programs
    (they were missing re-exports that broke ftp_sync_service at runtime)
"""

import pytest
from app.api._programs_validate import _validate_tool
from app.parsers.gcode_parser import GCodeParser


# ---------------------------------------------------------------------------
# Fixtures — minimal tool records
# ---------------------------------------------------------------------------

def _machine_data(*tools):
    """Wrap tool dicts in the expected machine_tool_data shape."""
    return {"tools": list(tools)}


def _tool(tool_number, diameter=0.5, length=4.0, tool_name="END MILL"):
    """Machine tool table entry."""
    return {
        "tool_number": tool_number,
        "diameter": diameter,
        "length": length,
        "tool_name": tool_name,
    }


def _program_tool(tool_number, diameter=0.5, length_total=4.0, from_tool_call=False):
    """G-code program tool entry (shape produced by GCodeParser.extract_tools)."""
    return {
        "tool_number": tool_number,
        "diameter": diameter,
        "length_total": length_total,
        "from_tool_call": from_tool_call,
    }


# ---------------------------------------------------------------------------
# 1.  length_total is the required-length key
# ---------------------------------------------------------------------------

class TestRequiredLengthKey:
    """_validate_tool must read length from length_total, not length."""

    def test_length_total_populates_required_length(self):
        """required_length in result must match the program tool's length_total."""
        prog_tool = _program_tool(1, length_total=3.75)
        result = _validate_tool(prog_tool, _machine_data(_tool(1, length=4.0)))
        assert result.required_length == pytest.approx(3.75)

    def test_length_key_absent_does_not_crash(self):
        """A tool dict without any length key should not raise; required_length=0."""
        prog_tool = {"tool_number": 1, "diameter": 0.5}
        result = _validate_tool(prog_tool, _machine_data(_tool(1, length=4.0)))
        assert result.required_length == pytest.approx(0.0)

    def test_zero_length_total_means_no_length_check(self):
        """When length_total=0, the tool should not fail a length check."""
        prog_tool = _program_tool(1, length_total=0.0)
        result = _validate_tool(prog_tool, _machine_data(_tool(1, length=0.5)))
        assert result.length_sufficient is True

    def test_length_total_none_treated_as_zero(self):
        """Explicit None in length_total must not cause a TypeError."""
        prog_tool = {"tool_number": 1, "diameter": 0.5, "length_total": None}
        result = _validate_tool(prog_tool, _machine_data(_tool(1, length=2.0)))
        assert result.required_length == pytest.approx(0.0)
        assert result.length_sufficient is True


# ---------------------------------------------------------------------------
# 2.  from_tool_call suppresses dimension validation (requirements_complete)
# ---------------------------------------------------------------------------

class TestFromToolCallFlag:
    """Tools detected only from a T-call (no CAM header) must not fail on dimensions."""

    def test_from_tool_call_tool_with_wrong_diameter_still_passes(self):
        """requirements_complete=False → diameter_match is not enforced."""
        prog_tool = _program_tool(5, diameter=0.75, from_tool_call=True)
        machine_data = _machine_data(_tool(5, diameter=0.25))  # Wrong diameter
        result = _validate_tool(
            prog_tool,
            machine_data,
            validate_diameter=True,
            validate_length=True,
        )
        assert result.available is True
        assert result.requirements_complete is False
        # Diameter check still runs but shouldn't be flagged as a hard failure
        # because requirements_complete is False — the caller decides how to treat it.

    def test_cam_header_tool_requirements_complete_true(self):
        """A tool from the CAM header (from_tool_call=False) is fully validated."""
        prog_tool = _program_tool(1, from_tool_call=False)
        result = _validate_tool(prog_tool, _machine_data(_tool(1)))
        assert result.requirements_complete is True

    def test_from_tool_call_missing_key_defaults_to_false(self):
        """Absence of from_tool_call key must default to requirements_complete=True."""
        prog_tool = {"tool_number": 1, "diameter": 0.5, "length_total": 3.0}
        result = _validate_tool(prog_tool, _machine_data(_tool(1)))
        assert result.requirements_complete is True


# ---------------------------------------------------------------------------
# 3.  Type-safe tool number comparison (str vs int)
# ---------------------------------------------------------------------------

class TestToolNumberComparison:
    """Tool numbers from Telnet may come back as strings; comparison must be int-safe."""

    def test_string_tool_number_in_machine_data_matches(self):
        """Machine tool table entry with str tool_number must match int program tool."""
        prog_tool = _program_tool(3, diameter=0.5, length_total=3.0)
        machine_data = _machine_data({"tool_number": "3", "diameter": 0.5, "length": 4.0})
        result = _validate_tool(prog_tool, machine_data)
        assert result.available is True

    def test_tool_not_found_returns_available_false(self):
        """Missing tool must return available=False with a clear warning."""
        prog_tool = _program_tool(99, diameter=0.5, length_total=3.0)
        result = _validate_tool(prog_tool, _machine_data(_tool(1), _tool(2)))
        assert result.available is False
        assert any("T99" in w for w in result.warnings)

    def test_available_tools_listed_in_warning(self, caplog):
        """Available tools are logged as a warning when a tool is not found."""
        import logging
        prog_tool = _program_tool(7)
        with caplog.at_level(logging.WARNING):
            result = _validate_tool(prog_tool, _machine_data(_tool(1), _tool(3)))
        assert result.available is False
        # Available tool numbers must appear in the logger.warning output
        combined = caplog.text
        assert "1" in combined
        assert "3" in combined


# ---------------------------------------------------------------------------
# 4.  Diameter and length validation logic
# ---------------------------------------------------------------------------

class TestDiameterValidation:
    def test_exact_diameter_match_passes(self):
        prog_tool = _program_tool(1, diameter=0.5)
        result = _validate_tool(prog_tool, _machine_data(_tool(1, diameter=0.5)))
        assert result.diameter_match is True

    def test_diameter_mismatch_beyond_tolerance_fails(self):
        prog_tool = _program_tool(1, diameter=0.5)
        result = _validate_tool(
            prog_tool,
            _machine_data(_tool(1, diameter=0.6)),
            diameter_tolerance=0.001,
        )
        assert result.diameter_match is False
        assert any("diameter" in w.lower() for w in result.warnings)

    def test_diameter_within_tolerance_passes(self):
        prog_tool = _program_tool(1, diameter=0.5)
        result = _validate_tool(
            prog_tool,
            _machine_data(_tool(1, diameter=0.5002)),
            diameter_tolerance=0.001,
        )
        assert result.diameter_match is True

    def test_validate_diameter_false_skips_check(self):
        prog_tool = _program_tool(1, diameter=0.5)
        result = _validate_tool(
            prog_tool,
            _machine_data(_tool(1, diameter=1.0)),  # Very wrong
            validate_diameter=False,
        )
        assert result.diameter_match is True


class TestLengthValidation:
    def test_machine_length_exceeds_required_passes(self):
        # In gcode_defaults mode (default), machine only needs to be >= required length.
        prog_tool = _program_tool(1, length_total=3.0)
        result = _validate_tool(prog_tool, _machine_data(_tool(1, length=4.0)))
        assert result.length_sufficient is True

    def test_machine_length_too_short_fails(self):
        prog_tool = _program_tool(1, length_total=4.0)
        result = _validate_tool(
            prog_tool,
            _machine_data(_tool(1, length=2.0)),
            length_tolerance_minus=0.0,
            length_tolerance_plus=0.5,
        )
        assert result.length_sufficient is False
        assert any("length" in w.lower() for w in result.warnings)

    def test_validate_length_false_skips_check(self):
        prog_tool = _program_tool(1, length_total=10.0)
        result = _validate_tool(
            prog_tool,
            _machine_data(_tool(1, length=0.1)),  # Way too short
            validate_length=False,
        )
        assert result.length_sufficient is True

    def test_length_result_reports_machine_and_required(self):
        prog_tool = _program_tool(1, length_total=3.5)
        result = _validate_tool(prog_tool, _machine_data(_tool(1, length=4.0)))
        assert result.required_length == pytest.approx(3.5)
        assert result.machine_tool_data["length"] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# 5.  GCodeParser extract_tools — length_total field contract
# ---------------------------------------------------------------------------

SAMPLE_GCODE = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)
(T02 D=0.5 CR=0 - ZMIN=-0.125 - 1/2 END MILL - L=1.0/4.0)

N25 G100 T01 X0 Y0 G43 Z0 H01 S5000 M3
N30 G100 T02 X0 Y0 G43 Z0 H02 S4000 M3
M30
"""


class TestGCodeParserLengthTotal:
    """GCodeParser.extract_tools must produce length_total, not length."""

    def test_extract_tools_produces_length_total_key(self):
        parser = GCodeParser(SAMPLE_GCODE)
        tools = parser.extract_tools()
        assert len(tools) == 2
        for tool in tools:
            assert "length_total" in tool, (
                f"Tool {tool.get('tool_number')} missing length_total key"
            )

    def test_length_key_absent_from_extract_tools(self):
        """There must be no bare 'length' key — callers must use length_total."""
        parser = GCodeParser(SAMPLE_GCODE)
        tools = parser.extract_tools()
        for tool in tools:
            assert "length" not in tool, (
                f"Tool {tool.get('tool_number')} has ambiguous 'length' key; "
                "should be 'length_total'"
            )

    def test_length_total_values_parsed_correctly(self):
        parser = GCodeParser(SAMPLE_GCODE)
        tools = {t["tool_number"]: t for t in parser.extract_tools()}
        assert tools[1]["length_total"] == pytest.approx(3.609)
        assert tools[2]["length_total"] == pytest.approx(4.0)

    def test_from_tool_call_false_for_header_tools(self):
        parser = GCodeParser(SAMPLE_GCODE)
        tools = parser.extract_tools()
        for tool in tools:
            assert tool.get("from_tool_call") is False

    def test_fallback_tools_have_from_tool_call_true(self):
        """Tools detected only from T-calls (no header) must set from_tool_call=True."""
        gcode_no_header = """
N10 G100 T05 X0 Y0 G43 Z0 H05 S3000 M3
M30
"""
        parser = GCodeParser(gcode_no_header)
        tools = parser.extract_tools()
        t05 = next((t for t in tools if t["tool_number"] == 5), None)
        assert t05 is not None
        assert t05["from_tool_call"] is True
        assert t05["length_total"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 6.  Pipeline integration: parse_gcode → _validate_tool
# ---------------------------------------------------------------------------

class TestGCodeToValidationPipeline:
    """End-to-end: gcode parser output feeds directly into _validate_tool."""

    def test_required_length_from_gcode_header_matches_machine(self):
        """Simulate the sync validation path: parse NC then validate against machine."""
        from app.parsers.gcode_parser import parse_gcode

        nc = """
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)
N25 G100 T01 X0 Y0 G43 Z0 H01 S5000 M3
M30
"""
        parsed = parse_gcode(nc)
        assert parsed["tools"], "Parser should find at least one tool"

        prog_tool = parsed["tools"][0]
        machine_data = _machine_data(_tool(1, diameter=0.25, length=4.0))

        result = _validate_tool(prog_tool, machine_data)

        assert result.available is True
        assert result.required_length == pytest.approx(3.609), (
            "required_length must come from length_total in the G-code header, not 0.0"
        )
        # gcode_defaults mode: machine length (4.0) >= required (3.609) → sufficient
        assert result.length_sufficient is True

    def test_tool_call_only_tool_is_availability_checked(self):
        """A T-call-only tool must be found in the machine table but not dimension-checked."""
        from app.parsers.gcode_parser import parse_gcode

        nc = """
N10 G100 T07 X0 Y0 G43 Z0 H07 S3000 M3
M30
"""
        parsed = parse_gcode(nc)
        t07 = next((t for t in parsed["tools"] if t["tool_number"] == 7), None)
        assert t07 is not None

        result = _validate_tool(t07, _machine_data(_tool(7, diameter=1.0, length=5.0)))

        assert result.available is True
        assert result.requirements_complete is False


# ---------------------------------------------------------------------------
# 7.  Re-export contract: validate_program and upload_program importable
#     from app.api.programs (ftp_sync_service depends on these at runtime)
# ---------------------------------------------------------------------------

class TestProgramsModuleReExports:
    """Ensure ftp_sync_service import paths never break silently."""

    def test_validate_program_importable_from_programs(self):
        from app.api.programs import validate_program
        import asyncio
        assert asyncio.iscoroutinefunction(validate_program), (
            "validate_program must be an async function"
        )

    def test_upload_program_importable_from_programs(self):
        from app.api.programs import upload_program
        import asyncio
        assert asyncio.iscoroutinefunction(upload_program), (
            "upload_program must be an async function"
        )

    def test_program_validate_request_importable_from_programs(self):
        """ProgramValidateRequest used alongside validate_program in ftp_sync_service."""
        from app.api.programs import ProgramValidateRequest
        from pydantic import BaseModel
        assert issubclass(ProgramValidateRequest, BaseModel)
        assert "gcode_content" in ProgramValidateRequest.model_fields
