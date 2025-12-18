"""Program validation and upload endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
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
    required_length: float
    available: bool
    diameter_match: bool = False
    length_sufficient: bool = False
    machine_tool_data: Dict[str, Any] = {}
    warnings: List[str] = []
    # Tolerance values from machine settings (not from NC file)
    diameter_tolerance: Optional[float] = None
    length_tolerance_plus: Optional[float] = None
    length_tolerance_minus: Optional[float] = None


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


class ProgramValidationWithContentResponse(BaseModel):
    """Validation results with the validated content."""
    validation: ProgramValidationResponse
    gcode_content: str


class DeployValidatedRequest(BaseModel):
    """Request to deploy a file that's already on the machine."""
    deployed_filename: str
    gcode_content: str
    validation_results: dict


@router.post("/machines/{machine_id}/programs/validate", response_model=ProgramValidationResponse)
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

    # Parse G-code (gracefully handle macro files and other non-standard formats)
    try:
        parsed = parse_gcode(request.gcode_content)
    except Exception as e:
        # For macro files or non-standard formats, return empty parse result
        # This allows validation to proceed with empty tool/WCS data
        parsed = {
            "tools": [],
            "posted_date": None,
            "estimated_runtime_seconds": 0.0,
            "wcs_offset": None,
            "stock_size": None,
            "line_count": len(request.gcode_content.split('\n')),
            "file_size": len(request.gcode_content.encode('utf-8')),
            "is_macro_program": False,  # Unknown if parser failed
        }

    # Initialize validation response
    warnings = []
    errors = []
    tools_validation = {}
    wcs_validation = None
    
    # Check if this is a macro program - macros don't have tools/WCS to validate
    is_macro = parsed.get("is_macro_program", False)
    if is_macro:
        warnings.append("Macro program detected - tool and WCS validation not applicable")
    
    # Always fetch machine tool data (even if no tools in NC)
    machine_tool_data = {}
    machine_tool_fetch_failed = False
    try:
        http_client = CNCHttpClient(machine.ip_address, machine.http_port)
        machine_tool_data = http_client.get_tool_data()
    except Exception as e:
        machine_tool_fetch_failed = True
        warnings.append(f"Could not fetch machine tool data: {str(e)}")

    # Validate tools (skip for macro programs)
    if is_macro:
        # Macro programs don't have tools to validate
        pass
    elif parsed["tools"]:
            # Validate each tool using machine tolerances
            for tool in parsed["tools"]:
                tool_num = tool["tool_number"]
                result = _validate_tool(
                    tool,
                    machine_tool_data,
                    diameter_tolerance=machine.diameter_tolerance,
                    length_tolerance_plus=machine.length_tolerance_plus,
                    length_tolerance_minus=machine.length_tolerance_minus
                )
                # Add tolerance values to result for display
                result.diameter_tolerance = machine.diameter_tolerance
                result.length_tolerance_plus = machine.length_tolerance_plus
                result.length_tolerance_minus = machine.length_tolerance_minus
                tools_validation[tool_num] = result

            if not result.available:
                errors.append(f"Tool T{tool_num:02d} not found in machine tool table")
            else:
                if not result.diameter_match:
                    warnings.append(f"Tool T{tool_num:02d} diameter mismatch")
                if not result.length_sufficient:
                    errors.append(f"Tool T{tool_num:02d} too short (need {result.required_length:.4f}\", have {result.machine_tool_data.get('length', 0):.4f}\")")
    else:
        # No tools found in NC code
        if not machine_tool_fetch_failed and len(machine_tool_data) > 0:
            # Machine data available - show available tools
            warnings.append("No tool data found in NC program")
            
            # Create entries for all available machine tools to show what's available
            for tool_num, tool_data in machine_tool_data.items():
                tools_validation[tool_num] = ToolValidationResult(
                    tool_number=tool_num,
                    required_diameter=0.0,  # Not specified in NC
                    required_length=0.0,  # Not specified in NC
                    available=True,
                    diameter_match=False,  # N/A - not specified in NC
                    length_sufficient=False,  # N/A - not specified in NC
                    machine_tool_data=tool_data,
                    warnings=["Tool not referenced in NC program"],
                    diameter_tolerance=machine.diameter_tolerance,
                    length_tolerance_plus=machine.length_tolerance_plus,
                    length_tolerance_minus=machine.length_tolerance_minus
                )
        elif machine_tool_fetch_failed:
            # Machine unreachable - add warning
            warnings.append("No tool data in NC program and machine data unavailable")

    # Always fetch machine work offsets (even if no WCS in NC)
    position_data = None
    wcs_fetch_failed = False
    try:
        ftp_client = CNCFtpClient(
            machine.ip_address,
            machine.ftp_port,
            machine.ftp_username,
            machine.ftp_password
        )
        position_data = await ftp_client.get_position_data()
        
        if not position_data:
            raise Exception("Could not retrieve POSNI1.NC from machine (file may not exist or FTP connection failed)")
    except Exception as e:
        # Log FTP error but don't prevent other validation
        wcs_fetch_failed = True
        import traceback
        error_msg = f"Could not fetch machine WCS data: {str(e)}"
        warnings.append(error_msg)
        print(f"WCS Fetch Error: {error_msg}")
        print(traceback.format_exc())

    # Validate WCS offset (skip for macro programs)
    if is_macro:
        # Macro programs don't have WCS offsets to validate
        pass
    elif parsed["wcs_offset"] and position_data:
        # WCS found in NC code - validate against machine
        wcs_validation = _validate_wcs_offset(
            parsed["wcs_offset"],
            position_data,
            tolerance_x=machine.tolerance_x,
            tolerance_y=machine.tolerance_y,
            tolerance_z=machine.tolerance_z
        )

        # Always return WCS validation result (even if not within tolerance)
        if not wcs_validation.within_tolerance:
            errors.append(
                f"WCS G{wcs_validation.work_offset} offset outside tolerance: "
                f"X={wcs_validation.difference['x']:.4f}\", "
                f"Y={wcs_validation.difference['y']:.4f}\", "
                f"Z={wcs_validation.difference['z']:.4f}\""
            )
    elif not parsed["wcs_offset"]:
        # No WCS in NC code
        if position_data and not wcs_fetch_failed:
            # Machine data available - show machine WCS data
            warnings.append("No WCS offset found in NC program")
            # Get all available WCS offsets from machine and show first one as reference
            from app.parsers.posni_parser import parse_posni
            
            parsed_posni = parse_posni(position_data.encode('utf-8'))
            work_offsets = parsed_posni.get("work_offsets", {})
            
            # Create a validation result showing machine has WCS data but NC doesn't specify
            if work_offsets:
                # Show G54 as default reference
                first_offset_num = 54
                # Keys in work_offsets are INTEGERS (54, 55, etc.), not strings
                first_offset_data = work_offsets.get(54, {"x": 0.0, "y": 0.0, "z": 0.0})
                
                wcs_validation = WCSValidationResult(
                    valid=False,
                    work_offset=first_offset_num,
                    expected={"x": 0.0, "y": 0.0, "z": 0.0},  # Not specified in NC
                    actual=first_offset_data,
                    difference={"x": 0.0, "y": 0.0, "z": 0.0},
                    tolerance=max(machine.tolerance_x, machine.tolerance_y, machine.tolerance_z),
                    within_tolerance=False,
                    warnings=["WCS offset not specified in NC program - showing G54 machine data for reference"]
                )
        elif wcs_fetch_failed:
            # Machine unreachable - add warning
            warnings.append("No WCS data in NC program and machine data unavailable")

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


