"""Telnet client for communicating with Brother CNC machines via Protocol Type 2.

Brother CNC machines support Protocol Type 2 over TCP/IP port 10000, which provides:
- Direct data file reading (same format as FTP files)
- Write operations (tool offsets, tool life, ATC configuration)
- Macro variable access
- More reliable than HTTP/FTP for data reads
"""
import asyncio
import socket
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Per-machine asyncio locks (single-backend deployment)
_machine_locks: Dict[Tuple[str, int], asyncio.Lock] = {}
_locks_lock = asyncio.Lock()

# In-memory control version cache: (ip, port) -> (version_str, expiry_time from loop.time())
_control_version_cache: Dict[Tuple[str, int], Tuple[str, float]] = {}


async def create_fresh_connection(ip_address: str, port: int = 10000, timeout: int = 10) -> 'CNCTelnetClient':
    """
    Create a fresh telnet connection for a machine.

    This creates a fresh connection that will be closed after use.

    Args:
        ip_address: Machine IP address
        port: Telnet port (default 10000)
        timeout: Connection timeout in seconds

    Returns:
        New CNCTelnetClient instance

    Raises:
        ConnectionError: If connection fails
    """
    client = CNCTelnetClient(ip_address, port, timeout=timeout)
    connected = await client.connect()
    if not connected:
        raise ConnectionError(f"Failed to connect to {ip_address}:{port}")
    return client


async def _get_machine_lock(ip_address: str, port: int) -> asyncio.Lock:
    """
    Get per-machine lock for serializing telnet operations.

    Ensures only one telnet operation runs at a time per machine (same ip:port),
    preventing conflicts between polling and writes. Uses in-process asyncio.Lock.
    """
    key = (ip_address, port)
    async with _locks_lock:
        if key not in _machine_locks:
            _machine_locks[key] = asyncio.Lock()
        return _machine_locks[key]


# Completion Code Meanings (from Section 5.5.9.2 of Brother Protocol)
COMPLETION_CODES = {
    "00": "Normally ended",
    "01": "Invalid data is received",
    "02": "Illegal slave command header",
    "04": "Illegal slave command check sum",
    "05": "Currently in editing or operation mode, or folder in use - cannot delete",
    "06": "Editing error occurred during file operation",
    "07": "The specified data does not exist",
    "08": "Slave command data name is incorrect",
    "09": "The specified data cannot be saved or deleted",
    "10": "Data protection enabled",
    "11": "Remote operation not permitted",
    "13": "Data item is not within allowed range or item count doesn't match",
    "14": "Data version error",
    "15": "During special startup",
    "16": "Cannot read the specified data",
    "17": "Output of drawing data was attempted during drawing",
    "18": "The folder already exists or cannot be deleted",
    "19": "Data size designation is abnormal",
    "20": "Binary data storage error",
    "21": "Auto notification function reserve 1",
    "22": "Auto notification function reserve 2",
    "23": "Access is restricted",
    "30": "Program/data/tool number invalid or out of range",
    "31": "Operation mode conflict or protection enabled",
    "32": "Cannot change during operation or editing",
    "33": "Signal cannot be turned off",
    "34": "Magazine item change without tool number",
    "35": "Pot adjacent to specified pot contains large tool",
    "36": "ATC tool change attempted during memory operation",
    "37": "ATC tool change attempted during MDI operation",
    "38": "Unspecified error during ATC tool change",
    "39": "Unregistered tool registration attempted",
    "40": "Conflict due to communication using other port",
    "41": "Check sum error in specified data",
    "42": "Parity error in specified data",
    "43": "Data too large to store",
    "44": "Cannot store - programs #8000-#8999 are write-protected",
    "45": "Machine unit system is different",
    "46": "Tool unable to change group/main tool/type/color in ATC",
    "60": "Mode change not permitted",
    "61": "Mode change not permitted signal is on",
    "62": "MDI operation mode",
    "63": "During tool change",
    "64": "During automatic centering",
    "65": "During automatic workpiece measurement",
    "66": "Automatic door operation not possible",
    "67": "Operation not possible",
    "68": "No program",
    "69": "Not in memory operation mode",
    "70": "The outer door is open",
    "71": "The door is open",
    "72": "The side door is open",
    "73": "Resetting",
    "74": "Servo control is on",
    "75": "[FEED HOLD] switch is held down",
    "76": "Zero return was not conducted",
    "77": "Restarting program or sequence search in progress",
    "78": "Pallet position error",
    "79": "Performing tool breakage detection",
    "80": "Program number error or different from pallet program",
    "81": "Outer pallet A and B-axes operating",
    "82": "No quick table",
    "83": "[PALLET] key is set to [OFF]",
    "84": "Workpiece counter end",
    "85": "Executing external output command",
    "86": "Memory operation mode",
    "87": "External input not available",
    "88": "In handle mode",
    "89": "XY-axes lock signal is on",
    "90": "Z-axis lock signal is on",
    "91": "*-axis lock signal is on",
    "92": "Pot is not at the top end",
    "93": "Zero return command error",
    "94": "Indexing not permitted signal is on",
    "95": "Pallet start reversed",
    "96": "Outer pallet operating",
    "97": "Communicating",
    "98": "NC or conversation mode is not selected correctly",
    "99": "Reservation",
}


