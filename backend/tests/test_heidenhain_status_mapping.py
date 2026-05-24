"""Tests for Heidenhain OPC UA status mapping."""
from app.controllers.heidenhain.status_mapping import (
    derive_status,
    map_exec_state_to_status,
    map_nc_state_to_available,
)


def test_map_exec_state_running():
    assert map_exec_state_to_status("Running") == "operating"


def test_map_exec_state_idle():
    assert map_exec_state_to_status("Idle") == "standby"


def test_map_exec_state_error():
    assert map_exec_state_to_status("Error") == "error"


def test_map_nc_state_available():
    assert map_nc_state_to_available("NCIsAvailable") is True
    assert map_nc_state_to_available("NCIsBooted") is False


def test_derive_status_when_nc_unavailable():
    assert derive_status("NCIsBooted", "Running") == "off"


def test_derive_status_running():
    assert derive_status("NCIsAvailable", "Running") == "operating"


def test_derive_status_errors_elevate_to_error():
    assert derive_status("NCIsAvailable", "Idle", has_errors=True) == "error"


def test_derive_status_operating_not_overridden_by_errors():
    assert derive_status("NCIsAvailable", "Running", has_errors=True) == "operating"