@router.post("/machines/{machine_id}/programs/validate-file", response_model=ProgramValidationWithContentResponse)
async def validate_file_on_machine(
    machine_id: int,
    file_path: str = Query(..., description="Path to file on machine"),
    db: Session = Depends(get_db)
):
    """
    Validate a file already on the machine by downloading and validating it.
    Returns both validation results AND file content for subsequent deployment.

    Args:
        machine_id: Target machine ID
        file_path: Path to file on machine (e.g., "/O2000.NC")
        db: Database session

    Returns:
        Validation results with the validated content
    """
    # Get machine from database
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine {machine_id} not found"
        )

    # Download file via FTP
    try:
        ftp_client = CNCFtpClient(
            machine.ip_address,
            machine.ftp_port,
            machine.ftp_username,
            machine.ftp_password
        )
        file_bytes = await ftp_client.download_file(file_path)
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found on machine: {file_path}"
            )

        gcode_content = file_bytes.decode('utf-8', errors='replace')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file from machine: {str(e)}"
        )

    # Call existing validate_program logic to ensure identical validation
    request = ProgramValidateRequest(gcode_content=gcode_content)
    validation_result = await validate_program(machine_id, request, db)

    # Return validation results WITH content for deployment
    return ProgramValidationWithContentResponse(
        validation=validation_result,
        gcode_content=gcode_content
    )


