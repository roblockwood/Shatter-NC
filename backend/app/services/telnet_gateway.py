# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Per-machine Telnet connection gateway (Phase 0).

The Brother "Protocol Type 2" TCP interface on port 10000 is the primary data
source for machine polling, but the CNC control's embedded TCP stack is
sensitive to connection churn and request bursts: the poller historically
opened a fresh TCP connection per poll phase and paced commands per client
instance (so the throttle reset every time a new client was constructed).

This module wraps that reality behind a single owner per machine:

- one persistent ``CNCTelnetClient`` TCP connection per (ip, port),
- one worker task pumping an ``asyncio.PriorityQueue`` (interactive writes
  jump ahead of bulk poll reads),
- request coalescing (N concurrent reads for the same data name -> one LOD),
- a TTL cache per data type so slow-changing data stops hitting the machine,
- adaptive inter-command pacing enforced in one place (not per client),
- a circuit breaker that sheds load when the control starts failing,
- a keepalive so idle connections don't go stale.

Provenance note: the C00 telnet protocol behaviour is unchanged — the
no-retry-after-drain rule (CM7522 protection) still lives in
``CNCTelnetClient._send_command``. The gateway only changes how the backend
schedules its requests.

Phase 0 is flag-gated (``SHATTER_TELNET_GATEWAY_ENABLED``) and nothing else
in the codebase routes through it yet; the poller migrates in Phase 1+.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from app.clients import telnet_client as _telnet_client_mod
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Priorities (lower value = processed sooner)
# ---------------------------------------------------------------------------

PRIORITY_INTERACTIVE = 0  # panel keys, mode changes — operator is waiting
PRIORITY_WRITE = 1        # tool/macro/ATC writes
PRIORITY_READ = 2         # poll reads (bulk, deferrable)


class GatewayCircuitOpen(RuntimeError):
    """Raised when a write is submitted while the breaker is open."""


class GatewayNotStarted(RuntimeError):
    """Raised when the gateway is used after :meth:`aclose`."""


# ---------------------------------------------------------------------------
# TTL tiers — which LOD data names belong to which freshness tier.
# Tier *durations* come from settings (user-tunable); membership lives here.
# Verified against backend/app/clients/_telnet_data_reads.py data names.
#
# Phase 1b: TOLN/ATC reads can also be issued with a per-call ``ttl``
# override (state-aware: short while the operator may be editing at the
# panel, slow while the machine is operating). Command-path reads
# (``read_command``) default to the volatile tier unless overridden.
# ---------------------------------------------------------------------------

_TTL_TIER_VOLATILE = frozenset(
    {
        "MONTR",    # monitor / running status
        "PRD3",     # production data 3 (C00)
        "PRDD3",    # production data 3 (D00)
        "POSNI1",   # position / work offsets (inches)
        "POSNM1",   # position / work offsets (mm)
        "ALARM",    # alarm list
        "PANEL",    # panel display data
    }
)
_TTL_TIER_SEMISTATIC = frozenset(
    {
        "MEM",  # current program info
        "DIR",  # directory listing
    }
)
_TTL_TIER_SLOW = frozenset(
    {
        "TOLNI1",  # tool table (inches)
        "TOLNM1",  # tool table (mm)
        "ATCTL",   # ATC magazine (C00)
        "ATDTL",   # ATC magazine (D00)
    }
)


def _default_client_factory(ip_address: str, port: int):
    """Build a real client. Resolved via module so tests can monkeypatch."""
    # command_delay=0.0: pacing is enforced centrally by the gateway worker,
    # so the per-client throttle must not double-pace.
    return _telnet_client_mod.CNCTelnetClient(
        ip_address, port=port, timeout=10, command_delay=0.0
    )


@dataclass(order=False)
class _QueueItem:
    kind: str  # "read" | "write" ("read" covers LOD reads and read_command() fns)
    future: "asyncio.Future[Any]"
    data_name: Optional[str] = None  # LOD name for read(); cache key for read_command()
    fn: Optional[Callable[[Any], Awaitable[Any]]] = None  # write() op, or read_command() fn
    invalidate: Tuple[str, ...] = ()


