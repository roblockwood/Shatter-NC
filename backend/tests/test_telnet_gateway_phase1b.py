# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Phase 1b telnet-gateway tests: tool-poll routing, fast-poll remainder
(ALARM/PANEL/MACRO), state-aware tool TTL, on-demand API reads, the gateway
command path, and write-path cache invalidation.

All tests use fakes — no live machine required.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services._gateway_shadow import (
    TOOL_DATA_NAMES,
    canonical_json,
    gw_on_demand,
    invalidate_tool_data_caches,
    macro_cache_key,
    read_atc_via_gateway,
    read_macro_range_via_gateway,
    read_prd3_via_gateway,
)
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
        atc_pockets=24,
    )


_UNSET = object()


def _tool_direct_fake():
    """Direct client fake for the tool poll."""
    fake = MagicMock()
    fake.get_tool_table_data = AsyncMock(return_value="TOLN-BYTES")
    fake.get_atc_magazine_data = AsyncMock(return_value="ATCTL-BYTES")
    fake.disconnect = AsyncMock()
    return fake


def _tool_gateway_fake(toln="TOLN-BYTES", atcl="ATCTL-BYTES"):
    """Gateway fake for the tool poll; records read() kwargs for TTL checks."""
    gw = MagicMock()
    read_kwargs = []

    async def _read(data_name, **kwargs):
        read_kwargs.append((data_name, kwargs))
        return {"TOLNI1": toln, "ATCTL": atcl, "ATDTL": atcl}.get(data_name)

    gw.read = AsyncMock(side_effect=_read)
    gw.read_kwargs = read_kwargs
    gw.invalidate = MagicMock()
    gw.stats = MagicMock(return_value={"breaker_state": "closed"})
    return gw


def _fast_direct_fake():
    """Direct client fake for the fast poll (Phase 1b datasets)."""
    fake = MagicMock()
    fake.get_monitor_data = AsyncMock(return_value="MONTR")
    fake.get_prd3_data = AsyncMock(return_value="PRD3")
    fake.get_memory_data = AsyncMock(return_value="MEM")
    fake.get_alarm_data = AsyncMock(return_value="ALARM-BYTES")
    fake.get_panel_data = AsyncMock(return_value="PANEL-BYTES")
    fake.get_macro_variable_range = AsyncMock(return_value=[1.0, 2.0])
    fake.disconnect = AsyncMock()
    return fake


def _fast_gateway_fake():
    gw = MagicMock()

    async def _read(data_name, **kwargs):
        return {
            "MONTR": "MONTR",
            "PRD3": "PRD3",
            "PRDD3": None,
            "MEM": "MEM",
            "ALARM": "ALARM-BYTES",
            "PANEL": "PANEL-BYTES",
        }.get(data_name)

    gw.read = AsyncMock(side_effect=_read)
    gw.read_command = AsyncMock(return_value=[1.0, 2.0])
    gw.invalidate = MagicMock()
    gw.stats = MagicMock(return_value={"breaker_state": "closed"})
    return gw


async def _poll_tool_with(poller, monkeypatch, direct_fake, gateway_fake, enabled, authoritative,
                         spindle_tool=5):
    """Run one poll_tool_data() with the gateway flags set and fakes installed."""
    monkeypatch.setattr(
        "app.services._machine_poller.settings.SHATTER_TELNET_GATEWAY_ENABLED",
        enabled,
    )
    monkeypatch.setattr(
        "app.services._machine_poller.settings.SHATTER_TELNET_GW_AUTHORITATIVE",
        authoritative,
    )
    # Bypass the real TOLN/ATCTL parsers and merge helpers: the canned parse
    # results carry a spindle tool so current_tool is deterministic.
    atc_tools = [
        {"tool_number": spindle_tool, "pot_number": "SPINDLE"},
        {
            "tool_number": 1,
            "pot_number": 3,
            "group": "A",
            "tool_type": "ENDMILL",
            "color": "red",
        },
    ]
    with patch("app.services._machine_poller.CNCTelnetClient", return_value=direct_fake):
        with patch(
            "app.services._machine_poller.get_gateway",
            new=AsyncMock(return_value=gateway_fake),
        ):
            with patch(
                "app.services._machine_poller.parse_tolni_v2",
                return_value={"tools": [{"tool_number": 1}]},
            ):
                with patch(
                    "app.services._machine_poller.parse_atctl_v2",
                    return_value={"tools": atc_tools},
                ):
                    with patch(
                        "app.services._machine_poller.merge_atc_tools_for_display",
                        return_value=[],
                    ):
                        with patch(
                            "app.services._machine_poller.build_unified_tool_view",
                            return_value={"atc_available": True},
                        ):
                            return await poller.poll_tool_data()


