"""Tool write routes — ATC operations, tool life, and tool offset.

Routes:
    POST /{machine_id}/status/tools/refresh           — trigger polling refresh
    PUT  /{machine_id}/tools/atc/pot/{pot}/color      — single color change
    PUT  /{machine_id}/tools/atc/colors/batch         — batch color change
    PUT  /{machine_id}/tools/atc/pot/{pot}/tool       — assign tool to pot
    PUT  /{machine_id}/tools/atc/pot/{pot}/type       — change tool type
    DELETE /{machine_id}/tools/atc/pot/{pot}          — remove tool from pot
    PUT  /{machine_id}/tools/spindle                  — change spindle tool
    PUT  /{machine_id}/tools/{tool_number}/life       — set tool life
    PUT  /{machine_id}/tools/{tool_number}/offset     — set tool offset
    PUT  /{machine_id}/macros/{macro_number}          — set macro variable (#500-999)
    PUT  /{machine_id}/tools/measurement-tool         — set macro #920 (measurement tool)
"""
from datetime import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.machine import Machine
from app.api._status_state import (
    BatchColorChangeRequest,
    BatchColorChangeResponse,
    ColorChangeResult,
)
import app.api._status_state as _state
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

MEASUREMENT_TOOL_MACRO = 920


@router.post("/{machine_id}/status/tools/refresh")
async def refresh_tool_data(
    machine_id: int,
    db: Session = Depends(get_db)
):
    """
    Trigger immediate refresh of tool data (tool table and ATC magazine).
    Returns updated tool data.

    This endpoint allows manual refresh of tool data without waiting for the slow polling cycle.
    Useful when tool data may have changed (e.g., after tool changes on the machine).
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not _state.polling_service:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polling service not available",
        )

    try:
        tool_data = await _state.polling_service.refresh_tool_data(machine_id)

        return {
            "machine_id": machine_id,
            "machine_name": db_machine.name,
            "tool_data": tool_data,
            "refreshed_at": datetime.now().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error refreshing tool data for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh tool data: {str(e)}",
        )


@router.put("/{machine_id}/tools/atc/pot/{pot_number}/color")
async def change_tool_color(
    machine_id: int,
    pot_number: int,
    tool_number: int = Query(..., description="Tool number in the pot"),
    color: int = Query(..., description="Color value (0-7)"),
    db: Session = Depends(get_db)
):
    """
    Change tool color in ATC magazine.

    Args:
        machine_id: Machine ID
        pot_number: Pot number (1-99)
        tool_number: Tool number in the pot (for verification)
        color: Color value (0=None, 1=Blue, 2=Red, 3=Purple, 4=Green, 5=Light Blue, 6=Yellow, 7=White)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 1 <= pot_number <= 99:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pot number: {pot_number} (must be 1-99)",
        )

    if not 0 <= color <= 7:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid color value: {color} (must be 0-7)",
        )

    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="tool_color",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        success, status_code = await telnet_client.change_atc_tool(
            operation_type='C',
            magazine_pos=pot_number,
            tool_num=tool_number,
            new_value=color,
            verbose=True
        )

        logger.info(f"Color change result: success={success}, status_code={status_code}")

        from app.services.audit_logger import AuditLogger
        color_names = {0: "None", 1: "Blue", 2: "Red", 3: "Purple", 4: "Green", 5: "Light Blue", 6: "Yellow", 7: "White"}
        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="tool_color",
            operation_details={
                "pot_number": pot_number,
                "tool_number": tool_number,
                "new_color": color,
                "new_color_name": color_names.get(color, "Unknown"),
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data
        )

        if not success:
            logger.error(f"Failed to change tool color for pot {pot_number}, tool {tool_number}, color {color}: {status_desc} (status={status_code})")
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to change tool color: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63") if status_code else False
            }
            if status_data:
                error_response["machine_state"] = status_data
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        if _state.polling_service:
            try:
                await _state.polling_service.refresh_tool_data(machine_id)
                logger.debug(f"Refreshed tool data for machine {machine_id} after color change")
            except Exception as e:
                logger.warning(f"Failed to refresh tool data after color change for machine {machine_id}: {e}")

        return {
            "success": True,
            "pot_number": pot_number,
            "tool_number": tool_number,
            "color": color,
            "color_name": color_names.get(color, "Unknown"),
            "message": f"Tool color changed to {color_names.get(color, 'Unknown')}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing tool color for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{machine_id}/tools/atc/colors/batch", response_model=BatchColorChangeResponse)
