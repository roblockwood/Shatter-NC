"""Tests for history_service pure helpers."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.history_service import (
    _build_operating_intervals,
    _build_status_intervals,
    _compute_counter_increments_for_interval,
)


def _row(**kwargs):
    defaults = {
        "time": datetime(2024, 1, 1, 12, 0, 0),
        "status": "standby",
        "status_code": 2,
        "program_no": None,
        "error_no": None,
        "folder_name": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_status_intervals_empty():
    assert _build_status_intervals([]) == []


def test_build_status_intervals_contiguous():
    t0 = datetime(2024, 1, 1, 12, 0, 0)
    t1 = t0 + timedelta(minutes=5)
    t2 = t0 + timedelta(minutes=10)
    rows = [
        _row(time=t0, status="standby"),
        _row(time=t1, status="operating", program_no="O1000"),
        _row(time=t2, status="standby"),
    ]
    intervals = _build_status_intervals(rows)
    assert len(intervals) == 3
    assert intervals[0]["end_time"] == t1
    assert intervals[1]["status"] == "operating"
    assert intervals[2]["end_time"] is None


def test_build_operating_intervals_filters():
    t0 = datetime(2024, 1, 1, 12, 0, 0)
    rows = [
        _row(time=t0, status="operating", program_no="O1"),
        _row(time=t0, status="operating", program_no=None),
        _row(time=t0, status="standby", program_no="O1"),
    ]
    intervals = _build_operating_intervals(rows)
    assert len(intervals) == 1
    assert intervals[0]["program_no"] == "O1"


def test_compute_counter_increments():
    assert _compute_counter_increments_for_interval([]) == {}
    t0 = datetime(2024, 1, 1, 12, 0, 0)
    snaps = [
        SimpleNamespace(time=t0, data=[{"counter_number": 1, "count": 5}]),
        SimpleNamespace(
            time=t0 + timedelta(minutes=1),
            data=[{"counter_number": 1, "count": 8}, {"counter_number": 2, "count": 1}],
        ),
        SimpleNamespace(
            time=t0 + timedelta(minutes=2),
            data=[{"counter_number": 1, "count": 8}, {"counter_number": 2, "count": 1}],
        ),
    ]
    increments = _compute_counter_increments_for_interval(snaps)
    assert increments[1] == 3
    assert 2 not in increments  # no increase
