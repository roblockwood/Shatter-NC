from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, text
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.base import get_db
from app.models.machine import Machine
from app.models.compressor import Compressor
from app.models.event import ProductionRun, MachineStatusEvent, CompressorStatusEvent, CompressorStatusSample

router = APIRouter()

# Polling service and WebSocket manager will be injected from main.py
# These are initialized in main.py and accessed as globals
from app.api import websocket as websocket_api
polling_service = None
compressor_polling_service = None

def set_polling_service(service):
    """Inject the polling service from main.py"""
    global polling_service
    polling_service = service


def set_compressor_polling_service(service):
    """Inject the compressor polling service from main.py"""
    global compressor_polling_service
    compressor_polling_service = service

# Pydantic models for responses

class PollingDataPoint(BaseModel):
    """Single polling history data point."""
    time: datetime
    success: bool
    response_time_ms: Optional[int] = None

class StatusEvent(BaseModel):
    """Single status history event."""
    time: datetime
    status: str

class RunningSummaryMachine(BaseModel):
    machine_id: int
    machine_name: str
    current_status: Optional[str] = None
    total_run_time_seconds: float
    total_run_time_formatted: str
    run_percentage: float
    active_runs_count: int
    last_run_start: Optional[datetime] = None
    current_program: Optional[str] = None
    status_history: List[StatusEvent] = []  # Status history for oscilloscope (operating/standby/stopped/error only)

class RunningSummary(BaseModel):
    time_range: str
    total_machines: int
    machines: List[RunningSummaryMachine]

class PollingStatsSummary(BaseModel):
    """Summary statistics for polling history."""
    total_polls: int
    successful_polls: int
    failed_polls: int
    success_rate: float  # 0-100%
    avg_response_time_ms: Optional[int] = None
    current_streak: int  # positive = consecutive successes, negative = consecutive failures

class MachineStatusSummary(BaseModel):
    """Unified machine/compressor status with polling data."""
    machine_id: int  # CNC machine_id or compressor_id (see asset_kind)
    machine_name: str
    asset_kind: str = "cnc"  # "cnc" | "compressor"
    is_online: bool
    uptime_8h_percent: float  # % of successful polls in 8h window
    current_status: Optional[str] = None  # "running", "idle", "alarm", etc.
    connection_health: str  # "healthy", "degraded", "stale"

    # Duration tracking
    online_duration_formatted: str  # If online: how long online
    offline_duration_formatted: str  # If offline: how long offline
    status_changed_at: Optional[datetime] = None  # When status last changed

    # Polling history for visualization
    polling_history_8h: List[PollingDataPoint]
    polling_summary: PollingStatsSummary

class MachinesSummary(BaseModel):
    """Summary of all fleet asset statuses (CNC + compressors)."""
    total_machines: int
    online_count: int
    offline_count: int
    machines: List[MachineStatusSummary]

