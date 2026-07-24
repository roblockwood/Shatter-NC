"""Behavioral tests for NC tool-sequence extractor."""
from app.parsers.nc_tool_sequence_parser import (
    extract_tool_sequence,
    build_transition_counts,
    _clean_line,
)


def test_clean_line_block_skip():
    assert _clean_line("/T01 M6") == ""
    assert _clean_line("  /comment") == ""


def test_clean_line_strips_comments():
    assert _clean_line("T01 (comment) M6") == "T01  M6"
    assert _clean_line("T01 ; trailing").startswith("T01")


def test_g100_same_line():
    nc = "N30 G100 T02 X0 S5000 M3\nN40 G100 T05 X10\n"
    assert extract_tool_sequence(nc) == [2, 5]


def test_m6_same_line_variants():
    nc = "T03 M6\nM6 T04\n"
    assert extract_tool_sequence(nc) == [3, 4]


def test_m6_preselect_previous_line():
    nc = "T07\nM6\n"
    assert extract_tool_sequence(nc) == [7]


def test_block_skip_ignored():
    nc = "T01 M6\n/T99 M6\nT02 M6\n"
    assert extract_tool_sequence(nc) == [1, 2]


def test_commented_tool_ignored():
    nc = "T01 M6\n(T99 M6)\nT02 M6\n"
    assert extract_tool_sequence(nc) == [1, 2]


def test_does_not_match_h_or_d_words():
    nc = "H02 D02\nT03 M6\n"
    assert extract_tool_sequence(nc) == [3]


def test_build_transition_counts():
    seq = [1, 2, 2, 3, 1]
    counts = build_transition_counts(seq)
    assert counts[(1, 2)] == 1
    assert counts[(2, 3)] == 1
    assert counts[(3, 1)] == 1
    assert (2, 2) not in counts


def test_empty_sequence():
    assert extract_tool_sequence("") == []
    assert build_transition_counts([]) == {}
