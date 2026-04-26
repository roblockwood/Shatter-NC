"""Tests for the PRD3 (Production History) parser v2.

PRD3 files record the machine's operational status history.
The key consumer of this parser is the machine state validator (safe-for-write check)
which reads current_status.status to determine if the machine is running.
"""
from app.parsers.prd3_parser_v2 import parse_prd3_v2


# --- Empty / no content ---

def test_empty_content_returns_empty_dicts():
    result = parse_prd3_v2(b"")
    assert result["header"] == {}
    assert result["current_status"] == {}
    assert result["history"] == []


def test_empty_content_defaults_to_c00():
    result = parse_prd3_v2(b"")
    assert result["control_version"] == "C00"


# --- Header (A01 line) ---

def test_a01_header_fields_parsed():
    """A01 line populates start_pointer, end_pointer, status."""
    content = b"A01,0,5,2\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["header"]["start_pointer"] == 0
    assert result["header"]["end_pointer"] == 5
    assert result["header"]["status"] == 2


def test_a01_only_no_current_status():
    """A01 alone does not populate current_status (needs C01 for that)."""
    content = b"A01,0,0,2\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["current_status"] == {}


# --- Status code mapping (from C01 line) ---

def test_status_2_maps_to_standby():
    content = b"A01,0,1,2\r\nC01,20250424,2,0,O2045,MAIN\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["current_status"]["status"] == "standby"


def test_status_3_maps_to_operating():
    content = b"A01,0,1,3\r\nC01,20250424,3,0,O2045,MAIN\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["current_status"]["status"] == "operating"


def test_status_4_maps_to_stopped():
    content = b"A01,0,1,4\r\nC01,20250424,4,0,O2045,MAIN\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["current_status"]["status"] == "stopped"


def test_status_5_maps_to_error():
    content = b"A01,0,1,5\r\nC01,20250424,5,0,E0412,MAIN\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["current_status"]["status"] == "error"


def test_current_status_code_field_preserved():
    """The raw integer code is preserved alongside the mapped string."""
    content = b"A01,0,1,3\r\nC01,20250424,3,0,O2045,MAIN\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["current_status"]["current_status"] == 3


# --- History (B-lines) ---

def test_b_lines_parsed_as_history():
    """B0001-Bxxxx lines are parsed as history entries."""
    content = (
        b"A01,0,2,2\r\n"
        b"C01,20250424,2,0,O2045,MAIN\r\n"
        b"B0001,20250423,3,0,O2045,MAIN\r\n"
    )
    result = parse_prd3_v2(content, control_version="C00")
    assert len(result["history"]) == 1


def test_multiple_b_lines_all_in_history():
    content = (
        b"A01,0,3,2\r\n"
        b"C01,20250424,2,0,O2045,MAIN\r\n"
        b"B0001,20250423,3,0,O2045,MAIN\r\n"
        b"B0002,20250422,4,0,O1234,TEST\r\n"
    )
    result = parse_prd3_v2(content, control_version="C00")
    assert len(result["history"]) == 2


def test_history_entries_have_status_mapped():
    """History entries also have their status code mapped to a string."""
    content = (
        b"A01,0,2,2\r\n"
        b"C01,20250424,2,0,O2045,MAIN\r\n"
        b"B0001,20250423,3,0,O2045,MAIN\r\n"
    )
    result = parse_prd3_v2(content, control_version="C00")
    assert result["history"][0]["status"] == "operating"


# --- Control version ---

def test_explicit_c00_recorded():
    result = parse_prd3_v2(b"A01,0,0,2\r\n", control_version="C00")
    assert result["control_version"] == "C00"


def test_explicit_d00_recorded():
    # D00 A01 has 4 fields (adds file_writing_index)
    result = parse_prd3_v2(b"A01,0,0,2,0\r\n", control_version="D00")
    assert result["control_version"] == "D00"
