"""Seam-level tests for CNCTelnetClient.

Strategy: inject fake reader/writer directly into the client instance after
construction. This avoids opening any real TCP connections while exercising
the full protocol parsing, checksum, retry, and state-machine logic.

The architectural seam tested here is:
    CNCTelnetClient._send_command  ←→  asyncio.StreamReader / StreamWriter

Mocking at this seam lets us test:
- Frame building and checksum calculation (static, no I/O)
- Response parsing: status code extraction, data extraction
- load_data retry behavior without sleeping in tests
- connect() state transitions with monkeypatched open_connection
"""
import asyncio
import pytest

from app.clients.telnet_client import CNCTelnetClient


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_response(command: str, args: str, status: str = "00", data: str = "") -> bytes:
    """Build a minimal valid Brother protocol response frame.

    Frame format:
        %R[command(7)][args(8)][status(2)]\\r\\n
        [data]\\r\\n
        [checksum(2)]%\\r\\n
    """
    cmd_padded = command.ljust(7)[:7]
    args_padded = args.ljust(8)[:8]
    header = f"%R{cmd_padded}{args_padded}{status}\r\n"
    body = f"{data}\r\n" if data else ""
    return f"{header}{body}05%\r\n".encode("ascii")


class _FakeReader:
    """Yields one response chunk then EOF."""

    def __init__(self, response: bytes) -> None:
        self._chunks = [response] if response else []

    async def read(self, n: int) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)
        return b""


class _FakeWriter:
    """Records writes; simulates a healthy, non-closing connection."""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self._closing = False

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        pass

    def is_closing(self) -> bool:
        return self._closing

    def close(self) -> None:
        self._closing = True

    async def wait_closed(self) -> None:
        pass


def _make_connected_client(response: bytes = b"") -> tuple[CNCTelnetClient, _FakeWriter]:
    """Return a client with injected fake transport, already marked connected."""
    client = CNCTelnetClient("10.0.0.1", port=10000, timeout=5, command_delay=0.0)
    writer = _FakeWriter()
    client.reader = _FakeReader(response)  # type: ignore[assignment]
    client.writer = writer  # type: ignore[assignment]
    client._connected = True
    return client, writer


# ---------------------------------------------------------------------------
# Static helpers — no I/O
# ---------------------------------------------------------------------------

def test_is_success_true_for_00():
    assert CNCTelnetClient.is_success("00") is True


def test_is_success_false_for_nonzero():
    assert CNCTelnetClient.is_success("01") is False
    assert CNCTelnetClient.is_success("71") is False


def test_can_retry_true_for_range_60_to_99():
    assert CNCTelnetClient.can_retry("60") is True
    assert CNCTelnetClient.can_retry("99") is True


def test_can_retry_false_below_60():
    assert CNCTelnetClient.can_retry("01") is False
    assert CNCTelnetClient.can_retry("59") is False


def test_can_retry_false_for_empty_string():
    assert CNCTelnetClient.can_retry("") is False


def test_get_status_description_returns_nonempty_string():
    desc = CNCTelnetClient.get_status_description("00")
    assert isinstance(desc, str) and len(desc) > 0


def test_get_status_description_unknown_code():
    desc = CNCTelnetClient.get_status_description("ZZ")
    assert "ZZ" in desc


# ---------------------------------------------------------------------------
# Checksum and frame building — no I/O
# ---------------------------------------------------------------------------

def test_calculate_checksum_matches_modulo_16():
    data = "CLOD    MEM       \r\n"
    expected = f"{sum(ord(c) for c in data) % 16:02d}"
    assert CNCTelnetClient.calculate_checksum(data) == expected


def test_calculate_checksum_empty_string_is_00():
    assert CNCTelnetClient.calculate_checksum("") == "00"


def test_build_command_starts_with_percent_c():
    client = CNCTelnetClient("10.0.0.1")
    assert client._build_command("LOD", "MEM").startswith(b"%C")


def test_build_command_ends_with_percent_crlf():
    client = CNCTelnetClient("10.0.0.1")
    assert client._build_command("LOD", "MEM").endswith(b"%\r\n")


