"""Broader telnet mixin coverage via mocked _send_command / wrappers."""
from unittest.mock import AsyncMock, patch

import pytest

from app.clients.telnet_client import CNCTelnetClient
from tests.helpers import FakeReader, FakeWriter, make_brother_response


def _connected(response: bytes = b"") -> CNCTelnetClient:
    client = CNCTelnetClient("10.0.0.1", port=10000, timeout=5, command_delay=0.0)
    client.reader = FakeReader(response)  # type: ignore[assignment]
    client.writer = FakeWriter()  # type: ignore[assignment]
    client._connected = True
    return client


@pytest.mark.asyncio
async def test_lod_wrappers_delegate_to_load_data():
    client = _connected()
    client.load_data = AsyncMock(return_value="PAYLOAD")

    assert await client.get_memory_data() == "PAYLOAD"
    client.load_data.assert_awaited_with("MEM", verbose=False)

    assert await client.get_tool_table_data(units="in") == "PAYLOAD"
    client.load_data.assert_awaited_with("TOLNI1", verbose=False)

    assert await client.get_tool_table_data(units="mm") == "PAYLOAD"
    client.load_data.assert_awaited_with("TOLNM1", verbose=False)

    assert await client.get_position_data(units="mm") == "PAYLOAD"
    client.load_data.assert_awaited_with("POSNM1", verbose=False)

    assert await client.get_monitor_data() == "PAYLOAD"
    assert await client.get_alarm_data() == "PAYLOAD"
    assert await client.get_panel_data() == "PAYLOAD"


@pytest.mark.asyncio
async def test_get_prd3_data_primary_and_fallback():
    client = _connected()
    client.load_data = AsyncMock(side_effect=[None, "FALLBACK"])
    client.detect_control_type = AsyncMock(return_value="D00")
    data = await client.get_prd3_data(control_version=None)
    assert data == "FALLBACK"
    assert client.load_data.await_args_list[0].args[0] == "PRDD3"
    assert client.load_data.await_args_list[1].args[0] == "PRD3"


@pytest.mark.asyncio
async def test_get_atc_magazine_data():
    client = _connected()
    client.load_data = AsyncMock(return_value="ATC")
    assert await client.get_atc_magazine_data(control_version="C00") == "ATC"
    client.load_data.assert_awaited_with("ATCTL", verbose=False)


@pytest.mark.asyncio
async def test_get_tool_compensation_and_life():
    client = _connected()
    client._send_command = AsyncMock(return_value=(True, "00", "1.2345"))
    val = await client.get_tool_compensation(1, 0)
    assert val == pytest.approx(1.2345, abs=1e-3)

    client2 = _connected()
    client2._send_command = AsyncMock(return_value=(True, "00", "000100"))
    life = await client2.get_tool_life(1, 3)
    assert life == 100


@pytest.mark.asyncio
async def test_get_directory_listing():
    client = _connected()
    client._send_command = AsyncMock(return_value=(True, "00", "O2000   010"))
    raw = await client.get_directory_listing()
    assert raw is not None
    assert "O2000" in raw


@pytest.mark.asyncio
async def test_get_plc_signal_bool():
    client = _connected()
    client._send_command = AsyncMock(return_value=(True, "00", "1"))
    val = await client.get_plc_signal("X", 1)
    assert val is True

    client._send_command = AsyncMock(return_value=(True, "00", "0"))
    assert await client.get_plc_signal("X", 1) is False


@pytest.mark.asyncio
async def test_change_atc_validation_and_success():
    client = _connected()
    ok, status = await client.change_atc_tool("Z", 1, new_value=1)
    assert ok is False and status == "01"

    ok, status = await client.change_atc_tool("M", 100, new_value=1)
    assert ok is False and status == "30"

    ok, status = await client.change_atc_tool("K", 1, new_value=9)
    assert ok is False and status == "13"

    ok, status = await client.change_atc_tool("C", 1, new_value=9)
    assert ok is False and status == "13"

    client2 = _connected(make_brother_response("CHGMAGC", status="00"))
    ok, status = await client2.change_atc_tool("C", 1, new_value=3)
    assert ok is True

    client3 = _connected(make_brother_response("CHGMAGD", status="00"))
    ok, status = await client3.change_atc_tool("D", 2)
    assert ok is True


@pytest.mark.asyncio
async def test_change_atc_tool_magazine_assign_argument_format():
    """CHGMAGM uses pot(2)+tool(2) for T1-99, not pot(2)+tool(3)."""
    client = _connected(make_brother_response("CHGMAGM", status="00"))
    client._send_command = AsyncMock(return_value=(True, "00", None))

    ok, status = await client.change_atc_tool("M", 4, new_value=7)
    assert ok is True
    args = client._send_command.await_args.args[1]
    assert args.startswith("0407")

    client._send_command.reset_mock()
    ok, status = await client.change_atc_tool("M", 2, new_value=101)
    assert ok is True
    args = client._send_command.await_args.args[1]
    assert args.startswith("02101")


@pytest.mark.asyncio
async def test_assign_tool_to_pot_clears_cap_before_assign():
    client = _connected(make_brother_response("CHGMAGM", status="00"))
    client._read_pot_tool_number = AsyncMock(return_value=255)
    client.remove_tool_from_pot = AsyncMock(return_value=(True, "00"))
    client._send_command = AsyncMock(return_value=(True, "00", None))

    ok, status = await client.assign_tool_to_pot(6, 7, clear_cap=True)
    assert ok is True
    client.remove_tool_from_pot.assert_awaited_once_with(6, verbose=False)
    args = client._send_command.await_args.args[1]
    assert args.startswith("0607")


@pytest.mark.asyncio
async def test_clear_cap_from_pot_skips_delete_when_not_cap():
    client = _connected()
    client._read_pot_tool_number = AsyncMock(return_value=12)
    client.remove_tool_from_pot = AsyncMock()

    ok, status = await client.clear_cap_from_pot(3)
    assert ok is True and status == "00"
    client.remove_tool_from_pot.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_tool_to_pot_rejects_spindle():
    client = _connected()
    ok, status = await client.assign_tool_to_pot(0, 5)
    assert ok is False and status == "30"


@pytest.mark.asyncio
async def test_load_data_timeout_no_retry():
    client = _connected()
    client._send_command = AsyncMock(return_value=(False, "TIMEOUT", None))
    with patch("app.clients._telnet_data_reads.asyncio.sleep", AsyncMock()) as sleep:
        result = await client.load_data("MEM", max_retries=2)
    assert result is None
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_data_success():
    client = _connected(make_brother_response("LOD", args="MEM", data="A01,'F',2045,0,0,0,0,0"))
    data = await client.load_data("MEM", max_retries=0)
    assert data is not None
    assert "2045" in data
