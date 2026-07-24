"""Behavioral tests for PRD3 parser v2."""
from app.parsers.prd3_parser_v2 import parse_prd3_v2, STATUS_CODE_MAP


def test_empty_content():
    result = parse_prd3_v2(b"", control_version="C00")
    assert result["header"] == {}
    assert result["current_status"] == {}
    assert result["history"] == []
    assert result["control_version"] == "C00"


def test_c00_operating_status():
    content = (
        b"A01,1,10,1\r\n"
        b"C01,20240101120000,3,0,2045,'FOLDER  ',0\r\n"
        b"B0001,20240101110000,2,0,2045,'FOLDER  ',0\r\n"
    )
    result = parse_prd3_v2(content, control_version="C00")
    assert result["control_version"] == "C00"
    assert result["header"]["start_pointer"] == 1
    assert result["header"]["end_pointer"] == 10
    assert result["current_status"]["current_status"] == 3
    assert result["current_status"]["status"] == "operating"
    assert result["current_status"]["program_or_error_no"] == "2045"
    assert result["current_status"]["folder_name"].strip() == "FOLDER"
    assert len(result["history"]) == 1
    assert result["history"][0]["index"] == 1
    assert result["history"][0]["status"] == "standby"


def test_status_code_map_all_values():
    for code, label in STATUS_CODE_MAP.items():
        content = (
            f"A01,1,2,1\r\n"
            f"C01,20240101120000,{code},0,0000,'F',0\r\n"
        ).encode()
        result = parse_prd3_v2(content, control_version="C00")
        assert result["current_status"]["status"] == label


def test_auto_detect_d00_from_a01():
    content = b"A01,1,10,1,5\r\nC01,20240101120000,2,0,2045,'FOLDER',0\r\n"
    result = parse_prd3_v2(content, control_version=None)
    assert result["control_version"] == "D00"
    assert result["header"].get("file_writing_index") == 5


def test_overrides_wrong_control_version_from_content():
    # Caller says C00 but A01 has 4 fields → content wins
    content = b"A01,1,10,1,5\r\nC01,20240101120000,4,0,2045,'FOLDER',0\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert result["control_version"] == "D00"
    assert result["current_status"]["status"] == "stopped"


def test_non_numeric_memory_operation_type_skipped():
    content = b"A01,1,2,1\r\nC01,20240101120000,3,0,2045,'FOLDER','PROGRAM '\r\n"
    result = parse_prd3_v2(content, control_version="C00")
    assert "memory_operation_type" not in result["current_status"]
    assert result["current_status"]["status"] == "operating"
