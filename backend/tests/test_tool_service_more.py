"""Additional aggregation tests for ToolService."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.tool_service import ToolService


def test_get_tool_detail_returns_empty_shape_when_tool_is_unknown():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = []

    result = ToolService.get_tool_detail(db, 88)

    assert result.tool_number == 88
    assert result.specifications["diameter_range"] == [0, 0]
    assert result.usage_statistics["total_production_runs"] == 0
    assert result.machines == []
    assert result.alarms == []


def test_operation_stats_exposes_schema_mismatch_for_aggregate_values():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = [
        SimpleNamespace(
            operation_name="ROUGH",
            spindle_speed=10000.0,
            feedrate_cutting=50.0,
            feedrate_plunge=None,
            feedrate_finish=None,
            feedrate_entry=None,
            feedrate_exit=None,
            feedrate_direct=None,
            feedrate_transition=None,
        ),
        SimpleNamespace(
            operation_name="ROUGH",
            spindle_speed=12000.0,
            feedrate_cutting=70.0,
            feedrate_plunge=None,
            feedrate_finish=None,
            feedrate_entry=None,
            feedrate_exit=None,
            feedrate_direct=None,
            feedrate_transition=None,
        ),
        SimpleNamespace(
            operation_name=None,
            spindle_speed=None,
            feedrate_cutting=10.0,
            feedrate_plunge=None,
            feedrate_finish=None,
            feedrate_entry=None,
            feedrate_exit=None,
            feedrate_direct=None,
            feedrate_transition=None,
        ),
    ]

    with pytest.raises(ValueError, match="spindle_speed"):
        ToolService._get_operation_stats(db, 5)


def test_alarm_correlation_groups_codes_and_keeps_latest_occurrence():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = [SimpleNamespace(id=4)]
    alarms = [
        SimpleNamespace(alarm_code="A1", alarm_message="Old", time=datetime(2024, 1, 1)),
        SimpleNamespace(alarm_code="A1", alarm_message="New", time=datetime(2024, 1, 3)),
        SimpleNamespace(alarm_code="B2", alarm_message="Other", time=datetime(2024, 1, 2)),
    ]
    db.query.return_value.filter.return_value.all.return_value = alarms

    result = ToolService._get_alarm_correlation(db, 5)

    assert result[0].alarm_code == "A1"
    assert result[0].occurrences == 2
    assert result[0].alarm_message == "New"
    assert result[0].last_occurrence == datetime(2024, 1, 3)


def test_detailed_usage_stats_divides_runtime_by_tools_and_counts_parts():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = [SimpleNamespace(id=4)]
    runs = [
        SimpleNamespace(program_id=4, duration_seconds=100, parts_produced=3),
        SimpleNamespace(program_id=4, duration_seconds=None, parts_produced=None),
    ]
    db.query.return_value.filter.return_value.all.return_value = runs
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        program_metadata={"tools": [{}, {}]}
    )

    result = ToolService._get_detailed_usage_stats(db, 5)

    assert result == {
        "total_programs": 1,
        "total_production_runs": 2,
        "estimated_runtime_seconds": 50.0,
        "total_parts_produced": 3,
    }