# Helper functions

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format (e.g., '12h 30m')"""
    if seconds < 0:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def parse_time_range(time_range: str) -> timedelta:
    """Parse time range string to timedelta"""
    time_range_map = {
        '1h': timedelta(hours=1),
        '4h': timedelta(hours=4),
        '8h': timedelta(hours=8),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30),
    }
    if time_range not in time_range_map:
        raise HTTPException(status_code=400, detail=f"Invalid time_range. Must be one of: {', '.join(time_range_map.keys())}")
    return time_range_map[time_range]

def get_connection_health(last_seen_at: Optional[datetime]) -> str:
    """Determine connection health based on last_seen_at timestamp"""
    if last_seen_at is None:
        return "stale"

    now = datetime.utcnow()
    seconds_since = (now - last_seen_at.replace(tzinfo=None) if last_seen_at.tzinfo else now - last_seen_at).total_seconds()

    if seconds_since < 30:
        return "healthy"
    elif seconds_since < 300:  # 5 minutes
        return "degraded"
    else:
        return "stale"


def is_backend_healthy() -> bool:
    """
    Check if backend/polling service is healthy and has had time to poll machines.
    
    Returns True only if:
    - Polling service is running
    - Polling service has been running long enough to have attempted at least one poll
      (allows for initial startup delay)

    Compressors alone also count as healthy when compressor polling is active.
    """
    compressor_ok = False
    if compressor_polling_service and compressor_polling_service.is_running:
        if len(getattr(compressor_polling_service, "pollers", {}) or {}) > 0:
            compressor_ok = True

    if not polling_service:
        return compressor_ok
    
    if not polling_service.is_running:
        return compressor_ok
    
    # Check if we have any recent polling events (within last 2 polling intervals = 10 seconds)
    # This ensures the backend has actually been polling, not just started
    from app.models.event import PollingEvent
    from app.db.base import SessionLocal
    
    db = SessionLocal()
    try:
        # Check for any polling event in the last 10 seconds
        # This confirms the polling service is actively working
        recent_poll = db.query(PollingEvent).filter(
            PollingEvent.time >= datetime.utcnow() - timedelta(seconds=10)
        ).first()
        
        # If no recent polls, backend might have just started - give it a grace period
        # Check if polling service has pollers (means it's set up)
        if not recent_poll and len(polling_service.pollers) == 0:
            return compressor_ok
        
        # If we have pollers but no recent polls, backend might be starting up
        # Allow a grace period of 15 seconds after startup
        if not recent_poll:
            # Check if there are any polling events at all (backend has polled before)
            any_poll = db.query(PollingEvent).first()
            if not any_poll:
                # No polls ever - backend just started, give it grace period
                return compressor_ok
        
        return True
    except Exception as e:
        # If we can't check, assume backend is healthy to avoid false negatives
        return True
    finally:
        db.close()

def get_polling_history(machine_id: int, db: Session, hours: int = 8) -> List[PollingDataPoint]:
    """Get polling history for a machine over the trailing N hours."""
    from app.models.event import PollingEvent

    now = datetime.utcnow()
    time_ago = now - timedelta(hours=hours)

    events = db.query(PollingEvent).filter(
        PollingEvent.machine_id == machine_id,
        PollingEvent.time >= time_ago
    ).order_by(PollingEvent.time).all()

    return [
        PollingDataPoint(
            time=event.time,
            success=event.success,
            response_time_ms=event.response_time_ms
        )
        for event in events
    ]


def _compressor_sample_success(sample: CompressorStatusSample) -> bool:
    """Treat a compressor status sample as a successful poll when online."""
    metrics = sample.metrics if isinstance(sample.metrics, dict) else {}
    if "is_online" in metrics:
        return bool(metrics.get("is_online"))
    status = (sample.status or "").lower()
    return status not in ("offline", "off", "unreachable", "unknown")


def get_compressor_polling_history(
    compressor_id: int, db: Session, hours: int = 8
) -> List[PollingDataPoint]:
    """Build polling-style history from compressor_status_samples."""
    now = datetime.utcnow()
    time_ago = now - timedelta(hours=hours)

    samples = (
        db.query(CompressorStatusSample)
        .filter(
            CompressorStatusSample.compressor_id == compressor_id,
            CompressorStatusSample.time >= time_ago,
        )
        .order_by(CompressorStatusSample.time)
        .all()
    )

    history: List[PollingDataPoint] = []
    for sample in samples:
        metrics = sample.metrics if isinstance(sample.metrics, dict) else {}
        response_ms = metrics.get("response_time_ms")
        try:
            response_ms = int(response_ms) if response_ms is not None else None
        except (TypeError, ValueError):
            response_ms = None
        history.append(
            PollingDataPoint(
                time=sample.time,
                success=_compressor_sample_success(sample),
                response_time_ms=response_ms,
            )
        )
    return history


def _duration_fields_for_asset(
    *,
    is_online: bool,
    backend_healthy: bool,
    last_seen_at: Optional[datetime],
    status_changed_at: Optional[datetime],
) -> tuple[str, str, Optional[datetime]]:
    """Return (online_duration_formatted, offline_duration_formatted, status_changed_at)."""
    now = datetime.utcnow()
    changed = status_changed_at or last_seen_at

    if is_online:
        if changed:
            changed_naive = changed.replace(tzinfo=None) if changed.tzinfo else changed
            duration_seconds = int((now - changed_naive).total_seconds())
        else:
            duration_seconds = 0
        return format_duration(duration_seconds), "", changed

    if backend_healthy:
        if changed:
            changed_naive = changed.replace(tzinfo=None) if changed.tzinfo else changed
            duration_seconds = int((now - changed_naive).total_seconds())
        else:
            duration_seconds = 0
        return "", format_duration(duration_seconds), changed

    return "", "", changed

def calculate_polling_stats(polling_history: List[PollingDataPoint]) -> PollingStatsSummary:
    """Calculate polling statistics from polling history."""
    total_polls = len(polling_history)

    if total_polls == 0:
        return PollingStatsSummary(
            total_polls=0,
            successful_polls=0,
            failed_polls=0,
            success_rate=0.0,
            avg_response_time_ms=None,
            current_streak=0
        )

    successful_polls = sum(1 for p in polling_history if p.success)
    failed_polls = total_polls - successful_polls
    success_rate = (successful_polls / total_polls * 100) if total_polls > 0 else 0.0

    # Calculate average response time (only from successful polls)
    response_times = [p.response_time_ms for p in polling_history if p.success and p.response_time_ms]
    avg_response_time_ms = int(sum(response_times) / len(response_times)) if response_times else None

    # Calculate current streak (positive for successes, negative for failures)
    current_streak = 0
    for p in reversed(polling_history):
        if p.success:
            if current_streak >= 0:
                current_streak += 1
            else:
                break
        else:
            if current_streak <= 0:
                current_streak -= 1
            else:
                break

    return PollingStatsSummary(
        total_polls=total_polls,
        successful_polls=successful_polls,
        failed_polls=failed_polls,
        success_rate=round(success_rate, 1),
        avg_response_time_ms=avg_response_time_ms,
        current_streak=current_streak
    )

# API Endpoints

@router.get("/summary/running", response_model=RunningSummary)
def get_running_summary(
    time_range: str = Query(default="24h", pattern="^(1h|4h|8h|24h|7d|30d)$"),
    db: Session = Depends(get_db)
):
    """
    Get running summary showing machines sorted by total run time within the specified time range.

    Query Parameters:
    - time_range: One of '1h', '4h', '8h', '24h', '7d', '30d' (default: '24h')

    Returns machines sorted by total run time (descending) with run percentages and current status.
    """
    # Parse time range
    time_delta = parse_time_range(time_range)
    start_time = datetime.utcnow() - time_delta

    # Query production runs within time range
    # Calculate total run time per machine
    query = db.query(
        Machine.id.label('machine_id'),
        Machine.name.label('machine_name'),
        func.coalesce(
            func.sum(
                case(
                    # If run is still active (ended_at is NULL and started_at is in range)
                    (ProductionRun.ended_at.is_(None),
                     extract('epoch', func.now() - ProductionRun.started_at)),
                    # If run ended within range
                    else_=ProductionRun.duration_seconds
                )
            ),
            0
        ).label('total_run_time_seconds'),
        func.count(ProductionRun.id).label('runs_count'),
        func.max(ProductionRun.started_at).label('last_run_start'),
        func.max(ProductionRun.program_name).label('current_program')
    ).outerjoin(
        ProductionRun,
        (ProductionRun.machine_id == Machine.id) &
        (ProductionRun.started_at >= start_time)
    ).group_by(
        Machine.id, Machine.name
    ).order_by(
        text('total_run_time_seconds DESC')
    ).all()

    # Calculate time range in seconds for percentage calculation
    time_range_seconds = time_delta.total_seconds()

    # Build response
    machines = []
    for row in query:
        total_run_time = float(row.total_run_time_seconds)
        run_percentage = (total_run_time / time_range_seconds * 100) if time_range_seconds > 0 else 0.0

        # Get current status from in-memory cache
        cached_status = websocket_api.websocket_manager.get_machine_status_from_cache(row.machine_id) if websocket_api.websocket_manager else {}
        current_status = cached_status.get("status") if cached_status else None

        # Get status history for the time range (filter out 'off' status)
        # Parse time range for status history
        end_time = datetime.utcnow()
        start_time = end_time - time_delta
        
        status_events_query = db.query(MachineStatusEvent).filter(
            MachineStatusEvent.machine_id == row.machine_id,
            MachineStatusEvent.time >= start_time,
            MachineStatusEvent.time <= end_time,
            MachineStatusEvent.status.notin_(['off'])  # Exclude offline status
        ).order_by(MachineStatusEvent.time.asc()).limit(1000).all()
        
        status_history = [
            StatusEvent(time=event.time, status=event.status)
            for event in status_events_query
        ]

        machines.append(RunningSummaryMachine(
            machine_id=row.machine_id,
            machine_name=row.machine_name,
            current_status=current_status,
            total_run_time_seconds=total_run_time,
            total_run_time_formatted=format_duration(int(total_run_time)),
            run_percentage=round(run_percentage, 1),
            active_runs_count=row.runs_count or 0,
            last_run_start=row.last_run_start,
            current_program=row.current_program,
            status_history=status_history
        ))

    return RunningSummary(
        time_range=time_range,
        total_machines=len(machines),
        machines=machines
    )

@router.get("/summary/machines", response_model=MachinesSummary)
def get_machines_summary(
    db: Session = Depends(get_db),
    time_range: str = Query("8h", description="Time range for polling history: 1h, 8h, 24h, 7d")
):
    """
    Get unified fleet status summary: enabled CNC machines and Kaeser compressors.

    Returns all assets (online and offline) with polling history, uptime percentage,
    and connection health indicators. Matches the dashboard ONLINE count
    (machines + compressors).
    """
    # Parse time range to hours
    hours_map = {
        '1h': 1,
        '8h': 8,
        '24h': 24,
        '7d': 168,  # 7 days = 168 hours
    }
    hours = hours_map.get(time_range, 8)

    machines_query = db.query(Machine).filter(Machine.enabled == True).all()
    compressors_query = db.query(Compressor).filter(Compressor.enabled == True).all()

    assets_list: List[MachineStatusSummary] = []
    online_count = 0
    offline_count = 0

    backend_healthy = is_backend_healthy()
    ws = websocket_api.websocket_manager

    for machine in machines_query:
        is_online = False
        if polling_service:
            poller_status = polling_service.get_machine_status(machine.id)
            is_online = poller_status.get("is_online", False) if poller_status else False

        if is_online:
            online_count += 1
        elif backend_healthy:
            offline_count += 1

        polling_history = get_polling_history(machine.id, db, hours=hours)
        polling_history_8h = get_polling_history(machine.id, db, hours=8)
        polling_stats = calculate_polling_stats(polling_history_8h)
        uptime_8h_percent = polling_stats.success_rate

        if is_online:
            online_since_query = db.query(MachineStatusEvent.time).filter(
                MachineStatusEvent.machine_id == machine.id,
                MachineStatusEvent.status.notin_(['error', 'alarm'])
            ).order_by(MachineStatusEvent.time.desc()).first()
            status_changed_at = online_since_query.time if online_since_query else machine.last_seen_at
        else:
            last_status_query = db.query(MachineStatusEvent.time).filter(
                MachineStatusEvent.machine_id == machine.id
            ).order_by(MachineStatusEvent.time.desc()).first()
            status_changed_at = last_status_query.time if last_status_query else machine.last_seen_at

        online_fmt, offline_fmt, status_changed_at = _duration_fields_for_asset(
            is_online=is_online,
            backend_healthy=backend_healthy,
            last_seen_at=machine.last_seen_at,
            status_changed_at=status_changed_at,
        )

        cached_status = ws.get_machine_status(machine.id) if ws else None
        current_status = cached_status.get("status") if cached_status else None

        assets_list.append(MachineStatusSummary(
            machine_id=machine.id,
            machine_name=machine.name,
            asset_kind="cnc",
            is_online=is_online,
            uptime_8h_percent=uptime_8h_percent,
            current_status=current_status,
            connection_health=get_connection_health(machine.last_seen_at),
            online_duration_formatted=online_fmt,
            offline_duration_formatted=offline_fmt,
            status_changed_at=status_changed_at,
            polling_history_8h=polling_history,
            polling_summary=polling_stats,
        ))

    for compressor in compressors_query:
        cached = ws.get_compressor_status(compressor.id) if ws else {}
        is_online = bool(cached.get("is_online")) if cached else False

        if is_online:
            online_count += 1
        elif backend_healthy:
            offline_count += 1

        polling_history = get_compressor_polling_history(compressor.id, db, hours=hours)
        polling_history_8h = get_compressor_polling_history(compressor.id, db, hours=8)
        polling_stats = calculate_polling_stats(polling_history_8h)
        uptime_8h_percent = polling_stats.success_rate

        last_event = (
            db.query(CompressorStatusEvent.time)
            .filter(CompressorStatusEvent.compressor_id == compressor.id)
            .order_by(CompressorStatusEvent.time.desc())
            .first()
        )
        status_changed_at = last_event.time if last_event else compressor.last_seen_at

        online_fmt, offline_fmt, status_changed_at = _duration_fields_for_asset(
            is_online=is_online,
            backend_healthy=backend_healthy,
            last_seen_at=compressor.last_seen_at,
            status_changed_at=status_changed_at,
        )

        current_status = cached.get("status") if cached else None

        assets_list.append(MachineStatusSummary(
            machine_id=compressor.id,
            machine_name=compressor.name,
            asset_kind="compressor",
            is_online=is_online,
            uptime_8h_percent=uptime_8h_percent,
            current_status=current_status,
            connection_health=get_connection_health(compressor.last_seen_at),
            online_duration_formatted=online_fmt,
            offline_duration_formatted=offline_fmt,
            status_changed_at=status_changed_at,
            polling_history_8h=polling_history,
            polling_summary=polling_stats,
        ))

    # Online first, then by uptime
    assets_list.sort(
        key=lambda x: (
            not x.is_online,
            -x.uptime_8h_percent,
            x.machine_name.lower(),
        )
    )

    total = len(machines_query) + len(compressors_query)
    return MachinesSummary(
        total_machines=total,
        online_count=online_count,
        offline_count=offline_count,
        machines=assets_list,
    )
