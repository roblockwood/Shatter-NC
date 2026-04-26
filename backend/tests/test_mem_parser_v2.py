"""Tests for the MEM (Memory Operation) parser v2."""
from app.parsers.mem_parser_v2 import parse_mem_v2


# --- Empty / no content ---

def test_empty_content_returns_none_program():
    result = parse_mem_v2(b"")
    assert result["program_name"] is None
    assert result["control_version"] == "C00"


# --- Program name formatting ---

def test_numeric_program_name_formatted_as_o_number():
    """4-digit program number is prefixed with 'O'."""
    content = b"A01,'MAIN    ',2045,1,0,0,2,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["program_name"] == "O2045"


def test_zero_program_number_formatted_as_o0000():
    content = b"A01,'',0000,0,0,0,0,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["program_name"] == "O0000"


def test_program_name_without_a01_prefix():
    """Bare line (no A01 prefix) parses the same as prefixed line."""
    content = b"'MAIN    ',2045,1,0,0,2,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["program_name"] == "O2045"


# --- Mode and operation_status fields ---

def test_mode_memory_operation():
    """Mode 2 = Memory operation (program running)."""
    content = b"A01,'MAIN    ',2045,1,0,0,2,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["mode"] == 2
    assert result["operation_status"] == 1


def test_mode_manual_reset():
    """Mode 0 = Manual, operation_status 0 = Reset (idle state)."""
    content = b"A01,'',0000,0,0,0,0,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["mode"] == 0
    assert result["operation_status"] == 0


def test_mode_edit():
    """Mode 3 = Edit (unsafe for tool assignments)."""
    content = b"A01,'MAIN    ',2045,0,0,0,3,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["mode"] == 3


# --- Folder name ---

def test_operation_folder_name_stripped_of_quotes():
    """Quoted folder names have quotes removed."""
    content = b"A01,'MAIN    ',2045,1,0,0,2,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["operation_folder_name"] == "MAIN"


def test_empty_folder_name_is_empty_string():
    content = b"A01,'',0000,0,0,0,0,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["operation_folder_name"] == ""


# --- Control version ---

def test_explicit_c00_version_recorded():
    content = b"A01,'MAIN    ',2045,1,0,0,2,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["control_version"] == "C00"


def test_explicit_d00_version_recorded():
    # D00 has 34-byte program name field
    content = b"A01,'D00 FOLDER NAME HERE   ',00002045                  ,1,0,0,2,0\r\n"
    result = parse_mem_v2(content, control_version="D00")
    assert result["control_version"] == "D00"


# --- All fields present ---

def test_all_expected_fields_returned():
    """A valid MEM line should produce all expected top-level keys."""
    content = b"A01,'MAIN    ',2045,1,0,0,2,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    for key in ("program_name", "operation_folder_name", "mode", "operation_status", "control_version"):
        assert key in result, f"Expected key '{key}' missing from result"
