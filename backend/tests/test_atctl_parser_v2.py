"""Behavioral tests for ATCTL parser v2."""
from app.parsers.atctl_parser_v2 import parse_atctl_v2


def test_empty_content():
    result = parse_atctl_v2(b"", control_version="C00")
    assert result["tools"] == []
    assert result["total_tools"] == 0
    assert result["control_version"] == "C00"


def test_c00_spindle_and_pots():
    # Schema fields vary; provide enough CSV columns for typical C00 ATCTL
    content = (
        b"M01,5,1,0,1,0\r\n"
        b"M02,10,2,0,1,0\r\n"
        b"M03,12,3,0,1,0\r\n"
    )
    result = parse_atctl_v2(content, control_version="C00")
    assert result["total_tools"] >= 2
    assert result["control_version"] == "C00"
    # Spindle should be first with pot_number SPINDLE
    spindle = result["tools"][0]
    assert spindle["pot_number"] == "SPINDLE"
    # Pot M02 → pot_number 1
    pots = [t for t in result["tools"] if t.get("pot_number") != "SPINDLE"]
    assert pots[0]["pot_number"] == 1
    assert pots[1]["pot_number"] == 2


def test_auto_detect_c00_no_stockers():
    content = b"M01,5,1,0,1,0\r\nM02,10,2,0,1,0\r\n"
    result = parse_atctl_v2(content, control_version=None)
    assert result["control_version"] == "C00"


def test_auto_detect_d00_with_stocker_lines():
    content = b"M01,5,1,0,1,0\r\nR01,1,0,0\r\nL01,2,0,0\r\n"
    result = parse_atctl_v2(content, control_version=None)
    assert result["control_version"] == "D00"


def test_short_line_skipped():
    content = b"M02\r\nM03,10,2,0,1,0\r\n"
    result = parse_atctl_v2(content, control_version="C00")
    pots = [t for t in result["tools"] if t.get("pot_number") != "SPINDLE"]
    assert len(pots) == 1
    assert pots[0]["pot_number"] == 2