def _validate_tool(
    program_tool: Dict[str, Any],
    machine_tool_data: Dict[str, Any],
    diameter_tolerance: float = 0.00025,
    length_tolerance_plus: float = 0.0079,
    length_tolerance_minus: float = 0.0
) -> ToolValidationResult:
    """
    Validate a single tool against machine tool table.

    Args:
        program_tool: Tool requirements from G-code
        machine_tool_data: Tool data from machine
        diameter_tolerance: Machine diameter tolerance (±)
        length_tolerance_plus: Machine length tolerance in positive direction (+)
        length_tolerance_minus: Machine length tolerance in negative direction (-)

    Returns:
        ToolValidationResult
    """
    tool_num = program_tool["tool_number"]

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
            required_length=program_tool["length_total"],
            available=False,
            diameter_match=False,
            length_sufficient=False,
            machine_tool_data={},
            warnings=[f"Tool T{tool_num:02d} not found in machine tool table"]
        )

    # Validate diameter (within tolerance)
    machine_diameter = machine_tool.get("diameter", 0)
    diameter_diff = abs(machine_diameter - program_tool["diameter"])
    diameter_match = diameter_diff <= diameter_tolerance

    # Validate length (machine tool must be within tolerance range)
    # Allows: required - length_tolerance_minus <= machine_length <= required + length_tolerance_plus
    machine_length = machine_tool.get("length", 0)
    required_length = program_tool["length_total"]
    length_min = required_length - length_tolerance_minus
    length_max = required_length + length_tolerance_plus
    length_sufficient = length_min <= machine_length <= length_max

    warnings = []
    if not diameter_match:
        warnings.append(
            f"Diameter mismatch: need {program_tool['diameter']:.4f}\", "
            f"have {machine_diameter:.4f}\" (diff: {diameter_diff:.4f}\", tolerance: ±{diameter_tolerance:.5f}\")"
        )
    if not length_sufficient:
        warnings.append(
            f"Tool length out of tolerance: need {required_length:.4f}\", "
            f"have {machine_length:.4f}\" (acceptable: {length_min:.4f}\" to {length_max:.4f}\")"
        )

    return ToolValidationResult(
        tool_number=tool_num,
        required_diameter=program_tool["diameter"],
        required_length=program_tool["length_total"],
        available=True,
        diameter_match=diameter_match,
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
    machine_position_data: str,
    tolerance_x: float = 0.0394,
    tolerance_y: float = 0.0394,
    tolerance_z: float = 0.0394
) -> WCSValidationResult:
    """
    Validate WCS offset against machine's work coordinate system.

    Args:
        program_wcs: Expected WCS offset from G-code
        machine_position_data: POSNI1.NC file content from machine (as string)
        tolerance_x: Machine X tolerance (±)
        tolerance_y: Machine Y tolerance (±)
        tolerance_z: Machine Z tolerance (±)

    Returns:
        WCSValidationResult
    """
    work_offset = program_wcs["work_offset"]
    expected = {
        "x": program_wcs["x"],
        "y": program_wcs["y"],
        "z": program_wcs["z"],
    }
    # Use program tolerance (E parameter) if specified, otherwise use machine per-axis tolerances
    # Program E parameter applies uniformly to all axes if specified
    program_tolerance = program_wcs.get("tolerance")
    if program_tolerance:
        # Program specifies a uniform tolerance (E parameter)
        tolerance_x = tolerance_y = tolerance_z = program_tolerance

    # Store the primary tolerance for display (use max if different per-axis)
    tolerance = max(tolerance_x, tolerance_y, tolerance_z)

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

    # Check if within tolerance (per-axis tolerances)
    within_tolerance = (
        difference["x"] <= tolerance_x and
        difference["y"] <= tolerance_y and
        difference["z"] <= tolerance_z
    )

    warnings = []
    if not within_tolerance:
        if difference["x"] > tolerance_x:
            warnings.append(f"X axis difference {difference['x']:.4f}\" exceeds tolerance ±{tolerance_x}\"")
        if difference["y"] > tolerance_y:
            warnings.append(f"Y axis difference {difference['y']:.4f}\" exceeds tolerance ±{tolerance_y}\"")
        if difference["z"] > tolerance_z:
            warnings.append(f"Z axis difference {difference['z']:.4f}\" exceeds tolerance ±{tolerance_z}\"")

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

