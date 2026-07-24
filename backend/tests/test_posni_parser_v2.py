"""Behavioral tests for POSNI parser v2."""
from app.parsers.posni_parser_v2 import parse_posni_v2


def test_empty_content():
    result = parse_posni_v2(b"", units="in", control_version="C00")
    assert result["work_offsets"] == {}
    assert result["extended_offsets"] == {}
    assert result["units"] == "in"
    assert result["control_version"] == "C00"


def test_c00_work_and_extended_offsets():
    content = (
        b"G54,-20.3678,-1.0124,2.9996,0.000,0.000,0.000\r\n"
        b"G55,1.0,2.0,3.0,0.0,0.0,0.0\r\n"
        b"X01,10.5,20.5,30.5,0.0,0.0,0.0\r\n"
        b"H01,0.1,0.2,0.3,0.0,0.0,0.0\r\n"
        b"B01,1.1,1.2,1.3,0.0,0.0,0.0\r\n"
    )
    result = parse_posni_v2(content, units="in", control_version="C00")
    assert 54 in result["work_offsets"]
    assert result["work_offsets"][54]["x"] == -20.3678
    assert result["work_offsets"][54]["y"] == -1.0124
    assert result["work_offsets"][54]["z"] == 2.9996
    assert 55 in result["work_offsets"]
    assert 1 in result["extended_offsets"]
    assert result["extended_offsets"][1]["x"] == 10.5
    assert 1 in result["fixture_offsets"]
    assert 1 in result["rotary_offsets"]
    assert result["control_version"] == "C00"


def test_d00_offset_names():
    content = (
        b"G054,-20.3678,-1.0124,2.9996,0.000,0.000,0.000\r\n"
        b"X001,10.5,20.5,30.5,0.0,0.0,0.0\r\n"
    )
    result = parse_posni_v2(content, units="mm", control_version="D00")
    assert result["units"] == "mm"
    assert 54 in result["work_offsets"]
    assert 1 in result["extended_offsets"]
    assert result["control_version"] == "D00"


def test_auto_detect_c00():
    content = b"G54,1.0,2.0,3.0,0.0,0.0,0.0\r\n"
    result = parse_posni_v2(content, control_version=None)
    assert result["control_version"] == "C00"


def test_auto_detect_d00():
    # D00 names + long digit fields (detection uses >9 digits as D00 signal)
    content = (
        b"G054,12345678901,12345678901,12345678901,0.0,0.0,0.0\r\n"
        b"G055,12345678901,12345678901,12345678901,0.0,0.0,0.0\r\n"
        b"X001,12345678901,12345678901,12345678901,0.0,0.0,0.0\r\n"
    )
    result = parse_posni_v2(content, control_version=None)
    assert result["control_version"] == "D00"


def test_short_line_skipped():
    content = b"G54,1.0\r\nG55,1.0,2.0,3.0,0.0,0.0,0.0\r\n"
    result = parse_posni_v2(content, control_version="C00")
    assert 54 not in result["work_offsets"]
    assert 55 in result["work_offsets"]
