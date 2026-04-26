"""Tests for the alarm parser v2 (schema-based ALARM.NC parser)."""
import pytest
from app.parsers.alarm_parser_v2 import parse_alarm_v2, ALARMParserV2


# --- Empty / no content ---

def test_empty_content_returns_no_alarms():
    """Empty byte string produces empty alarm lists."""
    result = parse_alarm_v2(b"")
    assert result["alarms"] == []
    assert result["loading_alarms"] == []


def test_no_e01_line_returns_no_alarms():
    """Content with no E01 line produces no alarms (and defaults to C00)."""
    result = parse_alarm_v2(b"SOMEOTHERDATA\r\n", control_version="C00")
    assert result["alarms"] == []
    assert result["control_version"] == "C00"


# --- C00 alarm parsing ---

def test_c00_single_active_alarm_code():
    """C00 active alarm: 10-byte code with category 04 (NC) and number 1234."""
    content = b"E01,0412340000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    assert len(result["alarms"]) == 1
    alarm = result["alarms"][0]
    assert alarm["code"] == "NC1234"
    assert alarm["category"] == "NC"
    assert alarm["category_code"] == "04"
    assert alarm["number"] == "1234"


def test_c00_servo_alarm():
    """Category 03 maps to SV (Servo) alarm type."""
    content = b"E01,0300560000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    alarm = result["alarms"][0]
    assert alarm["category"] == "SV"
    assert alarm["code"] == "SV0056"


def test_c00_two_alarms_on_same_line():
    """Multiple alarm codes on E01 line are each parsed as separate alarms."""
    content = b"E01,0412340000,0301230000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    assert len(result["alarms"]) == 2
    codes = {a["code"] for a in result["alarms"]}
    assert "NC1234" in codes
    assert "SV0123" in codes


def test_c00_zero_alarm_code_produces_unknown_entry():
    """An all-zero 10-byte code is parsed (not filtered); category resolves to UNKNOWN(00)."""
    content = b"E01,0000000000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    # Parser does not filter zero codes — caller filters if desired
    assert len(result["alarms"]) == 1
    assert result["alarms"][0]["category_code"] == "00"


# --- D00 alarm parsing ---

def test_d00_alarm_uses_22_byte_code():
    """D00 control: 22-byte alarm code is parsed with correct category and number."""
    # 22 chars: 04 (category) + 1234 (number) + 16 zeros (auxiliary)
    content = b"E01,0412340000000000000000\r\n"
    result = parse_alarm_v2(content, control_version="D00")
    assert len(result["alarms"]) == 1
    alarm = result["alarms"][0]
    assert alarm["code"] == "NC1234"
    assert alarm["category"] == "NC"
    assert result["control_version"] == "D00"


# --- Control version detection ---

def test_auto_detects_c00_from_short_alarm_code():
    """10-byte E01 field triggers C00 detection when no version is given."""
    content = b"E01,0412340000\r\n"
    result = parse_alarm_v2(content)  # no explicit version
    assert result["control_version"] == "C00"


def test_auto_detects_d00_from_long_alarm_code():
    """22-byte E01 field triggers D00 detection when no version is given."""
    content = b"E01,0412340000000000000000\r\n"
    result = parse_alarm_v2(content)  # no explicit version
    assert result["control_version"] == "D00"


# --- Loading system alarms ---

def test_l01_line_parsed_as_loading_alarm():
    """L01 line populates loading_alarms, not alarms."""
    content = b"L01,040123000000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    assert result["alarms"] == []
    assert len(result["loading_alarms"]) == 1


def test_e01_and_l01_both_parsed_independently():
    """E01 and L01 lines each populate their own list."""
    content = b"E01,0412340000\r\nL01,040123000000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    assert len(result["alarms"]) == 1
    assert len(result["loading_alarms"]) == 1


# --- alarm type field ---

def test_operator_message_type_for_category_90():
    """Category 90 (OM) produces type 'operator_message', not 'alarm'."""
    # Category 90 = OM (Operator Message)
    content = b"E01,9001230000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    assert len(result["alarms"]) == 1
    assert result["alarms"][0]["type"] == "operator_message"


def test_regular_alarm_has_type_alarm():
    """Non-90 category produces type 'alarm'."""
    content = b"E01,0412340000\r\n"
    result = parse_alarm_v2(content, control_version="C00")
    assert result["alarms"][0]["type"] == "alarm"
