"""Tests for export utilities."""
from datetime import datetime

import pytest

from app.utils.export_utils import (
    TOOL_EXPORT_CSV_HEADERS,
    flatten_tool_data_for_csv,
    generate_csv,
    generate_json_export,
)


def test_generate_csv_happy_path():
    raw = generate_csv([{"a": 1, "b": 2}], ["a", "b"]).decode("utf-8")
    assert "a" in raw and "b" in raw
    assert "1" in raw and "2" in raw


def test_generate_csv_ignores_extra_keys():
    raw = generate_csv([{"a": 1, "extra": 9}], ["a"]).decode("utf-8")
    assert "extra" not in raw
    assert "1" in raw


def test_generate_json_datetime():
    raw = generate_json_export({"t": datetime(2024, 1, 2, 3, 4, 5)}).decode("utf-8")
    assert "2024-01-02T03:04:05" in raw


def test_generate_json_non_serializable():
    with pytest.raises(TypeError):
        generate_json_export({"x": object()})


def test_flatten_no_programs():
    rows = flatten_tool_data_for_csv(1, 0.25, "endmill", 10.0, 0, 0, [])
    assert len(rows) == 1
    assert rows[0]["program_id"] is None
    assert rows[0]["program_filename"] == ""
    assert rows[0]["program_runs"] == 0


def test_flatten_program_without_ops():
    programs = [
        {
            "program_id": 5,
            "filename": "A.NC",
            "version": 1,
            "production_runs": 3,
            "operations": [],
        }
    ]
    rows = flatten_tool_data_for_csv(2, 0.5, "drill", 20.0, 1, 3, programs)
    assert len(rows) == 1
    assert rows[0]["program_id"] == 5
    assert rows[0]["program_filename"] == "A.NC"
    assert rows[0]["operation_name"] == ""


def test_flatten_multi_op():
    programs = [
        {
            "program_id": 1,
            "filename": "B.NC",
            "version": 2,
            "production_runs": 1,
            "operations": [
                {"operation_name": "rough", "spindle_speed": 5000, "feedrate_cutting": 100},
                {"operation_name": "finish", "spindle_speed": 8000, "feedrate_cutting": 50},
            ],
        }
    ]
    rows = flatten_tool_data_for_csv(3, 0.375, "mill", 30.0, 1, 1, programs)
    assert len(rows) == 2
    assert rows[0]["operation_name"] == "rough"
    assert rows[1]["operation_name"] == "finish"
    assert rows[0]["tool_number"] == rows[1]["tool_number"] == 3


def test_headers_and_round_trip():
    assert len(TOOL_EXPORT_CSV_HEADERS) == 19
    assert TOOL_EXPORT_CSV_HEADERS[0] == "tool_number"
    assert TOOL_EXPORT_CSV_HEADERS[-1] == "feedrate_transition"
    rows = flatten_tool_data_for_csv(1, 0.1, "t", 1.0, 0, 0, [])
    raw = generate_csv(rows, TOOL_EXPORT_CSV_HEADERS).decode("utf-8")
    assert "tool_number" in raw
