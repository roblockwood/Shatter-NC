"""Probe cycle API — stepped write / start / collect / poison.

Routes:
    GET  /{machine_id}/probe/catalog  — Blum routine catalog
    POST /{machine_id}/probe/exclusive — begin/end exclusive telnet hold
    POST /{machine_id}/probe/write    — write job macros only (no motion)
    POST /{machine_id}/probe/start    — MEMSTRT catalog target (motion)
    POST /{machine_id}/probe/collect  — wait idle, read #100+, poison
    POST /{machine_id}/probe/poison   — force sentinel macros
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.machine import Machine
from app.services.probe_catalog import catalog_for_api
from app.services.probe_cycle_service import (
    collect_probe_results,
    poison_probe_macros,
    start_probe_program,
    write_probe_macros,
)
from app.services.probe_exclusive import (
    begin_exclusive,
    end_exclusive,
    sweep_stale_holds,
    touch_probe_activity,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ProbeRunRequest(BaseModel):
    type: str = Field(..., description="Routine id from catalog (e.g. corner_xyz)")
    mode: str = Field(..., description="probe or measure")
    params: Dict[str, float] = Field(
        default_factory=dict,
        description="Macro values keyed by number (900) or field key (wcs)",
    )
    client_run_id: Optional[str] = Field(
        None,
        description="Optional client UUID to filter probe_progress WebSocket events",
    )


class ProbeCollectRequest(BaseModel):
    poison: bool = Field(
        True,
        description="Poison job macros after reading results (default true)",
    )
    client_run_id: Optional[str] = Field(
        None,
        description="Optional client UUID to filter probe_progress WebSocket events",
    )


class ProbeExclusiveRequest(BaseModel):
    active: bool = Field(..., description="True to begin exclusive hold, False to end")


class ProbePoisonRequest(BaseModel):
    client_run_id: Optional[str] = Field(
        None,
        description="Optional client UUID to filter probe_progress WebSocket events",
    )


def _get_machine(db: Session, machine_id: int) -> Machine:
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine {machine_id} not found",
        )
    return machine


def _result_payload(result: Any) -> Dict[str, Any]:
    return {
        "ok": result.ok,
        "program": result.program,
        "gate_program": result.gate_program,
        "target_program": result.target_program,
        "routine_id": result.routine_id,
        "mode": result.mode,
        "macros_written": {str(k): v for k, v in (result.macros_written or {}).items()},
        "results": result.results,
        "phase": result.phase,
        "error": result.error,
        "status_data": result.status_data,
        "elapsed_s": result.elapsed_s,
    }


def _raise_for_result(result: Any, payload: Dict[str, Any]) -> None:
    if result.ok:
        return
    if result.phase == "validate":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=payload,
        )
    if result.phase == "safety":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=payload,
        )
    raise HTTPException(
        status_code=http_status.HTTP_502_BAD_GATEWAY,
        detail=payload,
    )


async def _touch_and_sweep(machine_id: int) -> None:
    await sweep_stale_holds()
    touch_probe_activity(machine_id)


@router.get("/{machine_id}/probe/catalog")
async def get_probe_catalog(machine_id: int, db: Session = Depends(get_db)):
    """Return Blum probe/measure routine catalog for the Probes pane."""
    _get_machine(db, machine_id)
    return catalog_for_api()


@router.post("/{machine_id}/probe/exclusive")
async def post_probe_exclusive(
    machine_id: int,
    body: ProbeExclusiveRequest,
    db: Session = Depends(get_db),
):
    """Begin/end exclusive telnet hold (pauses that machine's fleet poller)."""
    _get_machine(db, machine_id)
    if body.active:
        return await begin_exclusive(machine_id)
    return await end_exclusive(machine_id)


@router.post("/{machine_id}/probe/write")
async def post_probe_write(
    machine_id: int,
    body: ProbeRunRequest,
    db: Session = Depends(get_db),
):
    """Write job macros only. Does not MEMSTRT or cause axis motion."""
    machine = _get_machine(db, machine_id)
    await _touch_and_sweep(machine_id)
    logger.info(
        "Probe write requested machine=%s type=%s mode=%s",
        machine_id,
        body.type,
        body.mode,
    )
    result = await write_probe_macros(
        db_machine=machine,
        machine_id=machine_id,
        routine_id=body.type,
        mode=body.mode,
        params=body.params or {},
        client_run_id=body.client_run_id,
    )
    payload = _result_payload(result)
    _raise_for_result(result, payload)
    return payload


@router.post("/{machine_id}/probe/start")
async def post_probe_start(
    machine_id: int,
    body: ProbeRunRequest,
    db: Session = Depends(get_db),
):
    """
    MEMSTRT the catalog target program (machine will move).

    Allowlisted O-numbers only. Call /probe/write first so macros are current.
    """
    machine = _get_machine(db, machine_id)
    await _touch_and_sweep(machine_id)
    logger.info(
        "Probe start requested machine=%s type=%s mode=%s",
        machine_id,
        body.type,
        body.mode,
    )
    result = await start_probe_program(
        db_machine=machine,
        machine_id=machine_id,
        routine_id=body.type,
        mode=body.mode,
        params=body.params or {},
        client_run_id=body.client_run_id,
    )
    payload = _result_payload(result)
    _raise_for_result(result, payload)
    return payload


@router.post("/{machine_id}/probe/collect")
async def post_probe_collect(
    machine_id: int,
    body: Optional[ProbeCollectRequest] = None,
    db: Session = Depends(get_db),
):
    """Wait for idle after motion, read #100+, optionally poison."""
    machine = _get_machine(db, machine_id)
    await _touch_and_sweep(machine_id)
    poison = True if body is None else body.poison
    client_run_id = None if body is None else body.client_run_id
    result = await collect_probe_results(
        db_machine=machine,
        machine_id=machine_id,
        poison=poison,
        client_run_id=client_run_id,
    )
    payload = _result_payload(result)
    if not result.ok:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=payload,
        )
    return payload


@router.post("/{machine_id}/probe/poison")
async def post_probe_poison(
    machine_id: int,
    body: Optional[ProbePoisonRequest] = None,
    db: Session = Depends(get_db),
):
    """Write sentinel values to probe job macros (#900-908, #920)."""
    machine = _get_machine(db, machine_id)
    await _touch_and_sweep(machine_id)
    client_run_id = None if body is None else body.client_run_id
    result = await poison_probe_macros(machine, client_run_id=client_run_id)
    payload = _result_payload(result)
    if not result.ok:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=payload,
        )
    return payload
