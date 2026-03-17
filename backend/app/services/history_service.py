"""History service utilities for cycle history, PRD3 status, counters, and alarms."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.event import PRD3StatusHistory, CounterHistory, AlarmEvent
from app.core.config import settings


def _build_status_intervals(
    rows: List[PRD3StatusHistory],
) -> List[Dict[str, Any]]:
    """
    Build contiguous status intervals from ordered PRD3StatusHistory rows.

    Each interval is a dict with:
        - start_time
        - end_time (may be None for the last/open interval)
        - status
        - status_code
        - program_no
        - error_no
        - folder_name
    """
    intervals: List[Dict[str, Any]] = []
    if not rows:
        return intervals

    # Rows are expected to be ordered by time ascending
    for idx, row in enumerate(rows):
        next_row: Optional[PRD3StatusHistory] = rows[idx + 1] if idx + 1 < len(rows) else None
        start_time = row.time
        end_time = next_row.time if next_row is not None else None

        intervals.append(
            {
                "start_time": start_time,
                "end_time": end_time,
                "status": row.status,
                "status_code": row.status_code,
                "program_no": row.program_no,
                "error_no": row.error_no,
                "folder_name": row.folder_name,
            }
        )

    return intervals


def _build_operating_intervals(
    rows: List[PRD3StatusHistory],
) -> List[Dict[str, Any]]:
    """
    Build operating intervals (candidate cycles) from ordered PRD3StatusHistory rows.
    """
    intervals: List[Dict[str, Any]] = []
    if not rows:
        return intervals

    # Rows are expected to be ordered by time ascending
    for idx, row in enumerate(rows):
        next_row: Optional[PRD3StatusHistory] = rows[idx + 1] if idx + 1 < len(rows) else None
        start_time = row.time
        end_time = next_row.time if next_row is not None else None

        if row.status == "operating" and row.program_no:
            intervals.append(
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": row.status,
                    "status_code": row.status_code,
                    "program_no": row.program_no,
                    "folder_name": row.folder_name,
                }
            )

    return intervals


def _compute_counter_increments_for_interval(
    snapshots: List[CounterHistory],
) -> Dict[int, int]:
    """
    Compute per-counter increments within a time interval from CounterHistory snapshots.

    This uses only snapshots inside the interval and compares each snapshot to the
    previous snapshot within the same interval. It may undercount if the first
    snapshot in the interval already includes increments that happened before it.
    """
    if not snapshots:
        return {}

    # Sort snapshots by time just in case
    snapshots_sorted = sorted(snapshots, key=lambda s: s.time)
    last_counts: Dict[int, int] = {}
    increments: Dict[int, int] = {}

    for snap in snapshots_sorted:
        data = snap.data or []
        for counter in data:
            counter_number = counter.get("counter_number")
            count = counter.get("count")
            if counter_number is None or count is None:
                continue

            prev = last_counts.get(counter_number)
            if prev is not None and count > prev:
                delta = count - prev
                increments[counter_number] = increments.get(counter_number, 0) + delta
            last_counts[counter_number] = count

    return increments


def get_cycle_history(
    db: Session,
    machine_id: int,
    since: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Build recent cycle history for a machine by joining PRD3 status history,
    counter increments, and alarms.

    Returns a list of dicts:
        - program_no
        - folder_name
        - start_time
        - end_time
        - duration_seconds
        - part_count (total across counters)
        - parts_by_counter {counter_number: count}
        - alarms: list of alarms during the run
    """
    if since is None:
        # Use configured local timezone for default "last 24h" window.
        try:
            tz = ZoneInfo(settings.LOCAL_TIMEZONE)
        except Exception:
            tz = timezone.utc
        since = datetime.now(tz) - timedelta(hours=24)

    # Load PRD3 status history for this machine since the given time
    prd3_rows: List[PRD3StatusHistory] = (
        db.query(PRD3StatusHistory)
        .filter(
            PRD3StatusHistory.machine_id == machine_id,
            PRD3StatusHistory.time >= since,
        )
        .order_by(PRD3StatusHistory.time.asc())
        .all()
    )

    # Full status intervals (all statuses) for detailed timing
    status_intervals = _build_status_intervals(prd3_rows)

    # Operating intervals (candidate cycles)
    intervals = _build_operating_intervals(prd3_rows)
    if not intervals:
        return []

    # Only keep the requested window of intervals (based on start_time), with pagination.
    # Sort by start_time descending (most recent first), then apply offset/limit slice,
    # then restore ascending order for per-interval processing.
    intervals = sorted(intervals, key=lambda i: i["start_time"], reverse=True)
    if offset < 0:
        offset = 0
    if limit <= 0:
        return []
    intervals = intervals[offset : offset + limit]
    intervals = sorted(intervals, key=lambda i: i["start_time"])  # back to ascending

    cycle_history: List[Dict[str, Any]] = []

    # Resolve timezone once
    try:
        tz = ZoneInfo(settings.LOCAL_TIMEZONE)
    except Exception:
        tz = timezone.utc

    for interval in intervals:
        start_time = interval["start_time"]
        end_time = interval["end_time"]

        # Normalize to configured local timezone for comparisons and durations
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=tz)
        else:
            start_time = start_time.astimezone(tz)

        if end_time is None:
            end_time = datetime.now(tz)
        elif end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=tz)
        else:
            end_time = end_time.astimezone(tz)

        # Compute per-status timing within this cycle window using full status intervals
        time_by_status: Dict[str, int] = {}
        for s_int in status_intervals:
            s_start = s_int["start_time"]
            s_end = s_int["end_time"]

            # Normalize status interval times
            if s_start.tzinfo is None:
                s_start = s_start.replace(tzinfo=tz)
            else:
                s_start = s_start.astimezone(tz)

            if s_end is None:
                s_end = datetime.now(tz)
            elif s_end.tzinfo is None:
                s_end = s_end.replace(tzinfo=tz)
            else:
                s_end = s_end.astimezone(tz)

            # Overlap between status interval and cycle window
            overlap_start = max(start_time, s_start)
            overlap_end = min(end_time, s_end)
            if overlap_end <= overlap_start:
                continue

            seconds = int((overlap_end - overlap_start).total_seconds())
            if seconds <= 0:
                continue

            status = s_int["status"]
            time_by_status[status] = time_by_status.get(status, 0) + seconds

        # Derive total duration from summed per-status times (fallback to end-start)
        total_duration = sum(time_by_status.values())
        if total_duration <= 0:
            total_duration = int((end_time - start_time).total_seconds())

        # Counter increments within this interval
        counter_snapshots: List[CounterHistory] = (
            db.query(CounterHistory)
            .filter(
                CounterHistory.machine_id == machine_id,
                CounterHistory.time >= start_time,
                CounterHistory.time < end_time,
            )
            .order_by(CounterHistory.time.asc())
            .all()
        )
        parts_by_counter = _compute_counter_increments_for_interval(counter_snapshots)
        total_parts = sum(parts_by_counter.values())

        # Alarms within this interval
        alarms: List[AlarmEvent] = (
            db.query(AlarmEvent)
            .filter(
                AlarmEvent.machine_id == machine_id,
                AlarmEvent.time >= start_time,
                AlarmEvent.time < end_time,
            )
            .order_by(AlarmEvent.time.asc())
            .all()
        )

        cycle_history.append(
            {
                "program_no": interval["program_no"],
                "folder_name": interval.get("folder_name"),
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": total_duration,
                "time_by_status": time_by_status,
                "part_count": total_parts,
                "parts_by_counter": parts_by_counter,
                "alarms": alarms,
            }
        )

    # Sort final result by start_time descending (most recent first)
    cycle_history.sort(key=lambda r: r["start_time"], reverse=True)
    return cycle_history