class TelnetGateway:
    """Owns the single persistent telnet connection for one machine."""

    def __init__(
        self,
        ip_address: str,
        port: int = 10000,
        *,
        client_factory: Optional[Callable[[str, int], Any]] = None,
        ttl_volatile: Optional[float] = None,
        ttl_semistatic: Optional[float] = None,
        ttl_slow: Optional[float] = None,
        min_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        breaker_failures: Optional[int] = None,
        breaker_cooldown: Optional[float] = None,
        keepalive_idle: Optional[float] = None,
    ) -> None:
        self.ip_address = ip_address
        self.port = port
        self._client_factory = client_factory or _default_client_factory
        self._client: Any = None

        self._ttl_volatile = settings.SHATTER_TELNET_GW_TTL_VOLATILE if ttl_volatile is None else ttl_volatile
        self._ttl_semistatic = settings.SHATTER_TELNET_GW_TTL_SEMISTATIC if ttl_semistatic is None else ttl_semistatic
        self._ttl_slow = settings.SHATTER_TELNET_GW_TTL_SLOW if ttl_slow is None else ttl_slow
        self._min_delay = settings.SHATTER_TELNET_GW_MIN_DELAY if min_delay is None else min_delay
        self._max_delay = settings.SHATTER_TELNET_GW_MAX_DELAY if max_delay is None else max_delay
        self._breaker_failures = settings.SHATTER_TELNET_GW_BREAKER_FAILURES if breaker_failures is None else breaker_failures
        self._breaker_cooldown = settings.SHATTER_TELNET_GW_BREAKER_COOLDOWN if breaker_cooldown is None else breaker_cooldown
        self._keepalive_idle = settings.SHATTER_TELNET_GW_KEEPALIVE_IDLE if keepalive_idle is None else keepalive_idle

        self._queue: "asyncio.PriorityQueue[Tuple[int, int, _QueueItem]]" = asyncio.PriorityQueue()
        self._seq = itertools.count()
        self._worker: Optional[asyncio.Task[None]] = None
        self._running = False
        self._closed = False

        # Read coalescing: data_name -> shared future for the in-flight LOD.
        self._inflight: Dict[str, "asyncio.Future[Any]"] = {}
        # TTL cache: data_name -> (value, fetched_at_monotonic). Values are
        # raw LOD strings for read(); arbitrary comparable values for
        # read_command().
        self._cache: Dict[str, Tuple[Any, float]] = {}

        # Adaptive pacing.
        self._current_delay = self._min_delay
        self._last_command_at = 0.0

        # Circuit breaker: "closed" | "open" | "half_open".
        self._breaker_state = "closed"
        self._consecutive_failures = 0
        self._breaker_opened_at = 0.0

        # Observability.
        self._counters: Dict[str, int] = {
            "commands_sent": 0,
            "cache_hits": 0,
            "coalesced": 0,
            "stale_served": 0,
            "timeouts": 0,
            "breaker_opens": 0,
            "keepalives": 0,
        }
        self._latencies: List[float] = []  # last 100 command latencies, seconds

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> "TelnetGateway":
        """Start the worker task (idempotent)."""
        if self._closed:
            raise GatewayNotStarted("gateway has been closed")
        if self._worker is None or self._worker.done():
            self._running = True
            self._worker = asyncio.get_running_loop().create_task(
                self._worker_loop(), name=f"telnet-gw-{self.ip_address}:{self.port}"
            )
        return self

    async def aclose(self) -> None:
        """Stop the worker and disconnect. The registry entry is dropped."""
        self._closed = True
        self._running = False
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except (asyncio.CancelledError, Exception):
                pass
            self._worker = None
        # Fail any waiters still queued.
        while not self._queue.empty():
            try:
                _, _, item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if not item.future.done():
                item.future.set_exception(GatewayNotStarted("gateway closed"))
        for fut in list(self._inflight.values()):
            if not fut.done():
                fut.set_exception(GatewayNotStarted("gateway closed"))
        self._inflight.clear()
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                logger.debug("gateway disconnect error", exc_info=True)
            self._client = None
        _drop_gateway(self.ip_address, self.port)

    async def __aenter__(self) -> "TelnetGateway":
        return await self.start()

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def _ensure_started(self) -> None:
        if self._closed:
            raise GatewayNotStarted("gateway has been closed")
        if self._worker is None or self._worker.done():
            await self.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def read(
        self,
        data_name: str,
        priority: int = PRIORITY_READ,
        ttl: Optional[float] = None,
        force_refresh: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[str]:
        """Read a data file (LOD) through the gateway.

        Serves from the TTL cache when fresh; concurrent reads for the same
        ``data_name`` share one in-flight LOD (coalescing).
        """
        await self._ensure_started()
        loop = asyncio.get_running_loop()
        now = loop.time()
        if ttl is None:
            ttl = self._ttl_for(data_name)

        if not force_refresh and ttl > 0:
            cached = self._cache.get(data_name)
            if cached is not None and now - cached[1] < ttl:
                self._counters["cache_hits"] += 1
                return cached[0]

        existing = self._inflight.get(data_name)
        if existing is not None:
            self._counters["coalesced"] += 1
            result = await asyncio.shield(existing)
            return result

        fut: "asyncio.Future[Optional[str]]" = loop.create_future()
        self._inflight[data_name] = fut
        item = _QueueItem(kind="read", future=fut, data_name=data_name)
        await self._enqueue(item, priority)
        if timeout is not None:
            return await asyncio.wait_for(asyncio.shield(fut), timeout)
        return await asyncio.shield(fut)

    async def read_command(
        self,
        cache_key: str,
        fn: Callable[[Any], Awaitable[Any]],
        *,
        priority: int = PRIORITY_READ,
        ttl: Optional[float] = None,
        force_refresh: bool = False,
        timeout: Optional[float] = None,
    ) -> Any:
        """Run an arbitrary read command ``fn(client)`` through the gateway.

        Phase 1b: not every machine read is a ``LOD <data_name>`` — the
        macro range read uses ``REDMCNM``. This runs any client coroutine
        while keeping the gateway's priority queue, adaptive pacing,
        circuit breaker, TTL cache, read coalescing, and stats, keyed by
        ``cache_key`` (e.g. ``"MACRO:500:500"``).

        ``fn`` runs on the gateway-owned client inside the worker task; it
        may acquire the per-machine lock itself, exactly like
        ``load_data()`` does. It must return a value that is safely
        comparable — callers canonicalize it (e.g. to JSON) for shadow
        comparison. ``ttl`` defaults to the volatile tier: command reads
        are assumed fresh-sensitive unless the caller says otherwise.
        """
        await self._ensure_started()
        loop = asyncio.get_running_loop()
        now = loop.time()
        if ttl is None:
            ttl = self._ttl_volatile

        if not force_refresh and ttl > 0:
            cached = self._cache.get(cache_key)
            if cached is not None and now - cached[1] < ttl:
                self._counters["cache_hits"] += 1
                return cached[0]

        existing = self._inflight.get(cache_key)
        if existing is not None:
            self._counters["coalesced"] += 1
            return await asyncio.shield(existing)

        fut: "asyncio.Future[Any]" = loop.create_future()
        self._inflight[cache_key] = fut
        item = _QueueItem(kind="read", future=fut, data_name=cache_key, fn=fn)
        await self._enqueue(item, priority)
        if timeout is not None:
            return await asyncio.wait_for(asyncio.shield(fut), timeout)
        return await asyncio.shield(fut)

    async def write(
        self,
        fn: Callable[[Any], Awaitable[Any]],
        priority: int = PRIORITY_WRITE,
        invalidate: Tuple[str, ...] = (),
        timeout: Optional[float] = None,
    ) -> Any:
        """Run ``fn(client)`` on the gateway-owned client.

        ``invalidate`` lists cached data names to drop on success
        (write-through invalidation). Raises :class:`GatewayCircuitOpen`
        without touching the machine when the breaker is open.
        """
        await self._ensure_started()
        loop = asyncio.get_running_loop()
        fut: "asyncio.Future[Any]" = loop.create_future()
        item = _QueueItem(kind="write", future=fut, fn=fn, invalidate=invalidate)
        await self._enqueue(item, priority)
        if timeout is not None:
            return await asyncio.wait_for(asyncio.shield(fut), timeout)
        return await asyncio.shield(fut)

    def invalidate(self, *data_names: str) -> None:
        """Drop cached entries (e.g. MEM after a program change is detected).

        The next read() for the name goes back to the machine. Unknown names
        are a no-op.
        """
        for name in data_names:
            self._cache.pop(name, None)

    def stats(self) -> Dict[str, Any]:
        """Snapshot of per-gateway observability counters."""
        lat = self._latencies
        return {
            "ip": self.ip_address,
            "port": self.port,
            "queue_depth": self._queue.qsize(),
            "inflight_reads": len(self._inflight),
            "cached_names": len(self._cache),
            "current_delay": round(self._current_delay, 3),
            "breaker_state": self._breaker_state,
            "consecutive_failures": self._consecutive_failures,
            "avg_latency_ms": round(sum(lat) / len(lat) * 1000, 1) if lat else None,
            **self._counters,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _enqueue(self, item: _QueueItem, priority: int) -> None:
        await self._queue.put((priority, next(self._seq), item))

    def _ttl_for(self, data_name: str) -> float:
        if data_name in _TTL_TIER_SLOW:
            return self._ttl_slow
        if data_name in _TTL_TIER_SEMISTATIC:
            return self._ttl_semistatic
        return self._ttl_volatile  # volatile is the safe default

    async def _ensure_connected(self) -> None:
        if self._client is None:
            self._client = self._client_factory(self.ip_address, self.port)
        if not self._client._connected:
            ok = await self._client.connect()
            if not ok:
                raise ConnectionError(
                    f"telnet connect failed for {self.ip_address}:{self.port}"
                )

    async def _pace(self) -> None:
        loop = asyncio.get_running_loop()
        now = loop.time()
        wait = self._last_command_at + self._current_delay - now
        if wait > 0:
            await asyncio.sleep(wait)

    def _note_success(self) -> None:
        self._consecutive_failures = 0
        # Decay back toward the floor so a recovered machine regains pace.
        self._current_delay = max(self._min_delay, self._current_delay - 0.05)
        if self._breaker_state == "half_open":
            logger.info(
                "telnet gateway %s:%s breaker closed (probe succeeded)",
                self.ip_address, self.port,
            )
            self._breaker_state = "closed"

    def _note_transport_failure(self) -> None:
        self._consecutive_failures += 1
        self._current_delay = min(self._max_delay, self._current_delay + 0.1)
        if self._breaker_state == "closed" and self._consecutive_failures >= self._breaker_failures:
            self._open_breaker("consecutive failures")
        elif self._breaker_state == "half_open":
            self._open_breaker("half-open probe failed")

    def _open_breaker(self, reason: str) -> None:
        self._breaker_state = "open"
        self._breaker_opened_at = asyncio.get_running_loop().time()
        self._counters["breaker_opens"] += 1
        logger.warning(
            "telnet gateway %s:%s circuit breaker OPEN (%s)",
            self.ip_address, self.port, reason,
        )

    def _breaker_allows_traffic(self) -> bool:
        if self._breaker_state == "closed":
            return True
        if self._breaker_state == "open":
            now = asyncio.get_running_loop().time()
            if now - self._breaker_opened_at >= self._breaker_cooldown:
                self._breaker_state = "half_open"
                logger.info(
                    "telnet gateway %s:%s breaker half-open (probing)",
                    self.ip_address, self.port,
                )
                return True
            return False
        return True  # half_open: the single in-flight probe is the current item

    def _record_latency(self, seconds: float) -> None:
        self._latencies.append(seconds)
        if len(self._latencies) > 100:
            del self._latencies[:-100]

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                _, _, item = await asyncio.wait_for(
                    self._queue.get(), timeout=self._keepalive_idle
                )
            except asyncio.TimeoutError:
                await self._maybe_keepalive()
                continue
            except asyncio.CancelledError:
                break
            try:
                if item.kind == "read":
                    await self._process_read(item)
                else:
                    await self._process_write(item)
            except Exception:
                logger.exception("telnet gateway worker error")
            finally:
                self._queue.task_done()

    async def _maybe_keepalive(self) -> None:
        """Send a cheap MONTR read when idle so the session doesn't go stale."""
        loop = asyncio.get_running_loop()
        if self._client is None or not self._client._connected:
            return
        if loop.time() - self._last_command_at < self._keepalive_idle:
            return
        try:
            await self._pace()
            t0 = loop.time()
            value = await self._client.load_data("MONTR")
            self._record_latency(loop.time() - t0)
            self._last_command_at = loop.time()
            self._counters["commands_sent"] += 1
            self._counters["keepalives"] += 1
            if value is not None:
                self._note_success()
                self._cache["MONTR"] = (value, loop.time())
            else:
                # load_data disconnects on failure; do NOT trip the breaker
                # for a background keepalive — just let the next real
                # command reconnect and be judged on its own merits.
                logger.debug(
                    "telnet gateway %s:%s keepalive failed", self.ip_address, self.port
                )
        except Exception:
            logger.debug(
                "telnet gateway %s:%s keepalive error", self.ip_address, self.port,
                exc_info=True,
            )

    async def _process_read(self, item: _QueueItem) -> None:
        assert item.data_name is not None
        key = item.data_name
        fut = item.future
        loop = asyncio.get_running_loop()
        try:
            if not self._breaker_allows_traffic():
                # Breaker open: serve stale cache or fail fast, never touch
                # the machine.
                stale = self._cache.get(key)
                if stale is not None:
                    self._counters["stale_served"] += 1
                if not fut.done():
                    fut.set_result(stale[0] if stale else None)
                return

            await self._pace()
            t0 = loop.time()
            await self._ensure_connected()
            if item.fn is not None:
                # Phase 1b command path (e.g. REDMCNM macro range): run the
                # caller's coroutine on the shared client. Like load_data(),
                # it may acquire the per-machine lock itself.
                value = await item.fn(self._client)
            else:
                value = await self._client.load_data(key)
            latency = loop.time() - t0
            self._record_latency(latency)
            self._last_command_at = loop.time()
            self._counters["commands_sent"] += 1

            if value is None:
                # load_data() leaves the client disconnected on every failure
                # path (TIMEOUT included — the CM7522 rule means it is never
                # retried). Treat as a transport failure for pacing/breaker;
                # serve stale cache rather than a bare None when we have it.
                self._counters["timeouts"] += 1
                self._note_transport_failure()
                stale = self._cache.get(key)
                if stale is not None:
                    self._counters["stale_served"] += 1
                if not fut.done():
                    fut.set_result(stale[0] if stale else None)
            else:
                self._note_success()
                self._cache[key] = (value, loop.time())
                if not fut.done():
                    fut.set_result(value)
        except Exception as exc:
            self._note_transport_failure()
            if not fut.done():
                fut.set_exception(exc)
        finally:
            self._inflight.pop(key, None)

    async def _process_write(self, item: _QueueItem) -> None:
        assert item.fn is not None
        fut = item.future
        loop = asyncio.get_running_loop()
        try:
            if not self._breaker_allows_traffic():
                raise GatewayCircuitOpen(
                    f"telnet gateway {self.ip_address}:{self.port} circuit breaker is open"
                )
            await self._pace()
            t0 = loop.time()
            await self._ensure_connected()
            result = await item.fn(self._client)
            latency = loop.time() - t0
            self._record_latency(latency)
            self._last_command_at = loop.time()
            self._counters["commands_sent"] += 1
            if not self._client._connected:
                # The operation tore the connection down — count it even
                # though fn() itself did not raise.
                self._note_transport_failure()
            else:
                self._note_success()
            for name in item.invalidate:
                self._cache.pop(name, None)
            if not fut.done():
                fut.set_result(result)
        except Exception as exc:
            # GatewayCircuitOpen is a fast-fail, not a machine failure.
            if not isinstance(exc, GatewayCircuitOpen):
                self._note_transport_failure()
            if not fut.done():
                fut.set_exception(exc)


# ---------------------------------------------------------------------------
# Module-level registry: one gateway per (ip, port)
# ---------------------------------------------------------------------------

_gateways: Dict[Tuple[str, int], TelnetGateway] = {}
_registry_lock = asyncio.Lock()


async def get_gateway(ip_address: str, port: int = 10000, **kwargs: Any) -> TelnetGateway:
    """Return the shared gateway for a machine, creating it on first use."""
    key = (ip_address, port)
    async with _registry_lock:
        gw = _gateways.get(key)
        if gw is None or gw._closed:
            gw = TelnetGateway(ip_address, port, **kwargs)
            _gateways[key] = gw
        return gw


def _drop_gateway(ip_address: str, port: int) -> None:
    _gateways.pop((ip_address, port), None)


async def close_all_gateways() -> int:
    """Close every registered gateway (used on shutdown/reload)."""
    async with _registry_lock:
        gateways = list(_gateways.values())
    count = 0
    for gw in gateways:
        try:
            await gw.aclose()
            count += 1
        except Exception:
            logger.debug("error closing telnet gateway", exc_info=True)
    return count