@router.get("", response_model=List[ProgramListItem])
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


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(program_id: int, db: Session = Depends(get_db)):
    """Get detailed program information."""
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.get("/by-filename/{filename}", response_model=List[ProgramResponse])
async def get_program_versions(filename: str, db: Session = Depends(get_db)):
    """Get all versions of a program by filename, ordered by version number (newest first)."""
    programs = db.query(Program).filter(
        Program.original_filename == filename
    ).order_by(Program.version_number.desc()).all()

    if not programs:
        raise HTTPException(status_code=404, detail="No programs found with that filename")

    return programs


# ========== PROGRAM UPLOAD ==========

@router.post("/upload", response_model=ProgramUploadResponse)
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
    5. If deploying: create deployment record with validation

    Returns:
        - program: The program record (new or existing)
        - is_new_version: Whether this is a new version
        - deployment: Deployment record (if deployed)
        - validation_results: Validation results if validation was performed
    """
    try:
        service = ProgramService(db)

        # Perform validation if requested and machine specified
        # Otherwise use validation_results passed in request (pre-computed by frontend)
        validation_results = request.validation_results
        if request.validate_before_upload and request.machine_id and not validation_results:
            # Call the validation endpoint to get full validation results
            validate_request = ProgramValidateRequest(gcode_content=request.gcode_content)
            validation_results = await validate_program(
                machine_id=request.machine_id,
                request=validate_request,
                db=db
            )

        result = service.upload_program(
            gcode_content=request.gcode_content,
            original_filename=request.original_filename,
            machine_id=request.machine_id,
            deployed_filename=request.deployed_filename,
            validate=request.validate_before_upload,
            validation_results=validation_results
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


@router.post("/machines/{machine_id}/programs/deploy-validated")
async def deploy_validated_program(
    machine_id: int,
    request: DeployValidatedRequest,
    db: Session = Depends(get_db)
):
    """
    Create a deployment record for a file already on the machine.

    The file is ALREADY on the machine - we're just creating a database record
    with validation results. This is different from upload which does FTP transfer.

    Args:
        machine_id: Target machine ID
        request: Deployment request with filename, content, and validation results
        db: Database session

    Returns:
        Deployment record
    """
    try:
        service = ProgramService(db)

        # Upload/get program record (creates or retrieves by content hash)
        # Note: No FTP upload happens here - file is already on machine
        result = service.upload_program(
            gcode_content=request.gcode_content,
            original_filename=request.deployed_filename,
            machine_id=machine_id,
            deployed_filename=request.deployed_filename,
            validate=False,  # Already validated
            validation_results=request.validation_results
        )

        return result["deployment"]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


# ========== DEPLOYMENT MANAGEMENT ==========

@router.post("/{program_id}/deploy", response_model=ProgramDeploymentResponse)
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


@router.get("/{program_id}/deployments", response_model=List[ProgramDeploymentResponse])
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


@router.get("/machines/{machine_id}/deployments/by-onumber/{onumber}")
async def get_deployment_by_onumber(
    machine_id: int,
    onumber: str,  # Accept "2000", "O2000", or "O2000.nc"
    include_program: bool = True,
    include_history: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get current deployment info for an O-number file with full program details.

    Accepts flexible O-number formats: "2000", "O2000", "O2000.nc" (case-insensitive).
    Returns deployment record with full program details and validation results.

    If include_history=true, also returns all previous deployments for this O-number.
    """
    import re

    # Extract numeric part: "2000", "O2000", "O2000.nc" -> 2000
    onumber_match = re.search(r'(\d{4})', onumber)
    if not onumber_match:
        raise HTTPException(status_code=400, detail="Invalid O-number format")

    onumber_int = int(onumber_match.group(1))
    deployed_filename_pattern = f"O{onumber_int}.nc"

    # Query current deployment with program join
    # Order by deployed_at DESC to get the most recent deployment
    query = db.query(ProgramDeployment).filter(
        ProgramDeployment.machine_id == machine_id,
        ProgramDeployment.deployed_filename.ilike(deployed_filename_pattern),
        ProgramDeployment.is_current == True
    ).order_by(ProgramDeployment.deployed_at.desc())

    if include_program:
        query = query.options(joinedload(ProgramDeployment.program))

    deployment = query.first()

    if not deployment:
        # Return 200 with null deployment instead of 404
        # This allows the frontend to handle programs running on machine
        # that weren't deployed through the system
        return {
            "deployment": None,
            "program": None
        }

    # Build response
    response = {
        "deployment": {
            "id": deployment.id,
            "deployed_filename": deployment.deployed_filename,
            "deployed_path": deployment.deployed_path,
            "deployed_at": deployment.deployed_at,
            "validation_passed": deployment.validation_passed,
            "validation_results": deployment.validation_results,
        }
    }

    if include_program and deployment.program:
        program = deployment.program
        response["program"] = {
            "id": program.id,
            "original_filename": program.original_filename,
            "version_number": program.version_number,
            "posted_date": program.posted_date,
            "estimated_runtime_seconds": program.estimated_runtime_seconds,
            "program_metadata": program.program_metadata,
            "file_size_bytes": program.file_size_bytes,
            "line_count": program.line_count,
        }

    # Get deployment history if requested
    if include_history:
        history = db.query(ProgramDeployment).filter(
            ProgramDeployment.machine_id == machine_id,
            ProgramDeployment.deployed_filename.ilike(deployed_filename_pattern)
        ).order_by(ProgramDeployment.deployed_at.desc()).all()

        response["history"] = [
            {
                "id": h.id,
                "deployed_at": h.deployed_at,
                "validation_passed": h.validation_passed,
                "replaced_at": h.replaced_at,
                "is_current": h.is_current,
                "program_version": h.program.version_number if h.program else None,
                "original_filename": h.program.original_filename if h.program else None,
            }
            for h in history
        ]

    return response