def get_production_runs_timeline(
    db: Session,
    machine_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Build a high-level production runs timeline by grouping sequential operating
    intervals with the same program_no into runs, and embedding status segments
    (operating/standby/stopped/error/off) inside each run window.
    """
    # Resolve time window (default: last 24h in configured local timezone)
    try:
        tz = ZoneInfo(settings.LOCAL_TIMEZONE)
    except Exception:
        tz = timezone.utc

    if end_time is None:
        end_time = datetime.now(tz)
    if start_time is None:
        start_time = end_time - timedelta(hours=24)

    # Normalize window to UTC for DB queries (timestamps are stored as timestamptz)
    if start_time.tzinfo is None:
        start_utc = start_time.replace(tzinfo=tz).astimezone(timezone.utc)
    else:
        start_utc = start_time.astimezone(timezone.utc)

    if end_time.tzinfo is None:
        end_utc = end_time.replace(tzinfo=tz).astimezone(timezone.utc)
    else:
        end_utc = end_time.astimezone(timezone.utc)

    # Load PRD3 status history rows for this machine and window
    prd3_rows: List[PRD3StatusHistory] = (
        db.query(PRD3StatusHistory)
        .filter(
            PRD3StatusHistory.machine_id == machine_id,
            PRD3StatusHistory.time >= start_utc,
            PRD3StatusHistory.time <= end_utc,
        )
        .order_by(PRD3StatusHistory.time.asc())
        .all()
    )

    if not prd3_rows:
        return []

    status_intervals = _build_status_intervals(prd3_rows)

    # Build primitive operating intervals (per-cycle slices)
    operating_intervals = _build_operating_intervals(prd3_rows)
    if not operating_intervals:
        return []

    # Group operating intervals into runs by contiguous same-program sequences.
    runs: List[Dict[str, Any]] = []
    current_run: Optional[Dict[str, Any]] = None

    for op in operating_intervals:
        prog = op["program_no"]
        op_start = op["start_time"]
        op_end = op["end_time"] or end_utc

        if current_run is None:
            current_run = {
                "program_no": prog,
                "run_start": op_start,
                "run_end": op_end,
                "cycles": 1,
            }
            continue

        # Same program: extend current run, even if there were off/error/standby
        # periods between cycles. We only break runs when the program changes.
        if current_run["program_no"] == prog:
            current_run["run_end"] = max(current_run["run_end"], op_end)
            current_run["cycles"] += 1
            continue

        # Different program or large gap: close current run and start a new one
        runs.append(current_run)
        current_run = {
            "program_no": prog,
            "run_start": op_start,
            "run_end": op_end,
            "cycles": 1,
        }

    if current_run is not None:
        runs.append(current_run)

    if not runs:
        return []

    # For each run, collect status segments and parts.
    timeline: List[Dict[str, Any]] = []

    for run in runs:
        rs = run["run_start"]
        re = run["run_end"]

        # Normalize run window to local tz for display and for subsequent queries
        rs_local = rs.astimezone(tz) if rs.tzinfo else rs.replace(tzinfo=tz)
        re_local = re.astimezone(tz) if re.tzinfo else re.replace(tzinfo=tz)

        # Build status segments by intersecting full status_intervals with run window
        segments: List[Dict[str, Any]] = []
        for s in status_intervals:
            s_start = s["start_time"]
            s_end = s["end_time"] or end_utc

            # Work in local time for consistency
            s_start_local = s_start.astimezone(tz) if s_start.tzinfo else s_start.replace(tzinfo=tz)
            s_end_local = s_end.astimezone(tz) if s_end.tzinfo else s_end.replace(tzinfo=tz)

            seg_start = max(rs_local, s_start_local)
            seg_end = min(re_local, s_end_local)
            if seg_end <= seg_start:
                continue

            segments.append(
                {
                    "status": s["status"],
                    "status_code": s.get("status_code"),
                    "start_time": seg_start,
                    "end_time": seg_end,
                    "error_no": s.get("error_no"),
                }
            )

        # Parts within the run window
        counter_snaps: List[CounterHistory] = (
            db.query(CounterHistory)
            .filter(
                CounterHistory.machine_id == machine_id,
                CounterHistory.time >= rs_local,
                CounterHistory.time < re_local,
            )
            .order_by(CounterHistory.time.asc())
            .all()
        )
        parts_by_counter = _compute_counter_increments_for_interval(counter_snaps)
        total_parts = sum(parts_by_counter.values())

        # Assemble run record (normalize run_start/run_end to local tz)
        timeline.append(
            {
                "program_no": run["program_no"],
                "run_start": rs_local,
                "run_end": re_local,
                "cycles": run["cycles"],
                "segments": segments,
                "part_count": total_parts,
                "parts_by_counter": parts_by_counter,
            }
        )

    # Newest runs first
    timeline.sort(key=lambda r: r["run_start"], reverse=True)
    return timeline
