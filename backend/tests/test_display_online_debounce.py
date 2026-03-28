"""Tests for debounced display_online and failure payloads on MachinePoller."""
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.polling import MachinePoller


def _discard_create_task(coro):
    coro.close()
    return MagicMock()


def _machine(mid: int = 1):
    return SimpleNamespace(
        id=mid,
        name="test-machine",
        ip_address="10.0.0.1",
        units="in",
        part_display_mode="parts",
    )


def test_display_online_never_succeeded():
    poller = MachinePoller(_machine(), None)
    poller.consecutive_failures = 0
    assert poller.display_online() is False


def test_display_online_after_success_clear_failures():
    poller = MachinePoller(_machine(), None)
    poller.last_successful_fast_poll_at = datetime.utcnow()
    poller.consecutive_failures = 0
    assert poller.display_online() is True


def test_display_online_transient_failures_below_threshold():
    poller = MachinePoller(_machine(), None)
    poller.last_successful_fast_poll_at = datetime.utcnow()
    poller.consecutive_failures = 2
    assert poller.display_online() is True


def test_display_online_at_threshold_offline():
    poller = MachinePoller(_machine(), None)
    poller.last_successful_fast_poll_at = datetime.utcnow()
    poller.consecutive_failures = 3
    assert poller.display_online() is False


@patch("app.services.polling.asyncio.create_task", _discard_create_task)
def test_finalize_poll_failure_softens_payload_below_threshold():
    ws = MagicMock()
    ws.get_machine_status.return_value = {"status": "operating", "last_successful_poll_at": "2020-01-01T00:00:00"}

    poller = MachinePoller(_machine(), ws)
    poller.last_successful_fast_poll_at = datetime.utcnow()
    poller.last_known_prd3_status = "standby"
    poller.consecutive_failures = 0

    ts = datetime.utcnow()
    payload = poller._finalize_poll_failure(RuntimeError("montr hiccup"), ts, time.time())

    assert payload["consecutive_failures"] == 1
    assert payload["is_online"] is True
    assert payload["status"] == "operating"
    assert "error" not in payload
    assert poller.is_online is True


@patch("app.services.polling.asyncio.create_task", _discard_create_task)
def test_finalize_poll_failure_full_offline_at_threshold():
    ws = MagicMock()
    ws.get_machine_status.return_value = {"status": "operating"}

    poller = MachinePoller(_machine(), ws)
    poller.last_successful_fast_poll_at = datetime.utcnow()
    poller.consecutive_failures = 2  # next increment -> 3

    ts = datetime.utcnow()
    payload = poller._finalize_poll_failure(ConnectionError("dead"), ts, time.time())

    assert payload["consecutive_failures"] == 3
    assert payload["is_online"] is False
    assert payload["status"] == "off"
    assert payload["error"] == "dead"
    assert poller.is_online is False


@patch("app.services.polling.asyncio.create_task", _discard_create_task)
def test_finalize_poll_failure_uses_last_known_when_cache_empty():
    ws = MagicMock()
    ws.get_machine_status.return_value = {}

    poller = MachinePoller(_machine(), ws)
    poller.last_successful_fast_poll_at = datetime.utcnow()
    poller.last_known_prd3_status = "standby"
    poller.consecutive_failures = 0

    ts = datetime.utcnow()
    payload = poller._finalize_poll_failure(RuntimeError("x"), ts, time.time())

    assert payload["is_online"] is True
    assert payload["status"] == "standby"
