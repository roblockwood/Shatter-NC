# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the per-machine telnet gateway (Phase 0).

The gateway is exercised with an injected fake client factory — no real
sockets, no real CNC. The fake mimics the two client behaviours the
gateway depends on:

- ``load_data(data_name)`` returns canned data (or None for failure), and
  leaves ``_connected = False`` on failure, mirroring the real client;
- ``connect()`` / ``disconnect()`` flip ``_connected``.
"""

from __future__ import annotations

import asyncio

import pytest

from app.services import telnet_gateway as gw_mod
from app.services.telnet_gateway import (
    GatewayCircuitOpen,
    TelnetGateway,
    get_gateway,
)


class FakeClient:
    """Minimal stand-in for CNCTelnetClient with scriptable reads."""

    def __init__(self, ip_address: str, port: int = 10000) -> None:
        self.ip_address = ip_address
        self.port = port
        self._connected = False
        self.reads: list[str] = []          # data names requested, in order
        self.writes: list[str] = []        # write fn labels executed, in order
        self.data: dict[str, str] = {}     # data_name -> canned response
        self.fail_names: set[str] = set()  # data names that fail as transport errors
        self.connect_calls = 0

    async def connect(self) -> bool:
        self.connect_calls += 1
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def load_data(self, data_name: str, verbose: bool = False):
        self.reads.append(data_name)
        if data_name in self.fail_names:
            # Mirrors the real client: failure paths disconnect.
            self._connected = False
            await self.disconnect()
            return None
        return self.data.get(data_name, f"<{data_name}>")


def make_gateway(**kwargs) -> tuple[TelnetGateway, dict]:
    """Build a gateway wired to a FakeClient; holder['client'] is set on connect."""
    holder: dict = {}

    def factory(ip: str, port: int) -> FakeClient:
        client = FakeClient(ip, port)
        holder["client"] = client
        return client

    defaults = dict(
        ttl_volatile=60.0,
        ttl_semistatic=60.0,
        ttl_slow=60.0,
        min_delay=0.0,
        max_delay=1.0,
        breaker_failures=3,
        breaker_cooldown=30.0,
        keepalive_idle=3600.0,
    )
    defaults.update(kwargs)
    gw = TelnetGateway("10.0.0.9", 10000, client_factory=factory, **defaults)
    return gw, holder


async def _client_of(gw: TelnetGateway, holder: dict) -> FakeClient:
    """Wait for the worker to create the client via the factory."""
    for _ in range(200):
        if "client" in holder:
            return holder["client"]
        await asyncio.sleep(0.01)
    raise AssertionError("gateway never created its client")


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_jumps_ahead_of_queued_reads():
    """A higher-priority write queued behind reads still executes first.

    Items are enqueued before the worker starts so all three are waiting in
    the queue when it begins draining — the only situation where priority
    ordering is observable.
    """
    gw, holder = make_gateway(ttl_volatile=0)
    # NOTE: worker not started yet — queue fills before it drains.
    try:
        loop = asyncio.get_running_loop()
        machine_order: list[str] = []

        async def write_fn(client):
            machine_order.append("write")
            return "wrote"

        class OrderClient(FakeClient):
            async def load_data(self, data_name: str, verbose: bool = False):
                machine_order.append(f"read:{data_name}")
                return await super().load_data(data_name, verbose)

        def order_factory(ip: str, port: int) -> FakeClient:
            c = OrderClient(ip, port)
            holder["client"] = c
            return c

        gw._client_factory = order_factory

        async def submit_read(name: str):
            fut = loop.create_future()
            item = gw_mod._QueueItem(kind="read", future=fut, data_name=name)
            gw._inflight[name] = fut  # keep read() coalescing out of this test
            await gw._enqueue(item, gw_mod.PRIORITY_READ)
            return await asyncio.shield(fut)

        async def submit_write():
            fut = loop.create_future()
            item = gw_mod._QueueItem(kind="write", future=fut, fn=write_fn)
            await gw._enqueue(item, gw_mod.PRIORITY_WRITE)
            return await asyncio.shield(fut)

        t1 = asyncio.ensure_future(submit_read("MONTR"))
        t2 = asyncio.ensure_future(submit_read("PRD3"))
        t3 = asyncio.ensure_future(submit_write())
        await asyncio.sleep(0)  # let the coroutines enqueue
        await gw.start()  # now the worker drains: write must go first
        await asyncio.gather(t1, t2, t3)

        assert machine_order[0] == "write"
        assert machine_order[1:] == ["read:MONTR", "read:PRD3"]
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# Read coalescing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_reads_for_same_data_name_coalesce():
    gw, _ = make_gateway(ttl_volatile=0)
    await gw.start()
    try:
        vals = await asyncio.gather(
            gw.read("MONTR"), gw.read("MONTR"), gw.read("MONTR")
        )
        assert vals == ["<MONTR>", "<MONTR>", "<MONTR>"]
        client = gw._client
        assert client.reads.count("MONTR") == 1
        assert gw.stats()["coalesced"] == 2
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# TTL cache
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ttl_cache_hit_miss_and_force_refresh():
    gw, _ = make_gateway(ttl_volatile=60.0)
    await gw.start()
    try:
        first = await gw.read("MONTR")
        second = await gw.read("MONTR")
        assert first == second == "<MONTR>"
        client = gw._client
        assert client.reads.count("MONTR") == 1
        assert gw.stats()["cache_hits"] == 1

        refreshed = await gw.read("MONTR", force_refresh=True)
        assert refreshed == "<MONTR>"
        assert client.reads.count("MONTR") == 2
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_ttl_expiry_triggers_refetch():
    gw, _ = make_gateway(ttl_volatile=0.05)
    await gw.start()
    try:
        await gw.read("MONTR")
        await asyncio.sleep(0.08)
        await gw.read("MONTR")
        client = gw._client
        assert client.reads.count("MONTR") == 2
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_slow_tier_data_uses_slow_ttl():
    gw, _ = make_gateway(ttl_volatile=0.01, ttl_slow=60.0)
    await gw.start()
    try:
        await gw.read("TOLNI1")
        await asyncio.sleep(0.03)  # volatile would have expired; slow has not
        await gw.read("TOLNI1")
        client = gw._client
        assert client.reads.count("TOLNI1") == 1
        assert gw.stats()["cache_hits"] == 1
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# Write invalidation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_invalidates_listed_cache_entries():
    gw, _ = make_gateway(ttl_slow=60.0)
    await gw.start()
    try:
        await gw.read("TOLNI1")
        client = gw._client
        assert client.reads.count("TOLNI1") == 1

        async def write_fn(c):
            c.writes.append("offset")
            return (True, "00")

        result = await gw.write(write_fn, invalidate=("TOLNI1",))
        assert result == (True, "00")

        await gw.read("TOLNI1")  # cache was invalidated -> refetch
        assert client.reads.count("TOLNI1") == 2
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_breaker_opens_and_reads_fail_fast():
    gw, holder = make_gateway(ttl_volatile=0, breaker_failures=2, breaker_cooldown=60.0)
    await gw.start()
    try:
        await gw.read("PRD3")  # healthy read forces client creation
        client = await _client_of(gw, holder)
        client.fail_names.add("MONTR")

        assert await gw.read("MONTR") is None
        assert await gw.read("MONTR") is None  # second failure -> breaker opens
        assert gw.stats()["breaker_state"] == "open"
        assert gw.stats()["breaker_opens"] == 1

        reads_before = len(client.reads)
        assert await gw.read("MONTR") is None  # fail fast, no machine contact
        assert len(client.reads) == reads_before
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_breaker_open_write_raises_gateway_circuit_open():
    gw, holder = make_gateway(ttl_volatile=0, breaker_failures=1, breaker_cooldown=60.0)
    await gw.start()
    try:
        await gw.read("PRD3")
        client = await _client_of(gw, holder)
        client.fail_names.add("MONTR")
        assert await gw.read("MONTR") is None
        assert gw.stats()["breaker_state"] == "open"

        async def write_fn(c):
            return "should-not-run"

        with pytest.raises(GatewayCircuitOpen):
            await gw.write(write_fn)
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_breaker_half_open_probe_closes_on_success():
    gw, holder = make_gateway(ttl_volatile=0, breaker_failures=1, breaker_cooldown=0.05)
    await gw.start()
    try:
        await gw.read("PRD3")
        client = await _client_of(gw, holder)
        client.fail_names.add("MONTR")
        assert await gw.read("MONTR") is None
        assert gw.stats()["breaker_state"] == "open"

        await asyncio.sleep(0.08)  # cooldown elapses
        client.fail_names.clear()  # machine recovered
        assert await gw.read("MONTR") == "<MONTR>"
        assert gw.stats()["breaker_state"] == "closed"
        assert gw.stats()["consecutive_failures"] == 0
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_breaker_serves_stale_cache_while_open():
    gw, holder = make_gateway(ttl_volatile=0.05, breaker_failures=1, breaker_cooldown=60.0)
    await gw.start()
    try:
        await gw.read("PRD3")
        client = await _client_of(gw, holder)
        assert await gw.read("MONTR") == "<MONTR>"  # populates cache
        await asyncio.sleep(0.08)  # let the volatile TTL expire
        client.fail_names.add("ALARM")
        assert await gw.read("ALARM") is None  # trips breaker
        assert gw.stats()["breaker_state"] == "open"

        # MONTR's cache is expired, so the request reaches the worker — but
        # the breaker is open, so the stale entry is served without machine
        # contact.
        reads_before = len(client.reads)
        assert await gw.read("MONTR") == "<MONTR>"
        assert len(client.reads) == reads_before
        assert gw.stats()["stale_served"] >= 1
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# Adaptive pacing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pacing_backs_off_on_failure_and_recovers():
    gw, holder = make_gateway(
        ttl_volatile=0, min_delay=0.05, max_delay=0.5,
        breaker_failures=100, breaker_cooldown=60.0,
    )
    await gw.start()
    try:
        await gw.read("PRD3")
        client = await _client_of(gw, holder)
        assert gw._current_delay == 0.05

        client.fail_names.add("MONTR")
        await gw.read("MONTR")
        assert gw._current_delay > 0.05
        await gw.read("MONTR")
        assert gw._current_delay <= 0.5

        client.fail_names.clear()
        for _ in range(20):
            await gw.read("MONTR")
        assert gw._current_delay == 0.05  # decayed back to the floor
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# Keepalive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_keepalive_issues_montr_when_idle():
    gw, holder = make_gateway(ttl_volatile=0, keepalive_idle=0.05)
    await gw.start()
    try:
        await gw.read("PRD3")  # forces client creation + connection
        client = await _client_of(gw, holder)
        reads_before = len(client.reads)
        await asyncio.sleep(0.25)
        montr_keepalives = [r for r in client.reads[reads_before:] if r == "MONTR"]
        assert len(montr_keepalives) >= 1
        assert gw.stats()["keepalives"] >= 1
    finally:
        await gw.aclose()


# ---------------------------------------------------------------------------
# Stats and registry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_snapshot_has_expected_keys():
    gw, _ = make_gateway()
    await gw.start()
    try:
        await gw.read("MONTR")
        await gw.read("MONTR")  # cache hit
        s = gw.stats()
        for key in (
            "commands_sent", "cache_hits", "coalesced", "stale_served",
            "timeouts", "breaker_opens", "queue_depth", "breaker_state",
            "avg_latency_ms", "current_delay",
        ):
            assert key in s, f"missing stats key: {key}"
        assert s["commands_sent"] == 1
        assert s["cache_hits"] == 1
        assert s["avg_latency_ms"] is not None
    finally:
        await gw.aclose()


@pytest.mark.asyncio
async def test_registry_returns_same_gateway_per_machine():
    gw1 = await get_gateway("10.9.9.1", 10000)
    gw2 = await get_gateway("10.9.9.1", 10000)
    gw3 = await get_gateway("10.9.9.2", 10000)
    try:
        assert gw1 is gw2
        assert gw1 is not gw3
    finally:
        await gw1.aclose()
        await gw3.aclose()


@pytest.mark.asyncio
async def test_no_retry_on_timeout_paths():
    """A TIMEOUT-style failure (client disconnects, returns None) must not
    be retried by the gateway — one LOD per read(), full stop."""
    gw, holder = make_gateway(ttl_volatile=0, breaker_failures=100, breaker_cooldown=60.0)
    await gw.start()
    try:
        await gw.read("PRD3")
        client = await _client_of(gw, holder)
        client.fail_names.add("MONTR")
        assert await gw.read("MONTR") is None
        assert client.reads.count("MONTR") == 1
    finally:
        await gw.aclose()
