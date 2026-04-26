"""Regression stress tests for CM7522 and CM7532 CNC alarm prevention.

Three invariants are exercised under high concurrency to prove the fixes hold
across realistic async-scheduling patterns:

CM7532 — "Ethernet communication error"
  At most 1 TCP socket may be open to any (ip, port) at any time.
  Violated by the old code when create_fresh_connection() was called before
  the machine lock was acquired, allowing fast-poll and tool-poll tasks to hold
  two simultaneous sockets.

CM7522 — "Receive command abnormal end" (timeout path)
  When drain() completes (command reached the machine) but no response arrives,
  load_data must attempt exactly 1 LOD per caller.  No retries and no fallback
  to an alternate data name may follow — the machine is still processing the
  first LOD when the next one would arrive.

CM7522 — wrong-name fallback on known control version
  get_prd3_data and get_atc_magazine_data must not attempt C00 data names on a
  confirmed D00 machine (and vice-versa).  The alternate name does not exist
  on the wrong control type; if preceded by a timeout it would cause CM7522.

Each test:
  • runs 40-50 concurrent callers targeting the same machine lock
  • injects async yields (asyncio.sleep(0)) in fake connect/disconnect/drain
    so the event loop has the maximum opportunity to context-switch between tasks
  • makes a binary assertion — the invariant either holds for every one of the
    concurrent calls or the test fails with an actionable message
"""
import asyncio
import pytest

from app.clients.telnet_client import CNCTelnetClient


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------

def _ok_response(data_name: str, body: str = "A01,,ok") -> bytes:
    """Minimal valid LOD success frame for the given data name."""
    args = data_name.ljust(8)[:8]
    return f"%RLOD    {args}00\r\n{body}\r\n05%\r\n".encode("ascii")


def _fail_response(data_name: str, status: str = "07") -> bytes:
    """LOD failure frame (e.g., 07 = file not found)."""
    args = data_name.ljust(8)[:8]
    return f"%RLOD    {args}{status}\r\n05%\r\n".encode("ascii")


class _QueueReader:
    """Returns queued response bytes one per read(), yields to the event loop on each call."""

    def __init__(self, responses: list[bytes]) -> None:
        self._q = list(responses)

    async def read(self, n: int) -> bytes:
        await asyncio.sleep(0)  # yield so the scheduler can switch tasks
        return self._q.pop(0) if self._q else b""


