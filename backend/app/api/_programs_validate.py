"""Program validation routes and helper functions.

Routes:
    POST /machines/{machine_id}/programs/validate        — validate G-code content
    POST /machines/{machine_id}/programs/validate-file   — download + validate file on machine
"""

import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import status as status_api
from app.api import websocket as websocket_api
from app.api.deps import get_machine_or_404
from app.clients.ftp_client import CNCFtpClient
from app.clients.telnet_client import create_fresh_connection
from app.db.base import get_db
from app.parsers.atctl_parser_v2 import parse_atctl_v2
from app.parsers.gcode_parser import parse_gcode
from app.parsers.posni_parser_v2 import parse_posni_v2
from app.parsers.tolni_parser_v2 import parse_tolni_v2

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ProgramValidateRequest(BaseModel):
    """Request to validate a G-code program before upload."""

    gcode_content: str
    # Pre-fetched tool data from the machine (e.g. provided by the sync service so it
    # only pays the Telnet cost once per run rather than once per file). External HTTP
    # callers simply omit this field.
    prefetched_tool_data: Optional[Dict[str, Any]] = None


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


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_tool(
    program_tool: Dict[str, Any],
    machine_tool_data: Dict[str, Any],
    use_machine_tolerances: bool = False,
    validate_diameter: bool = True,
    validate_length: bool = True,
    diameter_tolerance: float = 0.00025,
    length_tolerance_plus: float = 0.0079,
    length_tolerance_minus: float = 0.0,
) -> ToolValidationResult:
    """
    Validate a single tool against machine tool table.
    """
    tool_number = program_tool["tool_number"]
    required_diameter = program_tool.get("diameter", 0.0)
    required_length = float(program_tool.get("length_total", 0.0) or 0.0)

    if use_machine_tolerances:
        tolerance_source = "machine_settings"
        final_diameter_tolerance = diameter_tolerance
        final_length_tolerance_plus = length_tolerance_plus
        final_length_tolerance_minus = length_tolerance_minus
    else:
        gcode_diameter_tolerance = program_tool.get("diameter_tolerance")
        gcode_length_tolerance = program_tool.get("length_tolerance")
        tolerance_source = "gcode_defaults"
        if gcode_diameter_tolerance is not None:
            final_diameter_tolerance = gcode_diameter_tolerance
            tolerance_source = "gcode_specified"
        else:
            final_diameter_tolerance = diameter_tolerance
        if gcode_length_tolerance is not None:
            final_length_tolerance_plus = gcode_length_tolerance
            final_length_tolerance_minus = 0.0
            if tolerance_source != "gcode_specified":
                tolerance_source = "gcode_specified"
        else:
            final_length_tolerance_plus = length_tolerance_plus
            final_length_tolerance_minus = length_tolerance_minus

    requirements_complete = not bool(program_tool.get("from_tool_call", False))

    machine_tools = machine_tool_data.get("tools", [])
    machine_tool = None
    for t in machine_tools:
        machine_tool_num = t.get("tool_number")
        if machine_tool_num is not None:
            try:
                if int(machine_tool_num) == int(tool_number):
                    machine_tool = t
                    break
            except (ValueError, TypeError):
                continue

    if not machine_tool:
        logger.warning(
            f"Tool T{tool_number:02d} not found in machine tool table. "
            f"Available tools: {[int(t.get('tool_number', 0)) for t in machine_tools if t.get('tool_number') is not None]}"
        )
        return ToolValidationResult(
            tool_number=tool_number,
            required_diameter=required_diameter,
            required_length=required_length,
            available=False,
            diameter_match=False,
            length_sufficient=False,
            machine_tool_data={},
            warnings=[f"Tool T{tool_number:02d} not found in machine tool table"],
            validate_diameter=validate_diameter,
            validate_length=validate_length,
            requirements_complete=requirements_complete,
            tolerance_source=tolerance_source,
            diameter_tolerance=final_diameter_tolerance,
            length_tolerance_plus=final_length_tolerance_plus,
            length_tolerance_minus=final_length_tolerance_minus,
        )

    machine_diameter = machine_tool.get("diameter", 0.0) or 0.0
    machine_length = machine_tool.get("length", 0.0) or 0.0

    warnings: list[str] = []

    diameter_match = True
    if validate_diameter and required_diameter > 0:
        diameter_diff = abs(machine_diameter - required_diameter)
        diameter_match = diameter_diff <= final_diameter_tolerance
        if not diameter_match:
            warnings.append(
                f"Tool T{tool_number:02d} diameter mismatch: "
                f"required {required_diameter:.4f}\", machine {machine_diameter:.4f}\" "
                f"(diff {diameter_diff:.4f}\", tolerance ±{final_diameter_tolerance:.4f}\")"
            )

    length_sufficient = True
    if validate_length and required_length > 0:
        length_diff = machine_length - required_length
        if use_machine_tolerances:
            length_sufficient = -final_length_tolerance_minus <= length_diff <= final_length_tolerance_plus
        else:
            length_sufficient = machine_length >= required_length
        if not length_sufficient:
            warnings.append(
                f"Tool T{tool_number:02d} length issue: "
                f"required {required_length:.4f}\", machine {machine_length:.4f}\" "
                f"(diff {length_diff:+.4f}\", tolerance +{final_length_tolerance_plus:.4f}\"/-{final_length_tolerance_minus:.4f}\")"
            )

    return ToolValidationResult(
        tool_number=tool_number,
        required_diameter=required_diameter,
        required_length=required_length,
        available=True,
        diameter_match=diameter_match,
        length_sufficient=length_sufficient,
        machine_tool_data={
            "tool_number": machine_tool.get("tool_number"),
            "tool_name": machine_tool.get("tool_name"),
            "diameter": machine_diameter,
            "length": machine_length,
            "pot_number": machine_tool.get("pot_number"),
        },
        warnings=warnings,
        validate_diameter=validate_diameter,
        validate_length=validate_length,
        requirements_complete=requirements_complete,
        tolerance_source=tolerance_source,
        diameter_tolerance=final_diameter_tolerance,
        length_tolerance_plus=final_length_tolerance_plus,
        length_tolerance_minus=final_length_tolerance_minus,
    )


