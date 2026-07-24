"""Tests for small utils with high coverage leverage."""
from app.utils.montr_program_name import (
    is_meaningful_machine_program_name,
    is_placeholder_machine_program_name,
    meaningful_montr_operation_program_no,
)
from app.utils.alarm_code_lookup import _parse_alarm_code_range, enrich_alarm_with_lookup


def test_meaningful_montr_program():
    assert meaningful_montr_operation_program_no({}) is None
    assert meaningful_montr_operation_program_no({"operation_program_no": "----"}) is None
    assert meaningful_montr_operation_program_no({"operation_program_no": "  "}) is None
    assert meaningful_montr_operation_program_no({"operation_program_no": "O2045"}) == "O2045"


def test_placeholder_program_name():
    assert is_placeholder_machine_program_name(None) is True
    assert is_placeholder_machine_program_name("----") is True
    assert is_placeholder_machine_program_name("") is True
    assert is_placeholder_machine_program_name("O1000") is False
    assert is_meaningful_machine_program_name("O1000") is True


def test_parse_alarm_code_range_single():
    assert _parse_alarm_code_range("IO0518") == ["IO0518"]


def test_parse_alarm_code_range_span():
    codes = _parse_alarm_code_range("EX0000\n:\nEX0002")
    assert codes == ["EX0000", "EX0001", "EX0002"]


def test_enrich_alarm_passthrough_unknown():
    alarm = {"code": "ZZ9999", "category": "ZZ", "number": "9999"}
    enriched = enrich_alarm_with_lookup(alarm, control_version="C00")
    assert enriched["code"] == "ZZ9999"
