# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for machine_lock_guard (fail-closed MACHINE LOCK safety interlock)."""
import pytest

from app.clients._panel_safety import (
    MachineLockError,
    _read_machine_lock,
    machine_lock_guard,
)


class FakePanelClient:
    """Fake telnet client: set_panel_function mutates lock state and
    get_panel_data serves a real C00 K01 line so the parser path is exercised."""

    def __init__(
        self,
        machine_lock: int = 0,
        *,
        fail_writes: bool = False,
        unreadable: bool = False,
        stuck_on: bool = False,
    ):
        self._mlock = machine_lock
        self.fail_writes = fail_writes
        self.unreadable = unreadable
        self.stuck_on = stuck_on
        self.writes: list[bool] = []

    async def set_panel_function(self, function, on, verbose=False):
        assert function == "machine_lock"
        self.writes.append(on)
        if self.fail_writes:
            return False, "32"
        if on:
            self._mlock = 1
        elif not self.stuck_on:
            self._mlock = 0
        return True, "00"

    async def get_panel_data(self, verbose=False):
        if self.unreadable:
            return None
        fields = [2, 6, 0, 0, 0, 0, self._mlock, 0, 0, 0, 0]
        return "K01," + ",".join(str(f) for f in fields) + "\r\n"


@pytest.mark.asyncio
async def test_read_machine_lock_parses_k01():
    assert await _read_machine_lock(FakePanelClient(machine_lock=0)) == 0
    assert await _read_machine_lock(FakePanelClient(machine_lock=1)) == 1


@pytest.mark.asyncio
async def test_read_machine_lock_none_when_unreadable():
    assert await _read_machine_lock(FakePanelClient(unreadable=True)) is None


@pytest.mark.asyncio
async def test_guard_engages_and_restores_prior_off():
    client = FakePanelClient(machine_lock=0)
    ran = []

    async with machine_lock_guard(client, retries=1) as prior:
        assert prior == 0
        # Lock must be verifiably ON before the body runs.
        assert await _read_machine_lock(client) == 1
        ran.append(True)

    assert ran == [True]
    assert client.writes == [True, False]
    assert await _read_machine_lock(client) == 0


@pytest.mark.asyncio
async def test_guard_leaves_preexisting_lock_untouched():
    client = FakePanelClient(machine_lock=1)
    ran = []

    async with machine_lock_guard(client, retries=1) as prior:
        assert prior == 1
        ran.append(True)

    assert ran == [True]
    assert client.writes == []  # never clobbers the operator's lock
    assert await _read_machine_lock(client) == 1


@pytest.mark.asyncio
async def test_guard_fail_closed_when_engage_fails():
    client = FakePanelClient(machine_lock=0, fail_writes=True)
    ran = []

    with pytest.raises(MachineLockError):
        async with machine_lock_guard(client, retries=1):
            ran.append(True)

    assert ran == []  # body never runs
    assert await _read_machine_lock(client) == 0


@pytest.mark.asyncio
async def test_guard_fail_closed_when_state_unreadable():
    client = FakePanelClient(unreadable=True)
    ran = []

    with pytest.raises(MachineLockError):
        async with machine_lock_guard(client, retries=1):
            ran.append(True)

    assert ran == []
    assert client.writes == []


@pytest.mark.asyncio
async def test_guard_restores_even_when_body_raises():
    client = FakePanelClient(machine_lock=0)

    with pytest.raises(RuntimeError, match="boom"):
        async with machine_lock_guard(client, retries=1):
            raise RuntimeError("boom")

    assert client.writes == [True, False]
    assert await _read_machine_lock(client) == 0


@pytest.mark.asyncio
async def test_guard_raises_when_restore_fails_and_leaves_locked():
    client = FakePanelClient(machine_lock=0, stuck_on=True)
    ran = []

    with pytest.raises(MachineLockError, match="left locked"):
        async with machine_lock_guard(client, retries=1):
            ran.append(True)

    assert ran == [True]
    # Safe direction: machine stays locked rather than silently unlocked.
    assert await _read_machine_lock(client) == 1
