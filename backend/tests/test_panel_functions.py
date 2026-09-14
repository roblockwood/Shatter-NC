# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for set_panel_function() (CHGxxxx ON/OFF panel I/O toggles)."""
from unittest.mock import AsyncMock

import pytest

from app.clients.telnet_client import CNCTelnetClient
from tests.helpers import FakeReader, FakeWriter


def _connected() -> CNCTelnetClient:
    client = CNCTelnetClient("10.0.0.1", port=10000, timeout=5, command_delay=0.0)
    client.reader = FakeReader(b"")  # type: ignore[assignment]
    client.writer = FakeWriter()  # type: ignore[assignment]
    client._connected = True
    return client


EXPECTED_COMMANDS = {
    "block_skip": "CHGBLKS",
    "opt_stop": "CHGOPTS",
    "single_block": "CHGSNGL",
    "machine_lock": "CHGMACL",
}


def test_panel_function_allowlist_matches_expected_commands():
    assert CNCTelnetClient.PANEL_FUNCTION_COMMANDS == EXPECTED_COMMANDS


@pytest.mark.asyncio
@pytest.mark.parametrize("function,command", list(EXPECTED_COMMANDS.items()))
async def test_set_panel_function_sends_chg_command(function, command):
    client = _connected()
    client._send_command = AsyncMock(return_value=(True, "00", None))

    ok, status = await client.set_panel_function(function, True)
    assert ok is True
    assert status == "00"
    client._send_command.assert_awaited_once_with(command, "ON", verbose=False)

    ok, status = await client.set_panel_function(function, False)
    assert ok is True
    assert status == "00"
    client._send_command.assert_awaited_with(command, "OFF", verbose=False)


@pytest.mark.asyncio
async def test_set_panel_function_accepts_case_and_whitespace():
    client = _connected()
    client._send_command = AsyncMock(return_value=(True, "00", None))

    ok, _ = await client.set_panel_function("  Opt_Stop ", True)
    assert ok is True
    client._send_command.assert_awaited_once_with("CHGOPTS", "ON", verbose=False)


@pytest.mark.asyncio
async def test_set_panel_function_rejects_unknown_function():
    client = _connected()
    client._send_command = AsyncMock(return_value=(True, "00", None))

    ok, status = await client.set_panel_function("dry_run", True)
    assert ok is False
    assert status == "30"
    client._send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_panel_function_treats_status_60_as_success():
    """Status 60 = already in requested state; not a failure."""
    client = _connected()
    client._send_command = AsyncMock(return_value=(False, "60", None))

    ok, status = await client.set_panel_function("opt_stop", True)
    assert ok is True
    assert status == "60"


@pytest.mark.asyncio
async def test_set_panel_function_propagates_failure_status():
    client = _connected()
    client._send_command = AsyncMock(return_value=(False, "32", None))

    ok, status = await client.set_panel_function("machine_lock", True)
    assert ok is False
    assert status == "32"


@pytest.mark.asyncio
async def test_set_panel_function_connects_when_disconnected():
    client = _connected()
    client._connected = False
    client.connect = AsyncMock(return_value=True)  # type: ignore[assignment]
    client._send_command = AsyncMock(return_value=(True, "00", None))

    ok, _ = await client.set_panel_function("block_skip", True)
    assert ok is True
    client.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_panel_function_fails_when_connect_fails():
    client = _connected()
    client._connected = False
    client.connect = AsyncMock(return_value=False)  # type: ignore[assignment]

    ok, status = await client.set_panel_function("block_skip", True)
    assert ok is False
    assert status is None
