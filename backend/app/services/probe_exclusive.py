# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Exclusive telnet hold — pause fleet polling while a write owns the machine port.

Used by:
- Probes pane (dialog-scoped begin/end via POST /probe/exclusive)
- Tool table / ATC / macro write paths (request-scoped via exclusive_session)

Hold lifetime is owned by begin/end (or auto-timeout if abandoned).
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

logger = logging.getLogger(__name__)

EXCLUSIVE_HOLD_TIMEOUT_S = 300.0
EXCLUSIVE_COLLECT_POLL_S = 0.25

# machine_id -> hold metadata
_holds: Dict[int, Dict[str, Any]] = {}


def _polling_service():
    import app.api._status_state as status_state

    return status_state.polling_service


def is_exclusive_active(machine_id: int) -> bool:
    return machine_id in _holds


def touch_probe_activity(machine_id: int) -> None:
    hold = _holds.get(machine_id)
    if hold is not None:
        hold["last_activity_at"] = time.monotonic()


async def begin_exclusive(machine_id: int, reason: str = "probe") -> Dict[str, Any]:
    """Pause polling and record an exclusive hold. Idempotent for nested begins."""
    await sweep_stale_holds()
    now = time.monotonic()
    hold = _holds.get(machine_id)
    if hold is None:
        polling = _polling_service()
        if polling is not None:
            polling.pause_machine_polling(machine_id, reason=reason)
        _holds[machine_id] = {
            "refcount": 1,
            "held_at": now,
            "last_activity_at": now,
            "reason": reason,
        }
        logger.info("Exclusive begin machine=%s reason=%s", machine_id, reason)
    else:
        hold["refcount"] = int(hold.get("refcount", 1)) + 1
        hold["last_activity_at"] = now
        logger.info(
            "Exclusive begin (nested) machine=%s reason=%s count=%s",
            machine_id,
            hold.get("reason") or reason,
            hold["refcount"],
        )
    return {"active": True, "machine_id": machine_id, **_hold_public(_holds[machine_id])}


async def end_exclusive(machine_id: int) -> Dict[str, Any]:
    """Resume polling when the last nested hold ends."""
    hold = _holds.get(machine_id)
    if hold is None:
        logger.debug("Exclusive end with no hold machine=%s", machine_id)
        return {"active": False, "machine_id": machine_id}

    count = int(hold.get("refcount", 1)) - 1
    if count > 0:
        hold["refcount"] = count
        hold["last_activity_at"] = time.monotonic()
        logger.info(
            "Exclusive end (nested) machine=%s count=%s",
            machine_id,
            count,
        )
        return {"active": True, "machine_id": machine_id, **_hold_public(hold)}

    _holds.pop(machine_id, None)
    polling = _polling_service()
    if polling is not None:
        polling.resume_machine_polling(machine_id)
    logger.info("Exclusive end machine=%s", machine_id)
    return {"active": False, "machine_id": machine_id}


@asynccontextmanager
async def exclusive_session(
    machine_id: int, reason: str = "write"
) -> AsyncIterator[None]:
    """Pause fleet polling for the duration of a single write request."""
    await begin_exclusive(machine_id, reason=reason)
    try:
        yield
    finally:
        await end_exclusive(machine_id)


async def force_end_exclusive(machine_id: int, *, reason: str = "timeout") -> None:
    """Clear hold and resume regardless of refcount (abandoned dialog safety)."""
    if machine_id not in _holds:
        return
    _holds.pop(machine_id, None)
    polling = _polling_service()
    if polling is not None:
        # Drain any leftover pause refs for this machine.
        while polling.is_machine_polling_paused(machine_id):
            polling.resume_machine_polling(machine_id)
    logger.warning(
        "Exclusive force-end machine=%s reason=%s",
        machine_id,
        reason,
    )


async def sweep_stale_holds(timeout_s: float = EXCLUSIVE_HOLD_TIMEOUT_S) -> None:
    """Auto-resume holds with no activity for timeout_s."""
    now = time.monotonic()
    stale = [
        mid
        for mid, hold in list(_holds.items())
        if (now - float(hold.get("last_activity_at", hold.get("held_at", now))))
        >= timeout_s
    ]
    for mid in stale:
        await force_end_exclusive(mid, reason="stale_timeout")


def collect_poll_seconds(machine_id: int, default: float) -> float:
    """Use faster MEM/PRD3 wait poll while exclusive hold is active."""
    if is_exclusive_active(machine_id):
        return EXCLUSIVE_COLLECT_POLL_S
    return default


def _hold_public(hold: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "refcount": int(hold.get("refcount", 1)),
        "reason": hold.get("reason"),
    }


def _reset_for_tests() -> None:
    _holds.clear()
