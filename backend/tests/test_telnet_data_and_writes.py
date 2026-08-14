"""Behavioral tests for telnet data-read and write-ops mixins."""
from unittest.mock import AsyncMock

import pytest

from app.clients._telnet_write_ops import format_macro_set_value
from app.clients.telnet_client import CNCTelnetClient
from tests.helpers import FakeReader, FakeWriter, make_brother_response


def _connected(response: bytes = b"") -> tuple[CNCTelnetClient, FakeWriter]:
    client = CNCTelnetClient("10.0.0.1", port=10000, timeout=5, command_delay=0.0)
    writer = FakeWriter()
    client.reader = FakeReader(response)  # type: ignore[assignment]
    client.writer = writer  # type: ignore[assignment]
    client._connected = True
    return client, writer


@pytest.mark.asyncio
async def test_get_current_program_info():
    data = "00010002" + (" " * 14)  # 4 + 4 + 14 = 22
    # Actually need block number in [8:22] — pad to 22 chars total
    data = "0001" + "0002" + "00000000001234"  # 4+4+14=22
    client, writer = _connected(make_brother_response("REDPRGN", data=data))
    info = await client.get_current_program_info()
    assert info["currently_executed_program_number"] == "0001"
    assert info["main_program_number"] == "0002"
    assert "00000000001234" in info["currently_executed_block_number"]
    assert b"REDPRGN" in writer.written[0]


@pytest.mark.asyncio
async def test_get_current_program_info_too_short():
    client, _ = _connected(make_brother_response("REDPRGN", data="short"))
    assert await client.get_current_program_info() is None


@pytest.mark.asyncio
async def test_get_file_control_data():
    # 4 + 4 + 10 + 10 = 28
    data = "0010" + "0200" + "0000012345" + "0000098765"
    client, _ = _connected(make_brother_response("REDFILE", data=data))
    info = await client.get_file_control_data()
    assert info["number_of_registrations"] == 10
    assert info["number_of_possible_registrations"] == 200
    assert info["memory_usage"] == 12345
    assert info["remaining_memory"] == 98765


@pytest.mark.asyncio
async def test_get_date_time():
    client, _ = _connected(make_brother_response("REDDATE", data="20240101123045EXTRA"))
    dt = await client.get_date_time()
    assert dt == "20240101123045"


@pytest.mark.asyncio
async def test_get_hd_modal():
    client, _ = _connected(make_brother_response("REDTOFM", data="001002"))
    modal = await client.get_hd_modal()
    assert modal["h_modal"] == "001"
    assert modal["d_modal"] == "002"


@pytest.mark.asyncio
async def test_get_macro_variable_out_of_range():
    client, writer = _connected()
    assert await client.get_macro_variable(100) is None
    assert writer.written == []


@pytest.mark.asyncio
async def test_get_macro_variable():
    client, writer = _connected(make_brother_response("REDMCNM", data="12.5000"))
    val = await client.get_macro_variable(500)
    assert val == pytest.approx(12.5, abs=1e-3)
    assert b"REDMCNM" in writer.written[0]


@pytest.mark.asyncio
async def test_get_current_program_content_invalid_count():
    client, writer = _connected()
    assert await client.get_current_program_content(0) is None
    assert writer.written == []


@pytest.mark.asyncio
async def test_parse_directory_listing_c00():
    # 11 bytes per entry: 8-char name + 3-digit size in blocks
    data = "O2000   " + "010" + "O2001   " + "020"
    client, _ = _connected()
    entries = await client.parse_directory_listing(data, control_type="C00")
    assert len(entries) == 2
    assert entries[0]["name"].strip() == "O2000"
    assert entries[0]["size"] == 10 * 128
    assert entries[0]["size_in_bytes"] is False


@pytest.mark.asyncio
async def test_parse_directory_listing_empty():
    client, _ = _connected()
    assert await client.parse_directory_listing("") is None


@pytest.mark.asyncio
async def test_write_tool_life_validation():
    client, writer = _connected()
    ok, status = await client.write_tool_life(0, 100)
    assert ok is False and status == "30"
    ok, status = await client.write_tool_life(1, -1)
    assert ok is False and status == "13"
    assert writer.written == []


@pytest.mark.asyncio
async def test_write_tool_life_success():
    client, writer = _connected(make_brother_response("WRTTLLF", status="00"))
    ok, status = await client.write_tool_life(5, 1000, life_type="TIME")
    assert ok is True
    assert status == "00"
    assert b"WRTTLLF" in writer.written[0]


@pytest.mark.asyncio
async def test_write_tool_offset_invalid_type():
    client, writer = _connected()
    ok, status = await client.write_tool_offset(1, "Z", 1.0)
    assert ok is False and status == "01"
    assert writer.written == []


@pytest.mark.asyncio
async def test_write_tool_offset_success():
    client, writer = _connected(make_brother_response("WRTTOFS", status="00"))
    ok, status = await client.write_tool_offset(3, "H", 1.2345)
    assert ok is True
    assert status == "00"
    assert b"WRTTOFS" in writer.written[0]


def test_format_macro_set_value_twelve_bytes():
    assert len(format_macro_set_value(42.0)) == 12
    assert format_macro_set_value(42.0).strip() == "42.0000"
    assert format_macro_set_value(12.5).strip() == "12.5000"


@pytest.mark.asyncio
async def test_write_macro_variable_out_of_range():
    client, writer = _connected()
    ok, status, verified = await client.write_macro_variable(100, 5.0)
    assert ok is False
    assert status == "30"
    assert verified is None
    assert writer.written == []


@pytest.mark.asyncio
async def test_write_macro_variable_success():
    client, writer = _connected(make_brother_response("WRTMCNM", status="00"))
    ok, status, verified = await client.write_macro_variable(920, 5.0, verify=False)
    assert ok is True
    assert status == "00"
    assert verified is None
    assert b"WRTMCNM" in writer.written[0]
    assert b"5.0000" in writer.written[0]


@pytest.mark.asyncio
async def test_write_macro_variable_verify_success(monkeypatch):
    client, writer = _connected(make_brother_response("WRTMCNM", status="00"))
    monkeypatch.setattr(client, "get_macro_variable", AsyncMock(return_value=5.0))
    ok, status, verified = await client.write_macro_variable(920, 5.0, verify=True)
    assert ok is True
    assert status == "00"
    assert verified == pytest.approx(5.0)
    assert b"WRTMCNM" in writer.written[0]


@pytest.mark.asyncio
async def test_clear_tool_life_delegates():
    client, writer = _connected(make_brother_response("WRTTLLF", status="00"))
    ok, status = await client.clear_tool_life(2)
    assert ok is True
    assert status == "00"