def test_build_command_command_field_padded_to_7():
    """Command is left-justified and padded with spaces to exactly 7 bytes."""
    client = CNCTelnetClient("10.0.0.1")
    frame = client._build_command("LOD", "MEM")
    # Frame layout: %C (2 bytes) [command 7 bytes] [args 8 bytes] ...
    cmd_field = frame[2:9].decode("ascii")
    assert cmd_field == "LOD    "


def test_build_command_args_field_padded_to_8():
    """Args are left-justified and padded with spaces to exactly 8 bytes."""
    client = CNCTelnetClient("10.0.0.1")
    frame = client._build_command("LOD", "MEM")
    args_field = frame[9:17].decode("ascii")
    assert args_field == "MEM     "


# ---------------------------------------------------------------------------
# connect() — monkeypatched open_connection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_reuses_healthy_connection():
    """If already connected and writer is not closing, returns True with no I/O."""
    client, writer = _make_connected_client()
    result = await client.connect()
    assert result is True
    assert writer.written == []  # no new data sent


@pytest.mark.asyncio
async def test_connect_returns_false_on_connection_error(monkeypatch):
    async def _fail(*args, **kwargs):
        raise ConnectionRefusedError("test refused")

    monkeypatch.setattr(asyncio, "open_connection", _fail)
    client = CNCTelnetClient("10.0.0.1", port=10000)
    result = await client.connect()
    assert result is False
    assert client._connected is False


@pytest.mark.asyncio
async def test_connect_returns_false_on_timeout(monkeypatch):
    original_wait_for = asyncio.wait_for

    async def _timeout_wait_for(coro, timeout):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(asyncio, "wait_for", _timeout_wait_for)
    client = CNCTelnetClient("10.0.0.1", port=10000)
    result = await client.connect()
    assert result is False
    assert client._connected is False

    # Restore so other tests' wait_for calls work normally
    monkeypatch.setattr(asyncio, "wait_for", original_wait_for)


# ---------------------------------------------------------------------------
# _send_command — injected fake transport
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_command_returns_success_on_00_status():
    response = _make_response("LOD", "MEM", status="00", data="A01,,")
    client, _ = _make_connected_client(response)
    success, status, _ = await client._send_command("LOD", "MEM")
    assert success is True
    assert status == "00"


@pytest.mark.asyncio
async def test_send_command_data_contains_expected_content():
    response = _make_response("LOD", "MEM", status="00", data="A01,some,data")
    client, _ = _make_connected_client(response)
    _, _, data = await client._send_command("LOD", "MEM")
    assert data is not None
    assert "A01" in data


@pytest.mark.asyncio
async def test_send_command_returns_failure_on_nonzero_status():
    response = _make_response("LOD", "MEM", status="71")
    client, _ = _make_connected_client(response)
    success, status, _ = await client._send_command("LOD", "MEM")
    assert success is False
    assert status == "71"


@pytest.mark.asyncio
async def test_send_command_writes_correct_command_to_transport():
    """_send_command sends a frame that starts with %CLOD."""
    response = _make_response("LOD", "MEM", status="00")
    client, writer = _make_connected_client(response)
    await client._send_command("LOD", "MEM")
    assert len(writer.written) == 1
    assert writer.written[0].startswith(b"%CLOD")


@pytest.mark.asyncio
async def test_send_command_when_not_connected_returns_failure():
    client = CNCTelnetClient("10.0.0.1")
    # _connected is False by default — no reader/writer injected
    success, status, data = await client._send_command("LOD", "MEM")
    assert success is False
    assert status is None
    assert data is None


@pytest.mark.asyncio
async def test_send_command_short_response_returns_failure():
    """Responses shorter than 19 bytes are rejected as malformed."""
    client, _ = _make_connected_client(b"%RSHORT00%\r\n")  # only 12 bytes
    success, _, _ = await client._send_command("LOD", "MEM")
    assert success is False


@pytest.mark.asyncio
async def test_send_command_short_response_returns_timeout_sentinel():
    """Short responses return the TIMEOUT sentinel (command reached machine)."""
    client, _ = _make_connected_client(b"%RSHORT00%\r\n")  # only 12 bytes
    _, status, _ = await client._send_command("LOD", "MEM")
    assert status == "TIMEOUT"


