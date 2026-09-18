# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Shadow-mode helpers for the telnet-gateway rollout (Phase 1 + 1b).

When the gateway flag is enabled but not authoritative, the direct telnet
client stays authoritative for reads while the gateway performs the same
reads sequentially right after (direct first, then a gateway forced
refresh for a fair comparison). This module compares the two byte streams
so the gateway can be validated against the real control without ever
influencing results.

Phase 1 covered the fast-poll LOD reads (MONTR/PRD3/MEM). Phase 1b adds:
tool-poll reads (TOLN/ATC), the fast-poll remainder (ALARM/PANEL/MACRO via
the gateway command path), on-demand API reads (``gw_on_demand``), and
tool-data cache invalidation helpers.

Provenance note: the C00 telnet protocol is untouched — this module only
observes and compares bytes that both paths read from the machine.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from app.core.config import settings
from app.services.telnet_gateway import get_gateway

logger = logging.getLogger(__name__)


def _describe(value: Optional[str]) -> str:
    if value is None:
        return "None"
    return f"{len(value)} bytes"


class ShadowComparator:
    """Counts per-data-name agreement between direct and gateway reads."""

    def __init__(self) -> None:
        self._compared: Dict[str, int] = {}
        self._matched: Dict[str, int] = {}
        self._mismatched: Dict[str, int] = {}

    def compare(
        self, data_name: str, direct: Optional[str], via_gateway: Optional[str]
    ) -> bool:
        """Record one comparison. Returns True on exact match.

        Mismatches log at warning (lengths only); full contents go to debug
        so routine volatile-data drift doesn't flood logs with payloads.
        """
        self._compared[data_name] = self._compared.get(data_name, 0) + 1
        matched = direct == via_gateway
        if matched:
            self._matched[data_name] = self._matched.get(data_name, 0) + 1
        else:
            self._mismatched[data_name] = self._mismatched.get(data_name, 0) + 1
            logger.warning(
                "gateway shadow mismatch for %s: direct=%s gateway=%s",
                data_name,
                _describe(direct),
                _describe(via_gateway),
            )
            logger.debug("gateway shadow %s direct content: %r", data_name, direct)
            logger.debug("gateway shadow %s gateway content: %r", data_name, via_gateway)
        return matched

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        """Per-data-name {compared, matched, mismatched} counters."""
        return {
            name: {
                "compared": self._compared.get(name, 0),
                "matched": self._matched.get(name, 0),
                "mismatched": self._mismatched.get(name, 0),
            }
            for name in sorted(self._compared)
        }


async def read_prd3_via_gateway(
    gateway: Any,
    control_version: Optional[str],
    *,
    force_refresh: bool = False,
    ttl: Optional[float] = None,
) -> Optional[str]:
    """Mirror of CNCTelnetClient.get_prd3_data's primary/alternate fallback.

    C00 controls serve "PRD3", D00 controls serve "PRDD3"; each falls back to
    the other name when the primary read comes back empty — the same logic
    the direct path uses, so shadow comparisons stay apples-to-apples.
    """
    primary = "PRDD3" if control_version == "D00" else "PRD3"
    alternate = "PRD3" if primary == "PRDD3" else "PRDD3"
    data = await gateway.read(primary, force_refresh=force_refresh, ttl=ttl)
    if data is None:
        data = await gateway.read(alternate, force_refresh=force_refresh, ttl=ttl)
    return data


def _primary_data_name(control_version: Optional[str], c00_name: str, d00_name: str) -> str:
    return d00_name if control_version == "D00" else c00_name


async def read_atc_via_gateway(
    gateway: Any,
    control_version: Optional[str],
    *,
    force_refresh: bool = False,
    ttl: Optional[float] = None,
    attempts: int = 1,
    retry_delay: float = 0.5,
) -> Optional[str]:
    """Mirror of CNCTelnetClient.get_atc_magazine_data's primary/alternate fallback.

    C00 controls serve "ATCTL", D00 controls serve "ATDTL"; each falls back
    to the other name when the primary read comes back empty — the same
    logic the direct path uses, so shadow comparisons stay apples-to-apples.

    ``attempts`` mirrors the poller's ``_fetch_atc_data_with_retry``: ATCTL
    can fail briefly after TOLN FTP uploads, so the authoritative tool-poll
    path retries a couple of times. Each attempt is a fresh command (never
    a retry of a drained TIMEOUT), preserving the CM7522 no-retry rule.
    """
    primary = _primary_data_name(control_version, "ATCTL", "ATDTL")
    alternate = "ATCTL" if primary == "ATDTL" else "ATDTL"
    for attempt in range(max(1, attempts)):
        data = await gateway.read(primary, force_refresh=force_refresh, ttl=ttl)
        if data is None:
            data = await gateway.read(alternate, force_refresh=force_refresh, ttl=ttl)
        if data:
            return data
        if attempt < attempts - 1:
            logger.debug(
                "gateway ATCTL read failed (attempt %s/%s), retrying in %.1fs",
                attempt + 1,
                attempts,
                retry_delay,
            )
            await asyncio.sleep(retry_delay)
    return None


def macro_cache_key(start_macro: int, data_size: int) -> str:
    """Gateway cache key for a REDMCNM macro-range read."""
    return f"MACRO:{start_macro}:{data_size}"


