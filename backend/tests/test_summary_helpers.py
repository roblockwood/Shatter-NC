"""Pure helper tests for summary API."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.summary import (
    PollingDataPoint,
    calculate_polling_stats,
    format_duration,
    get_connection_health,
    is_backend_healthy,
    parse_time_range,
    set_polling_service,
)


def test_format_duration():
    assert format_duration(-1) == "0m"
    assert format_duration(45) == "0m"
    assert format_duration(90) == "1m"
    assert format_duration(3661) == "1h 1m"


def test_parse_time_range():
    assert parse_time_range("24h") == timedelta(hours=24)
    assert parse_time_range("7d") == timedelta(days=7)
    with pytest.raises(HTTPException):
        parse_time_range("bogus")


def test_get_connection_health():
    assert get_connection_health(None) == "stale"
    assert get_connection_health(datetime.utcnow()) == "healthy"
    assert get_connection_health(datetime.utcnow() - timedelta(minutes=2)) == "degraded"
    assert get_connection_health(datetime.utcnow() - timedelta(hours=1)) == "stale"


def test_is_backend_healthy_no_service():
    set_polling_service(None)
    assert is_backend_healthy() is False


def test_is_backend_healthy_not_running():
    svc = MagicMock()
    svc.is_running = False
    set_polling_service(svc)
    assert is_backend_healthy() is False
    set_polling_service(None)


def test_is_backend_healthy_with_pollers():
    svc = MagicMock()
    svc.is_running = True
    svc.pollers = {1: MagicMock()}
    set_polling_service(svc)
    with patch("app.db.base.SessionLocal") as session_local:
        db = MagicMock()
        session_local.return_value = db
        db.query.return_value.filter.return_value.first.return_value = MagicMock()
        assert is_backend_healthy() is True
    set_polling_service(None)


def test_calculate_polling_stats_empty():
    stats = calculate_polling_stats([])
    assert stats.total_polls == 0
    assert stats.success_rate == 0.0


def test_calculate_polling_stats():
    now = datetime.utcnow()
    history = [
        PollingDataPoint(time=now, success=True, response_time_ms=10),
        PollingDataPoint(time=now, success=True, response_time_ms=20),
        PollingDataPoint(time=now, success=False, response_time_ms=None),
    ]
    stats = calculate_polling_stats(history)
    assert stats.total_polls == 3
    assert stats.successful_polls == 2
    assert stats.failed_polls == 1
    assert stats.avg_response_time_ms == 15
    assert stats.current_streak == -1


def test_compressor_sample_success_from_metrics():
    from app.api.summary import _compressor_sample_success

    online = MagicMock(metrics={"is_online": True}, status="load")
    offline = MagicMock(metrics={"is_online": False}, status="offline")
    assert _compressor_sample_success(online) is True
    assert _compressor_sample_success(offline) is False


def test_compressor_sample_success_from_status():
    from app.api.summary import _compressor_sample_success

    load = MagicMock(metrics=None, status="load")
    off = MagicMock(metrics={}, status="offline")
    assert _compressor_sample_success(load) is True
    assert _compressor_sample_success(off) is False


def test_duration_fields_online():
    from app.api.summary import _duration_fields_for_asset

    changed = datetime.utcnow() - timedelta(minutes=5)
    online_fmt, offline_fmt, _ = _duration_fields_for_asset(
        is_online=True,
        backend_healthy=True,
        last_seen_at=changed,
        status_changed_at=changed,
    )
    assert online_fmt == "5m"
    assert offline_fmt == ""


def test_is_backend_healthy_compressor_only():
    from app.api import summary as summary_mod

    set_polling_service(None)
    summary_mod.compressor_polling_service = MagicMock(is_running=True, pollers={1: MagicMock()})
    assert is_backend_healthy() is True
    summary_mod.compressor_polling_service = None