@pytest.mark.asyncio
async def test_send_command_no_data_timeout_returns_timeout_sentinel(monkeypatch):
    """When drain() succeeds but reader times out with no data, status is 'TIMEOUT'.

    This is the key CM7522 prevention test: the machine received the LOD command
    (drain completed), so the caller must NOT retry.  If it retries, the machine
    sees a second LOD while still processing the first and raises CM7522.
    """
    original_wait_for = asyncio.wait_for

    drain_called = False

    class _SlowReader:
        """Simulates a machine that received the command but never responds."""
        async def read(self, n: int) -> bytes:
            raise asyncio.TimeoutError()

    # We need wait_for to propagate TimeoutError from the reader, not from connect.
    # Only replace wait_for after drain has been called.
    class _TrackingWriter(_FakeWriter):
        async def drain(self) -> None:
            nonlocal drain_called
            drain_called = True

    client = CNCTelnetClient("10.0.0.1", port=10000, timeout=5, command_delay=0.0)
    client.reader = _SlowReader()  # type: ignore[assignment]
    client.writer = _TrackingWriter()  # type: ignore[assignment]
    client._connected = True

    success, status, data = await client._send_command("LOD", "MEM", read_timeout=0.001)
    assert drain_called, "drain() must have been called (command was sent)"
    assert success is False
    assert status == "TIMEOUT", (
        "A timeout AFTER drain() must return 'TIMEOUT', not None, so load_data "
        "knows not to retry (which would cause CM7522 on D00 machines)"
    )


@pytest.mark.asyncio
async def test_load_data_does_not_retry_after_command_sent_timeout(monkeypatch):
    """load_data must NOT retry when _send_command returns TIMEOUT.

    If the command reached the machine (drain completed) and we got no response,
    retrying sends a second LOD command while the machine processes the first,
    which causes CM7522 ('Receive command abnormal end') on D00 controls.
    """
    call_count = 0

    original_send = CNCTelnetClient._send_command

    async def _mock_send(self, command, arguments="", verbose=False, read_timeout=1.0):
        nonlocal call_count
        call_count += 1
        return False, "TIMEOUT", None  # simulate: command sent, no response

    monkeypatch.setattr(CNCTelnetClient, "_send_command", _mock_send)

    client, _ = _make_connected_client()
    result = await client.load_data("MEM", max_retries=2)  # retries allowed in principle

    assert result is None, "Should return None when command timed out"
    assert call_count == 1, (
        f"load_data must attempt exactly ONE send on TIMEOUT (got {call_count}). "
        "Retrying after TIMEOUT sends a second LOD to the machine and causes CM7522."
    )


# ---------------------------------------------------------------------------
# load_data — injected fake transport (exercises retry wrapper)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_data_returns_string_on_success():
    response = _make_response("LOD", "MEM", status="00", data="A01,,some_data")
    client, _ = _make_connected_client(response)
    result = await client.load_data("MEM", max_retries=0)
    assert result is not None
    assert "A01" in result


@pytest.mark.asyncio
async def test_load_data_returns_none_on_command_failure():
    response = _make_response("LOD", "MEM", status="71")
    client, _ = _make_connected_client(response)
    result = await client.load_data("MEM", max_retries=0)
    assert result is None


@pytest.mark.asyncio
async def test_load_data_unit_selector_chooses_tolni1_for_inches():
    """get_tool_table_data(units='in') loads TOLNI1."""
    response = _make_response("LOD", "TOLNI1", status="00", data="A01,,")
    client, writer = _make_connected_client(response)
    await client.get_tool_table_data(units="in")
    sent_frame = writer.written[0].decode("ascii")
    assert "TOLNI1" in sent_frame


@pytest.mark.asyncio
async def test_load_data_unit_selector_chooses_tolnm1_for_mm():
    """get_tool_table_data(units='mm') loads TOLNM1."""
    response = _make_response("LOD", "TOLNM1", status="00", data="A01,,")
    client, writer = _make_connected_client(response)
    await client.get_tool_table_data(units="mm")
    sent_frame = writer.written[0].decode("ascii")
    assert "TOLNM1" in sent_frame


# ---------------------------------------------------------------------------
# Multi-response helper for fallback tests
# ---------------------------------------------------------------------------

class _MultiResponseReader:
    """Yields responses in sequence; returns EOF bytes once exhausted."""

    def __init__(self, responses: list[bytes]) -> None:
        self._responses = list(responses)

    async def read(self, n: int) -> bytes:
        if self._responses:
            return self._responses.pop(0)
        return b""


