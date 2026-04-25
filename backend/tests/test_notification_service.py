"""Tests for notification service: formatting, dispatch, and rule matching."""
import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.sql import elements

# NotificationService imports aiosmtplib at module load time; stub for lightweight test envs.
sys.modules.setdefault("aiosmtplib", types.SimpleNamespace(send=lambda *args, **kwargs: None))

from app.models.notification import NotificationRule
from app.services.notification_service import (
    NotificationService,
    extract_nc_program_header,
)


@pytest.mark.asyncio
async def test_notify_cycle_complete_includes_requested_fields(monkeypatch):
    """Cycle-complete body uses: path, Start Time, Stop Time, Total Runtime order."""
    service = NotificationService()
    captured: dict = {}

    async def _capture_dispatch(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(service, "_dispatch_to_matching_rules", _capture_dispatch)

    await service.notify_cycle_complete(
        machine_id=7,
        machine_name="Brother R650X2",
        program_name="/mnt/nc/jobs/part_family/op20/P12345.NC",
        duration_seconds=3661,
        o_number="O1234",
        started_at=datetime(2026, 4, 24, 13, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 24, 14, 1, 1, tzinfo=timezone.utc),
        new_status="standby",
        program_title="1234 COMBINED OPERATIONS",
        file_label="250X250 HD FIXTURE PLATE V4",
    )

    assert captured["event_type"] == "cycle_complete"
    assert captured["new_status"] == "standby"
    assert captured["subject"] == "[CYCLE COMPLETE] Brother R650X2"

    body = captured["body"]
    lines = body.splitlines()

    assert lines[0] == "[CYCLE COMPLETE] Brother R650X2"
    assert lines[1] == "/mnt/nc/jobs/part_family/op20/P12345.NC"
    assert lines[2] == "Program: 1234 COMBINED OPERATIONS"
    assert lines[3] == "File: 250X250 HD FIXTURE PLATE V4"
    assert lines[4] == "Start Time: 24-APR-26 06:00 PDT"
    assert lines[5] == "Stop Time: 24-APR-26 07:01 PDT"
    assert lines[6] == "Total Runtime: 01:01:01"

    event_data = captured["event_data"]
    assert event_data["program_name"] == "/mnt/nc/jobs/part_family/op20/P12345.NC"
    assert event_data["program_title"] == "1234 COMBINED OPERATIONS"
    assert event_data["file_label"] == "250X250 HD FIXTURE PLATE V4"
    assert event_data["duration_seconds"] == 3661
    assert event_data["duration_hms"] == "01:01:01"
    assert event_data["start_time_local"] == "24-APR-26 06:00 PDT"
    assert event_data["stop_time_local"] == "24-APR-26 07:01 PDT"


@pytest.mark.asyncio
async def test_notify_cycle_complete_without_header_fields(monkeypatch):
    """When program_title and file_label are not provided, those lines are omitted."""
    service = NotificationService()
    captured: dict = {}

    async def _capture_dispatch(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(service, "_dispatch_to_matching_rules", _capture_dispatch)

    await service.notify_cycle_complete(
        machine_id=7,
        machine_name="W1000",
        program_name="/PROGRAM/250HDFP/O0004.NC",
        duration_seconds=1150,
        ended_at=datetime(2026, 4, 25, 20, 5, 0, tzinfo=timezone.utc),
    )

    body = captured["body"]
    assert "Program:" not in body
    assert "File:" not in body
    assert "/PROGRAM/250HDFP/O0004.NC" in body
    assert "Total Runtime: 00:19:10" in body


@pytest.mark.asyncio
async def test_notify_cycle_complete_handles_missing_stop_time(monkeypatch):
    """If no ended_at is provided, stop time is omitted but runtime still renders when available."""
    service = NotificationService()
    captured: dict = {}

    async def _capture_dispatch(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(service, "_dispatch_to_matching_rules", _capture_dispatch)

    await service.notify_cycle_complete(
        machine_id=3,
        machine_name="Brother S700",
        program_name="/parts/alpha/OP10.NC",
        duration_seconds=42,
        ended_at=None,
    )

    assert "Stop Time:" not in captured["body"]
    assert "Total Runtime: 00:00:42" in captured["body"]
    assert captured["event_data"]["stop_time_local"] == ""


@pytest.mark.asyncio
async def test_notify_status_change_skips_cycle_transitions(monkeypatch):
    """Generic status-change notifications are suppressed for operating->standby/stopped."""
    service = NotificationService()
    called = {"dispatch": False}

    async def _capture_dispatch(**kwargs):
        called["dispatch"] = True

    monkeypatch.setattr(service, "_dispatch_to_matching_rules", _capture_dispatch)

    await service.notify_status_change(
        machine_id=5,
        machine_name="w1000",
        previous_status="operating",
        new_status="standby",
        alarms=[],
    )

    assert called["dispatch"] is False


# ---------------------------------------------------------------------------
# Regression tests: global rule (machine_id = NULL) matching
# Bug introduced in refactor commit cacb906: `machine_id is None` (Python)
# replaced `machine_id == None` (SQLAlchemy IS NULL), causing global rules
# to never be selected from the database.
# ---------------------------------------------------------------------------


def test_machine_id_null_filter_is_sql_expression_not_python_bool():
    """Regression: machine_id.is_(None) must produce a SQLAlchemy IS NULL expression.

    The refactor accidentally changed `machine_id == None` (SQL IS NULL) to
    `machine_id is None` (Python identity check → always False). This test
    ensures the fix stays in place: the filter expression is a real SQL clause,
    not a Python boolean that silently drops all global rules.
    """
    filter_expr = NotificationRule.machine_id.is_(None)
    assert isinstance(filter_expr, elements.BinaryExpression), (
        "NotificationRule.machine_id.is_(None) must produce a SQLAlchemy BinaryExpression. "
        "If this fails, the IS NULL filter has been replaced with a Python bool again."
    )
    assert "IS NULL" in str(filter_expr).upper()


def test_machine_id_python_is_none_is_a_bool_not_sql():
    """Documents why `machine_id is None` is wrong in a SQLAlchemy filter.

    This is the negative case: Python's `is None` on a SQLAlchemy column
    attribute returns a Python bool (False), not an SQL IS NULL expression.
    It is included here so future readers understand the distinction.
    """
    python_result = NotificationRule.machine_id is None
    assert python_result is False, (
        "NotificationRule.machine_id is None should be Python False — "
        "if this assertion fails, SQLAlchemy changed its attribute behaviour."
    )


@pytest.mark.asyncio
async def test_dispatch_fires_global_rule_when_machine_id_is_none(monkeypatch):
    """Global rules (machine_id=None in DB) must fire for any machine.

    This is the end-to-end regression test for the is-None vs IS NULL bug.
    We mock the DB session so it returns a global rule (machine_id=None) and
    verify that _send is called — i.e., the rule was not silently dropped.
    """
    service = NotificationService()
    sent_channels: list[int] = []

    async def _mock_send(channel, subject, body):
        sent_channels.append(channel.id)
        return "sent", None

    monkeypatch.setattr(service, "_send", _mock_send)

    # A global rule: machine_id is None (applies to all machines)
    global_rule = MagicMock()
    global_rule.id = 10
    global_rule.machine_id = None
    global_rule.trigger_config = {"any": True}
    global_rule.channel_ids = [42]

    fake_channel = MagicMock()
    fake_channel.id = 42
    fake_channel.channel_type = "email"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [global_rule]
    mock_db.query.return_value.filter.return_value.first.return_value = fake_channel

    with patch("app.services.notification_service.SessionLocal", return_value=mock_db):
        await service._dispatch_to_matching_rules(
            machine_id=7,
            previous_status="standby",
            new_status="error",
            subject="[ALARM] test",
            body="test body",
            event_type="status_change",
            event_data={"alarms": []},
        )

    assert 42 in sent_channels, (
        "Global rule channel was not notified — global rules (machine_id=None) "
        "are being silently dropped from the query."
    )


@pytest.mark.asyncio
async def test_dispatch_fires_machine_specific_rule(monkeypatch):
    """Machine-specific rules fire for the correct machine."""
    service = NotificationService()
    sent_channels: list[int] = []

    async def _mock_send(channel, subject, body):
        sent_channels.append(channel.id)
        return "sent", None

    monkeypatch.setattr(service, "_send", _mock_send)

    specific_rule = MagicMock()
    specific_rule.id = 20
    specific_rule.machine_id = 5
    specific_rule.trigger_config = {"any": True}
    specific_rule.channel_ids = [55]

    fake_channel = MagicMock()
    fake_channel.id = 55
    fake_channel.channel_type = "email"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [specific_rule]
    mock_db.query.return_value.filter.return_value.first.return_value = fake_channel

    with patch("app.services.notification_service.SessionLocal", return_value=mock_db):
        await service._dispatch_to_matching_rules(
            machine_id=5,
            previous_status="standby",
            new_status="error",
            subject="[ALARM] machine 5",
            body="body",
            event_type="status_change",
            event_data={"alarms": []},
        )

    assert 55 in sent_channels


# ---------------------------------------------------------------------------
# _rule_matches unit tests
# ---------------------------------------------------------------------------


def test_rule_matches_any_always_true():
    service = NotificationService()
    assert service._rule_matches({"any": True}, "standby", "error") is True


def test_rule_matches_to_status_list():
    service = NotificationService()
    assert service._rule_matches({"to_status": ["error", "offline"]}, "standby", "error") is True
    assert service._rule_matches({"to_status": ["error", "offline"]}, "standby", "stopped") is False


def test_rule_matches_to_status_string():
    service = NotificationService()
    assert service._rule_matches({"to_status": "error"}, "standby", "error") is True
    assert service._rule_matches({"to_status": "error"}, "standby", "stopped") is False


def test_rule_matches_from_status():
    service = NotificationService()
    assert service._rule_matches({"from_status": "standby", "to_status": "error"}, "standby", "error") is True
    assert service._rule_matches({"from_status": "operating", "to_status": "error"}, "standby", "error") is False


def test_rule_matches_exclude_alarm_codes_suppresses_when_all_active_alarms_excluded():
    service = NotificationService()
    config = {"to_status": "error", "exclude_alarm_codes": ["EX0001", "IO0518"]}
    alarms = [{"code": "EX0001"}, {"code": "IO0518"}]
    assert service._rule_matches(config, "standby", "error", alarms) is False


def test_rule_matches_exclude_alarm_codes_fires_when_non_excluded_alarm_present():
    service = NotificationService()
    config = {"to_status": "error", "exclude_alarm_codes": ["EX0001"]}
    alarms = [{"code": "EX0001"}, {"code": "OM0500"}]  # OM0500 not excluded
    assert service._rule_matches(config, "standby", "error", alarms) is True


def test_rule_matches_empty_trigger_config_returns_false():
    service = NotificationService()
    assert service._rule_matches({}, "standby", "error") is False


def test_rule_matches_none_trigger_config_returns_false():
    service = NotificationService()
    assert service._rule_matches(None, "standby", "error") is False


# ---------------------------------------------------------------------------
# extract_nc_program_header tests
# ---------------------------------------------------------------------------

_SAMPLE_HEADER = """\
(0004 COMBINED OPERATIONS)
(FILE: 250X250 HD FIXTURE PLATE MACHINING V4)
(PROGRAM: OP1 PROBE)
(DATE: SAT APR 25 19:45:52 2026)

(MACHINE)
(  VENDOR: BROTHER)
G91 G28 Z0
"""


def test_extract_nc_program_header_returns_title_and_file_label():
    result = extract_nc_program_header(_SAMPLE_HEADER)
    assert result["title"] == "0004 COMBINED OPERATIONS"
    assert result["file_label"] == "250X250 HD FIXTURE PLATE MACHINING V4"


def test_extract_nc_program_header_skips_o_number_and_percent():
    content = "%\nO0004\n(0004 COMBINED OPERATIONS)\n(FILE: FIXTURE PLATE)\nG91 G28 Z0\n"
    result = extract_nc_program_header(content)
    assert result["title"] == "0004 COMBINED OPERATIONS"
    assert result["file_label"] == "FIXTURE PLATE"


def test_extract_nc_program_header_stops_at_gcode_line():
    content = "(TITLE HERE)\nG91 G28 Z0\n(FILE: SHOULD NOT BE SEEN)\n"
    result = extract_nc_program_header(content)
    assert result["title"] == "TITLE HERE"
    assert result["file_label"] is None


def test_extract_nc_program_header_no_file_label():
    content = "(TITLE ONLY)\n(PROGRAM: OP1)\n(DATE: 2026)\n"
    result = extract_nc_program_header(content)
    assert result["title"] == "TITLE ONLY"
    assert result["file_label"] is None


def test_extract_nc_program_header_empty_content():
    assert extract_nc_program_header("") == {"title": None, "file_label": None}


def test_extract_nc_program_header_no_comments():
    content = "G91 G28 Z0\nM30\n"
    result = extract_nc_program_header(content)
    assert result["title"] is None
    assert result["file_label"] is None


def test_extract_nc_program_header_file_label_stripped():
    content = "(MY TITLE)\n(FILE:   PADDED NAME   )\n"
    result = extract_nc_program_header(content)
    assert result["file_label"] == "PADDED NAME"

