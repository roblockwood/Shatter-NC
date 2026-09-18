# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Shadow-mode helpers for the Phase 1 telnet-gateway rollout.

When the gateway flag is enabled but not authoritative, the direct telnet
client stays authoritative for fast-poll reads while the gateway performs
the same reads in parallel. This module compares the two byte streams so
the gateway can be validated against the real control without ever
influencing poll results.

Provenance note: the C00 telnet protocol is untouched — this module only
observes and compares bytes that both paths read from the machine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
) -> Optional[str]:
    """Mirror of CNCTelnetClient.get_prd3_data's primary/alternate fallback.

    C00 controls serve "PRD3", D00 controls serve "PRDD3"; each falls back to
    the other name when the primary read comes back empty — the same logic
    the direct path uses, so shadow comparisons stay apples-to-apples.
    """
    primary = "PRDD3" if control_version == "D00" else "PRD3"
    alternate = "PRD3" if primary == "PRDD3" else "PRDD3"
    data = await gateway.read(primary, force_refresh=force_refresh)
    if data is None:
        data = await gateway.read(alternate, force_refresh=force_refresh)
    return data
