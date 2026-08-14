"""Telnet client for communicating with Brother CNC machines via Protocol Type 2.

Brother CNC machines support Protocol Type 2 over TCP/IP port 10000, which provides:
- Direct data file reading (same format as FTP files)
- Write operations (tool offsets, tool life, ATC configuration, macro variables)
- Macro variable access
- More reliable than HTTP/FTP for data reads

Module organisation
-------------------
telnet_client.py      <- this file: CNCTelnetClient + module-level helpers
_telnet_state.py      <- module-level locks, COMPLETION_CODES, _get_machine_lock
_telnet_data_reads.py <- CNCDataReadsMixin  (all LOD / RED read operations)
_telnet_write_ops.py  <- CNCWriteOpsMixin   (tool offset / ATC write operations)
"""
import asyncio
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import logging

from app.clients._telnet_state import (
    _active_clients,
    _active_clients_lock,
    COMPLETION_CODES,
    _get_machine_lock,
)
from app.clients._telnet_data_reads import CNCDataReadsMixin
from app.clients._telnet_write_ops import CNCWriteOpsMixin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

async def create_fresh_connection(ip_address: str, port: int = 10000, timeout: int = 10) -> "CNCTelnetClient":
    """Create and connect a new CNCTelnetClient, raise ConnectionError on failure."""
    client = CNCTelnetClient(ip_address, port, timeout=timeout)
    connected = await client.connect()
    if not connected:
        raise ConnectionError(f"Failed to connect to {ip_address}:{port}")
    return client


