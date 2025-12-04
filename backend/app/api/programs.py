"""Program validation and upload endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.db.base import get_db
from app.models.machine import Machine
from app.models.program import Program, ProgramDeployment
from app.parsers.gcode_parser import parse_gcode
from app.parsers.posni_parser import get_work_offset
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient
from app.schemas.program import (
    ProgramUploadRequest,
    ProgramUploadResponse,
    ProgramResponse,
    ProgramListItem,
    ProgramDeploymentCreate,
    ProgramDeploymentResponse,
)
from app.services.program_service import ProgramService


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
                errors.append(
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
    tolerance_diameter = 0.001  # ±0.001" for diameter
    tolerance_length = 0.01     # ±0.01" for length

    # Find tool in machine tool table
    machine_tools = machine_tool_data.get("tools", [])
    machine_tool = None
    for t in machine_tools:
        if t["tool_number"] == tool_num:
            machine_tool = t
            break

    # Tool not found in machine
    if not machine_tool:
        return ToolValidationResult(
            tool_number=tool_num,
            required_diameter=program_tool["diameter"],
            required_corner_radius=program_tool["corner_radius"],
            required_length=program_tool["length_total"],
            available=False,
            diameter_match=False,
            corner_radius_match=False,
            length_sufficient=False,
            machine_tool_data={},
            warnings=[f"Tool T{tool_num:02d} not found in machine tool table"]
        )

    # Validate diameter (within tolerance)
    machine_diameter = machine_tool.get("diameter", 0)
    diameter_diff = abs(machine_diameter - program_tool["diameter"])
    diameter_match = diameter_diff <= tolerance_diameter

    # Validate length (machine tool must be >= required length)
    machine_length = machine_tool.get("length", 0)
    length_sufficient = machine_length >= program_tool["length_total"]

    # TODO: Corner radius validation requires additional machine data
    corner_radius_match = True  # Assume OK for now

    warnings = []
    if not diameter_match:
        warnings.append(
            f"Diameter mismatch: need {program_tool['diameter']:.4f}\", "
            f"have {machine_diameter:.4f}\" (diff: {diameter_diff:.4f}\")"
        )
    if not length_sufficient:
        warnings.append(
            f"Tool too short: need {program_tool['length_total']:.4f}\", "
            f"have {machine_length:.4f}\""
        )

    return ToolValidationResult(
        tool_number=tool_num,
        required_diameter=program_tool["diameter"],
        required_corner_radius=program_tool["corner_radius"],
        required_length=program_tool["length_total"],
        available=True,
        diameter_match=diameter_match,
        corner_radius_match=corner_radius_match,
        length_sufficient=length_sufficient,
        machine_tool_data={
            "tool_name": machine_tool.get("tool_name", ""),
            "diameter": machine_diameter,
            "length": machine_length,
        },
        warnings=warnings
    )


def _validate_wcs_offset(
    program_wcs: Dict[str, Any],
    machine_position_data: str
) -> WCSValidationResult:
    """
    Validate WCS offset against machine's work coordinate system.

    Args:
        program_wcs: Expected WCS offset from G-code
        machine_position_data: POSNI1.NC file content from machine (as string)

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
    # Convert string to bytes for parser
    actual_offset = get_work_offset(machine_position_data.encode('utf-8'), work_offset)

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


# ========== PROGRAM LIBRARY ENDPOINTS ==========

@router.get("/programs", response_model=List[ProgramListItem])
async def list_programs(
    skip: int = 0,
    limit: int = 100,
    filename_filter: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    List all programs in the library.

    Query params:
    - filename_filter: Filter by filename (partial match)
    - active_only: Only show active versions (default: True)
    """
    query = db.query(Program)

    if active_only:
        query = query.filter(Program.is_active == True)

    if filename_filter:
        query = query.filter(Program.original_filename.ilike(f"%{filename_filter}%"))

    query = query.order_by(Program.first_seen_at.desc())
    programs = query.offset(skip).limit(limit).all()

    return programs


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(program_id: int, db: Session = Depends(get_db)):
    """Get detailed program information."""
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.get("/programs/by-filename/{filename}", response_model=List[ProgramResponse])
async def get_program_versions(filename: str, db: Session = Depends(get_db)):
    """Get all versions of a program by filename, ordered by version number (newest first)."""
    programs = db.query(Program).filter(
        Program.original_filename == filename
    ).order_by(Program.version_number.desc()).all()

    if not programs:
        raise HTTPException(status_code=404, detail="No programs found with that filename")

    return programs


# ========== PROGRAM UPLOAD ==========

@router.post("/programs/upload", response_model=ProgramUploadResponse)
async def upload_program(
    request: ProgramUploadRequest,
    db: Session = Depends(get_db)
):
    """
    Upload a new NC program.

    Flow:
    1. Parse G-code and extract metadata
    2. Compute content hash
    3. Check if program already exists (by hash)
    4. If new: create Program record with next version number
    5. If deploying: create deployment record

    Returns:
        - program: The program record (new or existing)
        - is_new_version: Whether this is a new version
        - deployment: Deployment record (if deployed)
    """
    try:
        service = ProgramService(db)
        result = service.upload_program(
            gcode_content=request.gcode_content,
            original_filename=request.original_filename,
            machine_id=request.machine_id,
            deployed_filename=request.deployed_filename,
            validate=request.validate_before_upload
        )

        return ProgramUploadResponse(
            program=result["program"],
            is_new_version=result["is_new_version"],
            deployment=result["deployment"],
            validation_results=result["validation_results"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ========== DEPLOYMENT MANAGEMENT ==========

@router.post("/programs/{program_id}/deploy", response_model=ProgramDeploymentResponse)
async def deploy_program(
    program_id: int,
    request: ProgramDeploymentCreate,
    db: Session = Depends(get_db)
):
    """
    Deploy an existing program to a machine.

    This creates a deployment record linking the program to the machine with the specified O-number.
    """
    try:
        service = ProgramService(db)
        deployment = service.deploy_program(
            program_id=program_id,
            machine_id=request.machine_id,
            deployed_filename=request.deployed_filename,
            validate=request.validate_before_upload
        )
        return deployment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.get("/machines/{machine_id}/deployments", response_model=List[ProgramDeploymentResponse])
async def list_machine_deployments(
    machine_id: int,
    current_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all program deployments for a machine.

    Shows full history of what programs were deployed when.
    current_only: Only show currently deployed programs (is_current=True)
    """
    query = db.query(ProgramDeployment).filter(
        ProgramDeployment.machine_id == machine_id
    )

    if current_only:
        query = query.filter(ProgramDeployment.is_current == True)

    query = query.order_by(ProgramDeployment.deployed_at.desc())
    deployments = query.offset(skip).limit(limit).all()

    return deployments


@router.get("/programs/{program_id}/deployments", response_model=List[ProgramDeploymentResponse])
async def list_program_deployments(
    program_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all deployments of a specific program.

    Shows where this program has been deployed across all machines.
    """
    query = db.query(ProgramDeployment).filter(
        ProgramDeployment.program_id == program_id
    ).order_by(ProgramDeployment.deployed_at.desc())

    deployments = query.offset(skip).limit(limit).all()
    return deployments
