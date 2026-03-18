"""API endpoints for event history and analytics."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.base import get_db
from app.models.event import MachineStatusEvent, AlarmEvent, ProductionRun, PRD3StatusHistory
from app.services.history_service import get_cycle_history, _build_status_intervals, get_production_runs_timeline
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


# ========== Cycle History (PRD3 + Counters + Alarms) ==========

@router.get("/machines/{machine_id}/cycle-history")
async def get_cycle_history_endpoint(
    machine_id: int,
    since: Optional[datetime] = Query(
        None,
        description="Filter cycles starting at or after this time (defaults to last 24h)",
    ),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get recent cycle history for a machine by combining PRD3 status history,
    workpiece counter increments, and alarms.

    Returns a list of cycles (runs) with:
    - program_no, folder_name
    - start_time, end_time, duration_seconds
    - part_count (total across counters)
    - parts_by_counter {counter_number: count}
    - alarms during the run
    """
    cycles = get_cycle_history(
        db=db,
        machine_id=machine_id,
        since=since,
        limit=limit,
        offset=offset,
    )
    # FastAPI will auto-serialize ORM AlarmEvent objects; convert to dictionaries where needed
    serialized = []
    for c in cycles:
        alarms = []
        for a in c.get("alarms", []):
            alarms.append(
                {
                    "time": a.time,
                    "machine_id": a.machine_id,
                    "alarm_code": a.alarm_code,
                    "alarm_message": a.alarm_message,
                    "alarm_type": a.alarm_type,
                    "severity": a.severity,
                    "cleared_at": a.cleared_at,
                }
            )
        serialized.append(
            {
                "program_no": c.get("program_no"),
                "folder_name": c.get("folder_name"),
                "start_time": c.get("start_time"),
                "end_time": c.get("end_time"),
                "duration_seconds": c.get("duration_seconds"),
                "time_by_status": c.get("time_by_status", {}),
                "part_count": c.get("part_count"),
                "parts_by_counter": c.get("parts_by_counter"),
                "alarms": alarms,
            }
        )
    return serialized


# ========== PRD3 Status History Timeline ==========

