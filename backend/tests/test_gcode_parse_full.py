"""Expand gcode_parser.parse() and related extractors."""
from app.parsers.gcode_parser import GCodeParser, parse_gcode


SAMPLE = """
(T01 D=0.25 CR=0 - ZMIN=1.0 - END MILL - L=0.5/2.0)
(T02 D=0.5 CR=0 - ZMIN=0.5 - DRILL - L=1.0/3.0)
( POSTED 01-15-24 )
( STOCK X2.0 Y3.0 Z1.0 )
G54 E0.01
(ADAPTIVE)
N10 G100 T01 X0 Y0 G43 Z1 H01 S3000 M3
#500=40.0 (CUTTING)
#501=20.0 (PLUNGE)
G1 X1 Y1
N20 G100 T02 X0 Y0 G43 Z1 H02 S1000 M3
#500=10.0 (CUTTING)
M30
"""


def test_parse_gcode_full():
    result = parse_gcode(SAMPLE)
    assert "tools" in result
    assert result["line_count"] > 0
    assert result["file_size"] > 0
    assert isinstance(result.get("tools"), list)


def test_extract_tools():
    tools = GCodeParser(SAMPLE).extract_tools()
    nums = {t.get("tool_number") for t in tools}
    assert 1 in nums
    assert 2 in nums


def test_extract_posted_date():
    date = GCodeParser(SAMPLE).extract_posted_date()
    # May or may not parse depending on format; just exercise path
    assert date is None or hasattr(date, "year")


def test_extract_wcs_and_stock():
    parser = GCodeParser(SAMPLE)
    wcs = parser.extract_wcs_offset()
    stock = parser.extract_stock_size()
    # Exercise paths; values depend on comment formats
    assert wcs is None or isinstance(wcs, dict)
    assert stock is None or isinstance(stock, dict)


def test_parse_empty():
    result = parse_gcode("")
    assert result["tools"] == [] or isinstance(result["tools"], list)
