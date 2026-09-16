# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Machine lock as a test-safety interlock.

``CHGMACL`` (machine lock) inhibits axis motion on the Brother control: the
program still executes, but no axis moves. That makes it the safety net for
live-machine testing — engage it before running anything that could move the
machine and the worst case is a program that runs through without motion.

:func:`machine_lock_guard` is fail-closed: the guarded body only runs after
PANEL read-back confirms MACHINE LOCK is ON. On exit the guard restores the
MLOCK state it found on entry (verified via read-back), so it never clobbers
an operator's pre-existing lock.

Scope note: machine lock stops AXIS MOTION ONLY. Spindle, tool change, and
other M/S/T functions still execute. It prevents motion crashes, not every
hazard — keep hands clear and the enclosure closed regardless.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


class MachineLockError(RuntimeError):
    """Raised when the machine-lock safety interlock cannot be verified."""


async def _read_machine_lock(client: Any) -> Optional[int]:
    """Read the MACHINE LOCK bit from LOD PANEL (1=ON, 0=OFF, None=unreadable)."""
    from app.parsers.panel_parser_v2 import parse_panel_v2

    raw = await client.get_panel_data(verbose=False)
    if not raw:
        return None
    panel = parse_panel_v2(raw.encode("utf-8"))
    block = panel.get("mode_and_functions") or {}
    value = block.get("machine_lock")
    return int(value) if value is not None else None


async def _ensure_machine_lock(client: Any, on: bool, retries: int) -> bool:
    """Drive MACHINE LOCK to the requested state, verified via PANEL read-back.

    Uses the allowlisted CHGMACL write path (set_panel_function). Status 60
    (already in requested state) counts as success there. Returns True only
    when read-back confirms the requested state.
    """
    want = 1 if on else 0
    for _ in range(max(1, retries)):
        ok, _status = await client.set_panel_function("machine_lock", on)
        if not ok:
            continue
        if await _read_machine_lock(client) == want:
            return True
    return False


@asynccontextmanager
async def machine_lock_guard(
    client: Any, *, retries: int = 3
) -> AsyncIterator[int]:
    """Hold MACHINE LOCK on for the duration of a live-machine test.

    Fail-closed: if the lock cannot be verified ON via PANEL read-back, raises
    :class:`MachineLockError` and the guarded body never runs.

    On exit, restores the MLOCK state found on entry (verified via read-back).
    A pre-existing ON is left untouched; a restore failure raises
    :class:`MachineLockError` — the machine is left locked (the safe direction)
    and the operator must clear it deliberately.

    Yields the MLOCK state found on entry (1=was already locked, 0=was not).
    """
    prior = await _read_machine_lock(client)
    if prior is None:
        raise MachineLockError(
            "Cannot read MACHINE LOCK state from PANEL; refusing to run unverified."
        )

    engaged_by_guard = False
    if prior != 1:
        if not await _ensure_machine_lock(client, True, retries):
            raise MachineLockError(
                "Could not verify MACHINE LOCK engaged via PANEL read-back; "
                "refusing to run."
            )
        engaged_by_guard = True
        logger.info("[SAFETY] MACHINE LOCK engaged for guarded test run")

    try:
        yield prior
    finally:
        if engaged_by_guard:
            if await _ensure_machine_lock(client, False, retries):
                logger.info("[SAFETY] MACHINE LOCK restored to OFF after guarded run")
            else:
                logger.error(
                    "[SAFETY] Failed to restore MACHINE LOCK to OFF; "
                    "machine left locked (safe) — clear it deliberately."
                )
                raise MachineLockError(
                    "Could not restore MACHINE LOCK to OFF; machine left locked."
                )
