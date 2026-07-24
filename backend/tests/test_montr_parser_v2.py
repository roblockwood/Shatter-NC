"""Behavioral tests for MONTR parser v2."""
from app.parsers.montr_parser_v2 import parse_montr_v2


def test_empty_content():
    result = parse_montr_v2(b"", control_version="C00")
    assert result["program_info"] == {}
    assert result["time_info"] == {}
    assert result["counters"] == []
    assert result["control_version"] == "C00"


def test_c00_full_sample():
    content = (
        b"P01,2045,2046,'FOLDER  ','EDIT    '\r\n"
        b"T01,010203000,040506000,070809000\r\n"
        b"C01,001,000010,000100,000090\r\n"
        b"C02,002,000020,000200,000180\r\n"
    )
    result = parse_montr_v2(content, control_version="C00")
    assert result["control_version"] == "C00"
    assert result["program_info"]["operation_program_no"] == "O2045"
    assert result["program_info"]["edit_program_no"] == "O2046"
    assert result["time_info"]["total_operation_time"] == "010203000"
    assert result["time_info"]["power_on_time"] == "040506000"
    assert len(result["counters"]) == 2
    assert result["counters"][0]["counter_number"] == 1
    assert result["counters"][0]["count"] == 1
    assert result["counters"][0]["current"] == 10
    assert result["counters"][1]["counter_number"] == 2


def test_auto_detect_c00_short_program_name():
    content = b"P01,2045,2046,'FOLDER  ','EDIT    '\r\n"
    result = parse_montr_v2(content, control_version=None)
    assert result["control_version"] == "C00"


def test_auto_detect_d00_long_program_name():
    long_name = "PROGRAM_NAME_THAT_IS_LONGER_THAN_FOUR"
    content = f"P01,{long_name},EDITPROG,'FOLDER','EDIT'\r\n".encode()
    result = parse_montr_v2(content, control_version=None)
    assert result["control_version"] == "D00"


def test_format_program_with_o_prefix():
    content = b"P01,O1234,O5678,'F','E'\r\n"
    result = parse_montr_v2(content, control_version="C00")
    assert result["program_info"]["operation_program_no"] == "O1234"
    assert result["program_info"]["edit_program_no"] == "O5678"


def test_no_p01_defaults_c00():
    content = b"T01,010203000,040506000,070809000\r\n"
    result = parse_montr_v2(content, control_version=None)
    assert result["control_version"] == "C00"
    assert result["time_info"]["operation_time"] == "070809000"


def test_all_four_counters():
    content = (
        b"P01,1000,1000,'A','B'\r\n"
        b"C01,1,1,1,1\r\n"
        b"C02,2,2,2,2\r\n"
        b"C03,3,3,3,3\r\n"
        b"C04,4,4,4,4\r\n"
    )
    result = parse_montr_v2(content, control_version="C00")
    assert [c["counter_number"] for c in result["counters"]] == [1, 2, 3, 4]
