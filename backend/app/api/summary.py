from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, text
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.base import get_db
from app.models.machine import Machine
from app.models.event import ProductionRun, MachineStatusEvent

router = APIRouter()

# Polling service and WebSocket manager will be injected from main.py
# These are initialized in main.py and accessed as globals
from app.api.websocket import websocket_manager
polling_service = None

def set_polling_service(service):
    """Inject the polling service from main.py"""
    global polling_service
    polling_service = service

# Pydantic models for responses

class PollingDataPoint(BaseModel):
    """Single polling history data point."""
    time: datetime
    success: bool
    response_time_ms: Optional[int] = None

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

class RunningSummary(BaseModel):
    time_range: str
    total_machines: int
    machines: List[RunningSummaryMachine]

class OnlineSummaryMachine(BaseModel):
    machine_id: int
    machine_name: str
    is_online: bool
    online_since: Optional[datetime] = None
    online_duration_seconds: int
    online_duration_formatted: str
    last_seen_at: Optional[datetime] = None
    connection_health: str
    polling_history_8h: List[PollingDataPoint]

class OnlineSummary(BaseModel):
    total_online: int
    machines: List[OnlineSummaryMachine]

class OfflineSummaryMachine(BaseModel):
    machine_id: int
    machine_name: str
    is_online: bool
    offline_since: Optional[datetime] = None
    offline_duration_seconds: int
    offline_duration_formatted: str
    last_seen_at: Optional[datetime] = None
    last_known_status: Optional[str] = None
    enabled: bool
    polling_history_8h: List[PollingDataPoint]

class OfflineSummary(BaseModel):
    total_offline: int
    machines: List[OfflineSummaryMachine]

class PollingStatsSummary(BaseModel):
    """Summary statistics for polling history."""
    total_polls: int
    successful_polls: int
    failed_polls: int
    success_rate: float  # 0-100%
    avg_response_time_ms: Optional[int] = None
    current_streak: int  # positive = consecutive successes, negative = consecutive failures

