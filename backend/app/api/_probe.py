"""Probe cycle API — catalog, arm (O8099 gate), collect, poison.

Routes:
    GET  /{machine_id}/probe/catalog  — Blum routine catalog (+ gate_program)
    POST /{machine_id}/probe/run      — write macros + MEMSTRT O8099 only; wait for M0
    POST /{machine_id}/probe/collect  — wait idle after M0, read results, poison
    POST /{machine_id}/probe/poison   — force sentinel macros
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.machine import Machine
from app.services.probe_catalog import catalog_for_api
from app.services.probe_cycle_service import (
    arm_probe_cycle,
    collect_probe_results,
    poison_probe_macros,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ProbeRunRequest(BaseModel):
    type: str = Field(..., description="Routine id from catalog (e.g. corner_xyz)")
    mode: str = Field(..., description="probe or measure")
    params: Dict[str, float] = Field(
        default_factory=dict,
        description="Macro values keyed by number (900) or field key (wcs)",
    )


class ProbeCollectRequest(BaseModel):
    poison: bool = Field(
        True,
        description="Poison job macros after reading results (default true)",
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


@router.get("/{machine_id}/probe/catalog")
async def get_probe_catalog(machine_id: int, db: Session = Depends(get_db)):
    """Return Blum probe/measure routine catalog for the Probes pane."""
    _get_machine(db, machine_id)
    return catalog_for_api()


@router.post("/{machine_id}/probe/run")
async def post_probe_run(
    machine_id: int,
    body: ProbeRunRequest,
    db: Session = Depends(get_db),
):
    """
    Arm a gated probe cycle.

    Writes job macros + #908 (target O-number), MEMSTRTs **O8099 only**, waits
    until M0 / message stop. Does not start Blum helpers directly and does not
    poison macros (operator must Cycle Start past M0 on the control).
    """
    machine = _get_machine(db, machine_id)
    logger.info(
        "Probe arm requested machine=%s type=%s mode=%s",
        machine_id,
        body.type,
        body.mode,
    )
    result = await arm_probe_cycle(
        db_machine=machine,
        machine_id=machine_id,
        routine_id=body.type,
        mode=body.mode,
        params=body.params or {},
    )
    payload = _result_payload(result)
    if not result.ok and result.phase == "validate":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=payload,
        )
    if not result.ok and result.phase == "safety":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=payload,
        )
    if not result.ok:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=payload,
        )
    return payload


@router.post("/{machine_id}/probe/collect")
async def post_probe_collect(
    machine_id: int,
    body: Optional[ProbeCollectRequest] = None,
    db: Session = Depends(get_db),
):
    """Wait for idle after operator confirms past M0, read #100+, optionally poison."""
    machine = _get_machine(db, machine_id)
    poison = True if body is None else body.poison
    result = await collect_probe_results(
        db_machine=machine,
        machine_id=machine_id,
        poison=poison,
    )
    payload = _result_payload(result)
    if not result.ok:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=payload,
        )
    return payload


@router.post("/{machine_id}/probe/poison")
async def post_probe_poison(machine_id: int, db: Session = Depends(get_db)):
    """Write sentinel values to probe job macros (#900-908, #920)."""
    machine = _get_machine(db, machine_id)
    result = await poison_probe_macros(machine)
    payload = _result_payload(result)
    if not result.ok:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=payload,
        )
    return payload
