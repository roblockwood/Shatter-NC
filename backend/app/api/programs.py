"""Program validation and upload endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.db.base import get_db
from app.models.machine import Machine
from app.parsers.gcode_parser import parse_gcode
from app.parsers.posni_parser import get_work_offset
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient


router = APIRouter()


class ProgramValidateRequest(BaseModel):
    """Request to validate a G-code program before upload."""
    gcode_content: str


class ToolValidationResult(BaseModel):
    """Validation result for a single tool."""
    tool_number: int
    required_diameter: float
    required_corner_radius: float
    required_length: float
    available: bool
    diameter_match: bool = False
    corner_radius_match: bool = False
    length_sufficient: bool = False
    machine_tool_data: Dict[str, Any] = {}
    warnings: List[str] = []


class WCSValidationResult(BaseModel):
    """Validation result for WCS offset."""
    valid: bool
    work_offset: int  # 54 = G54, etc.
    expected: Dict[str, float]
    actual: Dict[str, float] = {}
    difference: Dict[str, float] = {}
    tolerance: float
    within_tolerance: bool = False
    warnings: List[str] = []


class ProgramValidationResponse(BaseModel):
    """Complete validation response."""
    valid: bool
    tools: Dict[int, ToolValidationResult]
    wcs_offset: Optional[WCSValidationResult]
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]


@router.post("/{machine_id}/programs/validate", response_model=ProgramValidationResponse)
async def validate_program(
    machine_id: int,
    request: ProgramValidateRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a G-code program against a machine's configuration.

    Checks:
    - Tool availability (number, diameter, corner radius, length)
    - WCS offset matches (if specified in program)

    Args:
        machine_id: Target machine ID
        request: G-code content to validate

    Returns:
        Validation results with warnings and errors
    """
    # Get machine from database
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine {machine_id} not found"
        )

    # Parse G-code
    try:
        parsed = parse_gcode(request.gcode_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse G-code: {str(e)}"
        )

    # Initialize validation response
    warnings = []
    errors = []
    tools_validation = {}
    wcs_validation = None

    # Validate tools
    if parsed["tools"]:
        try:
            # Fetch machine tool data via HTTP
            http_client = CNCHttpClient(machine.ip_address, machine.http_port)
            machine_tool_data = http_client.get_tool_data()

            # Validate each tool
            for tool in parsed["tools"]:
                tool_num = tool["tool_number"]
                result = _validate_tool(tool, machine_tool_data)
                tools_validation[tool_num] = result

                if not result.available:
                    errors.append(f"Tool T{tool_num:02d} not found in machine tool table")
                else:
                    if not result.diameter_match:
                        warnings.append(f"Tool T{tool_num:02d} diameter mismatch")
                    if not result.length_sufficient:
                        errors.append(f"Tool T{tool_num:02d} too short (need {result.required_length:.4f}\", have {result.machine_tool_data.get('length', 0):.4f}\")")

        except Exception as e:
            errors.append(f"Failed to fetch machine tool data: {str(e)}")

    # Validate WCS offset
    if parsed["wcs_offset"]:
        try:
            # Fetch machine work offsets via FTP (POSNI1.NC file)
            ftp_client = CNCFtpClient(
                machine.ip_address,
                machine.ftp_port,
                machine.ftp_username,
                machine.ftp_password
            )
            position_data = await ftp_client.get_position_data()

            wcs_validation = _validate_wcs_offset(parsed["wcs_offset"], position_data)

            if not wcs_validation.within_tolerance:
                warnings.append(
                    f"WCS G{wcs_validation.work_offset} offset outside tolerance: "
                    f"X={wcs_validation.difference['x']:.4f}\", "
                    f"Y={wcs_validation.difference['y']:.4f}\", "
                    f"Z={wcs_validation.difference['z']:.4f}\""
                )

        except Exception as e:
            warnings.append(f"Could not validate WCS offset: {str(e)}")

    # Overall validation status
    is_valid = len(errors) == 0

    return ProgramValidationResponse(
        valid=is_valid,
        tools=tools_validation,
        wcs_offset=wcs_validation,
        warnings=warnings,
        errors=errors,
        metadata={
            "posted_date": parsed["posted_date"],
            "estimated_runtime_seconds": parsed["estimated_runtime_seconds"],
            "tool_count": len(parsed["tools"]),
            "line_count": parsed["line_count"],
            "file_size": parsed["file_size"],
        }
    )


