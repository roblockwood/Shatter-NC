"""Program validation and upload endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.db.base import get_db
from app.models.machine import Machine
from app.models.program import Program, ProgramDeployment
from app.parsers.gcode_parser import parse_gcode
# Note: get_work_offset from posni_parser is deprecated - use parse_posni_v2 instead
from app.clients.ftp_client import CNCFtpClient
from app.api import websocket as websocket_api
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
    validate_diameter: bool = True
    validate_length: bool = True
    requirements_complete: bool = True
    tolerance_source: str = "gcode_defaults"
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
        }

    # Initialize validation response
    warnings = []
    errors = []
    tools_validation = {}
    wcs_validation = None
    
    # Always fetch machine tool data (even if no tools in NC)
    # Tool data is sourced from WebSocket cache populated by Telnet polling.
    # Brother HTTP endpoints do not provide tool table data.
    machine_tool_data = {}
    machine_tool_fetch_failed = False
    cached_status = None
    
    if websocket_api.websocket_manager:
        try:
            cached_status = websocket_api.websocket_manager.get_machine_status(machine.id)
            if cached_status and "tools" in cached_status and cached_status["tools"]:
                # Use cached tools from Telnet polling
                machine_tool_data = {"tools": cached_status["tools"]}
                logger.info(f"Machine {machine.id} - VALIDATE: Using {len(cached_status['tools'])} cached tools from WebSocket cache")
            else:
                logger.warning(f"Machine {machine.id} - VALIDATE: WebSocket cache empty/missing tools (ws_manager={'set' if websocket_api.websocket_manager else 'None'}, cached_status_keys={list((cached_status or {}).keys())}, tools_count={len((cached_status or {}).get('tools', []))})")
        except Exception as e:
            machine_tool_fetch_failed = True
            logger.warning(f"Machine {machine.id} - Error accessing WebSocket cache: {e}")
    
    # Tool data is ONLY available via Telnet (port 10000, Protocol Type 2).
    # First try the same polling-service refresh path that feeds the ATC card/WebSocket,
    # then fall back to a direct Telnet read for this request.
    if not machine_tool_data.get("tools"):
        logger.warning(f"Machine {machine.id} - No cached tool data available; attempting polling-service tool refresh for validation")
        try:
            from app.api import status as status_api

            if status_api.polling_service:
                for attempt in range(2):
                    refreshed_tool_data = await status_api.polling_service.refresh_tool_data(machine.id)
                    refreshed_tools = (refreshed_tool_data or {}).get("tools", [])
                    if refreshed_tools:
                        machine_tool_data = {"tools": refreshed_tools}
                        logger.debug(
                            f"Machine {machine.id} - Loaded {len(refreshed_tools)} tools via polling-service refresh for validation (attempt {attempt + 1})"
                        )
                        break
        except Exception as e:
            logger.warning(f"Machine {machine.id} - Polling-service refresh for validation failed: {e}")

    if not machine_tool_data.get("tools"):
        logger.warning(f"Machine {machine.id} - Polling-service refresh had no tools, fetching directly via Telnet for validation")
        try:
            from app.clients.telnet_client import create_fresh_connection
            from app.parsers.atctl_parser_v2 import parse_atctl_v2
            from app.parsers.tolni_parser_v2 import parse_tolni_v2

            tool_telnet_client = None
            try:
                tool_telnet_client = await create_fresh_connection(
                    ip_address=machine.ip_address,
                    port=10000,
                    timeout=10,
                )

                # Read tool table first (diameter/length/name)
                tool_table_content = await tool_telnet_client.get_tool_table_data(units=machine.units, verbose=False)
                if not tool_table_content:
                    # Force one fresh reconnect and retry for transient sessions
                    await tool_telnet_client.disconnect()
                    tool_telnet_client = await create_fresh_connection(
                        ip_address=machine.ip_address,
                        port=10000,
                        timeout=10,
                    )
                    tool_table_content = await tool_telnet_client.get_tool_table_data(units=machine.units, verbose=False)

                # Read ATC pot mappings
                control_version = machine.control_version if machine.control_version in ("C00", "D00") else None
                atc_data = await tool_telnet_client.get_atc_magazine_data(control_version=control_version, verbose=False)

                if tool_table_content and atc_data:
                    tool_table_parsed = parse_tolni_v2(
                        tool_table_content.encode('utf-8'),
                        units=machine.units,
                        control_version=control_version,
                    )
                    atc_parsed = parse_atctl_v2(atc_data.encode('utf-8'), control_version=control_version)

                    # Build lookup from tool table
                    tool_lookup = {}
                    for tool in tool_table_parsed.get("tools", []):
                        tool_num = tool.get("tool_number")
                        if tool_num:
                            tool_lookup[tool_num] = tool

                    merged_tools = []
                    for atc_tool in atc_parsed.get("tools", []):
                        tool_num = atc_tool.get("tool_number")
                        if tool_num and tool_num > 0 and tool_num != 255 and tool_num in tool_lookup:
                            tol_tool = tool_lookup[tool_num]
                            merged_tools.append(
                                {
                                    "pot_number": atc_tool.get("pot_number"),
                                    "tool_number": tool_num,
                                    "tool_name": tol_tool.get("tool_name"),
                                    "diameter": tol_tool.get("diameter"),
                                    "length": tol_tool.get("length"),
                                    "group": atc_tool.get("group"),
                                    "life": None,
                                    "tool_type": atc_tool.get("tool_type"),
                                    "color": atc_tool.get("color"),
                                }
                            )

                    machine_tool_data = {"tools": merged_tools}
                    logger.debug(f"Machine {machine.id} - Fetched {len(merged_tools)} tools via direct Telnet fallback for validation")

                    # Best effort: update websocket cache so subsequent validations can reuse cached tools
                    try:
                        if websocket_api.websocket_manager and merged_tools:
                            current = websocket_api.websocket_manager.get_machine_status(machine.id) or {}
                            merged_status = {**current, "machine_id": machine.id, "tools": merged_tools}
                            await websocket_api.websocket_manager.broadcast_status(merged_status)
                    except Exception:
                        pass
                else:
                    machine_tool_fetch_failed = True
                    logger.warning(f"Machine {machine.id} - Direct Telnet fallback returned incomplete tool data (table={bool(tool_table_content)}, atc={bool(atc_data)})")
            finally:
                if tool_telnet_client:
                    await tool_telnet_client.disconnect()
        except Exception as e:
            machine_tool_fetch_failed = True
            logger.warning(f"Machine {machine.id} - Direct Telnet fallback for tool validation failed: {e}")

    # Validate tools
    if parsed["tools"]:
        # Validate each tool using appropriate tolerance source
        for tool in parsed["tools"]:
            tool_num = tool["tool_number"]
            result = _validate_tool(
                tool,
                machine_tool_data,
                use_machine_tolerances=machine.use_machine_tool_tolerances,
                validate_diameter=machine.validate_tool_diameter,
                validate_length=machine.validate_tool_length,
                diameter_tolerance=machine.diameter_tolerance,
                length_tolerance_plus=machine.length_tolerance_plus,
                length_tolerance_minus=machine.length_tolerance_minus
            )
            tools_validation[tool_num] = result

            # Check each tool's validation result
            if not result.available:
                errors.append(f"Tool T{tool_num:02d} not found in machine tool table")
            else:
                if result.validate_diameter and not result.diameter_match:
                    warnings.append(f"Tool T{tool_num:02d} diameter mismatch")
                if result.validate_length and not result.length_sufficient:
                    errors.append(f"Tool T{tool_num:02d} too short (need {result.required_length:.4f}\", have {result.machine_tool_data.get('length', 0):.4f}\")")
    else:
        # No tools found in NC code
        if machine_tool_fetch_failed:
            # Machine unreachable - add warning
            warnings.append("No tool data in NC program and machine data unavailable")
        else:
            # No tools in NC program
            warnings.append("No tool data found in NC program")

    # Always fetch machine work offsets (even if no WCS in NC)
    # Phase 5: Using Telnet for data reads (FTP deprecated for data, kept only for file transfers)
    position_data = None
    wcs_fetch_failed = False
    telnet_client = None
    try:
        from app.clients.telnet_client import create_fresh_connection
        from app.parsers.posni_parser_v2 import parse_posni_v2

        # Create fresh connection
        telnet_client = await create_fresh_connection(
            ip_address=machine.ip_address,
            port=10000,
            timeout=10
        )
        
        # Use machine.units to select correct data name (POSNI1 vs POSNM1)
        position_data = await telnet_client.get_position_data(units=machine.units, verbose=False)
        
        if not position_data:
            raise Exception("Could not retrieve POSNI1.NC/POSNM1.NC from machine via Telnet (file may not exist or Telnet connection failed)")
        
        # Connection is cleaned up automatically
    except Exception as e:
        # Log Telnet error but don't prevent other validation
        wcs_fetch_failed = True
        import traceback
        error_msg = f"Could not fetch machine WCS data via Telnet: {str(e)}"
        warnings.append(error_msg)
        print(f"WCS Fetch Error: {error_msg}")
        print(traceback.format_exc())
    finally:
        if telnet_client:
            await telnet_client.disconnect()

    # Validate WCS offset
    if parsed["wcs_offset"] and position_data:
        # WCS found in NC code - validate against machine
        wcs_validation = _validate_wcs_offset(
            parsed["wcs_offset"],
            position_data,
            units=machine.units,
            use_machine_tolerances=machine.use_machine_wcs_tolerances,
            tolerance_x=machine.tolerance_x,
            tolerance_y=machine.tolerance_y,
            tolerance_z=machine.tolerance_z
        )

        # Always return WCS validation result (even if not within tolerance)
        if not wcs_validation.within_tolerance:
            # Only include difference values if they exist (may be empty if validation failed early)
            if wcs_validation.difference and all(key in wcs_validation.difference for key in ['x', 'y', 'z']):
                errors.append(
                    f"WCS G{wcs_validation.work_offset} offset outside tolerance: "
                    f"X={wcs_validation.difference['x']:.4f}\", "
                    f"Y={wcs_validation.difference['y']:.4f}\", "
                    f"Z={wcs_validation.difference['z']:.4f}\""
                )
            else:
                # Validation failed but no difference data (e.g., missing E parameter or machine data)
                error_msg = f"WCS G{wcs_validation.work_offset} validation failed"
                if wcs_validation.warnings:
                    error_msg += f": {wcs_validation.warnings[0]}"
                errors.append(error_msg)
    elif not parsed["wcs_offset"]:
        # No WCS in NC code
        if position_data and not wcs_fetch_failed:
            # Machine data available - show machine WCS data
            warnings.append("No WCS offset found in NC program")
            # Get all available WCS offsets from machine and show first one as reference
            # Use schema-based parser v2
            from app.parsers.posni_parser_v2 import parse_posni_v2
            
            parsed_posni = parse_posni_v2(position_data.encode('utf-8'), units=machine.units, control_version=None)
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

    # Normalize remote file path to avoid malformed values like "//O0003.NC"
    # while preserving subfolder paths (e.g. "/PROGRAM/O0003.NC").
    normalized_file_path = "/" + "/".join(
        segment for segment in file_path.replace("\\", "/").split("/") if segment
    )

    # Download file via FTP
    try:
        ftp_client = CNCFtpClient(
            machine.ip_address,
            machine.ftp_port,
            machine.ftp_username,
            machine.ftp_password
        )
        file_bytes = await ftp_client.download_file(normalized_file_path)
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found on machine: {normalized_file_path}"
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
    use_machine_tolerances: bool = False,
    validate_diameter: bool = True,
    validate_length: bool = True,
    diameter_tolerance: float = 0.00025,
    length_tolerance_plus: float = 0.0079,
    length_tolerance_minus: float = 0.0
) -> ToolValidationResult:
    """
    Validate a single tool against machine tool table.

    Args:
        program_tool: Tool requirements from G-code
        machine_tool_data: Tool data from machine
        use_machine_tolerances: If True, use machine tolerances. If False, use G-code defaults (exact match for diameter, length >= required)
        diameter_tolerance: Machine diameter tolerance (±) - only used if use_machine_tolerances=True
        length_tolerance_plus: Machine length tolerance in positive direction (+) - only used if use_machine_tolerances=True
        length_tolerance_minus: Machine length tolerance in negative direction (-) - only used if use_machine_tolerances=True

    Returns:
        ToolValidationResult
    """
    tool_num = program_tool["tool_number"]
    required_length = float(program_tool.get("length_total", 0.0) or 0.0)
    required_diameter = float(program_tool.get("diameter", 0.0) or 0.0)
    requirements_complete = not bool(program_tool.get("from_tool_call", False))

    # Find tool in machine tool table
    # Handle both string and integer tool numbers (type-safe comparison)
    machine_tools = machine_tool_data.get("tools", [])
    machine_tool = None
    for t in machine_tools:
        # Normalize both values to int for comparison
        machine_tool_num = t.get("tool_number")
        if machine_tool_num is not None:
            try:
                # Convert both to int for reliable comparison
                if int(machine_tool_num) == int(tool_num):
                    machine_tool = t
                    break
            except (ValueError, TypeError):
                # If conversion fails, skip this tool
                continue

    # Tool not found in machine
    if not machine_tool:
        # Log detailed debug info for troubleshooting
        logger.warning(
            f"Tool T{tool_num:02d} not found in machine tool table. "
            f"Available tools: {[int(t.get('tool_number', 0)) for t in machine_tools if t.get('tool_number') is not None]}"
        )
        return ToolValidationResult(
            tool_number=tool_num,
            required_diameter=required_diameter,
            required_length=required_length,
            available=False,
            diameter_match=False,
            length_sufficient=False,
            validate_diameter=validate_diameter,
            validate_length=validate_length,
            requirements_complete=requirements_complete,
            tolerance_source="machine_settings" if use_machine_tolerances else "gcode_defaults",
            machine_tool_data={},
            warnings=[f"Tool T{tool_num:02d} not found in machine tool table"]
        )

    machine_diameter = machine_tool.get("diameter", 0)
    machine_length = machine_tool.get("length", 0)
    diameter_diff = abs(machine_diameter - required_diameter)
    
    # Apply tolerances based on mode
    diameter_match = True
    length_sufficient = True

    if validate_diameter and requirements_complete:
        if use_machine_tolerances:
            diameter_match = diameter_diff <= diameter_tolerance
        else:
            diameter_match = diameter_diff < 0.0001

    if validate_length and requirements_complete:
        if use_machine_tolerances:
            length_min = required_length - length_tolerance_minus
            length_max = required_length + length_tolerance_plus
            length_sufficient = length_min <= machine_length <= length_max
        else:
            length_sufficient = machine_length >= required_length

    # Apply tolerances based on mode
    if use_machine_tolerances:
        # Use machine-defined tolerances
        if validate_length and requirements_complete:
            length_min = required_length - length_tolerance_minus
            length_max = required_length + length_tolerance_plus
    else:
        length_min = required_length
        length_max = None

    warnings = []
    if validate_diameter and requirements_complete and not diameter_match:
        if use_machine_tolerances:
            warnings.append(
                f"Diameter mismatch: need {required_diameter:.4f}\", "
                f"have {machine_diameter:.4f}\" (diff: {diameter_diff:.4f}\", tolerance: ±{diameter_tolerance:.5f}\")"
            )
        else:
            warnings.append(
                f"Diameter mismatch: need {required_diameter:.4f}\", "
                f"have {machine_diameter:.4f}\" (exact match required)"
            )
    if validate_length and requirements_complete and not length_sufficient:
        if use_machine_tolerances:
            warnings.append(
                f"Tool length out of tolerance: need {required_length:.4f}\", "
                f"have {machine_length:.4f}\" (acceptable: {length_min:.4f}\" to {length_max:.4f}\")"
            )
        else:
            warnings.append(
                f"Tool too short: need {required_length:.4f}\", "
                f"have {machine_length:.4f}\" (must be ≥ required)"
            )

    return ToolValidationResult(
        tool_number=tool_num,
        required_diameter=required_diameter,
        required_length=required_length,
        available=True,
        diameter_match=diameter_match,
        length_sufficient=length_sufficient,
        validate_diameter=validate_diameter,
        validate_length=validate_length,
        requirements_complete=requirements_complete,
        tolerance_source="machine_settings" if use_machine_tolerances else "gcode_defaults",
        machine_tool_data={
            "tool_name": machine_tool.get("tool_name", ""),
            "diameter": machine_diameter,
            "length": machine_length,
        },
        warnings=warnings,
        diameter_tolerance=diameter_tolerance if (use_machine_tolerances and validate_diameter and requirements_complete) else None,
        length_tolerance_plus=length_tolerance_plus if (use_machine_tolerances and validate_length and requirements_complete) else None,
        length_tolerance_minus=length_tolerance_minus if (use_machine_tolerances and validate_length and requirements_complete) else None,
    )


def _validate_wcs_offset(
    program_wcs: Dict[str, Any],
    machine_position_data: str,
    units: str = 'in',
    use_machine_tolerances: bool = False,
    tolerance_x: float = 0.0394,
    tolerance_y: float = 0.0394,
    tolerance_z: float = 0.0394
) -> WCSValidationResult:
    """
    Validate WCS offset against machine's work coordinate system.

    Args:
        program_wcs: Expected WCS offset from G-code
        machine_position_data: POSNI1.NC file content from machine (as string)
        use_machine_tolerances: If True, use machine tolerances. If False, use E parameter from G-code if present
        tolerance_x: Machine X tolerance (±) - only used if use_machine_tolerances=True
        tolerance_y: Machine Y tolerance (±) - only used if use_machine_tolerances=True
        tolerance_z: Machine Z tolerance (±) - only used if use_machine_tolerances=True

    Returns:
        WCSValidationResult
    """
    work_offset = program_wcs["work_offset"]
    expected = {
        "x": program_wcs["x"],
        "y": program_wcs["y"],
        "z": program_wcs["z"],
    }
    
    # Determine tolerance source
    if use_machine_tolerances:
        # Use machine per-axis tolerances
        final_tolerance_x = tolerance_x
        final_tolerance_y = tolerance_y
        final_tolerance_z = tolerance_z
    else:
        # Use program tolerance (E parameter) if specified, otherwise fail validation
        program_tolerance = program_wcs.get("tolerance")
        if program_tolerance:
            final_tolerance_x = final_tolerance_y = final_tolerance_z = program_tolerance
        else:
            # No E parameter in G-code - this is an error when using G-code mode
            return WCSValidationResult(
                valid=False,
                work_offset=work_offset,
                expected=expected,
                actual={},
                difference={},
                tolerance=0.0,
                within_tolerance=False,
                warnings=["No E parameter found in G-code WCS validation macro - cannot validate without tolerance"]
            )

    # Store the primary tolerance for display
    tolerance = max(final_tolerance_x, final_tolerance_y, final_tolerance_z)

    # Parse POSNI1/POSNM1 to get actual machine offset using schema-based parser v2
    # Use the units parameter to correctly parse the position data (POSNI1 for inches, POSNM1 for millimeters)
    from app.parsers.posni_parser_v2 import parse_posni_v2
    parsed_posni = parse_posni_v2(machine_position_data.encode('utf-8'), units=units, control_version=None)
    work_offsets = parsed_posni.get("work_offsets", {})
    actual_offset = work_offsets.get(work_offset)

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
        difference["x"] <= final_tolerance_x and
        difference["y"] <= final_tolerance_y and
        difference["z"] <= final_tolerance_z
    )

    warnings = []
    if not within_tolerance:
        if difference["x"] > final_tolerance_x:
            warnings.append(f"X axis difference {difference['x']:.4f}\" exceeds tolerance ±{final_tolerance_x}\"")
        if difference["y"] > final_tolerance_y:
            warnings.append(f"Y axis difference {difference['y']:.4f}\" exceeds tolerance ±{final_tolerance_y}\"")
        if difference["z"] > final_tolerance_z:
            warnings.append(f"Z axis difference {difference['z']:.4f}\" exceeds tolerance ±{final_tolerance_z}\"")

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
            deployed_path=request.deployed_path,
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

    # Extract numeric part and build both padded and unpadded filename patterns.
    # The machine may report "O0003" (zero-padded) or "O3" (unpadded), and stored
    # records may use either form depending on how they were registered.  Matching
    # both forms avoids a silent miss that produces "NO DEPLOYMENT DATA" in the UI.
    onumber_match = re.search(r'(\d+)', onumber)
    if not onumber_match:
        raise HTTPException(status_code=400, detail="Invalid O-number format")

    onumber_int = int(onumber_match.group(1))
    onumber_raw = onumber_match.group(1)  # preserve original digits (may be zero-padded)
    # Always represent as exactly 4 digits for the canonical padded form
    onumber_padded = f"{onumber_int:04d}"
    # Build the two filename patterns we want to match
    deployed_filename_padded   = f"O{onumber_padded}.nc"    # "O0003.nc"
    deployed_filename_unpadded = f"O{onumber_int}.nc"       # "O3.nc" (legacy)

    # Query current deployment with program join
    # Order by deployed_at DESC to get the most recent deployment
    from sqlalchemy import or_
    query = db.query(ProgramDeployment).filter(
        ProgramDeployment.machine_id == machine_id,
        or_(
            ProgramDeployment.deployed_filename.ilike(deployed_filename_padded),
            ProgramDeployment.deployed_filename.ilike(deployed_filename_unpadded),
        ),
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

    # If current deployment has a shallow/root path (e.g. "/O0003.NC"), try to recover
    # the canonical full remote path from history for the same machine/program/filename.
    # This prevents re-validation from targeting the wrong file when duplicate O-numbers exist
    # in subfolders (e.g. "/PROGRAM/F1USTD/O0003.NC").
    resolved_deployed_path = deployment.deployed_path
    try:
        def _path_depth(p: str) -> int:
            return len([seg for seg in str(p or "").replace('\\\\', '/').split('/') if seg])

        current_depth = _path_depth(resolved_deployed_path)
        if current_depth <= 1:
            better_path_row = (
                db.query(ProgramDeployment.deployed_path)
                .filter(
                    ProgramDeployment.machine_id == machine_id,
                    ProgramDeployment.program_id == deployment.program_id,
                    ProgramDeployment.deployed_filename.ilike(deployment.deployed_filename),
                    ProgramDeployment.deployed_path.isnot(None),
                )
                .order_by(ProgramDeployment.deployed_at.desc())
                .all()
            )

            for row in better_path_row:
                candidate = row.deployed_path
                if _path_depth(candidate) > current_depth:
                    resolved_deployed_path = candidate
                    break
    except Exception:
        # Best effort only; fall back to stored path.
        resolved_deployed_path = deployment.deployed_path

    # Build response
    response = {
        "deployment": {
            "id": deployment.id,
            "deployed_filename": deployment.deployed_filename,
            "deployed_path": resolved_deployed_path,
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
            or_(
                ProgramDeployment.deployed_filename.ilike(deployed_filename_padded),
                ProgramDeployment.deployed_filename.ilike(deployed_filename_unpadded),
            )
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


# ========== ATC POT OPTIMIZER ==========

class ATCOptimizeRequest(BaseModel):
    """Request body for the ATC pot optimizer."""
    gcode_content: str
    num_pockets: int = 21
    current_assignment: Dict[str, int] = {}  # str(tool_number) → current_pot (actual ATC data)
    pinned_tools: List[int] = []             # tool numbers to keep in their current pots


class ATCAssignmentEntry(BaseModel):
    """Recommended or baseline pot for a single tool."""
    tool_number: int
    pot: int


class ATCOptimizeResponse(BaseModel):
    """Optimised ATC pot assignments derived from an NC program."""
    tool_sequence: List[int]
    unique_tools: List[int]
    tool_change_count: int
    transition_matrix: Dict[str, int]
    baseline_assignment: Dict[str, int]
    optimized_assignment: Dict[str, int]
    baseline_cost: int
    optimized_cost: int
    improvement_pct: float


@router.post("/analyze-atc", response_model=ATCOptimizeResponse)
async def analyze_atc_pot_assignment(request: ATCOptimizeRequest):
    """Recommend optimised ATC pot assignments for a Brother NC program.

    Parses the NC content for tool-change calls (G100 / M6 with T-word),
    then runs a simulated-annealing + 2-opt optimiser to find the pot
    placement that minimises total carousel rotation distance.

    The Brother ATC is a rotary magazine: pocket N is physically adjacent to
    pocket 1, so shortest-path travel is ``min(|p1-p2|, N-|p1-p2|)`` steps.

    Args:
        request.gcode_content: Full NC program text.
        request.num_pockets:   Total pockets on the carousel (default 21).

    Returns:
        ATCOptimizeResponse with baseline vs optimised assignments and the
        percentage reduction in total carousel travel distance.
    """
    from app.parsers.nc_tool_sequence_parser import extract_tool_sequence
    from app.services.atc_optimizer import optimize_atc

    if request.num_pockets < 1 or request.num_pockets > 60:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="num_pockets must be between 1 and 60",
        )

    tool_sequence = extract_tool_sequence(request.gcode_content)

    if not tool_sequence:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No tool-change calls found in the NC program. "
                "Expected G100 T## or M6 T## patterns."
            ),
        )

    try:
        # Convert string-keyed current_assignment to int keys
        current_assignment = {int(k): v for k, v in request.current_assignment.items()} or None
        # Build pinned map: tool_number → its locked pot (must have a known current pot)
        pinned_map = {
            t: current_assignment[t]
            for t in request.pinned_tools
            if current_assignment and t in current_assignment
        } or None
        result = optimize_atc(
            tool_sequence=tool_sequence,
            num_pockets=request.num_pockets,
            current_assignment=current_assignment,
            pinned_tools=pinned_map,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return ATCOptimizeResponse(
        tool_sequence=result["tool_sequence"],
        unique_tools=result["unique_tools"],
        tool_change_count=result["tool_change_count"],
        transition_matrix=result["transition_matrix"],
        baseline_assignment={k.lstrip("T"): v for k, v in result["baseline_assignment"].items()},
        optimized_assignment={k.lstrip("T"): v for k, v in result["optimized_assignment"].items()},
        baseline_cost=result["baseline_cost"],
        optimized_cost=result["optimized_cost"],
        improvement_pct=result["improvement_pct"],
    )