async def close_all_connections() -> int:
    """Close all currently-open telnet sockets (called on FastAPI shutdown).

    Returns:
        Number of clients we attempted to close.
    """
    async with _active_clients_lock:
        clients = list(_active_clients)

    for client in clients:
        try:
            await client.disconnect()
        except Exception:
            pass

    return len(clients)


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class CNCTelnetClient(CNCDataReadsMixin, CNCWriteOpsMixin):
    """Async telnet client for Brother CNC machines using Protocol Type 2."""

    def __init__(
        self,
        ip_address: str,
        port: int = 10000,
        timeout: int = 10,
        command_delay: float = 0.2,
    ):
        """
        Initialize telnet client.

        Args:
            ip_address: CNC machine IP address
            port: TCP port (default 10000)
            timeout: Socket timeout in seconds
            command_delay: Minimum delay between commands in seconds (prevents machine overload)
        """
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
        self.command_delay = command_delay
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.last_command_time: float = 0.0
        self._connected = False

        # Optional Telnet proxy override (useful on macOS Docker Desktop where containers
        # can reach CNC HTTP/FTP but not Telnet port 10000 directly).
        proxy_host = (os.getenv("SHATTER_TELNET_PROXY_HOST") or "").strip()
        proxy_port_raw = (os.getenv("SHATTER_TELNET_PROXY_PORT") or "").strip()
        if proxy_host:
            try:
                proxy_port = int(proxy_port_raw) if proxy_port_raw else port
            except ValueError:
                logger.warning(
                    f"Invalid SHATTER_TELNET_PROXY_PORT='{proxy_port_raw}', falling back to {port}"
                )
                proxy_port = port

            self.target_ip_address = ip_address
            self.target_port = port
            self.ip_address = proxy_host
            self.port = proxy_port
            logger.info(
                f"Telnet proxy enabled: {self.target_ip_address}:{self.target_port} via {self.ip_address}:{self.port}"
            )
        else:
            self.target_ip_address = ip_address
            self.target_port = port

    # ------------------------------------------------------------------
    # Protocol helpers (static)
    # ------------------------------------------------------------------

    @staticmethod
    def get_status_description(status_code: str) -> str:
        """Get human-readable description of a completion code."""
        return COMPLETION_CODES.get(status_code, f"Unknown status code: {status_code}")

    @staticmethod
    def is_success(status_code: str) -> bool:
        """Check if status code indicates success."""
        return status_code == "00"

    @staticmethod
    def can_retry(status_code: str) -> bool:
        """Check whether a status code represents a transient failure worth retrying.

        Retryable codes (60-99) are typically temporary state/condition errors.
        Non-retryable codes (01-59) are permanent errors.
        """
        if not status_code:
            return False
        try:
            code_num = int(status_code)
            return 60 <= code_num <= 99
        except ValueError:
            return False

    @staticmethod
    def calculate_checksum(data: str) -> str:
        """Calculate Brother protocol checksum (sum of ASCII values mod 16).

        Returns:
            2-digit checksum string (00-15)
        """
        checksum = sum(ord(c) for c in data) % 16
        return f"{checksum:02d}"

    def _build_command(self, command: str, arguments: str = "", verbose: bool = False) -> bytes:
        """Build a Brother protocol command frame.

        Format: %C[Command(7)][Arguments(8)]  \r\n[Checksum]%\r\n
        """
        cmd_padded = command.ljust(7)[:7]
        args_padded = arguments.ljust(8)[:8]
        cmd_string = f"C{cmd_padded}{args_padded}  \r\n"
        checksum = self.calculate_checksum(cmd_string)
        frame = f"%{cmd_string}{checksum}%\r\n"
        frame_bytes = frame.encode("ascii")

        if verbose:
            logger.error("=== BUILDING COMMAND ===")
            logger.error(f"Command: {command}, Arguments: '{arguments}'")
            logger.error(f"Command padded: '{cmd_padded}' (7 bytes)")
            logger.error(f"Arguments padded: '{args_padded}' (8 bytes)")
            logger.error(f"Command string for checksum: {repr(cmd_string)}")
            logger.error(f"Checksum: '{checksum}'")
            logger.error(f"Complete frame (ASCII): {repr(frame)}")
            logger.error(f"Complete frame (hex): {frame_bytes.hex(' ')}")
            logger.error(f"Complete frame (bytes length): {len(frame_bytes)}")
            logger.error(f"Complete frame (raw): {frame_bytes}")
            logger.error("=== END BUILD ===")

        return frame_bytes

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish (or re-establish) the TCP connection to the machine."""
        if self._connected and self.reader and self.writer:
            try:
                if self.writer.is_closing():
                    logger.debug(f"Connection to {self.ip_address}:{self.port} is closing, reconnecting...")
                    self._connected = False
                    self.reader = None
                    self.writer = None
                else:
                    return True
            except Exception as e:
                logger.debug(f"Connection health check failed for {self.ip_address}:{self.port}: {e}, reconnecting...")
                self._connected = False
                self.reader = None
                self.writer = None

        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip_address, self.port),
                timeout=self.timeout,
            )
            self._connected = True
            self.last_command_time = asyncio.get_event_loop().time()
            async with _active_clients_lock:
                _active_clients.add(self)
            logger.debug(f"Connected to {self.ip_address}:{self.port}")
            return True
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to {self.ip_address}:{self.port}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Connection failed to {self.ip_address}:{self.port}: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Close the connection gracefully."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.debug(f"Error closing connection: {e}")
            finally:
                self.writer = None
                self.reader = None
                self._connected = False
                async with _active_clients_lock:
                    try:
                        _active_clients.discard(self)
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Core send / receive
    # ------------------------------------------------------------------

    async def _send_command(
        self,
        command: str,
        arguments: str = "",
        verbose: bool = False,
        read_timeout: float = 1.0,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send a single-part command and return (success, status_code, data)."""
        if not self._connected or not self.reader or not self.writer:
            logger.error("Not connected")
            return False, None, None

        # Track whether writer.drain() completed so we know if the machine received the
        # command.  If it did, we must NOT retry on timeout -- the machine is processing
        # the command and a second LOD for the same operation will cause CM7522
        # ("Receive command abnormal end") on D00 controls.
        command_sent = False
        try:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self.last_command_time
            if elapsed < self.command_delay:
                await asyncio.sleep(self.command_delay - elapsed)
                current_time = asyncio.get_event_loop().time()

            frame = self._build_command(command, arguments, verbose=verbose)
            if verbose:
                logger.debug(f"[TELNET] Sending {command} to {self.ip_address}: args={repr(arguments)}")
            self.writer.write(frame)
            await self.writer.drain()   # <-- machine has the command from this point on
            command_sent = True
            self.last_command_time = asyncio.get_event_loop().time()

            response = b""
            while True:
                try:
                    chunk = await asyncio.wait_for(self.reader.read(4096), timeout=read_timeout)
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b"%") or response.endswith(b"%\n") or response.endswith(b"%\r\n"):
                        break
                except asyncio.TimeoutError:
                    if response:
                        if verbose:
                            logger.debug(
                                f"[TELNET] Partial response from {self.ip_address} ({len(response)} bytes): {repr(response)}"
                            )
                        break
                    else:
                        logger.warning(f"Socket timeout - no data received for command {command}")
                        if verbose:
                            logger.error(f"Command was: {command}, Arguments: '{arguments}'")
                        # Return a sentinel that tells load_data the command reached the
                        # machine.  Retrying would send a second LOD while the machine
                        # is still processing the first one -- that triggers CM7522.
                        return False, "TIMEOUT", None

            if not response:
                logger.error("No response received")
                return False, "TIMEOUT", None

            response_str = response.decode("ascii", errors="replace")

            if len(response_str) < 19:
                logger.error(
                    f"Response too short: {len(response_str)} bytes, expected at least 19. Response: {repr(response_str[:50])}"
                )
                return False, "TIMEOUT", None

            status_code = response_str[17:19]
            success = status_code == "00"

            if verbose:
                logger.debug(
                    f"[TELNET] {self.ip_address} response: status={status_code}, len={len(response_str)} bytes, header={repr(response_str[:19])}"
                )

            first_newline = response_str.find("\n", 20)
            if first_newline == -1:
                data = None
            else:
                last_percent = response_str.rfind("%")
                if last_percent > first_newline:
                    data = response_str[first_newline + 1 : last_percent].strip()
                else:
                    data = None

            if not success:
                status_desc = self.get_status_description(status_code)
                logger.warning(f"Command failed with status {status_code}: {status_desc}")
                logger.warning(f"Failed command details: {command} {repr(arguments)}")
                logger.warning(f"Frame sent: {repr(frame.decode('ascii', errors='replace'))}")
                logger.warning(f"Frame hex: {frame.hex(' ')}")
            elif verbose:
                logger.info(f"Command succeeded with status {status_code}")
                if data:
                    logger.info(f"Response data length: {len(data)} bytes")

            return success, status_code, data

        except Exception as e:
            if command_sent:
                # Exception occurred after the command reached the machine (e.g. broken
                # pipe while reading the response).  Treat the same as TIMEOUT so the
                # caller knows not to retry.
                logger.error(f"Error reading response for {command}: {e}")
                self._connected = False
                return False, "TIMEOUT", None
            else:
                # Exception before drain() -- machine never received the command.
                logger.error(f"Error sending command {command}: {e}")
                self._connected = False
                return False, None, None

    async def _send_multipart_command(
        self,
        command: str,
        arguments: str = "",
        data_payload: str = "",
        verbose: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send a multi-part command with a separate data payload.

        Used for REDPLCR (PLC range) and REDMCNM (macro range).
        Returns (success, status_code, response_data).
        """
        if not self._connected or not self.reader or not self.writer:
            logger.error("Not connected")
            return False, None, None

        try:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self.last_command_time
            if elapsed < self.command_delay:
                await asyncio.sleep(self.command_delay - elapsed)

            cmd_padded = command.ljust(7)[:7]
            args_padded = arguments.ljust(8)[:8]
            header_line = f"C{cmd_padded}{args_padded}  \r\n"
            full_message = f"{header_line}{data_payload}\n"
            checksum = self.calculate_checksum(full_message)
            frame = f"%{header_line}{data_payload}\n{checksum}%\r\n"
            frame_bytes = frame.encode("ascii")

            if verbose:
                logger.debug(
                    f"[TELNET] Sending multipart {command} to {self.ip_address}: args={repr(arguments)}, data={repr(data_payload)}"
                )

            self.writer.write(frame_bytes)
            await self.writer.drain()
            self.last_command_time = asyncio.get_event_loop().time()

            response = b""
            read_timeout = 1.0

            while True:
                try:
                    chunk = await asyncio.wait_for(self.reader.read(4096), timeout=read_timeout)
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b"%\n"):
                        break
                except asyncio.TimeoutError:
                    if response:
                        break
                    else:
                        logger.error("Socket timeout - no data received")
                        return False, None, None

            if not response:
                logger.error("No response received")
                return False, None, None

            response_str = response.decode("ascii", errors="replace")

            if len(response_str) < 20:
                logger.error(f"Response too short: {response_str}")
                return False, None, None

            status_code = response_str[17:19]
            success = status_code == "00"

            if verbose:
                logger.debug(
                    f"[TELNET] {self.ip_address} multipart response: status={status_code}, len={len(response_str)} bytes"
                )

            first_newline = response_str.find("\n", 20)
            if first_newline == -1:
                data = None
            else:
                last_percent = response_str.rfind("%")
                if last_percent > first_newline:
                    data = response_str[first_newline + 1 : last_percent].strip()
                else:
                    data = None

            if not success:
                status_desc = self.get_status_description(status_code)
                logger.warning(f"Command failed with status {status_code}: {status_desc}")
            elif verbose:
                logger.info(f"Command succeeded with status {status_code}")
                if data:
                    logger.info(f"Response data length: {len(data)} bytes")

            return success, status_code, data

        except Exception as e:
            logger.error(f"Error in multipart command: {e}")
            return False, None, None

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity by sending a LOD MEM command.

        Returns:
            Dict with success, latency_ms, status_code, timestamp keys.
        """
        try:
            start_time = datetime.now()
            connected = await self.connect()
            if not connected:
                return {
                    "success": False,
                    "error": "Failed to establish connection",
                    "timestamp": datetime.now().isoformat(),
                }

            success, status, _ = await self._send_command("LOD", "MEM")
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds() * 1000

            await self.disconnect()

            return {
                "success": success,
                "latency_ms": round(latency, 2),
                "status_code": status,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            await self.disconnect()
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