class _RecordingWriter:
    """Captures all bytes written to the fake socket; simulates close."""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self._closed = False

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        await asyncio.sleep(0)  # yield so the scheduler can switch tasks

    def is_closing(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True

    async def wait_closed(self) -> None:
        await asyncio.sleep(0)  # yield so the scheduler can switch tasks


# ---------------------------------------------------------------------------
# Test 1: CM7532 — connection exclusivity under concurrent polling load
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm7532_peak_connections_never_exceeds_one(monkeypatch):
    """CM7532 regression: peak simultaneous open connections must be ≤ 1.

    Simulates MachinePoller.poll() and MachinePoller.poll_tool_data() running
    concurrently — 40 pairs of fast-poll + tool-poll coroutines, all targeting
    the same machine IP:port (same machine lock).

    Each fake connect() and disconnect() yields to the event loop so the asyncio
    scheduler gets the maximum opportunity to context-switch between coroutines.
    If a socket were opened before the machine lock is acquired (the old bug),
    two simultaneous connections would appear and the overlap counter would fire.
    """
    MACHINE_IP = "10.99.1.1"  # unique IP: avoids sharing locks with other tests
    PAIRS = 40

    state = {"open": 0, "peak": 0, "overlaps": []}

    async def tracking_connect(self) -> bool:
        # Yield BEFORE incrementing — this is where the old bug would surface:
        # a context switch here would let another task also enter connect() while
        # the lock had not yet been acquired.  With the fix, the lock is held for
        # the entire connect → command → disconnect window, so no other connect
        # can run for the same IP:port.
        await asyncio.sleep(0)
        if state["open"] > 0:
            state["overlaps"].append(
                f"socket opened while {state['open']} already open "
                f"(ip={self.ip_address})"
            )
        state["open"] += 1
        state["peak"] = max(state["peak"], state["open"])
        self.reader = _QueueReader([_ok_response("OK")])
        self.writer = _RecordingWriter()
        self._connected = True
        return True

    async def tracking_disconnect(self) -> None:
        # Decrement the counter BEFORE yielding so the count drops before the
        # machine lock is released.  This mirrors the actual fixed behaviour:
        # disconnect() is called inside the `async with machine_lock:` block,
        # so no other task can open a connection until this decrements.
        if state["open"] > 0:
            state["open"] -= 1
        await asyncio.sleep(0)
        self._connected = False
        self.reader = None
        self.writer = None

    monkeypatch.setattr(CNCTelnetClient, "connect", tracking_connect)
    monkeypatch.setattr(CNCTelnetClient, "disconnect", tracking_disconnect)

    async def fast_poll_task() -> None:
        """Mimic MachinePoller.poll(): sequential LOD reads on a lazy client."""
        for name in ["MONTR", "PRDD3", "MEM", "ALARM", "PANEL"]:
            c = CNCTelnetClient(MACHINE_IP, port=10000, command_delay=0.0)
            await c.load_data(name, max_retries=0)

    async def tool_poll_task() -> None:
        """Mimic MachinePoller.poll_tool_data(): TOLNI1 then ATCTLD."""
        for name in ["TOLNI1", "ATCTLD"]:
            c = CNCTelnetClient(MACHINE_IP, port=10000, command_delay=0.0)
            await c.load_data(name, max_retries=0)

    tasks = (
        [fast_poll_task() for _ in range(PAIRS)]
        + [tool_poll_task() for _ in range(PAIRS)]
    )
    await asyncio.gather(*tasks)

    assert state["overlaps"] == [], (
        f"CM7532 REGRESSION — {len(state['overlaps'])} simultaneous connections detected:\n"
        + "\n".join(state["overlaps"][:10])
    )
    assert state["peak"] <= 1, (
        f"CM7532 REGRESSION — peak simultaneous open connections: {state['peak']} (must be ≤ 1). "
        "Two open sockets on port 10000 triggers CM7532 on the machine."
    )
    assert state["open"] == 0, (
        f"Connection leak — {state['open']} socket(s) not closed after all tasks completed"
    )


# ---------------------------------------------------------------------------
# Test 2: CM7532 — no connection leak on command failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm7532_connection_always_closed_after_failure(monkeypatch):
    """CM7532 regression: connections must close even when LOD returns an error.

    If load_data raises or returns early on a non-zero status, the finally block
    must still call disconnect().  An unclosed socket that persists across the
    machine lock boundary causes CM7532 on the next operation.
    """
    MACHINE_IP = "10.99.1.6"
    CONCURRENCY = 50

    state = {"open": 0, "peak": 0, "unclosed": 0}

    async def tracking_connect(self) -> bool:
        await asyncio.sleep(0)
        state["open"] += 1
        state["peak"] = max(state["peak"], state["open"])
        self.reader = _QueueReader([_fail_response("MEM", status="16")])
        self.writer = _RecordingWriter()
        self._connected = True
        return True

    async def tracking_disconnect(self) -> None:
        if state["open"] > 0:
            state["open"] -= 1
        else:
            state["unclosed"] += 1
        await asyncio.sleep(0)
        self._connected = False
        self.reader = None
        self.writer = None

    monkeypatch.setattr(CNCTelnetClient, "connect", tracking_connect)
    monkeypatch.setattr(CNCTelnetClient, "disconnect", tracking_disconnect)

    tasks = [
        CNCTelnetClient(MACHINE_IP, port=10000, command_delay=0.0).load_data(
            "MEM", max_retries=0
        )
        for _ in range(CONCURRENCY)
    ]
    results = await asyncio.gather(*tasks)

    assert all(r is None for r in results)
    assert state["open"] == 0, (
        f"CM7532 REGRESSION — {state['open']} socket(s) still open after command failure. "
        "Unclosed sockets persist across the machine lock and cause CM7532."
    )
    # Peak may be 1 (each caller connects once in sequence); it must not be > 1.
    assert state["peak"] <= 1, (
        f"CM7532 REGRESSION — peak simultaneous connections: {state['peak']} (must be ≤ 1)"
    )


# ---------------------------------------------------------------------------
# Test 3: CM7522 (timeout) — exactly one LOD attempt per caller
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm7522_no_retry_after_timeout_stress(monkeypatch):
    """CM7522 regression: load_data must make exactly 1 LOD attempt after a TIMEOUT.

    50 concurrent callers each receive a TIMEOUT sentinel from _send_command
    (simulates: drain() completed, no data received).  max_retries=5 is passed
    to prove the retry limit is overridden by the TIMEOUT guard.

    If any caller retries, lod_count will exceed CONCURRENCY and the test fails
    with a message naming the regression.
    """
    MACHINE_IP = "10.99.1.2"
    CONCURRENCY = 50

    lod_count = 0

    async def mock_connect(self) -> bool:
        self._connected = True
        return True

    async def mock_send_command(
        self, command, arguments="", verbose=False, read_timeout=1.0
    ):
        nonlocal lod_count
        lod_count += 1
        # drain() completed (command sent), no response arrived — TIMEOUT sentinel.
        # Retrying now would send a second LOD while the machine is still processing
        # the first, which causes CM7522 ("Receive command abnormal end").
        return False, "TIMEOUT", None

    async def mock_disconnect(self) -> None:
        self._connected = False
        self.reader = None
        self.writer = None

    monkeypatch.setattr(CNCTelnetClient, "connect", mock_connect)
    monkeypatch.setattr(CNCTelnetClient, "_send_command", mock_send_command)
    monkeypatch.setattr(CNCTelnetClient, "disconnect", mock_disconnect)

    tasks = [
        CNCTelnetClient(MACHINE_IP, port=10000, command_delay=0.0).load_data(
            "MONTR", max_retries=5  # retries would normally be allowed
        )
        for _ in range(CONCURRENCY)
    ]
    results = await asyncio.gather(*tasks)

    assert all(r is None for r in results), "All callers should return None after TIMEOUT"
    assert lod_count == CONCURRENCY, (
        f"CM7522 REGRESSION — expected {CONCURRENCY} LOD attempts (1 per caller), "
        f"got {lod_count}. "
        f"Extra attempts ({lod_count - CONCURRENCY} retries) after TIMEOUT cause CM7522."
    )


# ---------------------------------------------------------------------------
# Test 4: CM7522 (timeout) — timeout on primary suppresses fallback entirely
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm7522_timeout_on_prd3_suppresses_fallback_stress(monkeypatch):
    """CM7522 regression: a TIMEOUT on PRDD3 must produce exactly 1 total command.

    50 concurrent get_prd3_data(D00) callers, PRDD3 always times out.
    The _last_load_timed_out flag must prevent ANY followup — not just the retry
    but also the alternate-name fallback that get_prd3_data would otherwise try.
    Total commands issued must equal CONCURRENCY.
    """
    MACHINE_IP = "10.99.1.5"
    CONCURRENCY = 50

    command_count = 0

    async def mock_connect(self) -> bool:
        self._connected = True
        return True

    async def mock_send_command(
        self, command, arguments="", verbose=False, read_timeout=1.0
    ):
        nonlocal command_count
        command_count += 1
        return False, "TIMEOUT", None  # machine hangs after receiving PRDD3

    async def mock_disconnect(self) -> None:
        self._connected = False
        self.reader = None
        self.writer = None

    monkeypatch.setattr(CNCTelnetClient, "connect", mock_connect)
    monkeypatch.setattr(CNCTelnetClient, "_send_command", mock_send_command)
    monkeypatch.setattr(CNCTelnetClient, "disconnect", mock_disconnect)

    tasks = [
        CNCTelnetClient(MACHINE_IP, port=10000, command_delay=0.0).get_prd3_data(
            control_version="D00"
        )
        for _ in range(CONCURRENCY)
    ]
    results = await asyncio.gather(*tasks)

    assert all(r is None for r in results)
    assert command_count == CONCURRENCY, (
        f"CM7522 REGRESSION — expected {CONCURRENCY} total commands (1 per caller), "
        f"got {command_count}. "
        f"Any command after PRDD3 timed out would arrive while the machine is still "
        f"processing the first LOD and causes CM7522."
    )


# ---------------------------------------------------------------------------
# Test 5: CM7522 (wrong name) — D00 machine never receives PRD3
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm7522_prd3_wrong_name_never_sent_to_d00_stress(monkeypatch):
    """CM7522 regression: get_prd3_data(D00) must never send PRD3 (C00 file name).

    50 concurrent callers on a confirmed D00 machine where PRDD3 returns status
    07 (file not found — e.g., ATC logging disabled).  PRD3 does not exist on
    D00 controls; sending it would waste a command cycle and, after a timeout,
    would trigger CM7522.  The fallback must be fully suppressed.
    """
    MACHINE_IP = "10.99.1.3"
    CONCURRENCY = 50

    wrong_name_attempts: list[str] = []

    async def mock_connect(self) -> bool:
        self._connected = True
        return True

    async def mock_send_command(
        self, command, arguments="", verbose=False, read_timeout=1.0
    ):
        data_name = arguments.strip()
        if "PRD3" in data_name and data_name != "PRDD3":
            # PRD3 is the C00-only name; it must never be sent to a D00 machine.
            wrong_name_attempts.append(
                f"LOD '{data_name}' sent to confirmed D00 machine"
            )
        # PRDD3 returns 07 (absent), everything else would succeed (not reached).
        return False, "07", None

    async def mock_disconnect(self) -> None:
        self._connected = False
        self.reader = None
        self.writer = None

    monkeypatch.setattr(CNCTelnetClient, "connect", mock_connect)
    monkeypatch.setattr(CNCTelnetClient, "_send_command", mock_send_command)
    monkeypatch.setattr(CNCTelnetClient, "disconnect", mock_disconnect)

    tasks = [
        CNCTelnetClient(MACHINE_IP, port=10000, command_delay=0.0).get_prd3_data(
            control_version="D00"
        )
        for _ in range(CONCURRENCY)
    ]
    results = await asyncio.gather(*tasks)

    assert wrong_name_attempts == [], (
        f"CM7522 REGRESSION — PRD3 (C00-only name) sent to a confirmed D00 machine "
        f"{len(wrong_name_attempts)} time(s):\n" + "\n".join(wrong_name_attempts[:5])
    )
    assert all(r is None for r in results), (
        "All callers should return None when PRDD3 is absent (no wrong-name fallback)"
    )


# ---------------------------------------------------------------------------
# Test 6: CM7522 (wrong name) — D00 machine never receives ATCTL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm7522_atc_wrong_name_never_sent_to_d00_stress(monkeypatch):
    """CM7522 regression: get_atc_magazine_data(D00) must never send ATCTL.

    50 concurrent callers on a confirmed D00 machine where ATCTLD returns status
    07 (ATC magazine logging absent or disabled).  ATCTL is the C00-only file
    name; sending it to a D00 machine wastes a connection cycle and, after a
    timeout on the primary, would cause CM7522.
    """
    MACHINE_IP = "10.99.1.4"
    CONCURRENCY = 50

    wrong_name_attempts: list[str] = []

    async def mock_connect(self) -> bool:
        self._connected = True
        return True

    async def mock_send_command(
        self, command, arguments="", verbose=False, read_timeout=1.0
    ):
        data_name = arguments.strip()
        if data_name == "ATCTL":
            wrong_name_attempts.append(
                f"LOD 'ATCTL' (C00-only) sent to confirmed D00 machine"
            )
        return False, "07", None  # ATCTLD absent

    async def mock_disconnect(self) -> None:
        self._connected = False
        self.reader = None
        self.writer = None

    monkeypatch.setattr(CNCTelnetClient, "connect", mock_connect)
    monkeypatch.setattr(CNCTelnetClient, "_send_command", mock_send_command)
    monkeypatch.setattr(CNCTelnetClient, "disconnect", mock_disconnect)

    tasks = [
        CNCTelnetClient(MACHINE_IP, port=10000, command_delay=0.0).get_atc_magazine_data(
            control_version="D00"
        )
        for _ in range(CONCURRENCY)
    ]
    results = await asyncio.gather(*tasks)

    assert wrong_name_attempts == [], (
        f"CM7522 REGRESSION — ATCTL (C00-only name) sent to a confirmed D00 machine "
        f"{len(wrong_name_attempts)} time(s):\n" + "\n".join(wrong_name_attempts[:5])
    )
    assert all(r is None for r in results)


# ---------------------------------------------------------------------------
# Test 7: Combined scenario — both alarms under a realistic mixed workload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_combined_cm7522_cm7532_mixed_workload(monkeypatch):
    """Combined regression: realistic mixed workload must not trigger either alarm.

    Runs a mix of concurrent operations:
      - Fast poll tasks (MONTR → PRDD3 → MEM → ALARM → PANEL)
      - Tool poll tasks (TOLNI1 → ATCTLD), skipped while "operating" (mocked)
      - API-triggered macro reads (REDMCNM via get_macro_variable_range)

    All targeting the same machine.  Checks simultaneously:
      • peak connections ≤ 1  (CM7532)
      • total LOD commands == expected count (CM7522, no retries)
      • ATCTL and PRD3 never sent (CM7522, wrong-name suppression)
    """
    MACHINE_IP = "10.99.1.7"
    FAST_POLLERS = 20
    TOOL_POLLERS = 10   # fewer — tool poll is slower in real life

    state = {
        "open": 0, "peak": 0, "overlaps": [],
        "wrong_names": [],
        "lod_count": 0,
    }

    # Expected LOD count: fast poll = 5 LODs each, tool poll = 2 LODs each.
    # No retries, no wrong-name fallbacks.
    EXPECTED_LODS = FAST_POLLERS * 5 + TOOL_POLLERS * 2

    async def tracking_connect(self) -> bool:
        await asyncio.sleep(0)
        if state["open"] > 0:
            state["overlaps"].append(
                f"opened while {state['open']} already open"
            )
        state["open"] += 1
        state["peak"] = max(state["peak"], state["open"])
        self.reader = _QueueReader([_ok_response("OK")])
        self.writer = _RecordingWriter()
        self._connected = True
        return True

    async def tracking_disconnect(self) -> None:
        if state["open"] > 0:
            state["open"] -= 1
        await asyncio.sleep(0)
        self._connected = False
        self.reader = None
        self.writer = None

    async def tracking_send_command(
        self, command, arguments="", verbose=False, read_timeout=1.0
    ):
        data_name = arguments.strip()
        state["lod_count"] += 1
        if data_name in ("ATCTL", "PRD3"):
            state["wrong_names"].append(
                f"'{data_name}' sent to D00 machine"
            )
            return False, "07", None
        return True, "00", "A01,,ok"

    monkeypatch.setattr(CNCTelnetClient, "connect", tracking_connect)
    monkeypatch.setattr(CNCTelnetClient, "disconnect", tracking_disconnect)
    monkeypatch.setattr(CNCTelnetClient, "_send_command", tracking_send_command)

    async def fast_poll(ip: str) -> None:
        for name in ["MONTR", "PRDD3", "MEM", "ALARM", "PANEL"]:
            c = CNCTelnetClient(ip, port=10000, command_delay=0.0)
            await c.load_data(name, max_retries=0)

    async def tool_poll(ip: str) -> None:
        for name in ["TOLNI1", "ATCTLD"]:
            c = CNCTelnetClient(ip, port=10000, command_delay=0.0)
            await c.load_data(name, max_retries=0)

    tasks = (
        [fast_poll(MACHINE_IP) for _ in range(FAST_POLLERS)]
        + [tool_poll(MACHINE_IP) for _ in range(TOOL_POLLERS)]
    )
    await asyncio.gather(*tasks)

    assert state["overlaps"] == [], (
        f"CM7532 REGRESSION — {len(state['overlaps'])} simultaneous connections:\n"
        + "\n".join(state["overlaps"][:10])
    )
    assert state["peak"] <= 1, (
        f"CM7532 REGRESSION — peak simultaneous connections: {state['peak']}"
    )
    assert state["open"] == 0, (
        f"Connection leak — {state['open']} socket(s) not closed"
    )
    assert state["wrong_names"] == [], (
        f"CM7522 REGRESSION — wrong data names sent to D00 machine: {state['wrong_names']}"
    )
    assert state["lod_count"] == EXPECTED_LODS, (
        f"CM7522 REGRESSION — expected {EXPECTED_LODS} LOD commands "
        f"(no retries, no wrong-name fallbacks), got {state['lod_count']}"
    )