def _validate_wcs_offset(
    program_wcs: Dict[str, Any],
    machine_position_data: str,
    units: str = "in",
    use_machine_tolerances: bool = False,
    tolerance_x: float = 0.0394,
    tolerance_y: float = 0.0394,
    tolerance_z: float = 0.0394,
) -> WCSValidationResult:
    """Validate WCS offset against machine's work coordinate system."""
    work_offset = program_wcs["work_offset"]
    expected = {
        "x": program_wcs["x"],
        "y": program_wcs["y"],
        "z": program_wcs["z"],
    }

    if use_machine_tolerances:
        final_tolerance_x = tolerance_x
        final_tolerance_y = tolerance_y
        final_tolerance_z = tolerance_z
    else:
        program_tolerance = program_wcs.get("tolerance")
        if program_tolerance:
            final_tolerance_x = final_tolerance_y = final_tolerance_z = program_tolerance
        else:
            return WCSValidationResult(
                valid=False,
                work_offset=work_offset,
                expected=expected,
                actual={},
                difference={},
                tolerance=0.0,
                within_tolerance=False,
                warnings=[
                    "No E parameter found in G-code WCS validation macro - cannot validate without tolerance"
                ],
            )

    tolerance = max(final_tolerance_x, final_tolerance_y, final_tolerance_z)

    parsed_posni = parse_posni_v2(machine_position_data.encode("utf-8"), units=units, control_version=None)
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
            warnings=[f"G{work_offset} offset not found in machine data"],
        )

    actual = {"x": actual_offset["x"], "y": actual_offset["y"], "z": actual_offset["z"]}

    difference = {
        "x": abs(actual["x"] - expected["x"]),
        "y": abs(actual["y"] - expected["y"]),
        "z": abs(actual["z"] - expected["z"]),
    }

    within_tolerance = (
        difference["x"] <= final_tolerance_x
        and difference["y"] <= final_tolerance_y
        and difference["z"] <= final_tolerance_z
    )

    warnings: list[str] = []
    if not within_tolerance:
        if difference["x"] > final_tolerance_x:
            warnings.append(f"X axis difference {difference['x']:.4f}\" exceeds tolerance ±{final_tolerance_x}\"")
        if difference["y"] > final_tolerance_y:
            warnings.append(f"Y axis difference {difference['y']:.4f}\" exceeds tolerance ±{final_tolerance_y}\"")
        if difference["z"] > final_tolerance_z:
            warnings.append(f"Z axis difference {difference['z']:.4f}\" exceeds tolerance ±{final_tolerance_z}\"")

    return WCSValidationResult(
        valid=within_tolerance,
        work_offset=work_offset,
        expected=expected,
        actual=actual,
        difference=difference,
        tolerance=tolerance,
        within_tolerance=within_tolerance,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/machines/{machine_id}/programs/validate", response_model=ProgramValidationResponse)
async def validate_program(
    machine_id: int,
    request: ProgramValidateRequest,
    db: Session = Depends(get_db),
):
    """Validate a G-code program against a machine's configuration."""

    machine = get_machine_or_404(machine_id, db)

    try:
        parsed = parse_gcode(request.gcode_content)
    except Exception:
        parsed = {
            "tools": [],
            "posted_date": None,
            "estimated_runtime_seconds": 0.0,
            "wcs_offset": None,
            "stock_size": None,
            "line_count": len(request.gcode_content.split("\n")),
            "file_size": len(request.gcode_content.encode("utf-8")),
        }

    warnings: list[str] = []
    errors: list[str] = []
    tools_validation: dict[int, ToolValidationResult] = {}
    wcs_validation: Optional[WCSValidationResult] = None

    machine_tool_data: dict = {}
    machine_tool_fetch_failed = False
    cached_status = None

    if request.prefetched_tool_data is not None:
        machine_tool_data = request.prefetched_tool_data
        if machine_tool_data.get("tools"):
            logger.info(
                f"Machine {machine.id} - VALIDATE: Using {len(machine_tool_data['tools'])} pre-fetched tools (sync run fast path)"
            )
        else:
            machine_tool_fetch_failed = True
            logger.info(
                f"Machine {machine.id} - VALIDATE: Pre-fetched tool data had no tools (machine offline during run)"
            )

    if (
        not machine_tool_data.get("tools")
        and request.prefetched_tool_data is None
        and websocket_api.websocket_manager
    ):
        try:
            cached_status = websocket_api.websocket_manager.get_machine_status(machine.id)
            if cached_status and "tools" in cached_status and cached_status["tools"]:
                machine_tool_data = {"tools": cached_status["tools"]}
                logger.info(
                    f"Machine {machine.id} - VALIDATE: Using {len(cached_status['tools'])} cached tools from WebSocket cache"
                )
            else:
                logger.warning(
                    f"Machine {machine.id} - VALIDATE: WebSocket cache empty/missing tools "
                    f"(ws_manager={'set' if websocket_api.websocket_manager else 'None'}, "
                    f"cached_status_keys={list((cached_status or {}).keys())}, "
                    f"tools_count={len((cached_status or {}).get('tools') or [])})"
                )
        except Exception as e:
            machine_tool_fetch_failed = True
            logger.warning(f"Machine {machine.id} - Error accessing WebSocket cache: {e}")

    polling_service_attempted = False
    if not machine_tool_data.get("tools") and request.prefetched_tool_data is None:
        logger.warning(
            f"Machine {machine.id} - No cached tool data available; attempting polling-service tool refresh for validation"
        )
        try:
            if status_api.polling_service:
                polling_service_attempted = True
                for attempt in range(2):
                    refreshed_tool_data = await status_api.polling_service.refresh_tool_data(machine.id)
                    refreshed_tools = (refreshed_tool_data or {}).get("tools", [])
                    if refreshed_tools:
                        machine_tool_data = {"tools": refreshed_tools}
                        logger.debug(
                            f"Machine {machine.id} - Loaded {len(refreshed_tools)} tools via polling-service refresh "
                            f"for validation (attempt {attempt + 1})"
                        )
                        break
        except Exception as e:
            logger.warning(f"Machine {machine.id} - Polling-service refresh for validation failed: {e}")

    if (
        not machine_tool_data.get("tools")
        and not polling_service_attempted
        and request.prefetched_tool_data is None
    ):
        logger.warning(
            f"Machine {machine.id} - Polling-service refresh had no tools, fetching directly via Telnet for validation"
        )
        try:
            tool_telnet_client = None
            try:
                tool_telnet_client = await create_fresh_connection(
                    ip_address=machine.ip_address,
                    port=10000,
                    timeout=10,
                )

                tool_table_content = await tool_telnet_client.get_tool_table_data(
                    units=machine.units,
                    verbose=False,
                )
                if not tool_table_content:
                    await tool_telnet_client.disconnect()
                    tool_telnet_client = await create_fresh_connection(
                        ip_address=machine.ip_address,
                        port=10000,
                        timeout=10,
                    )
                    tool_table_content = await tool_telnet_client.get_tool_table_data(
                        units=machine.units,
                        verbose=False,
                    )

                control_version = machine.control_version if machine.control_version in ("C00", "D00") else None
                atc_data = await tool_telnet_client.get_atc_magazine_data(
                    control_version=control_version,
                    verbose=False,
                )

                if tool_table_content and atc_data:
                    tool_table_parsed = parse_tolni_v2(
                        tool_table_content.encode("utf-8"),
                        units=machine.units,
                        control_version=control_version,
                    )
                    atc_parsed = parse_atctl_v2(atc_data.encode("utf-8"), control_version=control_version)

                    tool_lookup: dict[int, dict[str, Any]] = {}
                    for tool in tool_table_parsed.get("tools", []):
                        tool_num = tool.get("tool_number")
                        if tool_num:
                            tool_lookup[tool_num] = tool

                    merged_tools: list[dict[str, Any]] = []
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
                    logger.debug(
                        f"Machine {machine.id} - Fetched {len(merged_tools)} tools via direct Telnet fallback for validation"
                    )

                    try:
                        if websocket_api.websocket_manager and merged_tools:
                            current = websocket_api.websocket_manager.get_machine_status(machine.id) or {}
                            merged_status = {**current, "machine_id": machine.id, "tools": merged_tools}
                            await websocket_api.websocket_manager.broadcast_status(merged_status)
                    except Exception:
                        pass
                else:
                    machine_tool_fetch_failed = True
                    logger.warning(
                        f"Machine {machine.id} - Direct Telnet fallback returned incomplete tool data "
                        f"(table={bool(tool_table_content)}, atc={bool(atc_data)})"
                    )
            finally:
                if tool_telnet_client:
                    await tool_telnet_client.disconnect()
        except Exception as e:
            machine_tool_fetch_failed = True
            logger.warning(f"Machine {machine.id} - Direct Telnet fallback for tool validation failed: {e}")

    if parsed["tools"]:
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
                length_tolerance_minus=machine.length_tolerance_minus,
            )
            tools_validation[tool_num] = result

            if not result.available:
                errors.append(f"Tool T{tool_num:02d} not found in machine tool table")
            else:
                if result.validate_diameter and not result.diameter_match:
                    warnings.append(f"Tool T{tool_num:02d} diameter mismatch")
                if result.validate_length and not result.length_sufficient:
                    errors.append(
                        f"Tool T{tool_num:02d} too short (need {result.required_length:.4f}\", have {result.machine_tool_data.get('length', 0):.4f}\")"
                    )
    else:
        if machine_tool_fetch_failed:
            warnings.append("No tool data in NC program and machine data unavailable")
        else:
            warnings.append("No tool data found in NC program")

    position_data = None
    wcs_fetch_failed = False
    if parsed.get("wcs_offset"):
        telnet_client = None
        try:
            telnet_client = await create_fresh_connection(
                ip_address=machine.ip_address,
                port=10000,
                timeout=10,
            )

            position_data = await telnet_client.get_position_data(units=machine.units, verbose=False)

            if not position_data:
                raise Exception(
                    "Could not retrieve POSNI1.NC/POSNM1.NC from machine via Telnet "
                    "(file may not exist or Telnet connection failed)"
                )
        except Exception as e:
            wcs_fetch_failed = True
            import traceback

            error_msg = f"Could not fetch machine WCS data via Telnet: {str(e)}"
            warnings.append(error_msg)
            print(f"WCS Fetch Error: {error_msg}")
            print(traceback.format_exc())
        finally:
            if telnet_client:
                await telnet_client.disconnect()

    if parsed["wcs_offset"] and position_data:
        wcs_validation = _validate_wcs_offset(
            parsed["wcs_offset"],
            position_data,
            units=machine.units,
            use_machine_tolerances=machine.use_machine_wcs_tolerances,
            tolerance_x=machine.tolerance_x,
            tolerance_y=machine.tolerance_y,
            tolerance_z=machine.tolerance_z,
        )

        if not wcs_validation.within_tolerance:
            if wcs_validation.difference and all(key in wcs_validation.difference for key in ["x", "y", "z"]):
                errors.append(
                    f"WCS G{wcs_validation.work_offset} offset outside tolerance: "
                    f"X={wcs_validation.difference['x']:.4f}\", "
                    f"Y={wcs_validation.difference['y']:.4f}\", "
                    f"Z={wcs_validation.difference['z']:.4f}\""
                )
            else:
                error_msg = f"WCS G{wcs_validation.work_offset} validation failed"
                if wcs_validation.warnings:
                    error_msg += f": {wcs_validation.warnings[0]}"
                errors.append(error_msg)
    elif not parsed["wcs_offset"]:
        if position_data and not wcs_fetch_failed:
            warnings.append("No WCS offset found in NC program")

            parsed_posni = parse_posni_v2(position_data.encode("utf-8"), units=machine.units, control_version=None)
            work_offsets = parsed_posni.get("work_offsets", {})

            if work_offsets:
                first_offset_num = 54
                first_offset_data = work_offsets.get(54, {"x": 0.0, "y": 0.0, "z": 0.0})

                wcs_validation = WCSValidationResult(
                    valid=False,
                    work_offset=first_offset_num,
                    expected={"x": 0.0, "y": 0.0, "z": 0.0},
                    actual=first_offset_data,
                    difference={"x": 0.0, "y": 0.0, "z": 0.0},
                    tolerance=max(machine.tolerance_x, machine.tolerance_y, machine.tolerance_z),
                    within_tolerance=False,
                    warnings=["WCS offset not specified in NC program - showing G54 machine data for reference"],
                )
        elif wcs_fetch_failed:
            warnings.append("No WCS data in NC program and machine data unavailable")

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
        },
    )


@router.post("/machines/{machine_id}/programs/validate-file", response_model=ProgramValidationWithContentResponse)
async def validate_file_on_machine(
    machine_id: int,
    file_path: str = Query(..., description="Path to file on machine"),
    db: Session = Depends(get_db),
):
    """
    Validate a file already on the machine by downloading and validating it.
    Returns both validation results AND file content for subsequent deployment.
    """
    machine = get_machine_or_404(machine_id, db)

    normalized_file_path = "/" + "/".join(segment for segment in file_path.replace("\\", "/").split("/") if segment)

    try:
        ftp_client = CNCFtpClient(
            machine.ip_address,
            machine.ftp_port,
            machine.ftp_username,
            machine.ftp_password,
        )
        file_bytes = await ftp_client.download_file(normalized_file_path)
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found on machine: {normalized_file_path}",
            )

        gcode_content = file_bytes.decode("utf-8", errors="replace")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file from machine: {str(e)}",
        )

    req = ProgramValidateRequest(gcode_content=gcode_content)
    validation_result = await validate_program(machine_id, req, db)

    return ProgramValidationWithContentResponse(validation=validation_result, gcode_content=gcode_content)

