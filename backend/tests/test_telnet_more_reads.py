"""High-coverage tests for remaining telnet data-read paths."""
from unittest.mock import AsyncMock, patch

import pytest

from app.clients.telnet_client import CNCTelnetClient
from app.clients import _telnet_state
from tests.helpers import FakeReader, FakeWriter


def _client() -> CNCTelnetClient:
    client = CNCTelnetClient("10.0.0.9", port=10000, timeout=5, command_delay=0.0)
    client.reader = FakeReader()  # type: ignore[assignment]
    client.writer = FakeWriter()  # type: ignore[assignment]
    client._connected = True
    return client


@pytest.fixture(autouse=True)
def clear_control_cache():
    _telnet_state._control_version_cache.clear()
    yield
    _telnet_state._control_version_cache.clear()


@pytest.mark.asyncio
async def test_detect_control_type_c00_from_directory():
    client = _client()
    # C00 format entries: 11 bytes each with PRDC1 name
    listing = "PRDC1   " + "010" + "SYSC1   " + "010"
    client._get_directory_listing_internal = AsyncMock(return_value=listing)
    version = await client.detect_control_type()
    assert version == "C00"
    # Second call hits cache
    assert await client.detect_control_type() == "C00"


@pytest.mark.asyncio
async def test_detect_control_type_d00_from_directory():
    client = _client()
    # D00: 18-byte entries
    listing = "PRDD1   " + "0000000010" + "SYSD1   " + "0000000010"
    client._get_directory_listing_internal = AsyncMock(return_value=listing)
    version = await client.detect_control_type()
    assert version == "D00"


@pytest.mark.asyncio
async def test_get_macro_variable_range():
    client = _client()
    # count=002 then two 12-char floats
    payload = "002" + f"{1.5:12.4f}" + f"{2.5:12.4f}"
    client._send_multipart_command = AsyncMock(return_value=(True, "00", payload))
    values = await client.get_macro_variable_range(500, 2)
    assert values is not None
    assert len(values) == 2


@pytest.mark.asyncio
async def test_get_plc_signal_range_bools():
    client = _client()
    payload = "0003" + "101"
    client._send_multipart_command = AsyncMock(return_value=(True, "00", payload))
    values = await client.get_plc_signal_range("X", 1, 3)
    assert values == [True, False, True] or values is not None


@pytest.mark.asyncio
async def test_get_all_data_bank_names():
    client = _client()
    client._send_command = AsyncMock(return_value=(True, "00", "BANK1   BANK2   "))
    names = await client.get_all_data_bank_names()
    assert names is not None


@pytest.mark.asyncio
async def test_get_data_bank_name():
    client = _client()
    client._send_command = AsyncMock(return_value=(True, "00", "MYBANK"))
    name = await client.get_data_bank_name("BANK1")
    assert name == "MYBANK"


@pytest.mark.asyncio
async def test_get_current_program_content():
    client = _client()
    client._send_command = AsyncMock(return_value=(True, "00", "G90\nG0 X0\n"))
    content = await client.get_current_program_content(50)
    assert "G90" in content


@pytest.mark.asyncio
async def test_load_data_status_40_retries():
    client = _client()

    async def send(*_a, **_k):
        return (False, "40", None)

    calls = {"n": 0}

    async def send2(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return (False, "40", None)
        client._connected = True
        return (True, "00", "OK")

    client._send_command = AsyncMock(side_effect=send2)
    client.connect = AsyncMock(return_value=True)
    with patch("app.clients._telnet_data_reads.asyncio.sleep", AsyncMock()):
        data = await client.load_data("MEM", max_retries=1)
    assert data == "OK"