async def batch_change_tool_colors(
    machine_id: int,
    request: BatchColorChangeRequest,
    db: Session = Depends(get_db)
):
    """
    Batch change tool colors in ATC magazine.

    Validates machine state once, then processes all changes sequentially.
    This is more efficient than making multiple individual requests.

    Args:
        machine_id: Machine ID
        request: Batch request containing list of color changes
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not request.changes:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="No changes provided",
        )

    for change in request.changes:
        if not 1 <= change.pot_number <= 99:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pot number: {change.pot_number} (must be 1-99)",
            )
        if not 0 <= change.color <= 7:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid color value: {change.color} (must be 0-7)",
            )

    telnet_client = None
    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="tool_color",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
        from app.services.audit_logger import AuditLogger

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        color_names = {0: "None", 1: "Blue", 2: "Red", 3: "Purple", 4: "Green", 5: "Light Blue", 6: "Yellow", 7: "White"}
        results = []
        successful = 0
        failed = 0

        for change in request.changes:
            try:
                success, status_code = await telnet_client.change_atc_tool(
                    operation_type='C',
                    magazine_pos=change.pot_number,
                    tool_num=change.tool_number,
                    new_value=change.color,
                    verbose=False
                )

                status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
                AuditLogger.log_tool_modification(
                    machine_id=machine_id,
                    operation_type="tool_color",
                    operation_details={
                        "pot_number": change.pot_number,
                        "tool_number": change.tool_number,
                        "new_color": change.color,
                        "new_color_name": color_names.get(change.color, "Unknown"),
                    },
                    success=success,
                    error_message=status_desc,
                    machine_state=None
                )

                if success:
                    results.append(ColorChangeResult(
                        pot_number=change.pot_number,
                        tool_number=change.tool_number,
                        color=change.color,
                        success=True,
                        message=f"Tool color changed to {color_names.get(change.color, 'Unknown')}"
                    ))
                    successful += 1
                else:
                    error_msg = status_desc or f"Failed with status code {status_code}"
                    results.append(ColorChangeResult(
                        pot_number=change.pot_number,
                        tool_number=change.tool_number,
                        color=change.color,
                        success=False,
                        error_code=status_code or "unknown",
                        message=error_msg
                    ))
                    failed += 1
                    logger.error(f"Failed to change tool color for pot {change.pot_number}, tool {change.tool_number}, color {change.color}: {error_msg}")

            except Exception as e:
                error_msg = str(e)
                results.append(ColorChangeResult(
                    pot_number=change.pot_number,
                    tool_number=change.tool_number,
                    color=change.color,
                    success=False,
                    error_code="exception",
                    message=error_msg
                ))
                failed += 1
                logger.error(f"Exception changing tool color for pot {change.pot_number}, tool {change.tool_number}: {e}")

        if successful > 0 and _state.polling_service:
            try:
                await _state.polling_service.refresh_tool_data(machine_id)
                logger.debug(f"Refreshed tool data for machine {machine_id} after batch color changes ({successful} successful)")
            except Exception as e:
                logger.warning(f"Failed to refresh tool data after batch color changes for machine {machine_id}: {e}")

        return BatchColorChangeResponse(
            results=results,
            total=len(request.changes),
            successful=successful,
            failed=failed
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch color change: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch change tool colors: {str(e)}",
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()


@router.put("/{machine_id}/tools/atc/pot/{pot_number}/tool")
async def change_tool_assignment(
    machine_id: int,
    pot_number: int,
    tool_number: int = Query(..., description="New tool number to assign"),
    db: Session = Depends(get_db)
):
    """
    Assign or change tool number in an ATC pot (CHGMAGM).

    Args:
        machine_id: Machine ID
        pot_number: Pot number (1-99)
        tool_number: Tool number to assign (1-999)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 1 <= pot_number <= 99:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pot number: {pot_number} (must be 1-99)",
        )

    if not 1 <= tool_number <= 999:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool number: {tool_number} (must be 1-999)",
        )

    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="tool_assignment",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import create_fresh_connection
        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        success, status_code = await telnet_client.assign_tool_to_pot(
            pot_number=pot_number,
            tool_number=tool_number,
            verbose=True
        )

        from app.services.audit_logger import AuditLogger
        from app.clients.telnet_client import CNCTelnetClient
        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="tool_assignment",
            operation_details={
                "pot_number": pot_number,
                "new_tool_number": tool_number,
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to assign tool: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63") if status_code else False
            }
            if status_data:
                error_response["machine_state"] = status_data
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        if _state.polling_service:
            try:
                await _state.polling_service.refresh_tool_data(machine_id)
                logger.debug(f"Refreshed tool data for machine {machine_id} after tool assignment")
            except Exception as e:
                logger.warning(f"Failed to refresh tool data after tool assignment for machine {machine_id}: {e}")

        return {
            "success": True,
            "pot_number": pot_number,
            "tool_number": tool_number,
            "message": f"Tool {tool_number} assigned to pot {pot_number}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning tool: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{machine_id}/tools/atc/pot/{pot_number}/type")
