"""More machines API coverage via TestClient + dependency overrides."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.db.base import get_db
from app.main import app
from app.schemas.machine import MachineCreate
import app.api.machines as machines_api


def _machine_obj(**kwargs):
    defaults = dict(
        id=1,
        name="Mill-1",
        model="Brother CNC",
        ip_address="10.0.0.1",
        ftp_port=21,
        http_port=80,
        ftp_username="anonymous",
        ftp_password="anonymous",
        path="/",
        tags=[],
        poll_interval_seconds=5,
        enabled=True,
        diameter_tolerance=0.01,
        length_tolerance_plus=0.02,
        length_tolerance_minus=0.0,
        tolerance_x=0.0394,
        tolerance_y=0.0394,
        tolerance_z=0.0394,
        use_machine_tool_tolerances=False,
        use_machine_wcs_tolerances=False,
        validate_tool_diameter=True,
        validate_tool_length=True,
        units="in",
        control_version="C00",
        layout_config=None,
        part_display_mode="parts",
        ftp_sync_enabled=False,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
        last_seen_at=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


client = TestClient(app, raise_server_exceptions=False)


def test_create_machine_duplicate_name():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _machine_obj()

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        r = client.post(
            "/api/machines/",
            json={"name": "Mill-1", "ip_address": "10.0.0.2"},
        )
        assert r.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_delete_machine_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        r = client.delete("/api/machines/99")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_update_machine_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        r = client.put("/api/machines/99", json={"name": "X"})
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_notification_sanitize():
    from app.services.notification_service import NotificationService

    cleaned = NotificationService._sanitize_alarm_for_notification(
        {"code": " NC1 ", "description": "desc", "cause": "x", "extra": 1}
    )
    assert cleaned == {"code": "NC1", "description": "desc"}


async def _noop_notify(*_a, **_k):
    return None


def test_notify_status_change_same_status_returns_early():
    import asyncio
    from app.services.notification_service import NotificationService

    svc = NotificationService()
    asyncio.run(svc.notify_status_change(1, "M", "standby", "standby", []))