def canonical_json(value: Any) -> Optional[str]:
    """Canonical string form for non-LOD gateway results (shadow comparison).

    Macro reads return ``list[float]``; both the direct and gateway legs go
    through the same client parser, so identical machine bytes produce
    identical JSON. None stays None.
    """
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


async def read_macro_range_via_gateway(
    gateway: Any,
    start_macro: int,
    data_size: int,
    *,
    force_refresh: bool = False,
    ttl: Optional[float] = None,
    timeout: Optional[float] = None,
) -> Optional[list]:
    """Read macro variables through the gateway's command path.

    The macro range read is a ``REDMCNM`` multipart command, not ``LOD``,
    so it rides ``gateway.read_command()`` instead of ``gateway.read()``.
    Returns the parsed ``list[float]`` (or None), exactly like
    ``CNCTelnetClient.get_macro_variable_range``.
    """
    return await gateway.read_command(
        macro_cache_key(start_macro, data_size),
        lambda client: client.get_macro_variable_range(
            start_macro, data_size, verbose=False
        ),
        force_refresh=force_refresh,
        ttl=ttl,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# On-demand API reads (Phase 1b)
# ---------------------------------------------------------------------------

# Shadow comparisons for on-demand (API) reads accumulate here, separate
# from each poller's own comparator. The fast poll exposes a snapshot of
# this in its status payload for rollout observability.
_ondemand_comparator = ShadowComparator()


def ondemand_shadow_snapshot() -> Dict[str, Dict[str, int]]:
    """Snapshot of on-demand shadow comparison counters."""
    return _ondemand_comparator.snapshot()


async def gw_on_demand(
    ip_address: str,
    data_name: str,
    direct_fn: Callable[[], Awaitable[Optional[str]]],
    *,
    port: int = 10000,
    gateway_fn: Optional[Callable[..., Awaitable[Optional[str]]]] = None,
    force_refresh: bool = True,
    ttl: Optional[float] = None,
) -> Optional[str]:
    """Route one on-demand (API) read through the gateway when enabled.

    ``direct_fn`` performs the read on the caller's own client (created and
    owned by the caller as today). ``gateway_fn`` optionally overrides the
    gateway leg — it is called as
    ``gateway_fn(gateway, force_refresh=..., ttl=...)`` (e.g. the PRD3/ATC
    primary/alternate fallbacks); otherwise the leg is
    ``gateway.read(data_name, ...)``.

    - Gateway disabled or setup failed: ``direct_fn()`` only (today's behavior).
    - Authoritative: gateway only (``force_refresh`` as passed — on-demand
      reads default to True so a human asking always gets live data).
    - Shadow: direct first (authoritative result returned), then the gateway
      leg with ``force_refresh=True`` for a fair byte comparison; gateway
      failures are swallowed and never fail the request.
    """
    gateway = None
    gateway_authoritative = False
    if settings.SHATTER_TELNET_GATEWAY_ENABLED:
        try:
            gateway = await get_gateway(ip_address, port)
            gateway_authoritative = settings.SHATTER_TELNET_GW_AUTHORITATIVE
        except Exception as exc:
            logger.warning(
                "on-demand gateway unavailable for %s (%s); using direct client",
                ip_address,
                exc,
            )
            gateway = None

    async def _gateway_leg(*, force_refresh: bool) -> Optional[str]:
        assert gateway is not None
        if gateway_fn is not None:
            return await gateway_fn(
                gateway, force_refresh=force_refresh, ttl=ttl
            )
        return await gateway.read(
            data_name, force_refresh=force_refresh, ttl=ttl
        )

    if gateway is None:
        return await direct_fn()
    if gateway_authoritative:
        return await _gateway_leg(force_refresh=force_refresh)
    result = await direct_fn()
    try:
        compared = await _gateway_leg(force_refresh=True)
        _ondemand_comparator.compare(data_name, result, compared)
    except Exception as exc:
        logger.debug(
            "on-demand gateway shadow read %s failed (ignored): %s", data_name, exc
        )
    return result


# ---------------------------------------------------------------------------
# Tool-data cache invalidation (Phase 1b)
# ---------------------------------------------------------------------------

#: Cached LOD names invalidated after tool writes / TOLN uploads / tool changes.
TOOL_DATA_NAMES = ("TOLNI1", "TOLNM1", "ATCTL", "ATDTL")


async def invalidate_tool_data_caches(
    ip_address: str, port: int = 10000
) -> None:
    """Drop cached tool-data entries after a tool write or TOLN FTP upload.

    Best-effort and never raises: a no-op when the gateway flag is off or
    the gateway is unavailable. Callers must still treat their write as the
    source of truth — this only prevents the gateway from serving
    pre-write cached bytes afterwards.
    """
    if not settings.SHATTER_TELNET_GATEWAY_ENABLED:
        return
    try:
        gateway = await get_gateway(ip_address, port)
    except Exception:
        logger.debug(
            "tool-data cache invalidation skipped (gateway unavailable for %s)",
            ip_address,
            exc_info=True,
        )
        return
    try:
        gateway.invalidate(*TOOL_DATA_NAMES)
    except Exception:
        logger.debug("tool-data cache invalidation failed", exc_info=True)
