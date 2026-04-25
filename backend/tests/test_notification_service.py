"""Tests for cycle-complete notification formatting."""
import re
import sys
import types
from datetime import datetime, timezone

import pytest

# NotificationService imports aiosmtplib at module load time; stub for lightweight test envs.
sys.modules.setdefault("aiosmtplib", types.SimpleNamespace(send=lambda *args, **kwargs: None))

from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_notify_cycle_complete_includes_requested_fields(monkeypatch):
    """Cycle-complete body includes machine, full program path, local stop time, and total runtime."""
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
    )

    assert captured["event_type"] == "cycle_complete"
    assert captured["new_status"] == "standby"
    assert captured["subject"] == "[CYCLE COMPLETE] Brother R650X2"

    body = captured["body"]
    assert "[CYCLE COMPLETE] Brother R650X2" in body
    assert "Program: /mnt/nc/jobs/part_family/op20/P12345.NC" in body
    assert "Total Runtime: 01:01:01" in body
    assert "Start Time: 24-APR-26 06:00 PDT" in body
    assert "Stop Time: 24-APR-26 07:01 PDT" in body

    event_data = captured["event_data"]
    assert event_data["program_name"] == "/mnt/nc/jobs/part_family/op20/P12345.NC"
    assert event_data["duration_seconds"] == 3661
    assert event_data["duration_hms"] == "01:01:01"
    assert event_data["start_time_local"] == "24-APR-26 06:00 PDT"
    assert event_data["stop_time_local"] == "24-APR-26 07:01 PDT"


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
