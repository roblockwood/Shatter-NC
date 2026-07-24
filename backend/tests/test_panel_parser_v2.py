"""Behavioral tests for PANEL parser v2."""
from app.parsers.panel_parser_v2 import parse_panel_v2


def test_empty_content():
    result = parse_panel_v2(b"", control_version="C00")
    assert result["doors"] == {}
    assert result["mode_and_functions"] == {}
    assert result["overrides"] == {}
    assert result["control_version"] == "C00"


def test_c00_full_sample():
    # K01 C00: 11 fields (mode through pallet_select_key)
    content = (
        b"D01,1,0,1\r\n"
        b"K01,2,6,0,0,0,0,0,1,0,1,0\r\n"
        b"S01,4,100,100,1,0,0,1\r\n"
    )
    result = parse_panel_v2(content, control_version="C00")
    assert result["control_version"] == "C00"
    assert result["doors"]["outer_door"] == 1
    assert result["doors"]["inner_door"] == 0
    assert result["doors"]["side_door"] == 1
    assert result["mode_and_functions"]["mode"] == 2
    assert result["mode_and_functions"]["screen"] == 6
    assert result["mode_and_functions"]["coolant_pump"] == 1
    assert result["overrides"]["rapid_traverse_override"] == 4
    assert result["overrides"]["feedrate_override"] == 100
    assert result["overrides"]["emergency_stop"] == 1


def test_auto_detect_c00_from_k01_field_count():
    content = b"K01,2,6,0,0,0,0,0,1,0,1,0\r\n"
    result = parse_panel_v2(content, control_version=None)
    assert result["control_version"] == "C00"


def test_auto_detect_d00_from_k01_field_count():
    # D00: 13 fields
    content = b"K01,2,0,0,0,0,0,1,0,1,0,1,0,0\r\n"
    result = parse_panel_v2(content, control_version=None)
    assert result["control_version"] == "D00"


def test_d00_mode_without_screen():
    content = (
        b"D01,0,0,0\r\n"
        b"K01,2,0,0,0,0,0,1,0,1,0,1,0,0\r\n"
        b"S01,4,100,100,0,0,0,0,1,1\r\n"
    )
    result = parse_panel_v2(content, control_version="D00")
    assert result["mode_and_functions"]["mode"] == 2
    assert "screen" not in result["mode_and_functions"]
    assert result["mode_and_functions"].get("table_light") == 1


def test_no_k01_defaults_c00():
    content = b"D01,1,1,1\r\n"
    result = parse_panel_v2(content, control_version=None)
    assert result["control_version"] == "C00"
    assert result["doors"]["outer_door"] == 1
