"""Tests for TOLN tool name patching."""
import pytest

from app.parsers.tolni_parser_v2 import parse_tolni_v2
from app.services.tolni_patch import (
    collect_tool_names,
    format_tool_name_field,
    patch_tool_name_in_line,
    patch_tool_names,
    tool_names_match,
)

SAMPLE = """T01,3.4494,0.0000,0.0000,0.0000,1,10000,9500,9952,'.250 3FL      ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
T02,5.0000,0.0000,0.0000,0.0000,,0,0,0,'TEST          ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
V01,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
"""


def test_format_tool_name_field():
    assert format_tool_name_field("TEST") == "'TEST          '"
    assert len(format_tool_name_field("TEST")) == 16
    assert format_tool_name_field("abcdefghijklmnop") == "'abcdefghijklmn'"


def test_patch_tool_name_in_line():
    line = "T02,5.0000,0.0000,0.0000,0.0000,,0,0,0,'TEST          ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,"
    patched = patch_tool_name_in_line(line, 2, "NEW EM")
    assert "'NEW EM        '" in patched
    assert patched.startswith("T02,5.0000")


def test_patch_tool_names_preserves_other_tools():
    patched = patch_tool_names(SAMPLE, {2: "RENAMED"})
    assert "'RENAMED       '" in patched
    assert ".250 3FL" in patched
    assert "V01," in patched


def test_patch_tool_names_round_trip_parse():
    patched = patch_tool_names(SAMPLE, {2: "RENAMED"})
    result = parse_tolni_v2(patched.encode("utf-8"), units="in", control_version="C00")
    tool2 = next(t for t in result["tools"] if t["tool_number"] == 2)
    assert tool_names_match("RENAMED", tool2["tool_name"])


def test_collect_tool_names():
    names = collect_tool_names(SAMPLE, [1, 2, 99])
    assert names[1] == ".250 3FL      "
    assert names[2] == "TEST          "
    assert 99 not in names


def test_patch_missing_tool_raises():
    with pytest.raises(ValueError, match="not found"):
        patch_tool_names(SAMPLE, {99: "NOPE"})