async def _poll_fast_with(poller, monkeypatch, direct_fake, gateway_fake, enabled, authoritative):
    """Run one poll() with the gateway flags set and fakes installed."""
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
# macro_cache_key / canonical_json unit tests
# ---------------------------------------------------------------------------


def test_macro_cache_key_format():
    assert macro_cache_key(500, 500) == "MACRO:500:500"
    assert macro_cache_key(100, 10) == "MACRO:100:10"


def test_canonical_json_is_order_and_format_stable():
    assert canonical_json([1.0, 2.0]) == "[1.0,2.0]"
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})
    assert canonical_json(None) is None
    assert canonical_json("abc") == '"abc"'


# ---------------------------------------------------------------------------
# read_atc_via_gateway unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_atc_via_gateway_fallback():
    gw = MagicMock()
    # C00: primary ATCTL returns None -> falls back to ATDTL.
    gw.read = AsyncMock(side_effect=[None, "ATDTL-data"])
    result = await read_atc_via_gateway(gw, "C00", force_refresh=True)
    assert result == "ATDTL-data"
    assert [c.args[0] for c in gw.read.await_args_list] == ["ATCTL", "ATDTL"]
    for call in gw.read.await_args_list:
        assert call.kwargs["force_refresh"] is True

    # D00: primary ATDTL hit, no fallback read.
    gw2 = MagicMock()
    gw2.read = AsyncMock(return_value="ATDTL-data")
    result = await read_atc_via_gateway(gw2, "D00", force_refresh=True)
    assert result == "ATDTL-data"
    gw2.read.assert_awaited_once_with("ATDTL", force_refresh=True, ttl=None)


@pytest.mark.asyncio
async def test_read_atc_via_gateway_retries_fresh_commands():
    """attempts=3 retries the whole primary/fallback pair with no delay."""
    gw = MagicMock()
    gw.read = AsyncMock(side_effect=[None, None, None, "ATDTL-data"])
    result = await read_atc_via_gateway(
        gw, "C00", force_refresh=False, attempts=3, retry_delay=0
    )
    assert result == "ATDTL-data"
    assert [c.args[0] for c in gw.read.await_args_list] == [
        "ATCTL",
        "ATDTL",
        "ATCTL",
        "ATDTL",
    ]


@pytest.mark.asyncio
async def test_read_atc_via_gateway_returns_none_when_all_fail():
    gw = MagicMock()
    gw.read = AsyncMock(return_value=None)
    assert await read_atc_via_gateway(gw, "C00", attempts=2, retry_delay=0) is None
    assert gw.read.await_count == 4  # 2 attempts x (primary + fallback)


# ---------------------------------------------------------------------------
# read_macro_range_via_gateway unit test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_macro_range_via_gateway_uses_command_path():
    gw = MagicMock()
    gw.read_command = AsyncMock(return_value=[1.5, 2.5])
    result = await read_macro_range_via_gateway(
        gw, 500, 500, force_refresh=True, ttl=60.0, timeout=10.0
    )
    assert result == [1.5, 2.5]
    gw.read_command.assert_awaited_once()
    call = gw.read_command.await_args_list[0]
    assert call.args[0] == "MACRO:500:500"
    assert call.kwargs["force_refresh"] is True
    assert call.kwargs["ttl"] == 60.0
    assert call.kwargs["timeout"] == 10.0
    # The command fn delegates to the client's REDMCNM range read.
    client = MagicMock()
    client.get_macro_variable_range = AsyncMock(return_value=[9.0])
    assert await call.args[1](client) == [9.0]
    client.get_macro_variable_range.assert_awaited_once_with(500, 500, verbose=False)

