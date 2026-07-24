"""Unit tests for MachinePoller helpers and skip paths."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.polling import MachinePoller


def _machine(mid: int = 1):
    return SimpleNamespace(
        id=mid,
        name="test-machine",
        ip_address="10.0.0.1",
        units="in",
        part_display_mode="parts",
    )


def test_should_log_history_on_change():
    poller = MachinePoller(_machine(), None)
    now = datetime.utcnow()
    should, reason = poller._should_log_history({"a": 1}, {"a": 0}, now, now)
    assert should is True
    assert reason == "change"


def test_should_log_history_heartbeat():
    poller = MachinePoller(_machine(), None)
    poller.heartbeat_interval_minutes = 5
    now = datetime.utcnow()
    last = now - timedelta(minutes=6)
    should, reason = poller._should_log_history({"a": 1}, {"a": 1}, last, now)
    assert should is True
    assert reason == "heartbeat"


def test_should_log_history_hold():
    poller = MachinePoller(_machine(), None)
    poller.heartbeat_interval_minutes = 5
    now = datetime.utcnow()
    last = now - timedelta(minutes=1)
    should, reason = poller._should_log_history({"a": 1}, {"a": 1}, last, now)
    assert should is False
    assert reason == ""


def test_should_log_history_first_sight():
    poller = MachinePoller(_machine(), None)
    now = datetime.utcnow()
    should, reason = poller._should_log_history({"a": 1}, {"a": 1}, None, now)
    assert should is True
    assert reason == "heartbeat"


@pytest.mark.asyncio
async def test_poll_tool_data_skips_when_operating():
    poller = MachinePoller(_machine(), None)
    poller.last_known_prd3_status = "operating"
    with patch("app.services._machine_poller.CNCTelnetClient") as ctor:
        result = await poller.poll_tool_data()
    assert result == {}
    ctor.assert_not_called()


def test_display_online_helpers_still_imported():
    # Smoke: poller constructs with notification_service=None
    poller = MachinePoller(_machine(), MagicMock())
    assert poller.consecutive_failures == 0