class CNCTelnetClient:
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
        # Control version is cached in Redis (shared across all connections to same machine)

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
        """
        Check if an operation can be retried based on status code.
        
        Retryable codes (60-99) are typically temporary state/condition errors.
        Non-retryable codes (01-59) are permanent errors.
        """
        if not status_code:
            return False
        try:
            code_num = int(status_code)
            # Codes 60-99 are typically temporary/state conditions that can be retried
            return 60 <= code_num <= 99
        except ValueError:
            return False

    @staticmethod
    def calculate_checksum(data: str) -> str:
        """
        Calculate Brother protocol checksum.

        Sum ASCII values of all characters and take modulo 16.

        Args:
            data: String to checksum

        Returns:
            2-digit checksum string (00-15)
        """
        checksum = sum(ord(c) for c in data) % 16
        return f"{checksum:02d}"

    def _build_command(self, command: str, arguments: str = "", verbose: bool = False) -> bytes:
        """
        Build a Brother protocol command frame per schema 5.5.9.1.
        
        Header (19 bytes): % i1 c1-c3 f1-f4 s1-s8 r1-r2
        - %: Start symbol (1 byte)
        - i1: Identifier 'C' for command (1 byte)
        - c1-c3: Command type (3 bytes) - first 3 chars of command
        - f1-f4: Function (4 bytes) - next 4 chars of command (padded)
        - s1-s8: Message/arguments (8 bytes) - padded
        - r1-r2: Completion code "00" for command (2 bytes)
        
        Footer: LF + checksum (2 digits) + %
        Checksum: calculated from % in header to character before LF in footer
        """
        # Pad command to 7 chars, then split into c1-c3 (3) and f1-f4 (4)
        # f1-f4 should be left-justified (e.g., "LOD " -> "LOD " with space, "MAGC" -> "MAGC")
        # Special handling for CHGMAG: don't pad with space, use null or different padding
        if command == "CHGMAG":
            cmd_padded = command + "\x00\x00"  # Pad with null bytes instead of space
        else:
            cmd_padded = command.ljust(7)[:7]
        cmd_type = cmd_padded[:3].ljust(3)[:3]  # c1-c3 (3 bytes), left-justified
        function = cmd_padded[3:7].ljust(4)[:4]  # f1-f4 (4 bytes), left-justified
        
        # Pad arguments to 8 bytes (s1-s8)
        args_padded = arguments.ljust(8)[:8]
        
        # Build header: % + C + c1-c3 + f1-f4 + s1-s8 + r1-r2
        # r1-r2 is completion code "00" for commands (not the checksum)
        header = f"%C{cmd_type}{function}{args_padded}00"
        
        # Calculate checksum on header data (from % to before LF in footer)
        # Per schema: "from % in the header to the character before LF in the footer"
        # This means: calculate on the entire header (including the %)
        checksum = self.calculate_checksum(header)  # Already returns formatted string "00"-"15"
        
        # Build footer: LF + checksum + %
        # In ASCII, LF is CR+LF (\r\n), so footer is "\r\n{checksum}%"
        footer = f"\r\n{checksum}%"
        
        # Complete frame: header + footer
        frame = f"{header}{footer}"
        frame_bytes = frame.encode('ascii')

        if verbose:
            logger.error(f"=== BUILDING COMMAND ===")
            logger.error(f"Command: {command}, Arguments: '{arguments}'")
            logger.error(f"Command padded: '{cmd_padded}' (7 bytes)")
            logger.error(f"Header breakdown: % + C + '{cmd_type}' (c1-c3) + '{function}' (f1-f4) + '{args_padded}' (s1-s8) + '00' (r1-r2, completion code)")
            logger.error(f"Checksum: '{checksum}' (calculated from header, goes in footer)")
            logger.error(f"Checksum calculated from: C + '{cmd_type}' + '{function}' + '{args_padded}'")
            logger.error(f"Header: '{header}' (length: {len(header)} bytes, should be 19)")
            logger.error(f"Complete frame (ASCII): {repr(frame)}")
            logger.error(f"Complete frame (hex): {frame_bytes.hex(' ')}")
            logger.error(f"Complete frame (bytes length): {len(frame_bytes)}")
            logger.error(f"Complete frame (raw): {frame_bytes}")
            logger.error(f"=== END BUILD ===")

        return frame_bytes

    async def connect(self) -> bool:
        """
        Establish TCP connection to the machine.
        
        Supports persistent connections - if already connected and healthy, returns True.
        Automatically reconnects if connection is lost.
        """
        # Check if already connected and healthy
        if self._connected and self.reader and self.writer:
            try:
                # Check if writer is closing or closed
                if self.writer.is_closing():
                    logger.debug(f"Connection to {self.ip_address}:{self.port} is closing, reconnecting...")
                    self._connected = False
                    self.reader = None
                    self.writer = None
                else:
                    # Connection appears healthy, reuse it
                    return True
            except Exception as e:
                logger.debug(f"Connection health check failed for {self.ip_address}:{self.port}: {e}, reconnecting...")
                self._connected = False
                self.reader = None
                self.writer = None
        
        # Connect (new connection or reconnection)
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip_address, self.port),
                timeout=self.timeout
            )
            self._connected = True
            self.last_command_time = asyncio.get_event_loop().time()
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

    async def _send_command(
        self, command: str, arguments: str = "", verbose: bool = False, read_timeout: float = 1.0
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Send a command and receive response.

        Args:
            command: Command name
            arguments: Command arguments
            verbose: If True, log command details

        Returns:
            Tuple of (success, status_code, response_data)
            success: True if status code is "00"
            status_code: Response status code (2 chars)
            response_data: Response data (everything between header and footer)
        """
        if not self._connected or not self.reader or not self.writer:
            logger.error("Not connected")
            return False, None, None

        try:
            # Enforce minimum delay between commands (in-process rate limit)
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self.last_command_time
            if elapsed < self.command_delay:
                await asyncio.sleep(self.command_delay - elapsed)
                current_time = asyncio.get_event_loop().time()

            # Build and send frame
            frame = self._build_command(command, arguments, verbose=verbose)
            if verbose:
                logger.debug(f"[TELNET] Sending {command} to {self.ip_address}: args={repr(arguments)}")
            self.writer.write(frame)
            await self.writer.drain()
            current_time = asyncio.get_event_loop().time()
            self.last_command_time = current_time

            # Receive response with robust reading to handle complete frames
            response = b''
            # read_timeout is now a parameter (default 1.0, can be increased for write operations)

            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=read_timeout
                    )
                    if not chunk:
                        break
                    response += chunk
                    # Check if we have a complete frame (ends with %\n)
                    if response.endswith(b'%\n'):
                        break
                except asyncio.TimeoutError:
                    # Timeout on individual read, but we might have partial data
                    if response:
                        # Only log partial responses if verbose - these are often normal for large data
                        if verbose:
                            logger.debug(f"[TELNET] Partial response from {self.ip_address} ({len(response)} bytes): {repr(response)}")
                        break
                    else:
                        # Socket timeout with no data is an error - always log
                        logger.warning(f"Socket timeout - no data received for command {command}")
                        if verbose:
                            logger.error(f"Command was: {command}, Arguments: '{arguments}'")
                        return False, None, None

            if not response:
                logger.error("No response received")
                return False, None, None

            # Parse response
            response_str = response.decode('ascii', errors='replace')

            # Extract status code and data
            # Response header format (19 bytes): %R[Command(7)][Arguments(8)][StatusCode(2)]
            # Per schema: Header is 19 bytes, same as command but with 'R' instead of 'C'
            # Format: %R c1-c3 f1-f4 s1-s8 r1-r2 (where r1-r2 is status code)
            if len(response_str) < 19:
                logger.error(f"Response too short: {len(response_str)} bytes, expected at least 19. Response: {repr(response_str[:50])}")
                return False, None, None

            # Response header: %R[cmd_type(3)][function(4)][args(8)][status(2)] = 19 bytes
            # Status code is in r1-r2 position (bytes 17-18, 0-indexed)
            status_code = response_str[17:19]
            success = status_code == "00"
            
            if verbose:
                logger.debug(f"[TELNET] {self.ip_address} response: status={status_code}, len={len(response_str)} bytes, header={repr(response_str[:19])}")

            # Extract data between header and footer
            # Find first \n after header
            first_newline = response_str.find('\n', 20)
            if first_newline == -1:
                data = None
            else:
                # Find last % before end
                last_percent = response_str.rfind('%')
                if last_percent > first_newline:
                    data = response_str[first_newline + 1:last_percent].strip()
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
            logger.error(f"Error sending command: {e}")
            self._connected = False
            return False, None, None

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to CNC machine.

        Returns:
            Dict with connection test results
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

            # Try a simple command to verify connection works (MEM is more reliable than DIR)
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

    async def load_data(self, data_name: str, verbose: bool = False, max_retries: int = 2) -> Optional[str]:
        """
        Load arbitrary data by name using LOD command.
        
        Includes retry logic for transient connection failures.

        Args:
            data_name: Name of data to load (e.g., "MEM", "TOLNI1", "POSNI1", "ATCTL", "DIR")
            verbose: If True, log command details
            max_retries: Maximum number of retry attempts (default: 2, so 3 total attempts)

        Returns:
            Data content as string, or None on failure
        """
        for attempt in range(max_retries + 1):
            try:
                # Ensure connection (will reconnect if needed)
                if not self._connected:
                    connected = await self.connect()
                    if not connected:
                        if attempt < max_retries:
                            wait_time = 0.5 * (attempt + 1)  # 0.5s, 1s, 1.5s
                            logger.warning(f"Telnet connection failed for '{data_name}', retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                            await asyncio.sleep(wait_time)
                            continue
                        return None

                success, status, data = await self._send_command("LOD", data_name, verbose=verbose)
                if success:
                    return data
                else:
                    # Check if it's a transient error that might benefit from retry
                    # Status codes like "40" (conflict due to communication using other port) might be retryable
                    if status == "40" and attempt < max_retries:
                        wait_time = 0.5 * (attempt + 1)
                        logger.warning(f"Failed to load '{data_name}': status {status} (communication conflict), retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        # Mark connection as bad to force reconnection on next attempt
                        self._connected = False
                        continue
                    else:
                        logger.warning(f"Failed to load data '{data_name}': status {status}")
                        return None
            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                if attempt < max_retries:
                    wait_time = 0.5 * (attempt + 1)
                    logger.warning(f"Connection error loading '{data_name}': {e}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    # Mark connection as bad to force reconnection on next attempt
                    self._connected = False
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error loading data '{data_name}' after {max_retries + 1} attempts: {e}")
                    return None
            except Exception as e:
                # Non-retryable errors (parsing, etc.) - fail immediately
                logger.error(f"Error loading data '{data_name}': {e}")
                return None
        
        return None

    # Convenience methods for common data files
    async def get_memory_data(self, verbose: bool = False) -> Optional[str]:
        """Get memory/program information from MEM."""
        return await self.load_data("MEM", verbose=verbose)

    async def get_tool_table_data(self, units: str = 'in', verbose: bool = False) -> Optional[str]:
        """
        Get tool table data from TOLNI1 (inches) or TOLNM1 (millimeters).
        
        Args:
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
            verbose: If True, log command details
            
        Returns:
            Tool table data as string, or None on failure
        """
        data_name = "TOLNI1" if units == 'in' else "TOLNM1"
        return await self.load_data(data_name, verbose=verbose)

    async def get_position_data(self, units: str = 'in', verbose: bool = False) -> Optional[str]:
        """
        Get position/work offsets from POSNI1 (inches) or POSNM1 (millimeters).
        
        Args:
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
            verbose: If True, log command details
            
        Returns:
            Position data as string, or None on failure
        """
        data_name = "POSNI1" if units == 'in' else "POSNM1"
        return await self.load_data(data_name, verbose=verbose)

    async def get_monitor_data(self, verbose: bool = False) -> Optional[str]:
        """
        Get MONTR (Machine Monitor) data from CNC machine via Telnet.

        Args:
            verbose: If True, log command details

        Returns:
            Raw MONTR data as string, or None on failure
        """
        return await self.load_data("MONTR", verbose=verbose)

    async def get_alarm_data(self, verbose: bool = False) -> Optional[str]:
        """
        Get ALARM (Current Alarm) data from CNC machine via Telnet.

        Args:
            verbose: If True, log command details

        Returns:
            Raw ALARM data as string, or None on failure
        """
        return await self.load_data("ALARM", verbose=verbose)

    async def get_panel_data(self, verbose: bool = False) -> Optional[str]:
        """
        Get PANEL (Operation Panel Data) data from CNC machine via Telnet.

        Args:
            verbose: If True, log command details

        Returns:
            Raw PANEL data as string, or None on failure
        """
        return await self.load_data("PANEL", verbose=verbose)

    async def get_prd3_data(self, control_version: Optional[str] = None, verbose: bool = False) -> Optional[str]:
        """
        Get PRD3/PRDD3 (Production data 3 - Status history) data via Telnet.

        Args:
            control_version: Control version ('C00' or 'D00'). If None, uses detect_control_type().
            verbose: If True, enable verbose logging

        Returns:
            PRD3/PRDD3 data as string, or None if failed
        """
        # Determine data name based on control version
        if control_version is None:
            control_version = await self.detect_control_type()
        
        data_name = "PRDD3" if control_version == "D00" else "PRD3"
        return await self.load_data(data_name, verbose=verbose)

    async def get_atc_magazine_data(self, control_version: Optional[str] = None, verbose: bool = False) -> Optional[str]:
        """
        Get ATC magazine configuration from ATCTL (C00) or ATCTLD (D00).
        
        Args:
            control_version: Control version ('C00' or 'D00'). If None, auto-detects.
            verbose: If True, log command details
            
        Returns:
            ATC magazine data as string, or None on failure
        """
        # If control_version not provided, detect it first (uses Redis cache)
        if control_version is None:
            control_version = await self.detect_control_type(verbose=False)  # Don't spam logs for detection
            if verbose and control_version:
                logger.info(f"Auto-detected control version: {control_version}")
        
        # D00 uses ATCTLD, C00 uses ATCTL
        if control_version == "D00":
            data_name = "ATCTLD"
        elif control_version == "C00":
            data_name = "ATCTL"
        else:
            # Detection failed - try both (D00 first, then C00)
            if verbose:
                logger.warning("Control version detection failed, trying ATCTLD first, then ATCTL")
            data = await self.load_data("ATCTLD", verbose=verbose)
            if data:
                return data
            data_name = "ATCTL"
        
        return await self.load_data(data_name, verbose=verbose)

    async def _get_directory_listing_internal(self, verbose: bool = False) -> Optional[str]:
        """
        Internal method to get directory listing without acquiring lock.
        Used when already within a lock context.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return None

        try:
            # DRQALL - Request directory of all data
            # Command: DRQALL (no arguments needed)
            success, status, data = await self._send_command("DRQALL", "", verbose=verbose)
            if success:
                return data
            else:
                logger.warning(f"Failed to get directory listing: status {status}")
                return None
        except Exception as e:
            logger.error(f"Error getting directory listing: {e}")
            return None

    async def get_directory_listing(self, verbose: bool = False) -> Optional[str]:
        """
        Get directory listing using DRQALL command.
        
        Note: This replaces the invalid LOD DIR command. The protocol uses DRQALL
        to request directory of all data in the current folder.
        
        Response format: Each entry is 18 characters (8-byte data name + 10-byte size),
        all concatenated together without separators.
        
        Args:
            verbose: If True, log command details
            
        Returns:
            Directory listing as string (raw format), or None on failure
        """
        return await self._get_directory_listing_internal(verbose=verbose)

    async def parse_directory_listing(
        self, directory_data: str, control_type: Optional[str] = None
    ) -> Optional[list]:
        """
        Parse DRQALL directory listing response into a list of entries.
        
        Response format depends on control type:
        - C00 control (old type): 11 bytes per entry (8-byte name + 3-byte size in blocks)
        - D00 control (new type): 18 bytes per entry (8-byte name + 10-byte size in bytes)
        
        If control_type is not provided, attempts to auto-detect format.
        
        Args:
            directory_data: Raw directory data from get_directory_listing()
            control_type: "C00" or "D00" to force format. If None, auto-detects.
            
        Returns:
            List of dicts with 'name' and 'size' keys, or None on failure
        """
        if not directory_data:
            return None
        
        entries = []
        # Remove any newlines/whitespace and parse as concatenated entries
        data = directory_data.replace('\n', '').replace('\r', '').strip()
        
        if not data:
            return None
        
        # Determine format based on control type or auto-detect
        if control_type == "D00":
            # D00 control: 18 bytes per entry (8-byte name + 10-byte size)
            entry_length = 18
            size_start = 8
            size_length = 10
            size_in_bytes = True
        elif control_type == "C00":
            # C00 control: 11 bytes per entry (8-byte name + 3-byte size in blocks)
            entry_length = 11
            size_start = 8
            size_length = 3
            size_in_bytes = False  # Size is in blocks (1 block = 128 bytes)
        else:
            # Auto-detect: Try to determine format from data length
            # If data length is divisible by 18, likely D00 format
            # If data length is divisible by 11, likely C00 format
            # Prefer 11-byte format if both are possible (backward compatibility)
            if len(data) % 11 == 0:
                entry_length = 11
                size_start = 8
                size_length = 3
                size_in_bytes = False
                # Removed verbose logging - too noisy for websocket polling
            elif len(data) % 18 == 0:
                entry_length = 18
                size_start = 8
                size_length = 10
                size_in_bytes = True
                # Removed verbose logging - too noisy for websocket polling
            else:
                # Try both formats and see which one produces valid entries
                # Try C00 format first (more common)
                c00_entries = self._parse_directory_format(data, 11, 8, 3, False)
                d00_entries = self._parse_directory_format(data, 18, 8, 10, True)
                
                # Use format that produces more valid entries
                if len(c00_entries) >= len(d00_entries) and c00_entries:
                    entry_length = 11
                    size_start = 8
                    size_length = 3
                    size_in_bytes = False
                    # Removed verbose logging - too noisy for websocket polling
                elif d00_entries:
                    entry_length = 18
                    size_start = 8
                    size_length = 10
                    size_in_bytes = True
                    # Removed verbose logging - too noisy for websocket polling
                else:
                    logger.error(f"Could not determine directory listing format. Data length: {len(data)}")
                    return None
        
        # Parse entries
        i = 0
        while i + entry_length <= len(data):
            entry = data[i:i+entry_length]
            # Extract name (first 8 chars, right-trimmed)
            name = entry[0:8].rstrip()
            # Extract size
            size_str = entry[size_start:size_start + size_length].strip()
            
            # Only add if name is not empty
            if name and not name.isspace():
                try:
                    size_int = int(size_str) if size_str else 0
                    # Convert blocks to bytes for C00 format
                    if not size_in_bytes:
                        size_int = size_int * 128  # 1 block = 128 bytes
                    entries.append({
                        'name': name,
                        'size': size_int,
                        'size_str': size_str,
                        'size_in_bytes': size_in_bytes
                    })
                except ValueError:
                    # If size can't be parsed, still include the entry with size 0
                    entries.append({
                        'name': name,
                        'size': 0,
                        'size_str': size_str,
                        'size_in_bytes': size_in_bytes
                    })
            i += entry_length
        
        return entries if entries else None
    
    def _parse_directory_format(
        self, data: str, entry_length: int, size_start: int, size_length: int, size_in_bytes: bool
    ) -> list:
        """
        Helper method to parse directory listing in a specific format.
        
        Returns list of entries parsed in the specified format.
        """
        entries = []
        i = 0
        while i + entry_length <= len(data):
            entry = data[i:i+entry_length]
            name = entry[0:8].rstrip()
            size_str = entry[size_start:size_start + size_length].strip()
            
            if name and not name.isspace():
                try:
                    size_int = int(size_str) if size_str else 0
                    if not size_in_bytes:
                        size_int = size_int * 128
                    entries.append({
                        'name': name,
                        'size': size_int,
                        'size_str': size_str
                    })
                except ValueError:
                    pass
            i += entry_length
        return entries

    async def detect_control_type(self, verbose: bool = False) -> Optional[str]:
        """
        Detect machine control type (C00 or D00) by checking directory listing.
        
        This method solves the catch-22 problem by:
        1. Parsing the directory listing in BOTH formats (C00 and D00)
        2. Checking which format produces control-type indicator files
        3. Using the format that finds matching indicators with highest confidence
        
        Detection method (checks multiple file patterns for higher confidence):
        - C00 control indicators:
          * PRDC# files (e.g., PRDC1, PRDC2, PRDC89)
          * SYSC# files (e.g., SYSC89, SYSC94, SYSC99)
        - D00 control indicators:
          * PRDD# files (e.g., PRDD1, PRDD2, PRDD89)
          * SYSD# files (e.g., SYSD89, SYSD94, SYSD99)
        
        Confidence levels:
        - High: 2+ matching indicators found in correct format
        - Medium: 1 matching indicator found in correct format
        - Low: Fallback to format with more valid entries
        
        Args:
            verbose: If True, log detection details including all found indicators
            
        Returns:
            "C00" or "D00" if detected, None if uncertain
        """
        loop = asyncio.get_event_loop()
        now = loop.time()
        cache_key = (self.ip_address, self.port)
        if cache_key in _control_version_cache:
            version, expiry = _control_version_cache[cache_key]
            if expiry > now:
                if verbose:
                    logger.debug(f"Control version from cache: {version}")
                return version

        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            # Check cache again after acquiring lock
            if cache_key in _control_version_cache:
                version, expiry = _control_version_cache[cache_key]
                if expiry > now:
                    if verbose:
                        logger.debug(f"Control version from cache (after lock): {version}")
                    return version
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                # Get directory listing (use internal version since we're already within lock)
                directory_data = await self._get_directory_listing_internal(verbose=verbose)
                if not directory_data:
                    logger.warning("Failed to get directory listing for control type detection")
                    return None

                # Parse directory listing in BOTH formats to solve the catch-22
                # We don't know the format yet, so try both
                entries_c00 = await self.parse_directory_listing(directory_data, control_type="C00")
                entries_d00 = await self.parse_directory_listing(directory_data, control_type="D00")
                
                if not entries_c00 and not entries_d00:
                    logger.warning("No entries found in directory listing with either format")
                    return None

                # Check for multiple file patterns to increase confidence
                import re
                
                # C00 control indicators
                prdc_pattern = re.compile(r'^PRDC\d+$')  # PRDC1, PRDC2, PRDC89, etc.
                sysc_pattern = re.compile(r'^SYSC\d+$')  # SYSC89, SYSC94, SYSC99, etc.
                
                # D00 control indicators
                prdd_pattern = re.compile(r'^PRDD\d+$')  # PRDD1, PRDD2, PRDD89, etc.
                sysd_pattern = re.compile(r'^SYSD\d+$')  # SYSD89, SYSD94, SYSD99, etc.
                
                # Count indicators found in each format
                c00_indicators_in_c00_format = []
                d00_indicators_in_c00_format = []
                c00_indicators_in_d00_format = []
                d00_indicators_in_d00_format = []
                
                # Check C00 format results
                if entries_c00:
                    for entry in entries_c00:
                        name = entry.get('name', '')
                        if prdc_pattern.match(name):
                            c00_indicators_in_c00_format.append(name)
                            if verbose:
                                logger.info(f"Found C00 indicator (PRDC) in C00 format: {name}")
                        elif sysc_pattern.match(name):
                            c00_indicators_in_c00_format.append(name)
                            if verbose:
                                logger.info(f"Found C00 indicator (SYSC) in C00 format: {name}")
                        elif prdd_pattern.match(name):
                            d00_indicators_in_c00_format.append(name)
                            if verbose:
                                logger.info(f"Found D00 indicator (PRDD) in C00 format: {name}")
                        elif sysd_pattern.match(name):
                            d00_indicators_in_c00_format.append(name)
                            if verbose:
                                logger.info(f"Found D00 indicator (SYSD) in C00 format: {name}")
                
                # Check D00 format results
                if entries_d00:
                    for entry in entries_d00:
                        name = entry.get('name', '')
                        if prdc_pattern.match(name):
                            c00_indicators_in_d00_format.append(name)
                            if verbose:
                                logger.info(f"Found C00 indicator (PRDC) in D00 format: {name}")
                        elif sysc_pattern.match(name):
                            c00_indicators_in_d00_format.append(name)
                            if verbose:
                                logger.info(f"Found C00 indicator (SYSC) in D00 format: {name}")
                        elif prdd_pattern.match(name):
                            d00_indicators_in_d00_format.append(name)
                            if verbose:
                                logger.info(f"Found D00 indicator (PRDD) in D00 format: {name}")
                        elif sysd_pattern.match(name):
                            d00_indicators_in_d00_format.append(name)
                            if verbose:
                                logger.info(f"Found D00 indicator (SYSD) in D00 format: {name}")
                
                # Count indicators
                c00_count_in_c00_format = len(c00_indicators_in_c00_format)
                d00_count_in_c00_format = len(d00_indicators_in_c00_format)
                c00_count_in_d00_format = len(c00_indicators_in_d00_format)
                d00_count_in_d00_format = len(d00_indicators_in_d00_format)
                
                if verbose:
                    logger.info(f"C00 indicators in C00 format: {c00_count_in_c00_format} ({c00_indicators_in_c00_format})")
                    logger.info(f"D00 indicators in C00 format: {d00_count_in_c00_format} ({d00_indicators_in_c00_format})")
                    logger.info(f"C00 indicators in D00 format: {c00_count_in_d00_format} ({c00_indicators_in_d00_format})")
                    logger.info(f"D00 indicators in D00 format: {d00_count_in_d00_format} ({d00_indicators_in_d00_format})")

                # Determine control type based on indicator counts
                # Higher confidence when multiple indicators match in the correct format
                
                # Determine detected version and cache it
                detected_version = None
                
                # Best case: C00 format finds C00 indicators, no D00 indicators
                if c00_count_in_c00_format > 0 and d00_count_in_c00_format == 0:
                    confidence = "high" if c00_count_in_c00_format >= 2 else "medium"
                    if verbose:
                        logger.info(f"Control type detected: C00 (confidence: {confidence}, {c00_count_in_c00_format} indicators in C00 format)")
                    detected_version = "C00"
                
                # Best case: D00 format finds D00 indicators, no C00 indicators
                elif d00_count_in_d00_format > 0 and c00_count_in_d00_format == 0:
                    confidence = "high" if d00_count_in_d00_format >= 2 else "medium"
                    if verbose:
                        logger.info(f"Control type detected: D00 (confidence: {confidence}, {d00_count_in_d00_format} indicators in D00 format)")
                    detected_version = "D00"
                
                # Compare counts: use format that has more matching indicators
                else:
                    c00_score = c00_count_in_c00_format - d00_count_in_c00_format
                    d00_score = d00_count_in_d00_format - c00_count_in_d00_format
                    
                    if c00_score > d00_score and c00_score > 0:
                        confidence = "high" if c00_count_in_c00_format >= 2 else "medium"
                        if verbose:
                            logger.info(f"Control type detected: C00 (confidence: {confidence}, score: {c00_score}, {c00_count_in_c00_format} C00 indicators vs {d00_count_in_c00_format} D00 indicators in C00 format)")
                        detected_version = "C00"
                    
                    elif d00_score > c00_score and d00_score > 0:
                        confidence = "high" if d00_count_in_d00_format >= 2 else "medium"
                        if verbose:
                            logger.info(f"Control type detected: D00 (confidence: {confidence}, score: {d00_score}, {d00_count_in_d00_format} D00 indicators vs {c00_count_in_d00_format} C00 indicators in D00 format)")
                        detected_version = "D00"
                    
                    # If we found indicators but in wrong format, that's suspicious
                    elif c00_count_in_d00_format > 0 or d00_count_in_c00_format > 0:
                        logger.warning(f"Found control indicators in unexpected format - ambiguous (C00 in D00: {c00_count_in_d00_format}, D00 in C00: {d00_count_in_c00_format})")
                        # Still try to return something based on what we found
                        if c00_count_in_c00_format > 0:
                            detected_version = "C00"
                        elif d00_count_in_d00_format > 0:
                            detected_version = "D00"
                    
                    # Fallback: if no indicators found, use format that produces more valid entries
                    elif entries_c00 and entries_d00:
                        if len(entries_c00) > len(entries_d00):
                            if verbose:
                                logger.info("No control indicators found - defaulting to C00 format (more entries)")
                            detected_version = "C00"
                        else:
                            if verbose:
                                logger.info("No control indicators found - defaulting to D00 format (more entries)")
                            detected_version = "D00"
                    elif entries_c00:
                        if verbose:
                            logger.info("No control indicators found - defaulting to C00 format (only format with entries)")
                        detected_version = "C00"
                    elif entries_d00:
                        if verbose:
                            logger.info("No control indicators found - defaulting to D00 format (only format with entries)")
                        detected_version = "D00"
                    else:
                        logger.warning("No control indicators found and no valid entries - cannot determine control type")
                        return None
                
                # Cache the detected version in memory (1 hour TTL)
                if detected_version:
                    _control_version_cache[cache_key] = (detected_version, loop.time() + 3600)
                    if verbose:
                        logger.debug(f"Cached control type for {self.ip_address}:{self.port}: {detected_version}")
                
                return detected_version

            except Exception as e:
                logger.error(f"Error detecting control type: {e}")
                return None

    async def get_current_program_info(self, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get information on currently executed program using REDPRGN command.
        
        Returns information about the program currently selected in memory operation.
        
        Args:
            verbose: If True, log command details
            
        Returns:
            Dictionary with:
            - currently_executed_program_number: Currently selected program number (4 bytes)
            - main_program_number: Main program number (4 bytes)
            - currently_executed_block_number: Currently executed block number (14 bytes)
            Or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                success, status, data = await self._send_command("REDPRGN", "", verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get current program info: status {status}")
                    return None

                if not data:
                    return None

                # Parse response: Header LF Currently executed program number Main program number Currently executed block number LF Footer
                # The data returned by _send_command is already between the LFs
                # Format: <4 bytes program><4 bytes main><14 bytes block> (all on one line)
                # Remove any newlines and whitespace
                data_line = data.replace('\n', '').replace('\r', '').strip()
                
                if len(data_line) < 22:  # Minimum: 4 + 4 + 14 = 22 bytes
                    logger.warning(f"Response too short for REDPRGN: {len(data_line)} bytes, data: {repr(data_line)}")
                    return None

                try:
                    # Extract the three fields (fixed width)
                    currently_executed = data_line[0:4].strip()
                    main_program = data_line[4:8].strip()
                    block_number = data_line[8:22].strip()

                    return {
                        "currently_executed_program_number": currently_executed,
                        "main_program_number": main_program,
                        "currently_executed_block_number": block_number,
                    }
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing REDPRGN response: {e}, data: {repr(data_line)}")
                    return None

            except Exception as e:
                logger.error(f"Error getting current program info: {e}")
                return None

    async def get_current_program_content(self, character_count: int = 100, verbose: bool = False) -> Optional[str]:
        """
        Get currently executed program content by character count using REDPRG command.
        
        Returns that portion of the currently selected program running in memory operation
        which is equivalent to the specified number of characters, starting from the block
        number currently being executed.
        
        Args:
            character_count: Number of characters to acquire (1 to screen display character count)
            verbose: If True, log command details
            
        Returns:
            Program content as string, or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            if character_count < 1:
                logger.warning(f"Invalid character count: {character_count}, must be >= 1")
                return None

            try:
                # Format character count as 8-character string (padded)
                char_count_str = str(character_count).rjust(8)[:8]
                
                success, status, data = await self._send_command("REDPRG", char_count_str, verbose=verbose)
                if success:
                    # Response format: Header LF Program LF Footer
                    # The data returned by _send_command is already the program content between the LFs
                    if data:
                        # Remove any trailing newlines/whitespace but preserve the program content
                        return data.rstrip()
                    return None
                else:
                    logger.warning(f"Failed to get program content: status {status}")
                    return None
            except Exception as e:
                logger.error(f"Error getting program content: {e}")
                return None

    async def _send_multipart_command(
        self, command: str, arguments: str = "", data_payload: str = "", verbose: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Send a multi-part command with separate header and data payload.
        
        Format for multi-part commands (Brother protocol):
        - Header: %C[Command(7)][Arguments(8)]  \r\n
        - Data: [payload]\n
        - Footer: [checksum]%\r\n
        
        This is used for commands that require data payloads like REDPLCR (PLC range) 
        and REDMCNM (macro range).
        
        Args:
            command: Command name
            arguments: Command arguments
            data_payload: Data to send on separate line
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code, response_data)
        """
        if not self._connected or not self.reader or not self.writer:
            logger.error("Not connected")
            return False, None, None

        try:
            # Enforce minimum delay between commands
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self.last_command_time
            if elapsed < self.command_delay:
                await asyncio.sleep(self.command_delay - elapsed)

            # Pad command to 7 chars, arguments to 8 chars
            cmd_padded = command.ljust(7)[:7]
            args_padded = arguments.ljust(8)[:8]

            # Build header line
            header_line = f"C{cmd_padded}{args_padded}  \r\n"

            # Calculate checksum for complete message (header + data + newline)
            full_message = f"{header_line}{data_payload}\n"
            checksum = self.calculate_checksum(full_message)

            # Build complete frame
            frame = f"%{header_line}{data_payload}\n{checksum}%\r\n"
            frame_bytes = frame.encode('ascii')

            if verbose:
                logger.debug(f"[TELNET] Sending multipart {command} to {self.ip_address}: args={repr(arguments)}, data={repr(data_payload)}")

            self.writer.write(frame_bytes)
            await self.writer.drain()
            self.last_command_time = asyncio.get_event_loop().time()

            # Receive response (same as _send_command)
            response = b''
            read_timeout = 1.0

            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=read_timeout
                    )
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b'%\n'):
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

            # Parse response (same as _send_command)
            response_str = response.decode('ascii', errors='replace')

            if len(response_str) < 20:
                logger.error(f"Response too short: {response_str}")
                return False, None, None

            status_code = response_str[17:19]
            success = status_code == "00"

            if verbose:
                logger.debug(f"[TELNET] {self.ip_address} multipart response: status={status_code}, len={len(response_str)} bytes")

            first_newline = response_str.find('\n', 20)
            if first_newline == -1:
                data = None
            else:
                last_percent = response_str.rfind('%')
                if last_percent > first_newline:
                    data = response_str[first_newline + 1:last_percent].strip()
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

    # ===== RED (Read) Commands =====

    async def get_file_control_data(self, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get file control data using REDFILE command.
        
        Returns memory usage and registration information.
        
        Args:
            verbose: If True, log command details
            
        Returns:
            Dictionary with:
            - number_of_registrations: Number of programs currently registered (4 bytes)
            - number_of_possible_registrations: Number of programs that can be registered (4 bytes)
            - memory_usage: Memory in use in bytes (10 bytes)
            - remaining_memory: Remaining capacity in bytes (10 bytes)
            Or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                success, status, data = await self._send_command("REDFILE", "", verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get file control data: status {status}")
                    return None

                if not data:
                    return None

                # Parse response: Header LF Number of registrations Number of possible registrations Memory usage Remaining memory LF Footer
                # Format: <4 bytes><4 bytes><10 bytes><10 bytes>
                data_line = data.replace('\n', '').replace('\r', '').strip()
                
                if len(data_line) < 28:  # Minimum: 4 + 4 + 10 + 10 = 28 bytes
                    logger.warning(f"Response too short for REDFILE: {len(data_line)} bytes")
                    return None

                try:
                    num_reg = data_line[0:4].strip()
                    num_possible = data_line[4:8].strip()
                    memory_usage = data_line[8:18].strip()
                    remaining = data_line[18:28].strip()

                    return {
                        "number_of_registrations": int(num_reg) if num_reg.isdigit() else 0,
                        "number_of_possible_registrations": int(num_possible) if num_possible.isdigit() else 0,
                        "memory_usage": int(memory_usage) if memory_usage.isdigit() else 0,
                        "remaining_memory": int(remaining) if remaining.isdigit() else 0,
                    }
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing REDFILE response: {e}, data: {repr(data_line)}")
                    return None

            except Exception as e:
                logger.error(f"Error getting file control data: {e}")
                return None

    async def get_date_time(self, verbose: bool = False) -> Optional[str]:
        """
        Get machine date and time using REDDATE command.
        
        Args:
            verbose: If True, log command details
            
        Returns:
            Date/time string (14 bytes: YYYYMMDDHHMMSS), or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                success, status, data = await self._send_command("REDDATE", "", verbose=verbose)
                if success and data:
                    # Response format: Header LF Date LF Footer
                    # Date is 14 bytes: YYYYMMDDHHMMSS
                    date_str = data.replace('\n', '').replace('\r', '').strip()
                    if len(date_str) >= 14:
                        return date_str[:14]
                    return date_str
                else:
                    logger.warning(f"Failed to get date/time: status {status}")
                    return None
            except Exception as e:
                logger.error(f"Error getting date/time: {e}")
                return None

    async def get_plc_signal(
        self, signal_type: str, signal_number: int, verbose: bool = False
    ) -> Optional[Any]:
        """
        Get PLC signal data using REDPLCD command.
        
        Args:
            signal_type: Signal type (X, Y, BX, BY, BDX, BDXL, BDY, BDYL, M, D, DL, LM0-3, LD0-3, LDL0-3, LTV0-3, LTP0-3, LCV0-3, LCP0-3)
            signal_number: Signal number (format depends on signal type)
            verbose: If True, log command details
            
        Returns:
            Signal value (int or bool depending on signal type), or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                # Format arguments: k1k2k3k4 (4 chars signal type) + n1n2n3n4 (4 chars number)
                # Signal type must be padded to 4 chars, number must be formatted appropriately
                signal_type_padded = signal_type.ljust(4)[:4]
                # Format number based on signal type (hex for X/Y/BX/BY, decimal for others)
                if signal_type in ['X', 'Y', 'BX', 'BY']:
                    number_str = f"{signal_number:04X}"[:4]  # Hex, 4 digits
                else:
                    number_str = f"{signal_number:04d}"[:4]  # Decimal, 4 digits
                
                arguments = f"{signal_type_padded}{number_str}"
                
                success, status, data = await self._send_command("REDPLCD", arguments, verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get PLC signal: status {status}")
                    return None

                if not data:
                    return None

                # Parse value based on signal type
                value_str = data.replace('\n', '').replace('\r', '').strip()
                
                # Determine value size based on signal type
                if signal_type in ['X', 'Y', 'BX', 'BY', 'M'] or signal_type.startswith('LM'):
                    # 1 byte: 0/1
                    return value_str == '1' if value_str else False
                elif signal_type in ['BDXL', 'BDYL', 'DL'] or signal_type.startswith('LDL'):
                    # 11 bytes: long word
                    try:
                        return int(value_str) if value_str else 0
                    except ValueError:
                        return 0
                else:
                    # 6 bytes: word
                    try:
                        return int(value_str) if value_str else 0
                    except ValueError:
                        return 0

            except Exception as e:
                logger.error(f"Error getting PLC signal: {e}")
                return None

    async def get_plc_signal_range(
        self, signal_type: str, signal_number: int, data_size: int, verbose: bool = False
    ) -> Optional[list]:
        """
        Get PLC signal data range using REDPLCR command.
        
        Args:
            signal_type: Signal type (same as get_plc_signal)
            signal_number: Starting signal number
            data_size: Number of signals to read (1-9999)
            verbose: If True, log command details
            
        Returns:
            List of signal values, or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                # Format arguments: k1k2k3k4 (4 chars signal type) + n1n2n3n4 (4 chars number)
                signal_type_padded = signal_type.ljust(4)[:4]
                if signal_type in ['X', 'Y', 'BX', 'BY']:
                    number_str = f"{signal_number:04X}"[:4]
                else:
                    number_str = f"{signal_number:04d}"[:4]
                
                arguments = f"{signal_type_padded}{number_str}"
                
                # Data payload: Header LF Data size LF Footer
                data_payload = f"\n{data_size:04d}\n"
                
                success, status, data = await self._send_multipart_command(
                    "REDPLCR", arguments, data_payload, verbose=verbose
                )
                if not success:
                    logger.warning(f"Failed to get PLC signal range: status {status}")
                    return None

                if not data:
                    return None

                # Parse response: Header LF Data size Set value Set value ... Set value LF Footer
                # First 4 bytes are data size, then values follow
                data_line = data.replace('\n', '').replace('\r', '').strip()
                
                if len(data_line) < 4:
                    return None

                try:
                    # Extract data size
                    returned_size = int(data_line[0:4])
                    
                    # Determine value size based on signal type
                    if signal_type in ['X', 'Y', 'BX', 'BY', 'M'] or signal_type.startswith('LM'):
                        value_size = 1
                    elif signal_type in ['BDXL', 'BDYL', 'DL'] or signal_type.startswith('LDL'):
                        value_size = 11
                    else:
                        value_size = 6
                    
                    # Extract values
                    values = []
                    offset = 4
                    for i in range(returned_size):
                        if offset + value_size > len(data_line):
                            break
                        value_str = data_line[offset:offset + value_size].strip()
                        if value_size == 1:
                            values.append(value_str == '1')
                        else:
                            try:
                                values.append(int(value_str))
                            except ValueError:
                                values.append(0)
                        offset += value_size
                    
                    return values

                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing REDPLCR response: {e}")
                    return None

            except Exception as e:
                logger.error(f"Error getting PLC signal range: {e}")
                return None

    async def get_all_data_bank_names(self, verbose: bool = False) -> Optional[list]:
        """
        Get all current data bank names using REDCDBN command.
        
        Args:
            verbose: If True, log command details
            
        Returns:
            List of data bank names (8 bytes each), or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                success, status, data = await self._send_command("REDCDBN", "", verbose=verbose)
                if success and data:
                    # Response format: Header LF Data bank names (8 bytes each) ... LF Footer
                    data_line = data.replace('\n', '').replace('\r', '').strip()
                    
                    # Parse 8-byte entries
                    names = []
                    i = 0
                    while i + 8 <= len(data_line):
                        name = data_line[i:i+8].strip()
                        if name:
                            names.append(name)
                        i += 8
                    
                    return names if names else None
                else:
                    logger.warning(f"Failed to get data bank names: status {status}")
                    return None
            except Exception as e:
                logger.error(f"Error getting data bank names: {e}")
                return None

    async def get_data_bank_name(self, data_bank_name: str, verbose: bool = False) -> Optional[str]:
        """
        Get specific current data bank name using REDCDSL command.
        
        Args:
            data_bank_name: Data bank name (without data number, e.g., "UPRCM")
            verbose: If True, log command details
            
        Returns:
            Data bank name (8 bytes), or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                # Pad data bank name to 8 bytes
                name_padded = data_bank_name.ljust(8)[:8]
                
                success, status, data = await self._send_command("REDCDSL", name_padded, verbose=verbose)
                if success and data:
                    # Response format: Header LF Data bank name LF Footer
                    name = data.replace('\n', '').replace('\r', '').strip()
                    return name[:8] if name else None
                else:
                    logger.warning(f"Failed to get data bank name: status {status}")
                    return None
            except Exception as e:
                logger.error(f"Error getting data bank name: {e}")
                return None

    async def get_tool_compensation(
        self, tool_number: int, compensation_type: int, verbose: bool = False
    ) -> Optional[float]:
        """
        Get tool compensation using REDTOFS command.
        
        Args:
            tool_number: Tool number (01-99)
            compensation_type: Type (0: length offset, 1: length wear, 2: cutter comp, 
                                 3: cutter wear, 4: position X, 5: position wear X,
                                 6: position Y, 7: position wear Y)
            verbose: If True, log command details
            
        Returns:
            Compensation value as float, or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                # Format: n1n2 (tool 01-99) + k1 (type 0-7) + padding
                tool_str = f"{tool_number:02d}"
                type_str = str(compensation_type)
                arguments = f"{tool_str}{type_str}      "[:8]  # Pad to 8 chars
                
                success, status, data = await self._send_command("REDTOFS", arguments, verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get tool compensation: status {status}")
                    return None

                if not data:
                    return None

                # Parse compensation value
                # 9 bytes for types 0,2,4,6; 8 bytes for types 1,3,5,7
                value_str = data.replace('\n', '').replace('\r', '').strip()
                try:
                    return float(value_str)
                except ValueError:
                    logger.warning(f"Could not parse compensation value: {value_str}")
                    return None

            except Exception as e:
                logger.error(f"Error getting tool compensation: {e}")
                return None

    async def get_tool_life(
        self, tool_number: int, life_type: int, verbose: bool = False
    ) -> Optional[Any]:
        """
        Get tool life using REDTLLF command.
        
        Args:
            tool_number: Tool number (01-99)
            life_type: Type (0: life unit, 1: initial life, 2: life warning, 3: tool life)
            verbose: If True, log command details
            
        Returns:
            Life value (int for types 1-3, int 1-4 for type 0), or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                tool_str = f"{tool_number:02d}"
                type_str = str(life_type)
                arguments = f"{tool_str}{type_str}      "[:8]
                
                success, status, data = await self._send_command("REDTLLF", arguments, verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get tool life: status {status}")
                    return None

                if not data:
                    return None

                value_str = data.replace('\n', '').replace('\r', '').strip()
                try:
                    if life_type == 0:
                        # 1 byte: 1-4 (life unit)
                        return int(value_str) if value_str.isdigit() else None
                    else:
                        # 6 bytes: life value
                        return int(value_str) if value_str.isdigit() else None
                except ValueError:
                    return None

            except Exception as e:
                logger.error(f"Error getting tool life: {e}")
                return None

    async def write_tool_life(
        self,
        tool_number: int,
        life_value: int,
        life_type: str = 'TIME',
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Write/set tool life value using WRTTLLF command.
        
        Uses multipart command format with separate data payload.
        
        Args:
            tool_number: Tool number (1-99)
            life_value: Life value (0-999999)
            life_type: Type code ('TIME' or 'COUNT')
                - 'TIME' = Time-based life (type 3)
                - 'COUNT' = Count-based life (type 1)
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None
        
        # Validate inputs
        if not 1 <= tool_number <= 99:
            logger.error(f"Tool number {tool_number} out of valid range (1-99)")
            return False, "30"
        
        if life_value < 0 or life_value > 999999:
            logger.error(f"Life value {life_value} out of valid range (0-999999)")
            return False, "13"
        
        # Map life type to protocol code
        # 0 = life unit, 1 = initial, 2 = warning, 3 = life (actual)
        type_code = '3' if life_type == 'TIME' else ('1' if life_type == 'COUNT' else '3')
        
        # Format arguments: tool_number (01-99) + type_code
        arguments = f"{tool_number:02d}{type_code}    "[:8]
        
        # Format data payload: life value as 6-digit decimal
        data_payload = f"{life_value:06d}"
        
        # Acquire lock for this machine to prevent conflicts
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        start_time = asyncio.get_event_loop().time()
        try:
            async with machine_lock:
                # Use multipart command with longer timeout for write operations
                success, status, _ = await self._send_multipart_command(
                    "WRTTLLF", arguments, data_payload, verbose=verbose
                )
                
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                
                if success:
                    logger.info(f"[WRITE] Tool {tool_number} life ({life_type}) set to {life_value} ({duration_ms}ms)")
                else:
                    status_desc = self.get_status_description(status or "00")
                    logger.warning(f"Failed to write tool life: {status_desc}")
                
                return success, status
                
        except Exception as e:
            logger.error(f"Error writing tool life: {e}")
            return False, None

    async def clear_tool_life(
        self,
        tool_number: int,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Clear/reset tool life counter for a tool.
        
        Implemented as write_tool_life with value 0.
        
        Args:
            tool_number: Tool number (1-99)
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code)
        """
        return await self.write_tool_life(tool_number, 0, 'TIME', verbose)

    async def write_tool_offset(
        self,
        tool_number: int,
        offset_type: str,
        value: float,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Write tool offset data using WRTTOFS command.
        
        Uses multipart command format with separate data payload.
        
        Args:
            tool_number: Tool number (1-99)
            offset_type: Type of offset:
                'H' = Tool length offset (type 0)
                'D' = Diameter/cutter compensation offset (type 2)
                'W' = Wear offset (type 1)
            value: New offset value in mm (or inches depending on machine units)
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None
        
        # Validate inputs
        if not 1 <= tool_number <= 99:
            logger.error(f"Tool number {tool_number} out of valid range (1-99)")
            return False, "30"
        
        # Map offset type to protocol value
        type_map = {'H': '0', 'D': '2', 'W': '1'}
        if offset_type not in type_map:
            logger.error(f"Invalid offset type '{offset_type}'. Use 'H', 'D', or 'W'")
            return False, "01"
        
        k1 = type_map[offset_type]
        
        # Warn if value is extreme
        if abs(value) > 500:
            logger.warning(f"Offset value {value}mm is unusually large for {offset_type}")
        
        # Format arguments: tool_number (01-99) + type_code
        tool_str = f"{tool_number:02d}"
        arguments = f"{tool_str}{k1}     "[:8]  # Tool 01-99, type code, then 5 spaces = 8 chars
        
        # Format offset data with decimal point, padded to exact size
        # For types 0, 2 (H, D): 9 bytes total with trailing spaces
        # For type 1 (W): 8 bytes
        if k1 in ['0', '2']:
            offset_data = f"{value:.4f}".ljust(9)[:9]
        else:  # k1 == '1' (W)
            offset_data = f"{value:.4f}".ljust(8)[:8]
        
        # Acquire lock for this machine to prevent conflicts
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        start_time = asyncio.get_event_loop().time()
        try:
            async with machine_lock:
                # Use multipart command with longer timeout for write operations
                success, status, _ = await self._send_multipart_command(
                    "WRTTOFS", arguments, offset_data, verbose=verbose
                )
                
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                
                if success:
                    logger.info(f"[WRITE] Tool {tool_number} offset ({offset_type}) set to {value} ({duration_ms}ms)")
                else:
                    status_desc = self.get_status_description(status or "00")
                    logger.warning(f"Failed to write tool offset: {status_desc}")
                
                return success, status
                
        except Exception as e:
            logger.error(f"Error writing tool offset: {e}")
            return False, None

    async def get_hd_modal(self, verbose: bool = False) -> Optional[Dict[str, str]]:
        """
        Get H/D modal values using REDTOFM command.
        
        Args:
            verbose: If True, log command details
            
        Returns:
            Dictionary with 'h_modal' and 'd_modal' (3 bytes each), or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                success, status, data = await self._send_command("REDTOFM", "", verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get H/D modal: status {status}")
                    return None

                if not data:
                    return None

                # Parse response: Header LF H modal LF D modal Footer
                # Format: <3 bytes H><3 bytes D>
                data_line = data.replace('\n', '').replace('\r', '').strip()
                
                if len(data_line) >= 6:
                    h_modal = data_line[0:3].strip()
                    d_modal = data_line[3:6].strip()
                    return {
                        "h_modal": h_modal,
                        "d_modal": d_modal,
                    }
                else:
                    logger.warning(f"Response too short for REDTOFM: {len(data_line)} bytes")
                    return None

            except Exception as e:
                logger.error(f"Error getting H/D modal: {e}")
                return None

    async def get_macro_variable(self, macro_number: int, verbose: bool = False) -> Optional[float]:
        """
        Get macro variable value using REDMCNM command (single variable).
        
        Args:
            macro_number: Macro variable number (500-999)
            verbose: If True, log command details
            
        Returns:
            Macro variable value as float, or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            if macro_number < 500 or macro_number > 999:
                logger.warning(f"Macro number {macro_number} out of range (500-999)")
                return None

            try:
                # Format: n1n2n3 (macro number 500-999) + padding
                macro_str = f"{macro_number:03d}"
                arguments = f"{macro_str}     "[:8]  # Pad to 8 chars
                
                success, status, data = await self._send_command("REDMCNM", arguments, verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get macro variable: status {status}")
                    return None

                if not data:
                    return None

                # Parse value (12 bytes)
                value_str = data.replace('\n', '').replace('\r', '').strip()
                try:
                    return float(value_str)
                except ValueError:
                    logger.warning(f"Could not parse macro value: {value_str}")
                    return None

            except Exception as e:
                logger.error(f"Error getting macro variable: {e}")
                return None

    async def get_macro_variable_range(
        self, start_macro: int, data_size: int, verbose: bool = False
    ) -> Optional[list]:
        """
        Get macro variable values in range using REDMCNM command (range).
        
        Args:
            start_macro: Starting macro variable number (500-999)
            data_size: Number of variables to read (1-999)
            verbose: If True, log command details
            
        Returns:
            List of macro variable values (floats), or None on failure
        """
        # Acquire lock for this machine to serialize with other operations
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        
        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            if start_macro < 500 or start_macro > 999:
                logger.warning(f"Start macro {start_macro} out of range (500-999)")
                return None

            if data_size < 1 or data_size > 999:
                logger.warning(f"Data size {data_size} out of range (1-999)")
                return None

            try:
                # Format: n1n2n3 (macro number 500-999) + padding
                macro_str = f"{start_macro:03d}"
                arguments = f"{macro_str}     "[:8]
                
                # Data payload: Header LF Data size LF Footer
                data_payload = f"\n{data_size:03d}\n"
                
                success, status, data = await self._send_multipart_command(
                    "REDMCNM", arguments, data_payload, verbose=verbose
                )
                if not success:
                    logger.warning(f"Failed to get macro variable range: status {status}")
                    return None

                if not data:
                    return None

                # Parse response: Header LF Data size Set value Set value ... Set value LF Footer
                # First 3 bytes are data size, then 12-byte values follow
                data_line = data.replace('\n', '').replace('\r', '').strip()
                
                if len(data_line) < 3:
                    return None

                try:
                    # Extract data size
                    returned_size = int(data_line[0:3])
                    
                    # Extract values (12 bytes each)
                    values = []
                    offset = 3
                    for i in range(returned_size):
                        if offset + 12 > len(data_line):
                            break
                        value_str = data_line[offset:offset + 12].strip()
                        try:
                            values.append(float(value_str))
                        except ValueError:
                            values.append(0.0)
                        offset += 12
                    
                    return values

                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing REDMCNM range response: {e}")
                    return None

            except Exception as e:
                logger.error(f"Error getting macro variable range: {e}")
                return None

    # ===== Write Commands (Phase 6) =====

    async def change_atc_tool(
        self,
        operation_type: str,
        magazine_pos: int,
        tool_num: Optional[int] = None,
        new_value: Optional[int] = None,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Unified method for all ATC tool operations using CCHGMAG command.

        Supports all operation types:
        - 'M': Change tool number (magazine_pos, new_value=tool_number)
        - 'S': Change spindle tool (magazine_pos=0, new_value=tool_number)
        - 'K': Change tool type (magazine_pos, new_value=1/2/3 for Standard/Large/Medium)
        - 'C': Change color (magazine_pos, new_value=0-7 for color)
        - 'D': Delete tool (magazine_pos)

        Args:
            operation_type: Operation type ('M', 'S', 'K', 'C', 'D')
            magazine_pos: Magazine position (0=spindle, 1-99=pots)
            tool_num: Current tool number in position (optional, for verification)
            new_value: New value for the operation (tool number, type, or color depending on operation_type)
            verbose: If True, log command details

        Returns:
            Tuple of (success, status_code)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None

        # Validate operation type
        if operation_type not in ['M', 'S', 'K', 'C', 'D']:
            logger.error(f"Invalid operation_type: {operation_type} (must be M, S, K, C, or D)")
            return False, "01"  # Invalid data

        # Validate magazine position
        if not isinstance(magazine_pos, int) or not 0 <= magazine_pos <= 99:
            logger.error(f"Invalid magazine position: {magazine_pos} (must be 0-99)")
            return False, "30"  # Invalid tool/pot number

        # Validate new_value for operations that require it
        if operation_type in ['M', 'S', 'K', 'C']:
            if new_value is None or not isinstance(new_value, int):
                logger.error(f"Operation {operation_type} requires new_value")
                return False, "01"  # Invalid data

        # Operation-specific validation and argument formatting
        if operation_type == 'M':  # Change tool number
            if not 1 <= new_value <= 999:
                logger.error(f"Tool number {new_value} out of valid range (1-999)")
                return False, "30"  # Invalid tool/pot number
            # Format: m1m2 + t1t2t3 = 2-digit mag + 3-digit tool
            arguments = f"{magazine_pos:02d}{new_value:03d}"

        elif operation_type == 'S':  # Change spindle tool
            if not 0 <= new_value <= 999:
                logger.error(f"Spindle tool {new_value} out of valid range (0-999)")
                return False, "30"
            if magazine_pos != 0:
                logger.warning(f"Spindle tool change typically uses magazine position 0, got {magazine_pos}")
            # Format: m1m2 + t1t2t3 = 2-digit mag + 3-digit tool
            arguments = f"{magazine_pos:02d}{new_value:03d}"

        elif operation_type == 'K':  # Change tool type
            if not 1 <= new_value <= 3:
                logger.error(f"Tool type {new_value} out of valid range (1=Standard, 2=Large, 3=Medium)")
                return False, "13"  # Data item not within allowed range
            # Format: m1m2 + t1 = 2-digit mag + 1-digit type
            arguments = f"{magazine_pos:02d}{new_value}"

        elif operation_type == 'C':  # Change color
            if not 0 <= new_value <= 7:
                logger.error(f"Color {new_value} out of valid range (0-7)")
                return False, "13"
            # Format: m1m2 + t1 = 2-digit mag + 1-digit color
            arguments = f"{magazine_pos:02d}{new_value}"

        elif operation_type == 'D':  # Delete tool
            # Format: m1m2 = 2-digit mag
            arguments = f"{magazine_pos:02d}"

        # Pad arguments to 8 characters for C00/D00 compatibility
        arguments = f"{arguments:<8}"

        # Acquire lock for this machine to prevent conflicts with polling reads
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        start_time = asyncio.get_event_loop().time()
        try:
            async with machine_lock:
                # Use operation-specific commands (build_command adds %C prefix)
                command_map = {
                    'M': 'CHGMAGM',  # Change tool number
                    'S': 'CHGMAGS',  # Change spindle tool
                    'K': 'CHGMAGK',  # Change tool type
                    'C': 'CHGMAGC',  # Change color
                    'D': 'CHGMAGD',  # Delete tool
                }
                command = command_map.get(operation_type, 'CHGMAGC')  # Default to color command
                success, status, _ = await self._send_command(command, arguments, verbose=verbose, read_timeout=5.0)

                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                if success:
                    operation_names = {
                        'M': 'tool number',
                        'S': 'spindle tool',
                        'K': 'tool type',
                        'C': 'color',
                        'D': 'tool deletion'
                    }
                    operation_name = operation_names.get(operation_type, 'unknown')
                    logger.info(f"[WRITE] Successfully changed {operation_name} for magazine position {magazine_pos} ({duration_ms}ms)")
                else:
                    status_desc = self.get_status_description(status or "00")
                    logger.warning(f"Failed to execute {operation_type} operation: {status_desc}")

                return success, status

        except Exception as e:
            logger.error(f"Error executing {operation_type} operation: {e}")
            return False, None

    # Backwards compatibility alias
    async def change_atc_tool_color(
        self,
        pot_number: int,
        tool_number: int,
        color: int,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Legacy method for changing tool color. Use change_atc_tool() instead.
        """
        return await self.change_atc_tool(
            operation_type='C',
            magazine_pos=pot_number,
            tool_num=tool_number,
            new_value=color,
            verbose=verbose
        )

    # Backwards compatibility alias
    async def change_atc_tool_assignment(
        self,
        magazine_pos: int,
        tool_num: Optional[int],
        change_type: str,
        new_value: Optional[int] = None,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Legacy method for changing tool assignments. Use change_atc_tool() instead.
        """
        return await self.change_atc_tool(
            operation_type=change_type,
            magazine_pos=magazine_pos,
            tool_num=tool_num,
            new_value=new_value,
            verbose=verbose
        )

    async def assign_tool_to_pot(
        self,
        pot_number: int,
        tool_number: int,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Simplified wrapper: Assign a tool to an ATC pot.
        
        Args:
            pot_number: Pot number (1-99, not spindle)
            tool_number: Tool number to assign (1-999)
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code)
        """
        if pot_number == 0:
            logger.error("Cannot assign to spindle (pot 0). Use change_spindle_tool() instead.")
            return False, "30"
        
        return await self.change_atc_tool_assignment(
            magazine_pos=pot_number,
            tool_num=None,
            change_type='M',
            new_value=tool_number,
            verbose=verbose
        )

    async def remove_tool_from_pot(
        self,
        pot_number: int,
        tool_number: Optional[int] = None,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Simplified wrapper: Remove tool from ATC pot.
        
        Args:
            pot_number: Pot number (0-99, 0=spindle)
            tool_number: Tool number for verification (optional)
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code)
        """
        return await self.change_atc_tool_assignment(
            magazine_pos=pot_number,
            tool_num=tool_number,
            change_type='D',
            new_value=None,
            verbose=verbose
        )

    async def change_tool_type(
        self,
        pot_number: int,
        tool_type: int,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Simplified wrapper: Change tool type for a pot.
        
        Args:
            pot_number: Pot number (1-99)
            tool_type: Tool type (1=Standard, 2=Large, 3=Medium)
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code)
        """
        return await self.change_atc_tool_assignment(
            magazine_pos=pot_number,
            tool_num=None,
            change_type='K',
            new_value=tool_type,
            verbose=verbose
        )

    async def change_spindle_tool(
        self,
        tool_number: int,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Simplified wrapper: Change the tool in the spindle.
        
        Args:
            tool_number: Tool number for spindle (0-999, 0=no tool)
            verbose: If True, log command details
            
        Returns:
            Tuple of (success, status_code)
        """
        return await self.change_atc_tool_assignment(
            magazine_pos=0,
            tool_num=None,
            change_type='S',
            new_value=tool_number,
            verbose=verbose
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