# ---------------------------------------------------------------------------
# TelnetGateway.read_command tests (real gateway, fake client)
# ---------------------------------------------------------------------------


def _command_gateway(client):
    return TelnetGateway(
        "10.0.0.9",
        client_factory=lambda ip, port: client,
        ttl_volatile=60,
        ttl_semistatic=60,
        ttl_slow=60,
        min_delay=0.0,
        max_delay=0.0,
    )


def _command_client():
    client = MagicMock()
    client._connected = True
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_read_command_caches_and_force_refresh():
    client = _command_client()
    calls = []

    async def _fn(c):
        calls.append(c)
        return [1.0]

    gw = _command_gateway(client)
    await gw.start()
    try:
        assert await gw.read_command("MACRO#500-999x500", _fn) == [1.0]
        assert await gw.read_command("MACRO#500-999x500", _fn) == [1.0]  # cache hit
        assert len(calls) == 1
        assert await gw.read_command("MACRO#500-999x500", _fn, force_refresh=True) == [1.0]
        assert len(calls) == 2
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_read_command_invalidate_drops_entry():
    client = _command_client()
    calls = []

    async def _fn(c):
        calls.append(1)
        return [2.0]

    gw = _command_gateway(client)
    await gw.start()
    try:
        assert await gw.read_command("MACRO#500-999x500", _fn) == [2.0]
        gw.invalidate("MACRO#500-999x500")
        assert await gw.read_command("MACRO#500-999x500", _fn) == [2.0]
        assert len(calls) == 2
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_read_command_coalesces_concurrent_calls():
    import asyncio as _asyncio

    client = _command_client()
    calls = []

    async def _fn(c):
        calls.append(1)
        await _asyncio.sleep(0.05)
        return [3.0]

    gw = _command_gateway(client)
    await gw.start()
    try:
        r1, r2 = await _asyncio.gather(
            gw.read_command("MACRO#500-999x500", _fn),
            gw.read_command("MACRO#500-999x500", _fn),
        )
        assert r1 == r2 == [3.0]
        assert len(calls) == 1  # one machine command, two callers
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_read_command_respects_timeout():
    import asyncio as _asyncio

    client = _command_client()

    async def _slow(c):
        await _asyncio.sleep(5)
        return [1.0]

    gw = _command_gateway(client)
    await gw.start()
    try:
        with pytest.raises(_asyncio.TimeoutError):
            await gw.read_command("MACRO#500-999x500", _slow, timeout=0.05, force_refresh=True)
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# State-aware tool TTL
# ---------------------------------------------------------------------------


def test_tool_data_ttl_idle_vs_operating():
    from app.core.config import settings

    poller = MachinePoller(_machine(), None)
    poller.last_known_prd3_status = "operating"
    assert poller._tool_data_ttl() == settings.SHATTER_TELNET_GW_TTL_SLOW
    assert poller._tool_data_ttl() == 300.0

    for status in ("idle", "standby", "manual", "mdi", None, "alarm"):
        poller.last_known_prd3_status = status
        assert poller._tool_data_ttl() == settings.SHATTER_TELNET_GW_TTL_TOOL_IDLE
        assert poller._tool_data_ttl() == 30.0


# ---------------------------------------------------------------------------
# Tool-poll routing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_poll_shadow_mode_direct_authoritative(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _tool_direct_fake()
    gw = _tool_gateway_fake()

    result = await _poll_tool_with(poller, monkeypatch, direct, gw, True, False)

    assert result["current_tool"] == 5
    # Direct client did the authoritative reads.
    direct.get_tool_table_data.assert_awaited()
    # Gateway shadow reads were force-refreshed for a fair comparison...
    names = [name for name, kw in gw.read_kwargs]
    assert "TOLNI1" in names and "ATCTL" in names
    assert all(kw.get("force_refresh") is True for _, kw in gw.read_kwargs)
    # ...with the state-aware (idle) TTL.
    assert all(kw.get("ttl") == 30.0 for _, kw in gw.read_kwargs)
    # Comparator recorded both tool datasets as matching.
    snap = poller._shadow_comparator.snapshot()
    assert snap["TOLNI1"]["matched"] == 1
    assert snap["ATCTL"]["matched"] == 1


