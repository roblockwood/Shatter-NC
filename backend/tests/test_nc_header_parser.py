"""Tests for NC header comment parsing and program note formatting."""
from app.parsers.nc_header_parser import extract_nc_program_header, format_program_note


def test_extract_first_line_bracketed_title():
    content = """(O1234 — BRACKET POCKET)
(Fusion post)
G90 G54
M30
"""
    result = extract_nc_program_header(content)
    assert result["title"] == "O1234 — BRACKET POCKET"
    assert result["file_label"] is None


def test_extract_skips_percent_blank_and_o_number_lines():
    content = """
%
O1234
(O1234 — BRACKET POCKET)
G90
"""
    result = extract_nc_program_header(content)
    assert result["title"] == "O1234 — BRACKET POCKET"


def test_extract_file_label():
    content = """(O1234 — BRACKET POCKET)
(FILE: BRACKET_V2.NC)
G90
"""
    result = extract_nc_program_header(content)
    assert result["title"] == "O1234 — BRACKET POCKET"
    assert result["file_label"] == "BRACKET_V2.NC"


def test_extract_missing_comment_returns_none():
    content = """G90 G54
M30
"""
    result = extract_nc_program_header(content)
    assert result["title"] is None
    assert result["file_label"] is None


def test_format_program_note_strips_matching_onumber_prefix():
    title = "O1234 — BRACKET POCKET"
    assert format_program_note(title, "O1234.NC") == "BRACKET POCKET"


def test_format_program_note_strips_dash_separator():
    title = "O2000 - FACE OP"
    assert format_program_note(title, "O2000.NC") == "FACE OP"


def test_format_program_note_strips_colon_separator():
    title = "O3100: SECOND OP"
    assert format_program_note(title, "O3100.nc") == "SECOND OP"


def test_format_program_note_non_onumber_keeps_full_title():
    title = "SETUP ROUTINE"
    assert format_program_note(title, "SETUP.NC") == "SETUP ROUTINE"


def test_format_program_note_none_or_empty():
    assert format_program_note(None, "O1234.NC") is None
    assert format_program_note("", "O1234.NC") is None


def test_format_program_note_prefix_only_returns_none():
    title = "O1234 —"
    assert format_program_note(title, "O1234.NC") is None
