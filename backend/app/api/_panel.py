# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Operation panel I/O API — toggle panel function keys and the NC mode.

Routes:
    POST /{machine_id}/panel/function — set block_skip/opt_stop/single_block/machine_lock
    POST /{machine_id}/panel/mode     — CHGMODE to MEM/MDI/MNL/EDIT

Both routes hold a request-scoped exclusive telnet session (pausing the fleet
poller), refuse when the machine is running a program, and read back PANEL so
the response reflects confirmed controller state — not just the write result.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.machine import Machine

logger = logging.getLogger(__name__)

router = APIRouter()

#: Panel function key -> mode_and_functions field used for PANEL read-back.
PANEL_FUNCTIONS = {
    "block_skip": "block_skip",
    "opt_stop": "opt_stop",
    "single_block": "single_block",
    "machine_lock": "machine_lock",
}

#: CHGMODE arg -> expected PANEL mode value (0=Manual, 1=MDI, 2=Memory, 3=Edit).
PANEL_MODES = {
    "MNL": 0,
    "MDI": 1,
    "MEM": 2,
    "EDIT": 3,
}


class PanelFunctionRequest(BaseModel):
    function: str = Field(
        ...,
        description="Panel function key: block_skip, opt_stop, single_block, machine_lock",
    )
    state: bool = Field(..., description="True = ON, False = OFF")


class PanelModeRequest(BaseModel):
    mode: str = Field(..., description="NC mode: MEM, MDI, MNL, EDIT")


@asynccontextmanager
async def _exclusive_fresh_telnet(
    db_machine: Machine,
    machine_id: int,
    *,
    reason: str = "panel_function",
    timeout: int = 10,
) -> AsyncIterator:
    """Pause fleet polling and open a dedicated telnet session for one write."""
    from app.clients.telnet_client import create_fresh_connection
    from app.services.probe_exclusive import exclusive_session

    async with exclusive_session(machine_id, reason=reason):
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=timeout,
        )
        try:
            yield client
        finally:
            await client.disconnect()


def _get_machine_or_404(db: Session, machine_id: int) -> Machine:
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )
    return db_machine


async def _ensure_safe_for_panel_write(
    machine_id: int, db: Session, operation_type: str
) -> Dict[str, Any]:
    """Refuse panel writes while the machine is running a program."""
    from app.services.machine_state_validator import MachineStateValidator

    validator = MachineStateValidator()
    is_safe, error_message, status_data = await validator.validate_safe_for_write(
        machine_id=machine_id,
        operation_type=operation_type,
        db=db,
    )
    if not is_safe:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=error_message or "Machine is not in a safe state for this operation",
        )
    return status_data or {}


async def _read_panel_field(client: Any, field: str) -> Optional[int]:
    """Read one mode_and_functions field from LOD PANEL."""
    from app.parsers.panel_parser_v2 import parse_panel_v2

    raw = await client.get_panel_data(verbose=False)
    if not raw:
        return None
    panel = parse_panel_v2(raw.encode("utf-8"))
    block = panel.get("mode_and_functions") or {}
    value = block.get(field)
    return int(value) if value is not None else None


@router.post("/{machine_id}/panel/function")
async def set_panel_function_endpoint(
    machine_id: int,
    request: PanelFunctionRequest,
    db: Session = Depends(get_db),
):
    """Toggle an operation-panel function key (block skip, opt stop, ...).

    Refuses with 409 while the machine is running a program. The response
    carries the PANEL read-back so the UI converges on controller state.
    """
    function = (request.function or "").strip().lower()
    if function not in PANEL_FUNCTIONS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid panel function: {request.function!r} "
                f"(must be one of {', '.join(sorted(PANEL_FUNCTIONS))})"
            ),
        )

    db_machine = _get_machine_or_404(db, machine_id)
    await _ensure_safe_for_panel_write(
        machine_id, db, operation_type="panel_function"
    )

    from app.clients.telnet_client import CNCTelnetClient

    async with _exclusive_fresh_telnet(
        db_machine, machine_id, reason="panel_function"
    ) as telnet_client:
        success, status_code = await telnet_client.set_panel_function(
            function, request.state, verbose=True
        )

        if not success:
            status_desc = CNCTelnetClient.get_status_description(status_code or "00")
            logger.error(
                f"Failed to set panel function {function}={request.state} "
                f"on machine {machine_id}: {status_desc} (status={status_code})"
            )
            raise HTTPException(
                status_code=http_status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to set {function}: {status_desc}",
            )

        confirmed = await _read_panel_field(telnet_client, PANEL_FUNCTIONS[function])
        logger.info(
            f"Panel function {function} -> {'ON' if request.state else 'OFF'} "
            f"on machine {machine_id} (confirmed={confirmed})"
        )
        return {
            "success": True,
            "function": function,
            "requested_state": request.state,
            "confirmed_state": confirmed,
            "status_code": status_code,
        }


@router.post("/{machine_id}/panel/mode")
async def set_panel_mode_endpoint(
    machine_id: int,
    request: PanelModeRequest,
    db: Session = Depends(get_db),
):
    """Switch the NC mode (MEM/MDI/MNL/EDIT) via CHGMODE.

    Refuses with 409 while the machine is running a program.
    """
    mode = (request.mode or "").strip().upper()
    if mode not in PANEL_MODES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid mode: {request.mode!r} "
                f"(must be one of {', '.join(sorted(PANEL_MODES))})"
            ),
        )

    db_machine = _get_machine_or_404(db, machine_id)
    await _ensure_safe_for_panel_write(
        machine_id, db, operation_type="panel_mode"
    )

    from app.clients.telnet_client import CNCTelnetClient

    async with _exclusive_fresh_telnet(
        db_machine, machine_id, reason="panel_mode"
    ) as telnet_client:
        success, status_code = await telnet_client.change_mode(mode, verbose=True)

        if not success:
            status_desc = CNCTelnetClient.get_status_description(status_code or "00")
            logger.error(
                f"Failed to change mode to {mode} on machine {machine_id}: "
                f"{status_desc} (status={status_code})"
            )
            raise HTTPException(
                status_code=http_status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to change mode: {status_desc}",
            )

        confirmed = await _read_panel_field(telnet_client, "mode")
        logger.info(
            f"Mode -> {mode} on machine {machine_id} (confirmed={confirmed})"
        )
        return {
            "success": True,
            "mode": mode,
            "confirmed_mode": confirmed,
            "status_code": status_code,
        }
