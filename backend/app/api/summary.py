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
from app.api import websocket as websocket_api
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
    """
    if not polling_service:
        return False
    
    if not polling_service.is_running:
        return False
    
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
            return False
        
        # If we have pollers but no recent polls, backend might be starting up
        # Allow a grace period of 15 seconds after startup
        if not recent_poll:
            # Check if there are any polling events at all (backend has polled before)
            any_poll = db.query(PollingEvent).first()
            if not any_poll:
                # No polls ever - backend just started, give it grace period
                return False
        
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
    time_range: str = Query(default="24h", regex="^(1h|4h|8h|24h|7d|30d)$"),
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
    Get unified machine status summary showing all enabled machines with polling data.

    Returns all machines (online and offline) with polling history, uptime percentage,
    and connection health indicators. This is a unified view replacing separate
    online/offline summaries.

    Uses the polling service as the source of truth for online status.
    """
    # Parse time range to hours
    hours_map = {
        '1h': 1,
        '8h': 8,
        '24h': 24,
        '7d': 168,  # 7 days = 168 hours
    }
    hours = hours_map.get(time_range, 8)
    # Get all enabled machines
    machines_query = db.query(Machine).filter(Machine.enabled == True).all()

    machines_list = []
    online_count = 0
    offline_count = 0

    # Check if backend is healthy before marking machines as offline
    backend_healthy = is_backend_healthy()
    
    for machine in machines_query:
        # Use polling service as source of truth for online status
        is_online = False
        if polling_service:
            poller_status = polling_service.get_machine_status(machine.id)
            is_online = poller_status.get("is_online", False) if poller_status else False
        
        # Only mark as offline if backend is healthy AND machine is not responding
        # If backend was down, we can't know machine status, so don't mark as offline
        if is_online:
            online_count += 1
        elif backend_healthy:
            # Backend is healthy but machine is not responding - truly offline
            offline_count += 1
        else:
            # Backend is not healthy - can't determine machine status
            # Don't count as offline, but also don't count as online
            # This prevents false offline status when backend restarts
            pass

        # Get polling history for the specified time range
        polling_history = get_polling_history(machine.id, db, hours=hours)

        # Also get 8-hour history for calculating full stats (for uptime percentage)
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
        elif backend_healthy:
            # Backend is healthy but machine is not responding - calculate offline duration
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
        else:
            # Backend is not healthy - can't determine machine status
            # Use last known status but don't calculate offline duration
            # This prevents false offline timestamps when backend was down
            last_status_query = db.query(
                MachineStatusEvent.time,
                MachineStatusEvent.status
            ).filter(
                MachineStatusEvent.machine_id == machine.id
            ).order_by(MachineStatusEvent.time.desc()).first()

            status_changed_at = last_status_query.time if last_status_query else machine.last_seen_at
            online_duration_formatted = ""
            offline_duration_formatted = ""  # Don't show offline duration when backend was down

        # Get current status from WebSocket cache
        cached_status = websocket_api.websocket_manager.get_machine_status(machine.id) if websocket_api.websocket_manager else None
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
