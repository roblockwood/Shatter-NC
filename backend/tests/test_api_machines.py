"""API TestClient tests with dependency overrides."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.base import get_db
from app.main import app


def _machine(**kwargs):
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


def test_list_machines_empty():
    db = MagicMock()
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        r = client.get("/api/machines/")
        assert r.status_code == 200
        assert r.json() == []
    finally:
        app.dependency_overrides.clear()


def test_get_machine_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        r = client.get("/api/machines/99")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_get_machine_ok():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _machine()

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        r = client.get("/api/machines/1")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Mill-1"
        assert "ftp_password" not in body
    finally:
        app.dependency_overrides.clear()


def test_ftp_browse_machine_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("FTP_SYNC_LOCAL_BROWSE_ROOT", str(tmp_path))
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        r = client.get("/api/machines/1/ftp-sync/local-folders")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()
