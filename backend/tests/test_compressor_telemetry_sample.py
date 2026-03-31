"""Tests for operational → sample metrics telemetry extraction."""
from app.services.compressor_telemetry_sample import telemetry_fields_from_operational


def test_empty_operational():
    assert telemetry_fields_from_operational(None) == {}
    assert telemetry_fields_from_operational({}) == {}


def test_pressure_and_temp():
    op = {
        "pressure": {"value": 102.5, "unit": "psi"},
        "outletTemp": {"value": 72, "unit": "°F"},
    }
    m = telemetry_fields_from_operational(op)
    assert m["psi"] == 102.5
    assert m["psi_unit"] == "psi"
    assert m["outlet_temp"] == 72
    assert m["temp_unit"] == "°F"


def test_string_values():
    op = {"pressure": {"value": "100", "unit": "psi"}, "outletTemp": {"value": "68.2", "unit": "°F"}}
    m = telemetry_fields_from_operational(op)
    assert m["psi"] == 100.0
    assert m["outlet_temp"] == 68.2
