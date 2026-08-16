"""Tests for tool name FTP write service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api._status_state import ToolChangeItem
from app.services.tool_name_write_service import write_tool_names_via_ftp
from app.services.tolni_patch import tool_names_match
from app.services.tool_write_service import apply_tool_changes_batch

FULL_TOLN = """T07,3.4494,0.0000,0.0000,0.0000,1,10000,9500,9952,'OLD NAME      ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
M01,5,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0
"""


def _machine():
    m = MagicMock()
    m.id = 1
    m.ip_address = "10.0.0.1"
    m.ftp_port = 21
    m.ftp_username = "u"
    m.ftp_password = "p"
    m.units = "in"
    m.control_version = "C00"
    return m


def _db(machine):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = machine
    return db


@pytest.mark.asyncio
async def test_batch_name_changes_via_ftp(monkeypatch):
    from app.services import tool_name_write_service

    async def fake_write(machine, updates, telnet_client=None):
        assert updates == {7: "NEW EM"}
        return {7: "OLD NAME"}, {7: True}

    monkeypatch.setattr(tool_name_write_service, "write_tool_names_via_ftp", fake_write)

    with patch("app.services.machine_state_validator.MachineStateValidator") as Validator:
        Validator.return_value.validate_safe_for_write = AsyncMock(
            return_value=(True, None, {})
        )
        with patch("app.clients.telnet_client.create_fresh_connection") as conn:
            conn.return_value = AsyncMock()
            conn.return_value.disconnect = AsyncMock()
            with patch("app.services.audit_logger.AuditLogger"):
                result = await apply_tool_changes_batch(
                    _machine(),
                    1,
                    [
                        ToolChangeItem(
                            operation_type="name",
                            tool_number=7,
                            name_value="NEW EM",
                            client_id="t7-name",
                        )
                    ],
                    _db(_machine()),
                )

    assert result.successful == 1
    assert result.failed == 0
    assert result.results[0].operation_type == "name"
    assert result.results[0].name_value == "NEW EM"


@pytest.mark.asyncio
async def test_batch_telnet_then_name_order(monkeypatch):
    from app.services import tool_name_write_service

    order = []

    telnet = AsyncMock()
    telnet.write_tool_offset = AsyncMock(side_effect=lambda *a, **k: order.append("offset") or (True, "00"))
    telnet.disconnect = AsyncMock()

    async def fake_write(machine, updates, telnet_client=None):
        order.append("name")
        return {7: ""}, {7: True}

    monkeypatch.setattr(tool_name_write_service, "write_tool_names_via_ftp", fake_write)

    with patch("app.services.machine_state_validator.MachineStateValidator") as Validator:
        Validator.return_value.validate_safe_for_write = AsyncMock(
            return_value=(True, None, {})
        )
        with patch("app.clients.telnet_client.create_fresh_connection", return_value=telnet):
            with patch("app.services.audit_logger.AuditLogger"):
                result = await apply_tool_changes_batch(
                    _machine(),
                    1,
                    [
                        ToolChangeItem(
                            operation_type="name",
                            tool_number=7,
                            name_value="NEW EM",
                        ),
                        ToolChangeItem(
                            operation_type="offset",
                            tool_number=7,
                            offset_type="H",
                            value=1.5,
                        ),
                    ],
                    _db(_machine()),
                )

    assert result.successful == 2
    assert order == ["offset", "name"]


@pytest.mark.asyncio
async def test_write_tool_names_reads_full_file_via_ftp():
    machine = _machine()
    ftp = AsyncMock()
    ftp.get_tool_table_data = AsyncMock(return_value=FULL_TOLN)
    ftp.upload_file = AsyncMock(return_value={"success": True})
    ftp.disconnect = AsyncMock()

    telnet = AsyncMock()
    patched_toln = FULL_TOLN.replace("'OLD NAME      '", "'NEW EM        '")
    telnet.get_tool_table_data = AsyncMock(side_effect=[FULL_TOLN, patched_toln])
    telnet.disconnect = AsyncMock()

    with patch(
        "app.services.tool_name_write_service._ftp_client_for_machine",
        return_value=ftp,
    ):
        old_names, verified = await write_tool_names_via_ftp(
            machine,
            {7: "NEW EM"},
            telnet_client=telnet,
        )

    ftp.get_tool_table_data.assert_awaited_once()
    upload_bytes = ftp.upload_file.await_args.args[0]
    assert b"M01," in upload_bytes
    assert b"'NEW EM        '" in upload_bytes
    assert tool_names_match("OLD NAME", old_names[7])
    assert verified[7] is True