async def change_tool_type(
    machine_id: int,
    pot_number: int,
    tool_type: int = Query(..., description="Tool type (1=Standard, 2=Large, 3=Medium)"),
    db: Session = Depends(get_db)
):
    """
    Change tool type for an ATC pot (CHGMAGK).

    Args:
        machine_id: Machine ID
        pot_number: Pot number (1-99)
        tool_type: Tool type (1=Standard, 2=Large, 3=Medium)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 1 <= pot_number <= 99:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pot number: {pot_number} (must be 1-99)",
        )

    if tool_type not in (1, 2, 3):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool type: {tool_type} (must be 1=Standard, 2=Large, 3=Medium)",
        )

    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="tool_type",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import create_fresh_connection
        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        success, status_code = await telnet_client.change_tool_type(
            pot_number=pot_number,
            tool_type=tool_type,
            verbose=True
        )

        from app.services.audit_logger import AuditLogger
        from app.clients.telnet_client import CNCTelnetClient
        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        type_names = {1: "Standard", 2: "Large", 3: "Medium"}
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="tool_type",
            operation_details={
                "pot_number": pot_number,
                "new_tool_type": tool_type,
                "new_tool_type_name": type_names.get(tool_type, "Unknown"),
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to change tool type: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63") if status_code else False
            }
            if status_data:
                error_response["machine_state"] = status_data
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        if _state.polling_service:
            try:
                await _state.polling_service.refresh_tool_data(machine_id)
                logger.debug(f"Refreshed tool data for machine {machine_id} after tool type change")
            except Exception as e:
                logger.warning(f"Failed to refresh tool data after tool type change for machine {machine_id}: {e}")

        return {
            "success": True,
            "pot_number": pot_number,
            "tool_type": tool_type,
            "tool_type_name": type_names.get(tool_type, "Unknown"),
            "message": f"Tool type changed to {type_names.get(tool_type, 'Unknown')}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing tool type: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{machine_id}/tools/atc/pot/{pot_number}")
async def delete_tool_from_pot(
    machine_id: int,
    pot_number: int,
    tool_number: int = Query(None, description="Tool number for verification (optional)"),
    db: Session = Depends(get_db)
):
    """
    Remove/delete tool from an ATC pot (CHGMAGD).

    Args:
        machine_id: Machine ID
        pot_number: Pot number (0-99, 0=spindle)
        tool_number: Tool number for verification (optional)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 0 <= pot_number <= 99:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pot number: {pot_number} (must be 0-99)",
        )

    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="tool_delete",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import create_fresh_connection
        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        success, status_code = await telnet_client.remove_tool_from_pot(
            pot_number=pot_number,
            tool_number=tool_number,
            verbose=True
        )

        from app.services.audit_logger import AuditLogger
        from app.clients.telnet_client import CNCTelnetClient
        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="tool_delete",
            operation_details={
                "pot_number": pot_number,
                "tool_number": tool_number,
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to remove tool: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63") if status_code else False
            }
            if status_data:
                error_response["machine_state"] = status_data
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        if _state.polling_service:
            try:
                await _state.polling_service.refresh_tool_data(machine_id)
                logger.debug(f"Refreshed tool data for machine {machine_id} after tool deletion")
            except Exception as e:
                logger.warning(f"Failed to refresh tool data after tool deletion for machine {machine_id}: {e}")

        return {
            "success": True,
            "pot_number": pot_number,
            "message": f"Tool removed from pot {pot_number}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing tool: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{machine_id}/tools/spindle")