@router.get("/machines/{machine_id}/prd3-status-history")
async def get_prd3_status_history(
    machine_id: int,
    start_time: Optional[datetime] = Query(
        None,
        description="Filter status intervals starting at or after this time (defaults to last 24h)",
    ),
    end_time: Optional[datetime] = Query(
        None,
        description="Filter status intervals ending at or before this time (defaults to now)",
    ),
    limit: int = Query(500, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get a detailed PRD3-derived status history timeline for a machine.

    Primary behavior:
    - If no explicit time range is provided, use the last 7 days.
    - If that window has no intervals, fall back to the most recent PRD3 rows
      for this machine (capped) and build intervals from those.

    This endpoint returns contiguous status intervals (off/standby/operating/stopped/error)
    with start/end times and associated program/error context, built from
    PRD3StatusHistory rows.
    """
    FALLBACK_ROW_LIMIT = 500

    # Normalize end_time
    if end_time is None:
        end_time = datetime.utcnow()

    # Track whether the caller explicitly provided a time window
    explicit_range = start_time is not None

    # Default window: last 7 days if no explicit start_time
    if start_time is None:
        start_time = end_time - timedelta(days=7)

    # Primary query: PRD3 rows for this window
    rows = (
        db.query(PRD3StatusHistory)
        .filter(
            PRD3StatusHistory.machine_id == machine_id,
            PRD3StatusHistory.time >= start_time,
            PRD3StatusHistory.time <= end_time,
        )
        .order_by(PRD3StatusHistory.time.asc())
        .all()
    )

    intervals = _build_status_intervals(rows)

    # If no intervals and the caller did not specify an explicit time range,
    # fall back to building intervals from the most recent PRD3 rows.
    if not intervals and not explicit_range:
        rows_desc = (
            db.query(PRD3StatusHistory)
            .filter(PRD3StatusHistory.machine_id == machine_id)
            .order_by(PRD3StatusHistory.time.desc())
            .limit(FALLBACK_ROW_LIMIT)
            .all()
        )
        # Reverse to ascending for the interval builder
        rows_fallback = list(reversed(rows_desc))
        intervals = _build_status_intervals(rows_fallback)

    if not intervals:
        return []

    # Sort newest-first for the client (latest intervals first)
    intervals = sorted(
        intervals,
        key=lambda i: i.get("start_time") or datetime.min,
        reverse=True,
    )

    # Apply offset/limit on the interval list
    if offset < 0:
        offset = 0
    if limit <= 0:
        return []
    intervals = intervals[offset : offset + limit]

    # Map status to human-friendly label
    STATUS_LABELS = {
        "off": "Power is off",
        "standby": "Standby mode",
        "operating": "Running",
        "stopped": "Stopped",
        "error": "Error occurred",
    }

    serialized = []
    for interval in intervals:
        status = interval.get("status")
        program_no = interval.get("program_no")
        error_no = interval.get("error_no")
        start = interval.get("start_time")
        end = interval.get("end_time") or end_time

        # Derive label and detail
        label = STATUS_LABELS.get(status, status or "Unknown")
        detail: Optional[str] = None

        if status == "operating" and program_no:
            detail = f"PROGRAM/{program_no}"
        elif status == "error" and error_no:
            # Match IO0518 * style
            detail = f"{error_no} *"
        else:
            # For other statuses, use folder_name only when it's a real path (not the generic "PROGRAM" token)
            folder_name = interval.get("folder_name")
            if folder_name and folder_name.strip().upper() != "PROGRAM":
                detail = folder_name

        # Compute duration in whole seconds
        duration_seconds = None
        if isinstance(start, datetime) and isinstance(end, datetime):
            try:
                duration_seconds = int((end - start).total_seconds())
                if duration_seconds < 0:
                    duration_seconds = 0
            except Exception:
                duration_seconds = None

        serialized.append(
            {
                "status": status,
                "status_code": interval.get("status_code"),
                "program_no": program_no,
                "error_no": error_no,
                "start_time": interval.get("start_time"),
                "end_time": interval.get("end_time"),
                "label": label,
                "detail": detail,
                "duration_seconds": duration_seconds,
            }
        )

    return serialized


# ========== Production Runs Timeline (PRD3 + Counters) ==========

@router.get("/machines/{machine_id}/production-runs-timeline")
async def get_production_runs_timeline_endpoint(
    machine_id: int,
    start_time: Optional[datetime] = Query(
        None,
        description="Filter runs starting at or after this time (defaults to last 24h)",
    ),
    end_time: Optional[datetime] = Query(
        None,
        description="Filter runs ending at or before this time (defaults to now)",
    ),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get a production runs timeline by grouping sequential PRD3 operating intervals
    with the same program_no into runs, and embedding status segments inside each run.
    """
    runs = get_production_runs_timeline(
        db=db,
        machine_id=machine_id,
        start_time=start_time,
        end_time=end_time,
    )

    # Apply simple pagination on the runs list (newest-first already)
    if offset < 0:
        offset = 0
    if limit <= 0:
        return []
    runs = runs[offset : offset + limit]

    serialized = []
    for r in runs:
        segments = []
        for s in r.get("segments", []):
            segments.append(
                {
                    "status": s.get("status"),
                    "status_code": s.get("status_code"),
                    "start_time": s.get("start_time"),
                    "end_time": s.get("end_time"),
                    "error_no": s.get("error_no"),
                }
            )

        serialized.append(
            {
                "program_no": r.get("program_no"),
                "run_start": r.get("run_start"),
                "run_end": r.get("run_end"),
                "cycles": r.get("cycles"),
                "segments": segments,
                "part_count": r.get("part_count"),
                "parts_by_counter": r.get("parts_by_counter"),
            }
        )

    return serialized
