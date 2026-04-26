"""Seam-level tests for app.services.polling.

These tests lock in the public interface of the polling service so that a
split into sub-modules (MachinePoller / PollingService) can be verified
without requiring a running DB or live machine connection.

Tests cover:
  - Both classes are importable from app.services.polling
  - Constructor signatures accept the expected arguments
  - Key public methods / properties exist on each class
  - PollingService.get_machine_status returns None for unknown machine
  - PollingService.get_all_status returns a dict
  - MachinePoller.display_online property exists and is a bool
"""
import inspect
import pytest

from app.services.polling import MachinePoller, PollingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeWebsocketManager:
    """Minimal stand-in for WebsocketManager used in constructor tests."""
    async def broadcast_status(self, machine_id, data):
        pass


class _FakeMachine:
    """Minimal stand-in for Machine ORM object."""
    id = 1
    name = "Test Machine"
    ip_address = "192.168.1.100"
    status = "online"
    poll_interval = 5


# ---------------------------------------------------------------------------
# MachinePoller
# ---------------------------------------------------------------------------

def test_machine_poller_is_importable():
    """MachinePoller must be importable from app.services.polling."""
    assert MachinePoller is not None


def test_machine_poller_is_class():
    assert inspect.isclass(MachinePoller)


def test_machine_poller_init_accepts_machine_and_manager():
    """MachinePoller can be constructed with a machine and websocket manager."""
    mgr = _FakeWebsocketManager()
    machine = _FakeMachine()
    poller = MachinePoller(machine=machine, websocket_manager=mgr)
    assert poller is not None


def test_machine_poller_init_accepts_notification_service():
    """MachinePoller constructor accepts optional notification_service."""
    mgr = _FakeWebsocketManager()
    machine = _FakeMachine()
    poller = MachinePoller(machine=machine, websocket_manager=mgr, notification_service=None)
    assert poller is not None


def test_machine_poller_has_display_online():
    """display_online must be a callable that returns a bool."""
    mgr = _FakeWebsocketManager()
    machine = _FakeMachine()
    poller = MachinePoller(machine=machine, websocket_manager=mgr)
    val = poller.display_online()
    assert isinstance(val, bool)


def test_machine_poller_has_poll_method():
    """MachinePoller must have an async poll() method."""
    assert hasattr(MachinePoller, "poll")
    assert inspect.iscoroutinefunction(MachinePoller.poll)


def test_machine_poller_has_poll_tool_data_method():
    """MachinePoller must have an async poll_tool_data() method."""
    assert hasattr(MachinePoller, "poll_tool_data")
    assert inspect.iscoroutinefunction(MachinePoller.poll_tool_data)


def test_machine_poller_has_fetch_program_name_method():
    """MachinePoller must have an async fetch_program_name() method."""
    assert hasattr(MachinePoller, "fetch_program_name")
    assert inspect.iscoroutinefunction(MachinePoller.fetch_program_name)


def test_machine_poller_has_seed_last_status_from_db():
    """MachinePoller must have seed_last_status_from_db() method."""
    assert hasattr(MachinePoller, "seed_last_status_from_db")
    assert callable(MachinePoller.seed_last_status_from_db)


def test_machine_poller_stores_machine_reference():
    """Poller must expose the machine it was constructed with."""
    mgr = _FakeWebsocketManager()
    machine = _FakeMachine()
    poller = MachinePoller(machine=machine, websocket_manager=mgr)
    assert poller.machine is machine


# ---------------------------------------------------------------------------
# PollingService
# ---------------------------------------------------------------------------

def test_polling_service_is_importable():
    """PollingService must be importable from app.services.polling."""
    assert PollingService is not None


def test_polling_service_is_class():
    assert inspect.isclass(PollingService)


def test_polling_service_init_accepts_websocket_manager():
    """PollingService can be constructed with a websocket manager."""
    mgr = _FakeWebsocketManager()
    svc = PollingService(websocket_manager=mgr)
    assert svc is not None


def test_polling_service_init_accepts_mqtt_and_notification():
    """PollingService constructor accepts optional mqtt_publisher and notification_service."""
    mgr = _FakeWebsocketManager()
    svc = PollingService(websocket_manager=mgr, mqtt_publisher=None, notification_service=None)
    assert svc is not None


def test_polling_service_has_start_method():
    """PollingService must have an async start() method."""
    assert hasattr(PollingService, "start")
    assert inspect.iscoroutinefunction(PollingService.start)


def test_polling_service_has_stop_method():
    """PollingService must have an async stop() method."""
    assert hasattr(PollingService, "stop")
    assert inspect.iscoroutinefunction(PollingService.stop)


def test_polling_service_has_get_machine_status():
    """PollingService must have a synchronous get_machine_status() method."""
    assert hasattr(PollingService, "get_machine_status")
    assert not inspect.iscoroutinefunction(PollingService.get_machine_status)


def test_polling_service_has_get_all_status():
    """PollingService must have a synchronous get_all_status() method."""
    assert hasattr(PollingService, "get_all_status")
    assert not inspect.iscoroutinefunction(PollingService.get_all_status)


def test_polling_service_has_refresh_tool_data():
    """PollingService must have an async refresh_tool_data() method."""
    assert hasattr(PollingService, "refresh_tool_data")
    assert inspect.iscoroutinefunction(PollingService.refresh_tool_data)


def test_get_machine_status_returns_none_for_unknown_machine():
    """get_machine_status returns None when the machine has no cached status."""
    mgr = _FakeWebsocketManager()
    svc = PollingService(websocket_manager=mgr)
    result = svc.get_machine_status(machine_id=99999)
    assert result is None


def test_get_all_status_returns_dict():
    """get_all_status returns a dict (possibly empty at startup)."""
    mgr = _FakeWebsocketManager()
    svc = PollingService(websocket_manager=mgr)
    result = svc.get_all_status()
    assert isinstance(result, dict)
