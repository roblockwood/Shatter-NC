"""Read-only telnet operations for Brother CNC machines.

CNCDataReadsMixin provides every method that loads data from the controller
without modifying its state.  All methods call self._send_command() and
self._send_multipart_command() which live in the base CNCTelnetClient class.

Import graph:
    _telnet_state  (state, _get_machine_lock, _control_version_cache)
        ↑
    _telnet_data_reads  (this file)
        ↑
    telnet_client  (CNCTelnetClient inherits CNCDataReadsMixin)
"""
import asyncio
import re
import logging
from typing import Optional, Dict, Any, List

from app.clients._telnet_state import _get_machine_lock, _control_version_cache

logger = logging.getLogger(__name__)


class CNCDataReadsMixin:
    """Mixin of read-only LOD / RED / DRQALL operations.

    Assumes self has:
        self.ip_address: str
        self.port: int
        self._connected: bool
        self.connect() -> bool
        self._send_command(...) -> (bool, Optional[str], Optional[str])
        self._send_multipart_command(...) -> (bool, Optional[str], Optional[str])
    """

    # ------------------------------------------------------------------
    # Core LOD loader with retry
    # ------------------------------------------------------------------

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
        # Serialize all LOD operations per machine across all client instances.
        # Brother controls can reject or stall overlapping protocol sessions on the same port.
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
            for attempt in range(max_retries + 1):
                try:
                    # Ensure connection (will reconnect if needed)
                    if not self._connected:
                        connected = await self.connect()
                        if not connected:
                            if attempt < max_retries:
                                wait_time = 0.5 * (attempt + 1)
                                logger.warning(f"Telnet connection failed for '{data_name}', retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                                await asyncio.sleep(wait_time)
                                continue
                            return None

                    # Increased timeout to 5 seconds for large data files (e.g., TOLNI1 tool table)
                    success, status, data = await self._send_command("LOD", data_name, verbose=verbose, read_timeout=5.0)
                    if success:
                        return data
                    else:
                        if status == "TIMEOUT":
                            # The command reached the machine but got no response within
                            # the timeout.  Retrying would send a second LOD while the
                            # machine is still processing the first -- that triggers CM7522
                            # ("Receive command abnormal end") on D00 controls.
                            logger.warning(
                                f"Failed to load '{data_name}': command sent but no response "
                                f"(possible CM7522 risk) — not retrying"
                            )
                            return None
                        elif status is None and attempt < max_retries:
                            # Connection-level failure BEFORE the command was sent.
                            # Safe to reconnect and retry.
                            wait_time = 0.5 * (attempt + 1)
                            logger.warning(f"Failed to load '{data_name}': no response status, reconnecting and retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                            self._connected = False
                            await asyncio.sleep(wait_time)
                            continue
                        elif status == "40" and attempt < max_retries:
                            # Communication conflict: machine rejected the command
                            # without executing it, so retrying is safe.
                            wait_time = 0.5 * (attempt + 1)
                            logger.warning(f"Failed to load '{data_name}': status {status} (communication conflict), retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            self._connected = False
                            continue
                        else:
                            logger.warning(f"Failed to load data '{data_name}': status {status}")
                            return None
                except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                    if attempt < max_retries:
                        wait_time = 0.5 * (attempt + 1)
                        logger.warning(f"Connection error loading '{data_name}': {e}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                        self._connected = False
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Error loading data '{data_name}' after {max_retries + 1} attempts: {e}")
                        return None
                except Exception as e:
                    logger.error(f"Error loading data '{data_name}': {e}")
                    return None

        return None

    # ------------------------------------------------------------------
    # Convenience LOD wrappers
    # ------------------------------------------------------------------

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
        if control_version is None:
            control_version = await self.detect_control_type()

        primary = "PRDD3" if control_version == "D00" else "PRD3"
        alternate = "PRD3" if primary == "PRDD3" else "PRDD3"
        data = await self.load_data(primary, verbose=verbose)
        if data is not None:
            return data
        return await self.load_data(alternate, verbose=verbose)

    async def get_atc_magazine_data(self, control_version: Optional[str] = None, verbose: bool = False) -> Optional[str]:
        """
        Get ATC magazine data (ATCTL for C00, ATDTL for D00).

        Args:
            control_version: Control version ('C00' or 'D00'). If None, auto-detects.
            verbose: If True, enable verbose logging

        Returns:
            ATC magazine data as string, or None if failed
        """
        if control_version is None:
            control_version = await self.detect_control_type()

        data_name = "ATDTL" if control_version == "D00" else "ATCTL"
        data = await self.load_data(data_name, verbose=verbose)
        if data is not None:
            return data
        # Try alternate format name if primary fails
        alt_name = "ATCTL" if data_name == "ATDTL" else "ATDTL"
        return await self.load_data(alt_name, verbose=verbose)

    # ------------------------------------------------------------------
    # Directory listing
    # ------------------------------------------------------------------

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
        data = directory_data.replace('\n', '').replace('\r', '').strip()

        if not data:
            return None

        if control_type == "D00":
            entry_length = 18
            size_start = 8
            size_length = 10
            size_in_bytes = True
        elif control_type == "C00":
            entry_length = 11
            size_start = 8
            size_length = 3
            size_in_bytes = False
        else:
            if len(data) % 11 == 0:
                entry_length = 11
                size_start = 8
                size_length = 3
                size_in_bytes = False
            elif len(data) % 18 == 0:
                entry_length = 18
                size_start = 8
                size_length = 10
                size_in_bytes = True
            else:
                c00_entries = self._parse_directory_format(data, 11, 8, 3, False)
                d00_entries = self._parse_directory_format(data, 18, 8, 10, True)

                if len(c00_entries) >= len(d00_entries) and c00_entries:
                    entry_length = 11
                    size_start = 8
                    size_length = 3
                    size_in_bytes = False
                elif d00_entries:
                    entry_length = 18
                    size_start = 8
                    size_length = 10
                    size_in_bytes = True
                else:
                    logger.error(f"Could not determine directory listing format. Data length: {len(data)}")
                    return None

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
                        'size_str': size_str,
                        'size_in_bytes': size_in_bytes
                    })
                except ValueError:
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
        """Helper method to parse directory listing in a specific format."""
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

    # ------------------------------------------------------------------
    # Control type detection
    # ------------------------------------------------------------------

    async def detect_control_type(self, verbose: bool = False) -> Optional[str]:
        """
        Detect machine control type (C00 or D00) by checking directory listing.

        Detection method (checks multiple file patterns for higher confidence):
        - C00 control indicators: PRDC# files, SYSC# files
        - D00 control indicators: PRDD# files, SYSD# files

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

        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
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
                directory_data = await self._get_directory_listing_internal(verbose=verbose)
                if not directory_data:
                    logger.warning("Failed to get directory listing for control type detection")
                    return None

                entries_c00 = await self.parse_directory_listing(directory_data, control_type="C00")
                entries_d00 = await self.parse_directory_listing(directory_data, control_type="D00")

                if not entries_c00 and not entries_d00:
                    logger.warning("No entries found in directory listing with either format")
                    return None

                prdc_pattern = re.compile(r'^PRDC\d+$')
                sysc_pattern = re.compile(r'^SYSC\d+$')
                prdd_pattern = re.compile(r'^PRDD\d+$')
                sysd_pattern = re.compile(r'^SYSD\d+$')

                c00_indicators_in_c00_format = []
                d00_indicators_in_c00_format = []
                c00_indicators_in_d00_format = []
                d00_indicators_in_d00_format = []

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

                c00_count_in_c00_format = len(c00_indicators_in_c00_format)
                d00_count_in_c00_format = len(d00_indicators_in_c00_format)
                c00_count_in_d00_format = len(c00_indicators_in_d00_format)
                d00_count_in_d00_format = len(d00_indicators_in_d00_format)

                if verbose:
                    logger.info(f"C00 indicators in C00 format: {c00_count_in_c00_format} ({c00_indicators_in_c00_format})")
                    logger.info(f"D00 indicators in C00 format: {d00_count_in_c00_format} ({d00_indicators_in_c00_format})")
                    logger.info(f"C00 indicators in D00 format: {c00_count_in_d00_format} ({c00_indicators_in_d00_format})")
                    logger.info(f"D00 indicators in D00 format: {d00_count_in_d00_format} ({d00_indicators_in_d00_format})")

                detected_version = None

                if c00_count_in_c00_format > 0 and d00_count_in_c00_format == 0:
                    confidence = "high" if c00_count_in_c00_format >= 2 else "medium"
                    if verbose:
                        logger.info(f"Control type detected: C00 (confidence: {confidence}, {c00_count_in_c00_format} indicators in C00 format)")
                    detected_version = "C00"

                elif d00_count_in_d00_format > 0 and c00_count_in_d00_format == 0:
                    confidence = "high" if d00_count_in_d00_format >= 2 else "medium"
                    if verbose:
                        logger.info(f"Control type detected: D00 (confidence: {confidence}, {d00_count_in_d00_format} indicators in D00 format)")
                    detected_version = "D00"

                else:
                    c00_score = c00_count_in_c00_format - d00_count_in_c00_format
                    d00_score = d00_count_in_d00_format - c00_count_in_d00_format

                    if c00_score > d00_score and c00_score > 0:
                        confidence = "high" if c00_count_in_c00_format >= 2 else "medium"
                        if verbose:
                            logger.info(f"Control type detected: C00 (confidence: {confidence}, score: {c00_score})")
                        detected_version = "C00"

                    elif d00_score > c00_score and d00_score > 0:
                        confidence = "high" if d00_count_in_d00_format >= 2 else "medium"
                        if verbose:
                            logger.info(f"Control type detected: D00 (confidence: {confidence}, score: {d00_score})")
                        detected_version = "D00"

                    elif c00_count_in_d00_format > 0 or d00_count_in_c00_format > 0:
                        logger.warning(f"Found control indicators in unexpected format - ambiguous (C00 in D00: {c00_count_in_d00_format}, D00 in C00: {d00_count_in_c00_format})")
                        if c00_count_in_c00_format > 0:
                            detected_version = "C00"
                        elif d00_count_in_d00_format > 0:
                            detected_version = "D00"
                        elif d00_count_in_c00_format > c00_count_in_d00_format:
                            detected_version = "D00"
                        elif c00_count_in_d00_format > d00_count_in_c00_format:
                            detected_version = "C00"
                        elif d00_count_in_c00_format > 0:
                            detected_version = "D00"
                        elif c00_count_in_d00_format > 0:
                            detected_version = "C00"

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

                if detected_version:
                    _control_version_cache[cache_key] = (detected_version, loop.time() + 3600)
                    if verbose:
                        logger.debug(f"Cached control type for {self.ip_address}:{self.port}: {detected_version}")

                return detected_version

            except Exception as e:
                logger.error(f"Error detecting control type: {e}")
                return None

    # ------------------------------------------------------------------
    # Program info (RED commands)
    # ------------------------------------------------------------------

    async def get_current_program_info(self, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get information on currently executed program using REDPRGN command.

        Returns:
            Dictionary with currently_executed_program_number, main_program_number,
            currently_executed_block_number — or None on failure
        """
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

                data_line = data.replace('\n', '').replace('\r', '').strip()

                if len(data_line) < 22:
                    logger.warning(f"Response too short for REDPRGN: {len(data_line)} bytes, data: {repr(data_line)}")
                    return None

                try:
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

        Args:
            character_count: Number of characters to acquire (1 to screen display character count)
            verbose: If True, log command details

        Returns:
            Program content as string, or None on failure
        """
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
                char_count_str = str(character_count).rjust(8)[:8]

                success, status, data = await self._send_command("REDPRG", char_count_str, verbose=verbose)
                if success:
                    if data:
                        return data.rstrip()
                    return None
                else:
                    logger.warning(f"Failed to get program content: status {status}")
                    return None
            except Exception as e:
                logger.error(f"Error getting program content: {e}")
                return None

    # ------------------------------------------------------------------
    # File / memory info
    # ------------------------------------------------------------------

    async def get_file_control_data(self, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get file control data using REDFILE command.

        Returns:
            Dictionary with number_of_registrations, number_of_possible_registrations,
            memory_usage, remaining_memory — or None on failure
        """
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

                data_line = data.replace('\n', '').replace('\r', '').strip()

                if len(data_line) < 28:
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

        Returns:
            Date/time string (14 bytes: YYYYMMDDHHMMSS), or None on failure
        """
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                success, status, data = await self._send_command("REDDATE", "", verbose=verbose)
                if success and data:
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

    # ------------------------------------------------------------------
    # PLC signals
    # ------------------------------------------------------------------

    async def get_plc_signal(
        self, signal_type: str, signal_number: int, verbose: bool = False
    ) -> Optional[Any]:
        """
        Get PLC signal data using REDPLCD command.

        Args:
            signal_type: Signal type (X, Y, BX, BY, BDX, BDXL, BDY, BDYL, M, D, DL, etc.)
            signal_number: Signal number (format depends on signal type)
            verbose: If True, log command details

        Returns:
            Signal value (int or bool depending on signal type), or None on failure
        """
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                signal_type_padded = signal_type.ljust(4)[:4]
                if signal_type in ['X', 'Y', 'BX', 'BY']:
                    number_str = f"{signal_number:04X}"[:4]
                else:
                    number_str = f"{signal_number:04d}"[:4]

                arguments = f"{signal_type_padded}{number_str}"

                success, status, data = await self._send_command("REDPLCD", arguments, verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get PLC signal: status {status}")
                    return None

                if not data:
                    return None

                value_str = data.replace('\n', '').replace('\r', '').strip()

                if signal_type in ['X', 'Y', 'BX', 'BY', 'M'] or signal_type.startswith('LM'):
                    return value_str == '1' if value_str else False
                elif signal_type in ['BDXL', 'BDYL', 'DL'] or signal_type.startswith('LDL'):
                    try:
                        return int(value_str) if value_str else 0
                    except ValueError:
                        return 0
                else:
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
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                signal_type_padded = signal_type.ljust(4)[:4]
                if signal_type in ['X', 'Y', 'BX', 'BY']:
                    number_str = f"{signal_number:04X}"[:4]
                else:
                    number_str = f"{signal_number:04d}"[:4]

                arguments = f"{signal_type_padded}{number_str}"
                data_payload = f"\n{data_size:04d}\n"

                success, status, data = await self._send_multipart_command(
                    "REDPLCR", arguments, data_payload, verbose=verbose
                )
                if not success:
                    logger.warning(f"Failed to get PLC signal range: status {status}")
                    return None

                if not data:
                    return None

                data_line = data.replace('\n', '').replace('\r', '').strip()

                if len(data_line) < 4:
                    return None

                try:
                    returned_size = int(data_line[0:4])

                    if signal_type in ['X', 'Y', 'BX', 'BY', 'M'] or signal_type.startswith('LM'):
                        value_size = 1
                    elif signal_type in ['BDXL', 'BDYL', 'DL'] or signal_type.startswith('LDL'):
                        value_size = 11
                    else:
                        value_size = 6

                    values = []
                    offset = 4
                    for _ in range(returned_size):
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

    # ------------------------------------------------------------------
    # Data banks
    # ------------------------------------------------------------------

    async def get_all_data_bank_names(self, verbose: bool = False) -> Optional[list]:
        """
        Get all current data bank names using REDCDBN command.

        Returns:
            List of data bank names (8 bytes each), or None on failure
        """
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                success, status, data = await self._send_command("REDCDBN", "", verbose=verbose)
                if success and data:
                    data_line = data.replace('\n', '').replace('\r', '').strip()
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
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                name_padded = data_bank_name.ljust(8)[:8]

                success, status, data = await self._send_command("REDCDSL", name_padded, verbose=verbose)
                if success and data:
                    name = data.replace('\n', '').replace('\r', '').strip()
                    return name[:8] if name else None
                else:
                    logger.warning(f"Failed to get data bank name: status {status}")
                    return None
            except Exception as e:
                logger.error(f"Error getting data bank name: {e}")
                return None

    # ------------------------------------------------------------------
    # Tool reads
    # ------------------------------------------------------------------

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
        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        async with machine_lock:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return None

            try:
                tool_str = f"{tool_number:02d}"
                type_str = str(compensation_type)
                arguments = f"{tool_str}{type_str}      "[:8]

                success, status, data = await self._send_command("REDTOFS", arguments, verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get tool compensation: status {status}")
                    return None

                if not data:
                    return None

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
                        return int(value_str) if value_str.isdigit() else None
                    else:
                        return int(value_str) if value_str.isdigit() else None
                except ValueError:
                    return None

            except Exception as e:
                logger.error(f"Error getting tool life: {e}")
                return None

    # ------------------------------------------------------------------
    # H/D modal and macro variables
    # ------------------------------------------------------------------

    async def get_hd_modal(self, verbose: bool = False) -> Optional[Dict[str, str]]:
        """
        Get H/D modal values using REDTOFM command.

        Returns:
            Dictionary with 'h_modal' and 'd_modal' (3 bytes each), or None on failure
        """
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
                macro_str = f"{macro_number:03d}"
                arguments = f"{macro_str}     "[:8]

                success, status, data = await self._send_command("REDMCNM", arguments, verbose=verbose)
                if not success:
                    logger.warning(f"Failed to get macro variable: status {status}")
                    return None

                if not data:
                    return None

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
                macro_str = f"{start_macro:03d}"
                arguments = f"{macro_str}     "[:8]
                data_payload = f"\n{data_size:03d}\n"

                success, status, data = await self._send_multipart_command(
                    "REDMCNM", arguments, data_payload, verbose=verbose
                )
                if not success:
                    logger.warning(f"Failed to get macro variable range: status {status}")
                    return None

                if not data:
                    return None

                data_line = data.replace('\n', '').replace('\r', '').strip()

                if len(data_line) < 3:
                    return None

                try:
                    returned_size = int(data_line[0:3])

                    values = []
                    offset = 3
                    for _ in range(returned_size):
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
