"""FTP sync local browse helper + route coverage."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import ftp_sync as ftp_api
from app.core.config import settings
from app.db.base import get_db
from app.main import app


def test_resolve_local_browse_path_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "FTP_SYNC_LOCAL_BROWSE_ROOT", str(tmp_path))
    resolved = ftp_api._resolve_local_browse_path(None)
    assert resolved == tmp_path.resolve()


def test_resolve_local_browse_path_child(tmp_path, monkeypatch):
    child = tmp_path / "job"
    child.mkdir()
    monkeypatch.setattr(settings, "FTP_SYNC_LOCAL_BROWSE_ROOT", str(tmp_path))
    resolved = ftp_api._resolve_local_browse_path(str(child))
    assert resolved == child.resolve()


def test_resolve_local_browse_path_outside(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "FTP_SYNC_LOCAL_BROWSE_ROOT", str(tmp_path))
    with pytest.raises(HTTPException) as ei:
        ftp_api._resolve_local_browse_path("/tmp/definitely-outside-browse-root-xyz")
    assert ei.value.status_code in (400, 404)


def test_require_ftp_sync_enabled():
    machine = SimpleNamespace(ftp_sync_enabled=False)
    with pytest.raises(HTTPException) as ei:
        ftp_api._require_ftp_sync_enabled(machine)
    assert ei.value.status_code == 403


def test_browse_local_folders_success(tmp_path, monkeypatch):
    (tmp_path / "A").mkdir()
    (tmp_path / "B").mkdir()
    monkeypatch.setattr(settings, "FTP_SYNC_LOCAL_BROWSE_ROOT", str(tmp_path))
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        id=1, ftp_sync_enabled=True, name="M"
    )

    def override():
        yield db

    client = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides[get_db] = override
    try:
        r = client.get("/api/machines/1/ftp-sync/local-folders")
        assert r.status_code == 200
        names = {d["name"] for d in r.json().get("directories", r.json().get("folders", []))}
        # Response shape may use directories list
        body = r.json()
        assert "A" in str(body) and "B" in str(body)
    finally:
        app.dependency_overrides.clear()