@router.get("/deployments/{deployment_id}")
async def get_deployment_by_id(
    deployment_id: int,
    db: Session = Depends(get_db)
):
    """Get full deployment details by deployment ID."""

    deployment = db.query(ProgramDeployment).options(
        joinedload(ProgramDeployment.program)
    ).filter(
        ProgramDeployment.id == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment {deployment_id} not found"
        )

    response = {
        "deployment": {
            "id": deployment.id,
            "deployed_filename": deployment.deployed_filename,
            "deployed_path": deployment.deployed_path,
            "deployed_at": deployment.deployed_at,
            "validation_passed": deployment.validation_passed,
            "validation_results": deployment.validation_results,
        }
    }

    if deployment.program:
        program = deployment.program
        response["program"] = {
            "id": program.id,
            "original_filename": program.original_filename,
            "version_number": program.version_number,
            "posted_date": program.posted_date,
            "estimated_runtime_seconds": program.estimated_runtime_seconds,
            "program_metadata": program.program_metadata,
            "file_size_bytes": program.file_size_bytes,
            "line_count": program.line_count,
        }

    return response


@router.get("/machines/{machine_id}/next-onumber")
async def get_next_onumber_fifo(
    machine_id: int,
    filename: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get next available O-number using FIFO allocation (O2000-O3999).

    If filename is provided, check if that file already has an O-number on this machine.
    If yes, return that O-number. If no, allocate a new one.

    Returns the next O-number and indicates if it will replace an existing deployment.
    Uses revolving allocation: O2000-O3999 (2000 capacity), then overwrites oldest.
    """
    import re

    MIN_ONUMBER = 2000
    MAX_ONUMBER = 3999
    MAX_CAPACITY = 2000

    # Verify machine exists
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Check if file already has a deployment on this machine
    # FIFO association: Find the most recent deployment for this filename
    existing_deployment = None
    if filename:
        # FastAPI automatically URL-decodes query parameters
        import urllib.parse
        filename_normalized = urllib.parse.unquote_plus(filename).strip()
        
        # Find programs with this exact filename
        programs_with_filename = db.query(Program).filter(
            Program.original_filename == filename_normalized
        ).all()
        
        # If no exact match, try case-insensitive
        if not programs_with_filename:
            programs_with_filename = db.query(Program).filter(
                func.lower(Program.original_filename) == func.lower(filename_normalized)
            ).all()
        
        # For each program with matching filename, find its most recent deployment
        for program in programs_with_filename:
            deployment = db.query(ProgramDeployment).filter(
                ProgramDeployment.program_id == program.id,
                ProgramDeployment.machine_id == machine_id
            ).order_by(ProgramDeployment.id.desc()).first()
            
            if deployment:
                if not existing_deployment or deployment.id > existing_deployment.id:
                    existing_deployment = deployment

        if existing_deployment:
            # File already deployed - return its O-number (FIFO association)
            try:
                match = re.match(r'O(\d{4})', existing_deployment.deployed_filename, re.IGNORECASE)
                if match:
                    o_num = int(match.group(1))
                    # Force return - this MUST execute
                    result = {
                        "next_onumber": f"O{o_num}.nc",
                        "onumber_int": o_num,
                        "is_replacing": False,
                        "replacement_info": None,
                        "is_redeployment": True
                    }
                    # Log before returning
                    import sys
                    print(f"FIFO SUCCESS: Found existing deployment, returning {result['next_onumber']}", file=sys.stderr)
                    sys.stderr.flush()
                    return result
            except Exception as e:
                import sys
                import traceback
                print(f"FIFO ERROR in return logic: {e}", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                sys.stderr.flush()
                # Continue to allocate new O-number if there's an error
                existing_deployment = None

    # Get all current deployments, ordered by deployed_at (oldest first)
    deployments = db.query(ProgramDeployment).filter(
        ProgramDeployment.machine_id == machine_id,
        ProgramDeployment.is_current == True
    ).order_by(ProgramDeployment.deployed_at.asc()).all()

    # Parse existing O-numbers in range
    existing = {}  # {onumber_int: deployment}
    for d in deployments:
        match = re.match(r'O(\d{4})', d.deployed_filename, re.IGNORECASE)
        if match:
            o_num = int(match.group(1))
            if MIN_ONUMBER <= o_num <= MAX_ONUMBER:
                existing[o_num] = d

    # Find next O-number
    if len(existing) < MAX_CAPACITY:
        # Pool not full - find first available
        for o in range(MIN_ONUMBER, MAX_ONUMBER + 1):
            if o not in existing:
                return {
                    "next_onumber": f"O{o}.nc",
                    "onumber_int": o,
                    "is_replacing": False,
                    "replacement_info": None,
                    "is_redeployment": False
                }

    # Pool full - FIFO replacement (oldest deployment)
    oldest = deployments[0]
    match = re.match(r'O(\d{4})', oldest.deployed_filename, re.IGNORECASE)
    if match:
        o_num = int(match.group(1))
        if MIN_ONUMBER <= o_num <= MAX_ONUMBER:
            return {
                "next_onumber": f"O{o_num}.nc",
                "onumber_int": o_num,
                "is_replacing": True,
                "replacement_info": {
                    "onumber": str(o_num),
                    "deployed_at": oldest.deployed_at.isoformat(),
                    "original_filename": oldest.program.original_filename if oldest.program else "Unknown"
                },
                "is_redeployment": False
            }

    # Fallback
    return {
        "next_onumber": f"O{MIN_ONUMBER}.nc",
        "onumber_int": MIN_ONUMBER,
        "is_replacing": False,
        "replacement_info": None,
        "is_redeployment": False
    }
