"""Unit tests for Kaeser SC2 process map helpers (register serialization, status, alarms)."""
from app.integrations.kaeser_sc2.process_map_registers import (
    build_mvp_metrics,
    infer_operational_status,
    map_alarms_for_ui,
    registers_to_dict,
)


def test_registers_to_dict_empty():
    assert registers_to_dict(None, "h") == {}
    assert registers_to_dict([], "h") == {}


def test_registers_to_dict_indexes():
    assert registers_to_dict([10, 20], "x") == {"x_0": 10, "x_1": 20}


def test_build_mvp_metrics():
    m = build_mvp_metrics([1, 2], [3], None)
    assert m["holding_registers"] == [1, 2]
    assert m["input_registers"] == [3]
    m_err = build_mvp_metrics(None, None, "timeout")
    assert m_err["modbus_error"] == "timeout"


def test_infer_operational_status():
    assert infer_operational_status(False, None, None) == "offline"
    assert infer_operational_status(True, [], []) == "online"


def test_map_alarms_for_ui_placeholder():
    assert map_alarms_for_ui([1], [2]) == []
