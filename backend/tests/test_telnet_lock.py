"""Tests for per-machine asyncio lock (replaces Redis distributed lock)."""
import asyncio
import pytest
from app.clients.telnet_client import _get_machine_lock


@pytest.mark.anyio
async def test_same_key_returns_same_lock():
    """Same (ip, port) returns the same asyncio.Lock instance."""
    lock1 = await _get_machine_lock("192.168.1.1", 10000)
    lock2 = await _get_machine_lock("192.168.1.1", 10000)
    assert lock1 is lock2
    assert isinstance(lock1, asyncio.Lock)


@pytest.mark.anyio
async def test_different_keys_return_different_locks():
    """Different (ip, port) return different locks."""
    lock_a = await _get_machine_lock("192.168.1.1", 10000)
    lock_b = await _get_machine_lock("192.168.1.2", 10000)
    lock_c = await _get_machine_lock("192.168.1.1", 10001)
    assert lock_a is not lock_b
    assert lock_a is not lock_c
    assert lock_b is not lock_c


@pytest.mark.anyio
async def test_lock_serializes_concurrent_access():
    """Two coroutines using the same machine lock run one after the other."""
    order = []
    key = ("127.0.0.99", 10000)

    async def task(tag: str):
        machine_lock = await _get_machine_lock(*key)
        async with machine_lock:
            order.append(f"{tag}_enter")
            await asyncio.sleep(0.02)
            order.append(f"{tag}_exit")

    await asyncio.gather(task("A"), task("B"))
    # One task must fully enter and exit before the other enters
    assert order.index("A_enter") < order.index("A_exit") < order.index("B_enter") < order.index("B_exit") or \
           order.index("B_enter") < order.index("B_exit") < order.index("A_enter") < order.index("A_exit")