async def change_spindle_tool(
    machine_id: int,
    tool_number: int = Query(..., description="Tool number for spindle (0-999, 0=no tool)"),
    db: Session = Depends(get_db)
):
    """
    Change the tool in the spindle (CHGMAGS).

    Args:
        machine_id: Machine ID
        tool_number: Tool number for spindle (0-999, 0=no tool)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 0 <= tool_number <= 999:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool number: {tool_number} (must be 0-999)",
        )

    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="spindle_tool",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import create_fresh_connection
        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        success, status_code = await telnet_client.change_spindle_tool(
            tool_number=tool_number,
            verbose=True
        )

        from app.services.audit_logger import AuditLogger
        from app.clients.telnet_client import CNCTelnetClient
        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="spindle_tool",
            operation_details={
                "new_tool_number": tool_number,
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to change spindle tool: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63") if status_code else False
            }
            if status_data:
                error_response["machine_state"] = status_data
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        return {
            "success": True,
            "tool_number": tool_number,
            "message": f"Spindle tool changed to {tool_number if tool_number > 0 else 'none'}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing spindle tool: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{machine_id}/tools/{tool_number}/life")
async def set_tool_life(
    machine_id: int,
    tool_number: int,
    life_value: int = Query(..., description="Life value (0-999999)"),
    life_type: str = Query("TIME", description="Life type (TIME or COUNT)"),
    db: Session = Depends(get_db)
):
    """
    Set tool life value (WRTTLLF).

    Args:
        machine_id: Machine ID
        tool_number: Tool number (1-99)
        life_value: Life value (0-999999)
        life_type: Life type ('TIME' or 'COUNT')
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 1 <= tool_number <= 99:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool number: {tool_number} (must be 1-99)",
        )

    if not 0 <= life_value <= 999999:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid life value: {life_value} (must be 0-999999)",
        )

    if life_type not in ("TIME", "COUNT"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid life_type: {life_type} (must be TIME or COUNT)",
        )

    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="tool_life",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import create_fresh_connection
        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        success, status_code = await telnet_client.write_tool_life(
            tool_number=tool_number,
            life_value=life_value,
            life_type=life_type,
            verbose=True
        )

        from app.services.audit_logger import AuditLogger
        from app.clients.telnet_client import CNCTelnetClient
        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="tool_life",
            operation_details={
                "tool_number": tool_number,
                "new_life_value": life_value,
                "life_type": life_type,
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to set tool life: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63") if status_code else False
            }
            if status_data:
                error_response["machine_state"] = status_data
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        return {
            "success": True,
            "tool_number": tool_number,
            "life_value": life_value,
            "life_type": life_type,
            "message": f"Tool {tool_number} life ({life_type}) set to {life_value}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting tool life: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{machine_id}/tools/{tool_number}/offset")
