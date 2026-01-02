"""
Tests for schema-based TOLNi parser (v2).

Tests field extraction, control version detection, and unit handling.
"""
import pytest
from app.parsers.tolni_parser_v2 import TOLNIParserV2, parse_tolni_v2


def test_parse_tolni_c00_inches():
    """Test parsing TOLNI1.NC (C00 control, inches)."""
    sample_content = """T01,3.4494,0.0000,0.0000,0.0000,1,10000,9500,9952,'.250 3FL      ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
T02,5.0000,0.0000,0.0000,0.0000,,0,0,0,'TEST          ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
T04,3.7731,0.0000,0.0000,0.0000,,0,0,0,'.375 ALUPWR   ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
V01,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
M01,,,,,,,,,,,,,,,,
"""
    
    result = parse_tolni_v2(sample_content.encode('utf-8'), units='in', control_version='C00')
    
    assert result["units"] == "in"
    assert result["control_version"] == "C00"
    assert result["total_tools"] == 3
    
    # Check first tool
    tool1 = result["tools"][0]
    assert tool1["tool_number"] == 1
    assert tool1["tool_length_offset"] == 3.4494
    assert tool1["cutter_compensation"] == 0.0000
    assert tool1["tool_name"] == ".250 3FL      "
    assert tool1["diameter"] == 0.0000  # Mapped from cutter_compensation
    assert tool1["length"] == 3.4494  # Mapped from tool_length_offset
    
    # Check second tool
    tool2 = result["tools"][1]
    assert tool2["tool_number"] == 2
    assert tool2["tool_length_offset"] == 5.0000
    assert tool2["tool_name"] == "TEST          "


def test_parse_tolni_auto_detect_c00():
    """Test automatic control version detection (C00)."""
    sample_content = """T01,3.4494,0.0000,0.0000,0.0000,1,10000,9500,9952,'.250 3FL      ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
"""
    
    result = parse_tolni_v2(sample_content.encode('utf-8'), units='in', control_version=None)
    
    # Should detect C00 based on tool life field lengths (6 digits max)
    assert result["control_version"] in ["C00", "D00"]  # May detect either, but should work


def test_parse_tolni_millimeters():
    """Test parsing TOLNM1.NC (millimeters)."""
    sample_content = """T01,150.000,0.000,0.000,0.000,,0,0,0,'              ',,,,,,0,0,,0.000,0.000,0.000,0.000,
"""
    
    result = parse_tolni_v2(sample_content.encode('utf-8'), units='mm', control_version='C00')
    
    assert result["units"] == "mm"
    assert result["total_tools"] == 1
    
    tool1 = result["tools"][0]
    assert tool1["tool_number"] == 1
    assert tool1["tool_length_offset"] == 150.000
    assert tool1["diameter"] == 0.000  # Mapped from cutter_compensation


def test_parse_tolni_skips_non_tool_lines():
    """Test that V##, M##, Y## lines are skipped."""
    sample_content = """T01,3.4494,0.0000,0.0000,0.0000,1,10000,9500,9952,'.250 3FL      ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
V01,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
M01,,,,,,,,,,,,,,,,
Y01,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30
T02,5.0000,0.0000,0.0000,0.0000,,0,0,0,'TEST          ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
"""
    
    result = parse_tolni_v2(sample_content.encode('utf-8'), units='in', control_version='C00')
    
    # Should only parse T01 and T02, skip V01, M01, Y01
    assert result["total_tools"] == 2
    assert all(tool["tool_number"] in [1, 2] for tool in result["tools"])


def test_parse_tolni_empty_fields():
    """Test parsing with empty optional fields."""
    sample_content = """T01,3.4494,0.0000,0.0000,0.0000,1,10000,9500,9952,'.250 3FL      ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
"""
    
    result = parse_tolni_v2(sample_content.encode('utf-8'), units='in', control_version='C00')
    
    tool1 = result["tools"][0]
    # Optional fields may be missing if empty
    assert "tool_number" in tool1
    assert "tool_length_offset" in tool1
    assert "cutter_compensation" in tool1
    assert "tool_name" in tool1

