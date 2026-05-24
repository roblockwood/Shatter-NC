"""Tests for CNC controller adapter registry."""
from types import SimpleNamespace

from app.controllers.base import (
    BROTHER_CAPABILITIES,
    HEIDENHAIN_V1_CAPABILITIES,
    capabilities_as_list,
    get_capabilities_for_controller,
)
from app.controllers.brother_adapter import BrotherAdapter
from app.controllers.registry import get_adapter_for_machine


def _machine(**kwargs):
    defaults = {
        "id": 1,
        "name": "Test",
        "ip_address": "192.168.1.10",
        "controller_type": "brother",
        "controller_config": None,
        "units": "in",
        "control_version": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_brother_adapter_by_default():
    adapter = get_adapter_for_machine(_machine())
    assert isinstance(adapter, BrotherAdapter)
    assert adapter.capabilities() == BROTHER_CAPABILITIES


def test_heidenhain_adapter_selected():
    from app.controllers.heidenhain.adapter import HeidenhainOpcUaAdapter

    adapter = get_adapter_for_machine(
        _machine(controller_type="heidenhain", controller_config={"opcua_port": 4840})
    )
    assert isinstance(adapter, HeidenhainOpcUaAdapter)
    assert adapter.capabilities() == HEIDENHAIN_V1_CAPABILITIES


def test_capabilities_as_list_sorted():
    caps = capabilities_as_list("heidenhain")
    assert caps == sorted(HEIDENHAIN_V1_CAPABILITIES)


def test_unknown_controller_defaults_to_brother_capabilities():
    assert get_capabilities_for_controller(None) == BROTHER_CAPABILITIES
