"""API endpoints for event history and analytics."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime

from app.db.base import get_db
from app.models.event import MachineStatusEvent, AlarmEvent, ProductionRun
from app.schemas.event import (
    MachineStatusEventResponse,
    AlarmEventResponse,
    ProductionRunResponse
)

router = APIRouter()


# ========== Machine Status History ==========

@router.get("/machines/{machine_id}/status-history", response_model=List[MachineStatusEventResponse])
async def get_status_history(
    machine_id: int,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get status change history for a machine.

    Query params:
    - start_time: Filter from this datetime (ISO format)
    - end_time: Filter until this datetime (ISO format)
    - limit: Maximum number of events to return (max 1000)
    """
    query = db.query(MachineStatusEvent).filter(
        MachineStatusEvent.machine_id == machine_id
    )

    if start_time:
        query = query.filter(MachineStatusEvent.time >= start_time)
    if end_time:
        query = query.filter(MachineStatusEvent.time <= end_time)

    query = query.order_by(desc(MachineStatusEvent.time))
    events = query.limit(limit).all()

    return events


# ========== Alarm History ==========

@router.get("/machines/{machine_id}/alarms", response_model=List[AlarmEventResponse])
async def get_alarm_history(
    machine_id: int,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    active_only: bool = False,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get alarm history for a machine.

    Query params:
    - start_time: Filter from this datetime (ISO format)
    - end_time: Filter until this datetime (ISO format)
    - active_only: Only show active (uncleared) alarms
    - limit: Maximum number of events to return (max 1000)
    """
    query = db.query(AlarmEvent).filter(
        AlarmEvent.machine_id == machine_id
    )

    if start_time:
        query = query.filter(AlarmEvent.time >= start_time)
    if end_time:
        query = query.filter(AlarmEvent.time <= end_time)
    if active_only:
        query = query.filter(AlarmEvent.cleared_at.is_(None))

    query = query.order_by(desc(AlarmEvent.time))
    alarms = query.limit(limit).all()

    return alarms


@router.get("/alarms/active", response_model=List[AlarmEventResponse])
async def get_active_alarms(
    machine_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get all currently active alarms (across all machines or specific machine).

    Query params:
    - machine_id: Optional machine ID to filter to specific machine
    """
    query = db.query(AlarmEvent).filter(AlarmEvent.cleared_at.is_(None))

    if machine_id:
        query = query.filter(AlarmEvent.machine_id == machine_id)

    query = query.order_by(desc(AlarmEvent.time))
    alarms = query.all()

    return alarms


# ========== Production History ==========

@router.get("/machines/{machine_id}/production-runs", response_model=List[ProductionRunResponse])
async def get_production_runs(
    machine_id: int,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    program_id: Optional[int] = None,
    active_only: bool = False,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get production run history for a machine.

    Query params:
    - start_time: Filter from this datetime (ISO format)
    - end_time: Filter until this datetime (ISO format)
    - program_id: Filter by specific program
    - active_only: Only show active (not yet ended) runs
    - limit: Maximum number of runs to return (max 1000)
    """
    query = db.query(ProductionRun).filter(
        ProductionRun.machine_id == machine_id
    )

    if start_time:
        query = query.filter(ProductionRun.started_at >= start_time)
    if end_time:
        query = query.filter(ProductionRun.started_at <= end_time)
    if program_id:
        query = query.filter(ProductionRun.program_id == program_id)
    if active_only:
        query = query.filter(ProductionRun.ended_at.is_(None))

    query = query.order_by(desc(ProductionRun.started_at))
    runs = query.limit(limit).all()

    return runs


@router.get("/programs/{program_id}/production-runs", response_model=List[ProductionRunResponse])
async def get_program_production_history(
    program_id: int,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get production history for a specific program (across all machines).

    Shows where and when this program has been run.

    Query params:
    - limit: Maximum number of runs to return (max 1000)
    """
    query = db.query(ProductionRun).filter(
        ProductionRun.program_id == program_id
    ).order_by(desc(ProductionRun.started_at))

    runs = query.limit(limit).all()
    return runs
