"""Behavioral tests for MEM parser v2."""
from app.parsers.mem_parser_v2 import parse_mem_v2


def test_empty_content():
    result = parse_mem_v2(b"", control_version="C00")
    assert result["program_name"] is None
    assert result["control_version"] == "C00"


def test_c00_with_a01_prefix():
    content = b"A01,'FOLDER  ',2045,1,0,0,0,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["program_name"] == "O2045"
    assert result["operation_folder_name"] == "FOLDER"
    assert result["operation_status"] == 1
    assert result["control_version"] == "C00"


def test_program_already_o_prefixed():
    content = b"A01,'FOLDER  ',O1234,0,0,0,0,0\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["program_name"] == "O1234"


def test_auto_detect_c00_short_fields():
    content = b"A01,'FOLDER  ',2045,0,0,0,0,0\r\n"
    result = parse_mem_v2(content, control_version=None)
    assert result["control_version"] == "C00"


def test_auto_detect_d00_long_program_name():
    long_prog = "VERY_LONG_PROGRAM_NAME_PATH_HERE"
    content = f"A01,'LONG_FOLDER_NAME_EXCEEDING_TEN',{long_prog},0,0,0,0,0\r\n".encode()
    result = parse_mem_v2(content, control_version=None)
    assert result["control_version"] == "D00"


def test_insufficient_fields():
    content = b"A01,onlyone\r\n"
    result = parse_mem_v2(content, control_version="C00")
    assert result["program_name"] is None
