"""Tests for FtpSyncService._process_item decision branches."""
import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ftp_sync_service import FtpSyncService


def _run():
    return SimpleNamespace(
        failed_files=0,
        conflict_files=0,
        skipped_files=0,
        success_files=0,
    )


def _item(tmp_path, content=b"%\nO1\n%", remote="/PROGRAM/O1.NC"):
    f = tmp_path / "O1.NC"
    f.write_bytes(content)
    return SimpleNamespace(
        local_path=str(f),
        relative_path="O1.NC",
        remote_path=remote,
        status="pending",
        error_message=None,
        details={},
        content_hash=None,
    )


@pytest.mark.asyncio
async def test_process_item_download_redirect():
    service = FtpSyncService(None)
    service._process_item_download = AsyncMock()
    config = SimpleNamespace(sync_direction="download", id=1)
    item = SimpleNamespace()
    await service._process_item(
        MagicMock(), config, MagicMock(), _run(), item, MagicMock(), set()
    )
    service._process_item_download.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_item_missing_local(tmp_path):
    service = FtpSyncService(None)
    config = SimpleNamespace(sync_direction="upload", id=1, auto_validate=False, auto_register=False)
    item = SimpleNamespace(
        local_path=str(tmp_path / "missing.NC"),
        relative_path="missing.NC",
        remote_path="/PROGRAM/missing.NC",
        status="pending",
        error_message=None,
        details={},
    )
    run = _run()
    await service._process_item(MagicMock(), config, MagicMock(), run, item, MagicMock(), set())
    assert item.status == "failed"
    assert run.failed_files == 1


@pytest.mark.asyncio
async def test_process_item_remote_conflict(tmp_path):
    service = FtpSyncService(None)
    config = SimpleNamespace(sync_direction="upload", id=1, auto_validate=False, auto_register=False)
    item = _item(tmp_path)
    run = _run()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    await service._process_item(db, config, MagicMock(), run, item, MagicMock(), {"O1.NC"})
    assert item.status == "conflict"
    assert run.conflict_files == 1


@pytest.mark.asyncio
async def test_process_item_unchanged_skip(tmp_path):
    service = FtpSyncService(None)
    content = b"%\nO1\n%"
    item = _item(tmp_path, content=content)
    digest = hashlib.sha256(content).hexdigest()
    config = SimpleNamespace(sync_direction="upload", id=1, auto_validate=False, auto_register=False)
    file_state = SimpleNamespace(last_uploaded_hash=digest)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = file_state
    run = _run()
    await service._process_item(db, config, MagicMock(), run, item, MagicMock(), set())
    assert item.status == "skipped"
    assert item.details.get("reason") == "unchanged_content"
    assert run.skipped_files == 1


@pytest.mark.asyncio
async def test_process_item_upload_success(tmp_path):
    service = FtpSyncService(None)
    service._upload_with_retry = AsyncMock(return_value={"success": True})
    config = SimpleNamespace(sync_direction="upload", id=1, auto_validate=False, auto_register=False)
    item = _item(tmp_path)
    run = _run()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    await service._process_item(db, config, MagicMock(id=1), run, item, MagicMock(), set())
    assert item.status == "uploaded"
    assert run.success_files == 1