class MachineStatusSummary(BaseModel):
    """Unified machine status with polling data."""
    machine_id: int
    machine_name: str
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
    """Summary of all machine statuses."""
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
    time_range: str = Query(default="24h", regex="^(1h|4h|24h|7d|30d)$"),
    db: Session = Depends(get_db)
):
    """
    Get running summary showing machines sorted by total run time within the specified time range.

    Query Parameters:
    - time_range: One of '1h', '4h', '24h', '7d', '30d' (default: '24h')

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

        # Get current status from WebSocket cache
        cached_status = websocket_manager.get_machine_status(row.machine_id) if websocket_manager else None
        current_status = cached_status.get("status") if cached_status else None

        machines.append(RunningSummaryMachine(
            machine_id=row.machine_id,
            machine_name=row.machine_name,
            current_status=current_status,
            total_run_time_seconds=total_run_time,
            total_run_time_formatted=format_duration(int(total_run_time)),
            run_percentage=round(run_percentage, 1),
            active_runs_count=row.runs_count or 0,
            last_run_start=row.last_run_start,
            current_program=row.current_program
        ))

    return RunningSummary(
        time_range=time_range,
        total_machines=len(machines),
        machines=machines
    )

@router.get("/summary/online", response_model=OnlineSummary)
def get_online_summary(db: Session = Depends(get_db)):
    """
    DEPRECATED: Use /summary/machines instead for unified machine status view.

    Get online summary showing all currently online machines with connection health and service status.

    Returns machines with online duration, connection health indicators, and service availability.
    Uses the polling service as the source of truth for online status.
    """
    # Get all enabled machines
    machines_query = db.query(Machine).filter(Machine.enabled == True).all()

    online_machines = []

    for machine in machines_query:
        # Use polling service as source of truth for online status
        is_online = False
        if polling_service:
            poller_status = polling_service.get_machine_status(machine.id)
            is_online = poller_status.get("is_online", False) if poller_status else False

        # Only include online machines
        if not is_online:
            continue

        # Calculate online duration
        # Find most recent status change to online in machine_status_events
        online_since_query = db.query(MachineStatusEvent.time).filter(
            MachineStatusEvent.machine_id == machine.id,
            MachineStatusEvent.status.notin_(['error', 'alarm'])
        ).order_by(MachineStatusEvent.time.desc()).first()

        online_since = online_since_query.time if online_since_query else machine.last_seen_at

        # Calculate duration
        now = datetime.utcnow()
        if online_since:
            online_since_naive = online_since.replace(tzinfo=None) if online_since.tzinfo else online_since
            duration_seconds = int((now - online_since_naive).total_seconds())
        else:
            duration_seconds = 0

        # Get connection health
        connection_health = get_connection_health(machine.last_seen_at)

        # Get polling history for the trailing 8 hours
        polling_history = get_polling_history(machine.id, db, hours=8)

        online_machines.append(OnlineSummaryMachine(
            machine_id=machine.id,
            machine_name=machine.name,
            is_online=True,
            online_since=online_since,
            online_duration_seconds=duration_seconds,
            online_duration_formatted=format_duration(duration_seconds),
            last_seen_at=machine.last_seen_at,
            connection_health=connection_health,
            polling_history_8h=polling_history
        ))

    # Sort by online duration descending
    online_machines.sort(key=lambda x: x.online_duration_seconds, reverse=True)

    return OnlineSummary(
        total_online=len(online_machines),
        machines=online_machines
    )

@router.get("/summary/offline", response_model=OfflineSummary)
def get_offline_summary(db: Session = Depends(get_db)):
    """
    DEPRECATED: Use /summary/machines instead for unified machine status view.

    Get offline summary showing all currently offline machines with downtime and service errors.

    Returns machines that are offline with offline duration, service failure reasons,
    and last known status.
    Uses the polling service as the source of truth for online status.
    """
    # Get all enabled machines
    machines_query = db.query(Machine).filter(Machine.enabled == True).all()

    offline_machines = []

    for machine in machines_query:
        # Use polling service as source of truth for online status
        is_online = False
        if polling_service:
            poller_status = polling_service.get_machine_status(machine.id)
            is_online = poller_status.get("is_online", False) if poller_status else False

        # Only include offline machines
        if is_online:
            continue

        # Get last known status from machine_status_events
        last_status_query = db.query(
            MachineStatusEvent.time,
            MachineStatusEvent.status
        ).filter(
            MachineStatusEvent.machine_id == machine.id
        ).order_by(MachineStatusEvent.time.desc()).first()

        offline_since = last_status_query.time if last_status_query else machine.last_seen_at
        last_known_status = last_status_query.status if last_status_query else None

        # Calculate offline duration
        now = datetime.utcnow()
        if offline_since:
            offline_since_naive = offline_since.replace(tzinfo=None) if offline_since.tzinfo else offline_since
            duration_seconds = int((now - offline_since_naive).total_seconds())
        else:
            duration_seconds = 0

        # Get polling history for the trailing 8 hours
        polling_history = get_polling_history(machine.id, db, hours=8)

        offline_machines.append(OfflineSummaryMachine(
            machine_id=machine.id,
            machine_name=machine.name,
            is_online=False,
            offline_since=offline_since,
            offline_duration_seconds=duration_seconds,
            offline_duration_formatted=format_duration(duration_seconds),
            last_seen_at=machine.last_seen_at,
            last_known_status=last_known_status,
            enabled=machine.enabled,
            polling_history_8h=polling_history
        ))

    # Sort by offline duration descending
    offline_machines.sort(key=lambda x: x.offline_duration_seconds, reverse=True)

    return OfflineSummary(
        total_offline=len(offline_machines),
        machines=offline_machines
    )

@router.get("/summary/machines", response_model=MachinesSummary)
def get_machines_summary(db: Session = Depends(get_db)):
    """
    Get unified machine status summary showing all enabled machines with polling data.

    Returns all machines (online and offline) with polling history, uptime percentage,
    and connection health indicators. This is a unified view replacing separate
    online/offline summaries.

    Uses the polling service as the source of truth for online status.
    """
    # Get all enabled machines
    machines_query = db.query(Machine).filter(Machine.enabled == True).all()

    machines_list = []
    online_count = 0
    offline_count = 0

    for machine in machines_query:
        # Use polling service as source of truth for online status
        is_online = False
        if polling_service:
            poller_status = polling_service.get_machine_status(machine.id)
            is_online = poller_status.get("is_online", False) if poller_status else False

        if is_online:
            online_count += 1
        else:
            offline_count += 1

        # Get polling history (trailing 1 hour for detailed graph, but calculate stats over 8 hours)
        polling_history = get_polling_history(machine.id, db, hours=1)

        # Also get 8-hour history for calculating full stats
        polling_history_8h = get_polling_history(machine.id, db, hours=8)

        # Calculate polling stats from full 8-hour history
        polling_stats = calculate_polling_stats(polling_history_8h)

        # Calculate uptime percentage (same as success rate for 8h window)
        uptime_8h_percent = polling_stats.success_rate

        # Calculate current duration (online or offline)
        now = datetime.utcnow()

        if is_online:
            # Calculate how long online
            online_since_query = db.query(MachineStatusEvent.time).filter(
                MachineStatusEvent.machine_id == machine.id,
                MachineStatusEvent.status.notin_(['error', 'alarm'])
            ).order_by(MachineStatusEvent.time.desc()).first()

            online_since = online_since_query.time if online_since_query else machine.last_seen_at
            status_changed_at = online_since

            if online_since:
                online_since_naive = online_since.replace(tzinfo=None) if online_since.tzinfo else online_since
                duration_seconds = int((now - online_since_naive).total_seconds())
            else:
                duration_seconds = 0

            online_duration_formatted = format_duration(duration_seconds)
            offline_duration_formatted = ""
        else:
            # Calculate how long offline
            last_status_query = db.query(
                MachineStatusEvent.time,
                MachineStatusEvent.status
            ).filter(
                MachineStatusEvent.machine_id == machine.id
            ).order_by(MachineStatusEvent.time.desc()).first()

            offline_since = last_status_query.time if last_status_query else machine.last_seen_at
            status_changed_at = offline_since

            if offline_since:
                offline_since_naive = offline_since.replace(tzinfo=None) if offline_since.tzinfo else offline_since
                duration_seconds = int((now - offline_since_naive).total_seconds())
            else:
                duration_seconds = 0

            online_duration_formatted = ""
            offline_duration_formatted = format_duration(duration_seconds)

        # Get current status from WebSocket cache
        cached_status = websocket_manager.get_machine_status(machine.id) if websocket_manager else None
        current_status = cached_status.get("status") if cached_status else None

        # Get connection health
        connection_health = get_connection_health(machine.last_seen_at)

        machines_list.append(MachineStatusSummary(
            machine_id=machine.id,
            machine_name=machine.name,
            is_online=is_online,
            uptime_8h_percent=uptime_8h_percent,
            current_status=current_status,
            connection_health=connection_health,
            online_duration_formatted=online_duration_formatted,
            offline_duration_formatted=offline_duration_formatted,
            status_changed_at=status_changed_at,
            polling_history_8h=polling_history,
            polling_summary=polling_stats
        ))

    # Sort by online status first (online machines first), then by current duration
    machines_list.sort(
        key=lambda x: (
            not x.is_online,  # False (online) sorts before True (offline)
            -(
                # Duration of current state
                int(x.polling_summary.success_rate * 100) if x.is_online
                else int(x.polling_summary.success_rate * 100)
            )
        )
    )

    return MachinesSummary(
        total_machines=len(machines_query),
        online_count=online_count,
        offline_count=offline_count,
        machines=machines_list
    )