def _make_multi_response_client(responses: list[bytes]) -> tuple[CNCTelnetClient, _FakeWriter]:
    """Return a client with a multi-response fake reader, already marked connected."""
    client = CNCTelnetClient("10.0.0.1", port=10000, timeout=5, command_delay=0.0)
    writer = _FakeWriter()
    client.reader = _MultiResponseReader(responses)  # type: ignore[assignment]
    client.writer = writer  # type: ignore[assignment]
    client._connected = True
    return client, writer


# ---------------------------------------------------------------------------
# get_atc_magazine_data — file name selection by control version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_atc_magazine_d00_requests_atctld():
    """D00 control must load ATCTLD, not ATDTL or ATCTL."""
    response = _make_response("LOD", "ATCTLD", status="00", data="A01,,atc_data")
    client, writer = _make_connected_client(response)
    result = await client.get_atc_magazine_data(control_version="D00")
    sent_frame = writer.written[0].decode("ascii")
    assert "ATCTLD" in sent_frame
    assert result is not None


@pytest.mark.asyncio
async def test_atc_magazine_c00_requests_atctl():
    """C00 control must load ATCTL."""
    response = _make_response("LOD", "ATCTL", status="00", data="A01,,atc_data")
    client, writer = _make_connected_client(response)
    result = await client.get_atc_magazine_data(control_version="C00")
    sent_frame = writer.written[0].decode("ascii")
    assert "ATCTL" in sent_frame
    assert result is not None


@pytest.mark.asyncio
async def test_atc_magazine_d00_falls_back_to_atctl_on_status_07():
    """If ATCTLD returns status 07 (not found), fall back to ATCTL."""
    primary_fail = _make_response("LOD", "ATCTLD", status="07")
    fallback_ok = _make_response("LOD", "ATCTL", status="00", data="A01,,fallback")
    client, writer = _make_multi_response_client([primary_fail, fallback_ok])
    result = await client.get_atc_magazine_data(control_version="D00")
    frames = [f.decode("ascii") for f in writer.written]
    assert any("ATCTLD" in f for f in frames), "Should try ATCTLD first"
    assert any("ATCTL" in f for f in frames), "Should fall back to ATCTL"
    assert result is not None


@pytest.mark.asyncio
async def test_atc_magazine_returns_none_when_both_files_absent():
    """Returns None if both ATCTLD and ATCTL return status 07."""
    fail1 = _make_response("LOD", "ATCTLD", status="07")
    fail2 = _make_response("LOD", "ATCTL", status="07")
    client, _ = _make_multi_response_client([fail1, fail2])
    result = await client.get_atc_magazine_data(control_version="D00")
    assert result is None


# ---------------------------------------------------------------------------
# get_prd3_data — file name selection by control version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prd3_d00_requests_prdd3():
    """D00 control must load PRDD3."""
    response = _make_response("LOD", "PRDD3", status="00", data="A01,,prd_data")
    client, writer = _make_connected_client(response)
    result = await client.get_prd3_data(control_version="D00")
    sent_frame = writer.written[0].decode("ascii")
    assert "PRDD3" in sent_frame
    assert result is not None


@pytest.mark.asyncio
async def test_prd3_c00_requests_prd3():
    """C00 control must load PRD3."""
    response = _make_response("LOD", "PRD3", status="00", data="A01,,prd_data")
    client, writer = _make_connected_client(response)
    result = await client.get_prd3_data(control_version="C00")
    sent_frame = writer.written[0].decode("ascii")
    assert "PRD3" in sent_frame
    assert result is not None


@pytest.mark.asyncio
async def test_prd3_d00_falls_back_to_prd3_on_failure():
    """If PRDD3 is unavailable, falls back to PRD3."""
    primary_fail = _make_response("LOD", "PRDD3", status="07")
    fallback_ok = _make_response("LOD", "PRD3", status="00", data="A01,,fallback")
    client, writer = _make_multi_response_client([primary_fail, fallback_ok])
    result = await client.get_prd3_data(control_version="D00")
    frames = [f.decode("ascii") for f in writer.written]
    assert any("PRDD3" in f for f in frames)
    assert any("PRD3" in f for f in frames)
    assert result is not None
