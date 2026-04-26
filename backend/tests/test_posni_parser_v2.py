"""Tests for the POSNI (Position Offset) parser v2.

Uses the real Samples/POSNI1.NC file as a fixture where appropriate,
and synthetic minimal content for edge cases.
"""
import pytest
from pathlib import Path
from app.parsers.posni_parser_v2 import parse_posni_v2

# Path to the real sample file checked into the repo
_SAMPLE_FILE = Path(__file__).parents[2] / "Samples" / "POSNI1.NC"


# --- Empty / no content ---

def test_empty_content_returns_empty_dicts():
    result = parse_posni_v2(b"")
    assert result["work_offsets"] == {}
    assert result["extended_offsets"] == {}
    assert result["fixture_offsets"] == {}
    assert result["rotary_offsets"] == {}


def test_empty_content_records_control_version():
    result = parse_posni_v2(b"", control_version="C00")
    assert result["control_version"] == "C00"


def test_empty_content_records_units():
    result = parse_posni_v2(b"", units="mm")
    assert result["units"] == "mm"


# --- Work offsets (G54–G59 lines) ---

def test_single_g54_work_offset_parsed():
    content = b"G54,-20.3678,-1.0124,2.9996,0.000,0.000,0.000\r\n"
    result = parse_posni_v2(content, units="in", control_version="C00")
    assert 54 in result["work_offsets"]
    offset = result["work_offsets"][54]
    assert offset["x"] == pytest.approx(-20.3678)
    assert offset["y"] == pytest.approx(-1.0124)
    assert offset["z"] == pytest.approx(2.9996)


def test_g54_rotary_axes_present():
    """A, B, C axes are included alongside X, Y, Z."""
    content = b"G54,-20.3678,-1.0124,2.9996,0.000,0.000,0.000\r\n"
    result = parse_posni_v2(content, units="in", control_version="C00")
    offset = result["work_offsets"][54]
    for axis in ("a", "b", "c"):
        assert axis in offset


def test_multiple_work_offsets_all_parsed():
    content = (
        b"G54,-20.3678,-1.0124,2.9996,0.000,0.000,0.000\r\n"
        b"G55,-13.9774,-7.4936,0.0000,0.000,0.000,0.000\r\n"
        b"G56,0.0000,0.0000,0.0000,0.000,0.000,0.000\r\n"
    )
    result = parse_posni_v2(content, units="in", control_version="C00")
    assert len(result["work_offsets"]) == 3
    assert 55 in result["work_offsets"]
    assert result["work_offsets"][55]["x"] == pytest.approx(-13.9774)


def test_zero_offsets_parsed_as_zero_float():
    content = b"G56,0.0000,0.0000,0.0000,0.000,0.000,0.000\r\n"
    result = parse_posni_v2(content, units="in", control_version="C00")
    assert result["work_offsets"][56]["x"] == pytest.approx(0.0)
    assert result["work_offsets"][56]["z"] == pytest.approx(0.0)


# --- Units metadata ---

def test_units_inches_recorded():
    content = b"G54,1.0000,2.0000,3.0000,0.000,0.000,0.000\r\n"
    result = parse_posni_v2(content, units="in")
    assert result["units"] == "in"


def test_units_mm_recorded():
    content = b"G54,25.400,50.800,76.200,0.000,0.000,0.000\r\n"
    result = parse_posni_v2(content, units="mm")
    assert result["units"] == "mm"


# --- Sample file round-trip ---

def test_sample_file_parses_all_top_level_keys():
    """The real POSNI1.NC sample file produces all expected top-level keys."""
    content = _SAMPLE_FILE.read_bytes()
    result = parse_posni_v2(content, units="in", control_version="C00")
    for key in ("work_offsets", "extended_offsets", "fixture_offsets", "rotary_offsets", "units", "control_version"):
        assert key in result


def test_sample_file_g54_has_nonzero_offset():
    """G54 in the sample file has a real (non-zero) X offset."""
    content = _SAMPLE_FILE.read_bytes()
    result = parse_posni_v2(content, units="in", control_version="C00")
    assert result["work_offsets"][54]["x"] != pytest.approx(0.0)


def test_sample_file_has_multiple_work_offsets():
    """Sample file defines G54–G59 (at least 2 distinct work offsets)."""
    content = _SAMPLE_FILE.read_bytes()
    result = parse_posni_v2(content, units="in", control_version="C00")
    assert len(result["work_offsets"]) >= 2
