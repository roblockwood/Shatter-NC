"""Tests for the PANEL (Operation Panel) parser v2."""
from app.parsers.panel_parser_v2 import parse_panel_v2

# Reusable C00 fixture strings
_C00_FULL = (
    b"D01,1,0,0\r\n"          # outer_door=open, inner=closed, side=closed
    b"K01,2,4,1,0,0,0,0,0,0,0,0\r\n"  # mode=2 (memory), screen=4, block_skip=1
    b"S01,4,100,100,0,0,0,0\r\n"        # rapid_override=4(100%), feedrate=100%, spindle=100%
)


# --- Empty / no content ---

def test_empty_content_returns_empty_dicts():
    result = parse_panel_v2(b"")
    assert result["doors"] == {}
    assert result["mode_and_functions"] == {}
    assert result["overrides"] == {}
    assert result["control_version"] == "C00"


# --- Door status (D01 line) ---

def test_outer_door_open():
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert result["doors"]["outer_door"] == 1


def test_inner_and_side_doors_closed():
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert result["doors"]["inner_door"] == 0
    assert result["doors"]["side_door"] == 0


def test_all_doors_closed():
    content = b"D01,0,0,0\r\nK01,0,0,0,0,0,0,0,0,0,0,0\r\nS01,4,100,100,0,0,0,0\r\n"
    result = parse_panel_v2(content, control_version="C00")
    assert result["doors"]["outer_door"] == 0
    assert result["doors"]["inner_door"] == 0
    assert result["doors"]["side_door"] == 0


# --- Mode and functions (K01 line) ---

def test_mode_memory_operation():
    """Mode 2 = Memory operation."""
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert result["mode_and_functions"]["mode"] == 2


def test_mode_manual():
    content = b"D01,0,0,0\r\nK01,0,0,0,0,0,0,0,0,0,0,0\r\nS01,4,100,100,0,0,0,0\r\n"
    result = parse_panel_v2(content, control_version="C00")
    assert result["mode_and_functions"]["mode"] == 0


def test_block_skip_on():
    """block_skip=1 means block skip switch is ON."""
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert result["mode_and_functions"]["block_skip"] == 1


# --- Overrides (S01 line) ---

def test_feedrate_override_100_percent():
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert result["overrides"]["feedrate_override"] == 100


def test_spindle_override_100_percent():
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert result["overrides"]["spindle_override"] == 100


def test_rapid_traverse_override_field_present():
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert "rapid_traverse_override" in result["overrides"]


# --- Control version ---

def test_explicit_c00_recorded():
    result = parse_panel_v2(_C00_FULL, control_version="C00")
    assert result["control_version"] == "C00"


def test_top_level_keys_always_present():
    """Even with sparse content, top-level structure keys are always returned."""
    result = parse_panel_v2(b"K01,0,0,0,0,0,0,0,0,0,0,0\r\n", control_version="C00")
    for key in ("doors", "mode_and_functions", "overrides", "control_version"):
        assert key in result, f"Expected top-level key '{key}' missing"


# --- K01-only content (no D01 or S01) ---

def test_k01_only_populates_mode_and_functions():
    """K01 alone fills mode_and_functions without doors or overrides."""
    content = b"K01,1,0,0,0,0,0,0,0,0,0,0\r\n"
    result = parse_panel_v2(content, control_version="C00")
    assert result["mode_and_functions"].get("mode") == 1
    assert result["doors"] == {}
    assert result["overrides"] == {}