@pytest.mark.asyncio
async def test_tool_poll_authoritative_uses_gateway_not_direct(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _tool_direct_fake()
    gw = _tool_gateway_fake()

    result = await _poll_tool_with(poller, monkeypatch, direct, gw, True, True)

    assert result["current_tool"] == 5
    direct.get_tool_table_data.assert_not_called()
    direct.get_atc_magazine_data.assert_not_called()
    # Gateway reads were NOT force-refreshed in authoritative mode.
    assert all(kw.get("force_refresh") is False for _, kw in gw.read_kwargs)
    assert all(kw.get("ttl") == 30.0 for _, kw in gw.read_kwargs)


@pytest.mark.asyncio
async def test_tool_poll_gateway_setup_failure_falls_back_to_direct(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _tool_direct_fake()
    monkeypatch.setattr(
        "app.services._machine_poller.settings.SHATTER_TELNET_GATEWAY_ENABLED",
        True,
    )
    with patch("app.services._machine_poller.CNCTelnetClient", return_value=direct):
        with patch(
            "app.services._machine_poller.get_gateway",
            new=AsyncMock(side_effect=RuntimeError("no gateway")),
        ):
            with patch(
                "app.services._machine_poller.parse_tolni_v2",
                return_value={"tools": [{"tool_number": 1}]},
            ):
                with patch(
                    "app.services._machine_poller.parse_atctl_v2",
                    return_value={"tools": [{"tool_number": 5, "pot_number": "SPINDLE"}]},
                ):
                    with patch(
                        "app.services._machine_poller.merge_atc_tools_for_display",
                        return_value=[],
                    ):
                        with patch(
                            "app.services._machine_poller.build_unified_tool_view",
                            return_value={"atc_available": True},
                        ):
                            result = await poller.poll_tool_data()

    assert result["current_tool"] == 5
    direct.get_tool_table_data.assert_awaited()


@pytest.mark.asyncio
async def test_tool_poll_spindle_change_invalidates_tool_caches(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _tool_direct_fake()
    gw = _tool_gateway_fake()

    result = await _poll_tool_with(poller, monkeypatch, direct, gw, True, False)
    assert result["current_tool"] == 5
    assert poller._last_tool_poll_current_tool == 5
    gw.invalidate.assert_not_called()  # first sighting: nothing to invalidate

    # Second poll: the spindle now holds a different tool.
    result = await _poll_tool_with(
        poller, monkeypatch, direct, gw, True, False, spindle_tool=7
    )

    assert result["current_tool"] == 7
    assert poller._last_tool_poll_current_tool == 7
    gw.invalidate.assert_called_once_with(*TOOL_DATA_NAMES)
    assert set(gw.invalidate.call_args.args) == {"TOLNI1", "TOLNM1", "ATCTL", "ATDTL"}


@pytest.mark.asyncio
async def test_tool_poll_gateway_disabled_is_todays_behavior(monkeypatch):
    """Gateway flag off: direct client only, no gateway touched."""
    poller = MachinePoller(_machine(), None)
    direct = _tool_direct_fake()
    gw = _tool_gateway_fake()

    result = await _poll_tool_with(poller, monkeypatch, direct, gw, False, False)

    assert result["current_tool"] == 5
    direct.get_tool_table_data.assert_awaited()
    gw.read.assert_not_awaited()
    assert poller._shadow_comparator.snapshot() == {}

# ---------------------------------------------------------------------------
# Fast-poll remainder routing (ALARM / PANEL / MACRO)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_poll_shadow_mode_routes_alarm_panel_macro(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _fast_direct_fake()
    gw = _fast_gateway_fake()

    await _poll_fast_with(poller, monkeypatch, direct, gw, True, False)

    # Direct client stays authoritative for the Phase 1b datasets...
    direct.get_alarm_data.assert_awaited()
    direct.get_panel_data.assert_awaited()
    direct.get_macro_variable_range.assert_awaited()
    # ...while the gateway shadow comparisons all matched.
    snap = poller._shadow_comparator.snapshot()
    assert snap["ALARM"]["matched"] == 1
    assert snap["PANEL"]["matched"] == 1
    assert snap["MACRO:500:500"]["matched"] == 1


@pytest.mark.asyncio
async def test_fast_poll_authoritative_mode_routes_alarm_panel_macro(monkeypatch):
    poller = MachinePoller(_machine(), None)
    direct = _fast_direct_fake()
    gw = _fast_gateway_fake()

    result = await _poll_fast_with(poller, monkeypatch, direct, gw, True, True)

    direct.get_alarm_data.assert_not_called()
    direct.get_panel_data.assert_not_called()
    direct.get_macro_variable_range.assert_not_called()
    # Gateway bytes land in the status payload like direct bytes did.
    assert result["macros"] == {"500": 1.0, "501": 2.0}
    assert result["alarms"] == []  # "ALARM-BYTES" is not real alarm payload; parse path
    # The macro command path was used (not LOD).
    assert gw.read_command.await_count >= 1
    for call in gw.read_command.await_args_list:
        assert call.kwargs.get("force_refresh") is False


# ---------------------------------------------------------------------------
# gw_on_demand tests
# ---------------------------------------------------------------------------


def _ondemand_machine():
    return SimpleNamespace(id=2, ip_address="10.0.0.2")


@pytest.mark.asyncio
async def test_gw_on_demand_disabled_uses_direct_only(monkeypatch):
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", False)
    direct = AsyncMock(return_value="DIRECT-BYTES")
    get_gw = AsyncMock()
    monkeypatch.setattr(_gateway_shadow, "get_gateway", get_gw)

    result = await gw_on_demand("10.0.0.2", "TEST-MONTR-A", direct)

    assert result == "DIRECT-BYTES"
    direct.assert_awaited_once()
    get_gw.assert_not_called()


@pytest.mark.asyncio
async def test_gw_on_demand_shadow_returns_direct_and_compares(monkeypatch):
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", True)
    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GW_AUTHORITATIVE", False)

    gw = MagicMock()
    gw.read = AsyncMock(return_value="GW-BYTES")
    monkeypatch.setattr(_gateway_shadow, "get_gateway", AsyncMock(return_value=gw))

    direct = AsyncMock(return_value="DIRECT-BYTES")
    result = await gw_on_demand("10.0.0.2", "TEST-MONTR-B", direct)

    assert result == "DIRECT-BYTES"  # direct stays authoritative
    direct.assert_awaited_once()
    gw.read.assert_awaited_once_with("TEST-MONTR-B", force_refresh=True, ttl=None)
    snap = _gateway_shadow.ondemand_shadow_snapshot()
    assert snap["TEST-MONTR-B"]["mismatched"] == 1  # bytes differ


@pytest.mark.asyncio
async def test_gw_on_demand_authoritative_uses_gateway_only(monkeypatch):
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", True)
    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GW_AUTHORITATIVE", True)

    gw = MagicMock()
    gw.read = AsyncMock(return_value="GW-BYTES")
    monkeypatch.setattr(_gateway_shadow, "get_gateway", AsyncMock(return_value=gw))

    direct = AsyncMock(return_value="DIRECT-BYTES")
    result = await gw_on_demand("10.0.0.2", "TEST-MONTR-C", direct)

    assert result == "GW-BYTES"
    direct.assert_not_awaited()
    # On-demand reads default to force_refresh=True: a human asking always
    # gets live data, even in authoritative mode.
    gw.read.assert_awaited_once_with("TEST-MONTR-C", force_refresh=True, ttl=None)


@pytest.mark.asyncio
async def test_gw_on_demand_gateway_failure_falls_back_to_direct(monkeypatch):
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", True)
    monkeypatch.setattr(
        _gateway_shadow, "get_gateway", AsyncMock(side_effect=RuntimeError("down"))
    )

    direct = AsyncMock(return_value="DIRECT-BYTES")
    assert await gw_on_demand("10.0.0.2", "TEST-MONTR-D", direct) == "DIRECT-BYTES"


@pytest.mark.asyncio
async def test_gw_on_demand_prd3_fallback_via_gateway_fn(monkeypatch):
    """On-demand PRD3 mirrors the direct primary/alternate fallback on the gateway."""
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", True)
    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GW_AUTHORITATIVE", True)

    gw = MagicMock()
    gw.read = AsyncMock(side_effect=[None, "PRDD3-data"])
    monkeypatch.setattr(_gateway_shadow, "get_gateway", AsyncMock(return_value=gw))

    direct = AsyncMock(return_value="DIRECT-PRD3")
    result = await gw_on_demand(
        "10.0.0.2",
        "PRD3",
        direct,
        gateway_fn=lambda g, **kw: read_prd3_via_gateway(g, "C00", **kw),
    )

    assert result == "PRDD3-data"
    direct.assert_not_awaited()
    assert [c.args[0] for c in gw.read.await_args_list] == ["PRD3", "PRDD3"]


# ---------------------------------------------------------------------------
# invalidate_tool_data_caches tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalidate_tool_data_caches_disabled_is_noop(monkeypatch):
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", False)
    get_gw = AsyncMock()
    monkeypatch.setattr(_gateway_shadow, "get_gateway", get_gw)

    assert await invalidate_tool_data_caches("10.0.0.2", 10000) is None
    get_gw.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_tool_data_caches_invalidates_all_four_names(monkeypatch):
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", True)
    gw = MagicMock()
    gw.invalidate = MagicMock()
    monkeypatch.setattr(_gateway_shadow, "get_gateway", AsyncMock(return_value=gw))

    assert await invalidate_tool_data_caches("10.0.0.2", 10000) is None
    gw.invalidate.assert_called_once_with(*TOOL_DATA_NAMES)


@pytest.mark.asyncio
async def test_invalidate_tool_data_caches_gateway_failure_is_noop(monkeypatch):
    from app.services import _gateway_shadow

    monkeypatch.setattr(_gateway_shadow.settings, "SHATTER_TELNET_GATEWAY_ENABLED", True)
    monkeypatch.setattr(
        _gateway_shadow, "get_gateway", AsyncMock(side_effect=RuntimeError("down"))
    )

    assert await invalidate_tool_data_caches("10.0.0.2", 10000) is None


# ---------------------------------------------------------------------------
# Write-path invalidation tests
# ---------------------------------------------------------------------------

FULL_TOLN = """T07,3.4494,0.0000,0.0000,0.0000,1,10000,9500,9952,'OLD NAME      ',,,,,,0,0,,0.0000,0.0000,0.0000,0.0000,
M01,5,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0
"""
FULL_ATC = "M01,5,1,0,1,0\\r\\nM02,10,2,0,1,0\\r\\n"


def _w_machine():
    m = MagicMock()
    m.id = 1
    m.ip_address = "10.0.0.1"
    m.ftp_port = 21
    m.ftp_username = "u"
    m.ftp_password = "p"
    m.units = "in"
    m.control_version = "C00"
    return m


def _w_db(machine):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = machine
    return db


@pytest.mark.asyncio
async def test_batch_tool_write_success_invalidates_gateway_tool_cache(monkeypatch):
    from app.api._status_state import ToolChangeItem
    from app.services import tool_name_write_service, tool_write_service

    async def fake_write(machine, updates, telnet_client=None):
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
                with patch.object(
                    tool_write_service, "invalidate_tool_data_caches", new=AsyncMock()
                ) as inv:
                    result = await tool_write_service.apply_tool_changes_batch(
                        _w_machine(),
                        1,
                        [
                            ToolChangeItem(
                                operation_type="name",
                                tool_number=7,
                                name_value="NEW EM",
                                client_id="t7-name",
                            )
                        ],
                        _w_db(_w_machine()),
                    )

    assert result.successful == 1
    inv.assert_awaited_once_with("10.0.0.1", 10000)


@pytest.mark.asyncio
async def test_batch_tool_write_all_failed_does_not_invalidate(monkeypatch):
    from app.api._status_state import ToolChangeItem
    from app.services import tool_name_write_service, tool_write_service

    async def fake_write(machine, updates, telnet_client=None):
        return {7: "OLD NAME"}, {7: False}  # verification failed

    monkeypatch.setattr(tool_name_write_service, "write_tool_names_via_ftp", fake_write)

    with patch("app.services.machine_state_validator.MachineStateValidator") as Validator:
        Validator.return_value.validate_safe_for_write = AsyncMock(
            return_value=(True, None, {})
        )
        with patch("app.clients.telnet_client.create_fresh_connection") as conn:
            conn.return_value = AsyncMock()
            conn.return_value.disconnect = AsyncMock()
            with patch("app.services.audit_logger.AuditLogger"):
                with patch.object(
                    tool_write_service, "invalidate_tool_data_caches", new=AsyncMock()
                ) as inv:
                    result = await tool_write_service.apply_tool_changes_batch(
                        _w_machine(),
                        1,
                        [
                            ToolChangeItem(
                                operation_type="name",
                                tool_number=7,
                                name_value="NEW EM",
                                client_id="t7-name",
                            )
                        ],
                        _w_db(_w_machine()),
                    )

    assert result.successful == 0
    inv.assert_not_awaited()


@pytest.mark.asyncio
async def test_tool_name_ftp_upload_invalidates_gateway_tool_cache():
    from app.services import tool_name_write_service

    machine = _w_machine()
    ftp = AsyncMock()
    ftp.get_tool_table_data = AsyncMock(return_value=FULL_TOLN)
    ftp.get_atc_magazine_file = AsyncMock(return_value=(FULL_ATC, "ATCTL.NC"))
    ftp.upload_file = AsyncMock(return_value={"success": True})
    ftp.disconnect = AsyncMock()

    telnet = AsyncMock()
    patched_toln = FULL_TOLN.replace("'OLD NAME      '", "'NEW EM        '")
    telnet.get_tool_table_data = AsyncMock(return_value=patched_toln)
    telnet.get_atc_magazine_data = AsyncMock(return_value=FULL_ATC)
    telnet.disconnect = AsyncMock()

    with patch(
        "app.services.tool_name_write_service._ftp_client_for_machine",
        return_value=ftp,
    ):
        with patch.object(
            tool_name_write_service, "invalidate_tool_data_caches", new=AsyncMock()
        ) as inv:
            await tool_name_write_service.write_tool_names_via_ftp(
                machine, {7: "NEW EM"}, telnet_client=telnet
            )

    inv.assert_awaited_once_with("10.0.0.1", 10000)


@pytest.mark.asyncio
async def test_tool_name_ftp_upload_failure_does_not_invalidate():
    from app.services import tool_name_write_service

    machine = _w_machine()
    ftp = AsyncMock()
    ftp.get_tool_table_data = AsyncMock(return_value=FULL_TOLN)
    ftp.get_atc_magazine_file = AsyncMock(return_value=(FULL_ATC, "ATCTL.NC"))
    ftp.upload_file = AsyncMock(return_value={"success": False, "error": "disk full"})
    ftp.disconnect = AsyncMock()

    telnet = AsyncMock()
    patched_toln = FULL_TOLN.replace("'OLD NAME      '", "'NEW EM        '")
    telnet.get_tool_table_data = AsyncMock(return_value=patched_toln)
    telnet.get_atc_magazine_data = AsyncMock(return_value=FULL_ATC)
    telnet.disconnect = AsyncMock()

    with patch(
        "app.services.tool_name_write_service._ftp_client_for_machine",
        return_value=ftp,
    ):
        with patch.object(
            tool_name_write_service, "invalidate_tool_data_caches", new=AsyncMock()
        ) as inv:
            with pytest.raises(RuntimeError, match="FTP upload failed|disk full"):
                await tool_name_write_service.write_tool_names_via_ftp(
                    machine, {7: "NEW EM"}, telnet_client=telnet
                )

    inv.assert_not_awaited()