async def set_tool_offset(
    machine_id: int,
    tool_number: int,
    offset_type: str = Query(..., description="Offset type (H=Length, D=Diameter, W=Wear)"),
    value: float = Query(..., description="Offset value in mm"),
    db: Session = Depends(get_db)
):
    """
    Set tool offset value (WRTTOFS).

    Args:
        machine_id: Machine ID
        tool_number: Tool number (1-99)
        offset_type: Offset type ('H'=Length, 'D'=Diameter, 'W'=Wear)
        value: Offset value in mm (or inches depending on machine units)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 1 <= tool_number <= 99:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool number: {tool_number} (must be 1-99)",
        )

    if offset_type not in ("H", "D", "W"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid offset_type: {offset_type} (must be H, D, or W)",
        )

    try:
        from app.services.machine_state_validator import MachineStateValidator
        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="tool_offset",
            db=db
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        from app.clients.telnet_client import create_fresh_connection
        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        success, status_code = await telnet_client.write_tool_offset(
            tool_number=tool_number,
            offset_type=offset_type,
            value=value,
            verbose=True
        )

        from app.services.audit_logger import AuditLogger
        from app.clients.telnet_client import CNCTelnetClient
        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        offset_names = {"H": "Length", "D": "Diameter", "W": "Wear"}
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="tool_offset",
            operation_details={
                "tool_number": tool_number,
                "offset_type": offset_type,
                "offset_type_name": offset_names.get(offset_type, "Unknown"),
                "new_value": value,
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to set tool offset: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63") if status_code else False
            }
            if status_data:
                error_response["machine_state"] = status_data
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        return {
            "success": True,
            "tool_number": tool_number,
            "offset_type": offset_type,
            "offset_type_name": offset_names.get(offset_type, "Unknown"),
            "value": value,
            "message": f"Tool {tool_number} {offset_names.get(offset_type, 'offset')} offset set to {value}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting tool offset: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{machine_id}/macros/{macro_number}")
async def set_macro_variable(
    machine_id: int,
    macro_number: int,
    value: float = Query(..., description="Macro variable value to write"),
    db: Session = Depends(get_db),
):
    """
    Write a macro variable (#500-999) on the control via WRTMCNM.

    Verifies the write by reading the value back with REDMCNM.
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    if not 500 <= macro_number <= 999:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid macro number: {macro_number} (must be 500-999)",
        )

    telnet_client = None
    try:
        from app.services.machine_state_validator import MachineStateValidator
        from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
        from app.services.audit_logger import AuditLogger

        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="macro_write",
            db=db,
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        # Brief pause after validation disconnect so the control finishes the prior session
        # before the write connection opens (reduces CM7522 from overlapping telnet sessions).
        await asyncio.sleep(0.25)

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10,
        )

        success, status_code, verified_value = await telnet_client.write_macro_variable(
            macro_number=macro_number,
            value=value,
            verbose=True,
            verify=True,
        )

        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="macro_write",
            operation_details={
                "macro_number": macro_number,
                "new_value": value,
                "verified_value": verified_value,
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data,
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to write macro #{macro_number}: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63", "verify_failed", "verify_mismatch")
                if status_code
                else False,
            }
            if status_data:
                error_response["machine_state"] = status_data
            if verified_value is not None:
                error_response["verified_value"] = verified_value
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        return {
            "success": True,
            "macro_number": macro_number,
            "value": value,
            "verified_value": verified_value,
            "message": f"Macro #{macro_number} set to {verified_value if verified_value is not None else value}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing macro #{macro_number} for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()


@router.put("/{machine_id}/tools/measurement-tool")
async def set_measurement_tool(
    machine_id: int,
    tool_number: int = Query(..., description="Tool number to measure (1-999)"),
    db: Session = Depends(get_db),
):
    """
    Set macro #920 to the selected tool number (tool measurement selection).
    """
    if not 1 <= tool_number <= 999:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool number: {tool_number} (must be 1-999)",
        )

    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    telnet_client = None
    try:
        from app.services.machine_state_validator import MachineStateValidator
        from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
        from app.services.audit_logger import AuditLogger

        validator = MachineStateValidator()
        is_safe, error_message, status_data = await validator.validate_safe_for_write(
            machine_id=machine_id,
            operation_type="macro_write",
            db=db,
        )

        if not is_safe:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_message or "Machine is not in a safe state for this operation",
            )

        await asyncio.sleep(0.25)

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10,
        )

        success, status_code, verified_value = await telnet_client.write_macro_variable(
            macro_number=MEASUREMENT_TOOL_MACRO,
            value=float(tool_number),
            verbose=True,
            verify=True,
        )

        status_desc = CNCTelnetClient.get_status_description(status_code or "00") if not success else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="measurement_tool",
            operation_details={
                "macro_number": MEASUREMENT_TOOL_MACRO,
                "tool_number": tool_number,
                "verified_value": verified_value,
            },
            success=success,
            error_message=status_desc,
            machine_state=status_data,
        )

        if not success:
            error_response = {
                "error_code": status_code or "unknown",
                "message": f"Failed to set measurement tool: {status_desc}",
                "can_retry": status_code in ("32", "36", "37", "63", "verify_failed", "verify_mismatch")
                if status_code
                else False,
            }
            if status_data:
                error_response["machine_state"] = status_data
            if verified_value is not None:
                error_response["verified_value"] = verified_value
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=error_response,
            )

        return {
            "success": True,
            "tool_number": tool_number,
            "macro_number": MEASUREMENT_TOOL_MACRO,
            "verified_value": verified_value,
            "message": f"Measurement tool set to T{tool_number:02d}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting measurement tool for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()
