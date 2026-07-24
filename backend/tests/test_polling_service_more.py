"""PollingService coordinator unit tests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.polling import PollingService


@pytest.mark.asyncio
async def test_start_and_stop():
    ws = MagicMock()
    svc = PollingService(ws)
    with patch.object(svc, "_prepopulate_control_versions", AsyncMock()):
        with patch.object(svc, "_poll_loop", AsyncMock()):
            with patch.object(svc, "_tool_poll_loop", AsyncMock()):
                await svc.start()
                assert svc.is_running is True
                await svc.start()  # already running
                await svc.stop()
                assert svc.is_running is False


@pytest.mark.asyncio
async def test_poll_all_machines_no_machines():
    svc = PollingService(MagicMock())
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    with patch("app.services.polling.SessionLocal", return_value=db):
        await svc._poll_all_machines()
    assert svc.pollers == {}


@pytest.mark.asyncio
async def test_poll_all_machines_adds_poller():
    ws = MagicMock()
    ws.broadcast_status = AsyncMock()
    svc = PollingService(ws)
    machine = SimpleNamespace(
        id=7,
        name="M",
        ip_address="10.0.0.1",
        enabled=True,
        poll_interval_seconds=5,
        units="in",
        part_display_mode="parts",
        control_version="C00",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [machine]
    fake_poller = MagicMock()
    fake_poller.last_fast_poll_time = None
    fake_poller.seed_last_status_from_db = MagicMock()
    fake_poller.poll = AsyncMock(return_value={"status": "standby", "machine_id": 7})
    with patch("app.services.polling.SessionLocal", return_value=db):
        with patch("app.services.polling.MachinePoller", return_value=fake_poller):
            await svc._poll_all_machines()
    assert 7 in svc.pollers
    fake_poller.poll.assert_awaited()
    ws.broadcast_status.assert_awaited()


def test_history_cycle_empty():
    from app.services.history_service import get_cycle_history

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    assert get_cycle_history(db, machine_id=1, limit=10) == []


def test_history_cycle_limit_zero():
    from datetime import datetime
    from app.services.history_service import get_cycle_history

    row = SimpleNamespace(
        time=datetime(2024, 1, 1, 12, 0, 0),
        status="operating",
        status_code=3,
        program_no="O1",
        error_no=None,
        folder_name="F",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [row]
    assert get_cycle_history(db, machine_id=1, limit=0) == []


@pytest.mark.asyncio
async def test_refresh_tool_data():
    from datetime import datetime

    from tests.helpers import make_machine
    from app.services.polling import MachinePoller

    ws = MagicMock()
    ws.get_machine_status.return_value = {"status": "standby"}
    ws.broadcast_status = AsyncMock()
    svc = PollingService(ws)
    machine = make_machine(id=1, name="M1")
    poller = MachinePoller(machine, ws)
    poller.poll_tool_data = AsyncMock(return_value={"tools": []})
    svc.pollers[1] = poller
    data = await svc.refresh_tool_data(1)
    assert data == {"tools": []}
    assert poller.last_tool_poll_time is not None
    ws.broadcast_status.assert_awaited()
    with pytest.raises(ValueError):
        await svc.refresh_tool_data(99)


def test_get_machine_status_snapshot():
    from datetime import datetime

    from tests.helpers import make_machine
    from app.services.polling import MachinePoller

    svc = PollingService(MagicMock())
    machine = make_machine(id=1, name="M1")
    poller = MachinePoller(machine, MagicMock())
    poller.is_online = True
    poller.last_poll_time = datetime.utcnow()
    poller.consecutive_failures = 0
    svc.pollers[1] = poller
    snap = svc.get_machine_status(1)
    assert snap["machine_id"] == 1
    assert snap["is_online"] is True
    assert svc.get_machine_status(99) is None