def _validate_tool(
    program_tool: Dict[str, Any],
    machine_tool_data: Dict[str, Any]
) -> ToolValidationResult:
    """
    Validate a single tool against machine tool table.

    Args:
        program_tool: Tool requirements from G-code
        machine_tool_data: Tool data from machine

    Returns:
        ToolValidationResult
    """
    tool_num = program_tool["tool_number"]

    # TODO: Parse machine_tool_data (currently returns raw HTML)
    # For now, assume tool is available if we got data back
    # Real implementation will parse the tool table HTML

    # Placeholder validation
    result = ToolValidationResult(
        tool_number=tool_num,
        required_diameter=program_tool["diameter"],
        required_corner_radius=program_tool["corner_radius"],
        required_length=program_tool["length_total"],
        available=True,  # TODO: Check actual machine data
        diameter_match=True,  # TODO: Compare diameters
        corner_radius_match=True,  # TODO: Compare corner radius
        length_sufficient=True,  # TODO: Compare lengths
        machine_tool_data={},  # TODO: Add parsed machine tool data
        warnings=[]
    )

    # TODO: Add actual validation logic when machine tool parsing is implemented
    result.warnings.append("Tool validation not fully implemented - please verify manually")

    return result


def _validate_wcs_offset(
    program_wcs: Dict[str, Any],
    machine_position_data: bytes
) -> WCSValidationResult:
    """
    Validate WCS offset against machine's work coordinate system.

    Args:
        program_wcs: Expected WCS offset from G-code
        machine_position_data: POSNI1.NC file content from machine

    Returns:
        WCSValidationResult
    """
    work_offset = program_wcs["work_offset"]
    expected = {
        "x": program_wcs["x"],
        "y": program_wcs["y"],
        "z": program_wcs["z"],
    }
    tolerance = program_wcs["tolerance"]

    # Parse POSNI1.NC to get actual machine offset
    actual_offset = get_work_offset(machine_position_data, work_offset)

    if not actual_offset:
        return WCSValidationResult(
            valid=False,
            work_offset=work_offset,
            expected=expected,
            actual={},
            difference={},
            tolerance=tolerance,
            within_tolerance=False,
            warnings=[f"G{work_offset} offset not found in machine data"]
        )

    actual = {
        "x": actual_offset["x"],
        "y": actual_offset["y"],
        "z": actual_offset["z"],
    }

    # Calculate differences
    difference = {
        "x": abs(actual["x"] - expected["x"]),
        "y": abs(actual["y"] - expected["y"]),
        "z": abs(actual["z"] - expected["z"]),
    }

    # Check if within tolerance
    within_tolerance = (
        difference["x"] <= tolerance and
        difference["y"] <= tolerance and
        difference["z"] <= tolerance
    )

    warnings = []
    if not within_tolerance:
        if difference["x"] > tolerance:
            warnings.append(f"X axis difference {difference['x']:.4f}\" exceeds tolerance ±{tolerance}\"")
        if difference["y"] > tolerance:
            warnings.append(f"Y axis difference {difference['y']:.4f}\" exceeds tolerance ±{tolerance}\"")
        if difference["z"] > tolerance:
            warnings.append(f"Z axis difference {difference['z']:.4f}\" exceeds tolerance ±{tolerance}\"")

    result = WCSValidationResult(
        valid=within_tolerance,
        work_offset=work_offset,
        expected=expected,
        actual=actual,
        difference=difference,
        tolerance=tolerance,
        within_tolerance=within_tolerance,
        warnings=warnings
    )

    return result
