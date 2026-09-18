# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Phase 1 telnet-gateway tests: shadow mode, authoritative cutover, MEM
invalidation, and offline-path equivalence for fast-poll reads.

All tests use fakes — no live machine required.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services._gateway_shadow import ShadowComparator, read_prd3_via_gateway
from app.services.polling import MachinePoller
from app.services.telnet_gateway import TelnetGateway


def _discard_create_task(coro):
    if hasattr(coro, "close"):
        coro.close()
    return MagicMock()


def _machine():
    return SimpleNamespace(
        id=1,
        name="test-machine",
        ip_address="10.0.0.1",
        units="in",
        part_display_mode="parts",
        control_version="C00",
    )


def _montr_bytes(program_no="2045"):
    return (
        f"P01,{program_no},{program_no},'FOLDER  ','EDIT    '\r\n".encode()
        + b"T01,010203000,040506000,070809000\r\n"
        + b"C01,001,000010,000100,000090\r\n"
    )


def _prd3_bytes(status_code=2):
    return (
        f"A01,1,10,1\r\n"
        f"C01,20240101120000,{status_code},0,2045,'FOLDER  ',0\r\n"
    ).encode()


def _mem_bytes(program_no="2045"):
    return f"A01,'FOLDER  ',{program_no},0,0,0,0,0\r\n".encode()


def _working_direct_fake(montr_program_no="2045"):
    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(return_value=_montr_bytes(montr_program_no).decode())
    fake.get_prd3_data = AsyncMock(return_value=_prd3_bytes(2).decode())
    fake.get_memory_data = AsyncMock(return_value=_mem_bytes(montr_program_no).decode())
    fake.get_alarm_data = AsyncMock(return_value="")
    fake.get_panel_data = AsyncMock(return_value=None)
    fake.get_macro_variable_range = AsyncMock(return_value=[])
    fake.disconnect = AsyncMock()
    return fake


_UNSET = object()


def _fake_gateway(montr=_UNSET, prd3=_UNSET, mem=_UNSET, read_side_effect=None):
    """Fake gateway: read() serves canned bytes per data name.

    Explicit None means "the machine returned nothing" (offline path);
    omit the argument for the default canned payload.
    """
    gw = MagicMock()
    canned = {
        "MONTR": _montr_bytes().decode() if montr is _UNSET else montr,
        "PRD3": _prd3_bytes(2).decode() if prd3 is _UNSET else prd3,
        "PRDD3": None,
        "MEM": _mem_bytes().decode() if mem is _UNSET else mem,
    }
    if read_side_effect is not None:
        gw.read = AsyncMock(side_effect=read_side_effect)
    else:
        async def _read(data_name, **kwargs):
            return canned.get(data_name)

        gw.read = AsyncMock(side_effect=_read)
    gw.invalidate = MagicMock()
    gw.stats = MagicMock(return_value={"breaker_state": "closed"})
    return gw


async def _poll_with(poller, monkeypatch, direct_fake, gateway_fake, enabled, authoritative):
    """Run one poll() with the gateway flags set and fakes installed.

    NOTE: this helper is async on purpose -- poll() must be awaited INSIDE
    the patch context managers, otherwise the fakes are uninstalled before
    the coroutine runs and the real network clients get used.
    """
    monkeypatch.setattr(
        "app.services._machine_poller.settings.SHATTER_TELNET_GATEWAY_ENABLED",
        enabled,
    )
    monkeypatch.setattr(
        "app.services._machine_poller.settings.SHATTER_TELNET_GW_AUTHORITATIVE",
        authoritative,
    )
    with patch("app.services._machine_poller.CNCTelnetClient", return_value=direct_fake):
        with patch(
            "app.services._machine_poller.get_gateway",
            new=AsyncMock(return_value=gateway_fake),
        ):
            with patch(
                "app.services._machine_poller.asyncio.create_task",
                _discard_create_task,
            ):
                with patch("app.services._machine_poller.SessionLocal"):
                    return await poller.poll()


# ---------------------------------------------------------------------------
# ShadowComparator unit tests
# ---------------------------------------------------------------------------


def test_shadow_comparator_match_and_mismatch(caplog):
    comp = ShadowComparator()
    assert comp.compare("MONTR", "abc", "abc") is True
    assert comp.compare("MONTR", "abc", "abd") is False
    assert comp.compare("MONTR", "abc", None) is False
    assert comp.compare("MONTR", None, None) is True
    snap = comp.snapshot()
    assert snap["MONTR"] == {"compared": 4, "matched": 2, "mismatched": 2}
    assert "gateway shadow mismatch for MONTR" in caplog.text


@pytest.mark.asyncio
async def test_read_prd3_via_gateway_falls_back_to_alternate():
    gw = MagicMock()
    # C00: primary PRD3 returns None -> falls back to PRDD3.
    gw.read = AsyncMock(side_effect=[None, "PRDD3-data"])
    result = await read_prd3_via_gateway(gw, "C00", force_refresh=True)
    assert result == "PRDD3-data"
    assert [c.args[0] for c in gw.read.await_args_list] == ["PRD3", "PRDD3"]

    # D00: primary PRDD3 hit, no fallback read.
    gw2 = MagicMock()
    gw2.read = AsyncMock(return_value="PRDD3-data")
    result = await read_prd3_via_gateway(gw2, "D00", force_refresh=True)
    assert result == "PRDD3-data"
    gw2.read.assert_awaited_once_with("PRDD3", force_refresh=True)


# ---------------------------------------------------------------------------
# TelnetGateway.invalidate unit test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gateway_invalidate_drops_cached_entry():
    client = MagicMock()
    client._connected = True
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.load_data = AsyncMock(side_effect=lambda name: f"<{name}-payload>")

    gw = TelnetGateway(
        "10.0.0.9",
        client_factory=lambda ip, port: client,
        ttl_volatile=60,
        ttl_semistatic=60,
        ttl_slow=60,
        min_delay=0.0,
        max_delay=0.0,
    )
    await gw.start()
    try:
        assert await gw.read("MEM") == "<MEM-payload>"
        assert await gw.read("MEM") == "<MEM-payload>"  # cache hit
        assert client.load_data.await_count == 1
        gw.invalidate("MEM")
        assert await gw.read("MEM") == "<MEM-payload>"  # re-read from machine
        assert client.load_data.await_count == 2
        gw.invalidate("NOPE")  # unknown names are a no-op
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# Phase 1 poller integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shadow_mode_gateway_exception_never_fails_poll(monkeypatch):
    """Gateway explodes in shadow mode -> poll still succeeds on direct data."""
    poller = MachinePoller(_machine(), None)
    direct = _working_direct_fake()
    gw = _fake_gateway(read_side_effect=RuntimeError("gateway boom"))

    result = await _poll_with(poller, monkeypatch, direct, gw, True, False)

    assert result["status"] == "standby"
    assert result["program_name"] == "O2045"
    # Direct client did the authoritative reads.
    direct.get_monitor_data.assert_awaited()
    # Comparator recorded nothing (shadow read raised before compare).
    assert poller._shadow_comparator.snapshot() == {}


@pytest.mark.asyncio
async def test_shadow_mode_mismatch_recorded_direct_stays_authoritative(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _working_direct_fake()
    gw = _fake_gateway(montr="DIFFERENT-BYTES", prd3="ALSO-DIFFERENT")

    result = await _poll_with(poller, monkeypatch, direct, gw, True, False)

    # Poll result comes from the direct (authoritative) bytes.
    assert result["program_name"] == "O2045"
    assert result["status"] == "standby"
    snap = poller._shadow_comparator.snapshot()
    assert snap["MONTR"]["mismatched"] == 1
    assert snap["PRD3"]["mismatched"] == 1
    assert snap["MEM"]["matched"] == 1  # canned MEM matches the direct fixture


@pytest.mark.asyncio
async def test_authoritative_mode_uses_gateway_not_direct(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _working_direct_fake()
    gw = _fake_gateway()

    result = await _poll_with(poller, monkeypatch, direct, gw, True, True)

    # The three fast-poll reads must NOT touch the direct client...
    direct.get_monitor_data.assert_not_called()
    direct.get_prd3_data.assert_not_called()
    direct.get_memory_data.assert_not_called()
    # ...but alarms/panel/macros still do (out of Phase 1 scope).
    direct.get_alarm_data.assert_awaited()
    # Gateway bytes parse exactly like direct bytes.
    assert result["program_name"] == "O2045"
    assert result["status"] == "standby"
    # Gateway reads were NOT force-refreshed in authoritative mode (cache applies).
    for call in gw.read.await_args_list:
        assert call.kwargs.get("force_refresh") is False


@pytest.mark.asyncio
async def test_authoritative_mode_gateway_none_matches_direct_none(monkeypatch):
    """Gateway MONTR None in authoritative mode -> same failure path as direct None."""
    poller = MachinePoller(_machine(), None)
    poller.last_successful_fast_poll_at = None
    direct = _working_direct_fake()
    gw = _fake_gateway(montr=None, prd3=None, mem=None)

    result = await _poll_with(poller, monkeypatch, direct, gw, True, True)

    assert result["is_online"] is False or result.get("consecutive_failures", 0) >= 1


@pytest.mark.asyncio
async def test_mem_invalidated_on_program_change(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _working_direct_fake()
    # Second poll's MONTR reports a different program.
    direct.get_monitor_data = AsyncMock(
        side_effect=[_montr_bytes("2045").decode(), _montr_bytes("2046").decode()]
    )
    direct.get_memory_data = AsyncMock(
        side_effect=[_mem_bytes("2045").decode(), _mem_bytes("2046").decode()]
    )
    gw = _fake_gateway()

    await _poll_with(poller, monkeypatch, direct, gw, True, False)
    assert poller._last_fast_program_name == "O2045"
    gw.invalidate.assert_not_called()  # first sighting: nothing to invalidate

    result = await _poll_with(poller, monkeypatch, direct, gw, True, False)
    assert result["program_name"] == "O2046"
    gw.invalidate.assert_called_once_with("MEM")


def test_volatile_ttl_default_stays_under_fast_poll_interval():
    """Phase 1 decision: volatile TTL only dedups within a poll cycle.

    The default fast-poll interval is 5s (Machine.poll_interval_seconds);
    the volatile TTL default must stay comfortably under it.
    """
    from app.core.config import settings

    assert settings.SHATTER_TELNET_GW_TTL_VOLATILE < 5
