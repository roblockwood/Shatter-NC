"""Write operations (tool offsets, ATC magazine) for Brother CNC machines.

CNCWriteOpsMixin contains every method that modifies controller state.
All methods call self._send_command() or self._send_multipart_command()
which live in the base CNCTelnetClient class.

Import graph:
    _telnet_state  (state, _get_machine_lock)
        ↑
    _telnet_write_ops  (this file)
        ↑
    telnet_client  (CNCTelnetClient inherits CNCWriteOpsMixin)
"""
import asyncio
import logging
from typing import Optional, Tuple

from app.clients._telnet_state import _get_machine_lock

logger = logging.getLogger(__name__)

# C00 ATCTL cap marker (D00 uses 999). CHGMAGD clears cap → empty (0).
CAP_TOOL_NUMBER_C00 = 255
CAP_TOOL_NUMBER_D00 = 999

MACRO_VARIABLE_MIN = 500
MACRO_VARIABLE_MAX = 999


def format_macro_set_value(value: float) -> str:
    """Format a macro variable set value for WRTMCNM (12-byte data field).

    Whole numbers are sent without a decimal point. Fractional values use at most
    three decimal places — Brother rejects four-place payloads (status 30), e.g.
    ``12.5000`` fails while ``12.5`` / ``12.500`` succeed. The field is
    right-justified to 12 characters.
    """
    rounded = round(value)
    if abs(value - rounded) < 0.0005:
        return f"{int(rounded)}".rjust(12)[:12]
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text.rjust(12)[:12]


def macro_values_match(expected: float, actual: float) -> bool:
    """True when REDMCNM read-back matches the written value within Brother float noise.

    Controls often return values like 54.00012 for an integer write of 54. Absolute
    tolerance alone is too tight on larger magnitudes; combine a small floor with a
    relative term. Also allow ~0.001 for 3-decimal write rounding.
    """
    return abs(actual - expected) <= max(0.001, abs(expected) * 1e-4)


class CNCWriteOpsMixin:
    """Mixin of write operations that modify machine tool data and ATC magazine.

    Assumes self has:
        self.ip_address: str
        self.port: int
        self._connected: bool
        self.connect() -> bool
        self._send_command(...) -> (bool, Optional[str], Optional[str])
        self._send_multipart_command(...) -> (bool, Optional[str], Optional[str])
        self.get_status_description(code: str) -> str
    """

    # ------------------------------------------------------------------
    # Tool life write
    # ------------------------------------------------------------------

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

        if not 1 <= tool_number <= 99:
            logger.error(f"Tool number {tool_number} out of valid range (1-99)")
            return False, "30"

        if life_value < 0 or life_value > 999999:
            logger.error(f"Life value {life_value} out of valid range (0-999999)")
            return False, "13"

        type_code = '3' if life_type == 'TIME' else ('1' if life_type == 'COUNT' else '3')
        arguments = f"{tool_number:02d}{type_code}    "[:8]
        data_payload = f"{life_value:06d}"

        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        start_time = asyncio.get_event_loop().time()
        try:
            async with machine_lock:
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

    # ------------------------------------------------------------------
    # Tool offset write
    # ------------------------------------------------------------------

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

        if not 1 <= tool_number <= 99:
            logger.error(f"Tool number {tool_number} out of valid range (1-99)")
            return False, "30"

        type_map = {'H': '0', 'D': '2', 'W': '1'}
        if offset_type not in type_map:
            logger.error(f"Invalid offset type '{offset_type}'. Use 'H', 'D', or 'W'")
            return False, "01"

        k1 = type_map[offset_type]

        if abs(value) > 500:
            logger.warning(f"Offset value {value}mm is unusually large for {offset_type}")

        tool_str = f"{tool_number:02d}"
        arguments = f"{tool_str}{k1}     "[:8]

        if k1 in ['0', '2']:
            offset_data = f"{value:.4f}".ljust(9)[:9]
        else:
            offset_data = f"{value:.4f}".ljust(8)[:8]

        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        start_time = asyncio.get_event_loop().time()
        try:
            async with machine_lock:
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

    # ------------------------------------------------------------------
    # Macro variable write
    # ------------------------------------------------------------------

    async def write_macro_variable(
        self,
        macro_number: int,
        value: float,
        verbose: bool = False,
        verify: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Write macro variable value using WRTMCNM command.

        Args:
            macro_number: Macro variable number (500-999)
            value: Value to write
            verbose: If True, log command details
            verify: If True, read back via REDMCNM and confirm value matches

        Returns:
            Tuple of (success, status_code, verified_value)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None, None

        if not MACRO_VARIABLE_MIN <= macro_number <= MACRO_VARIABLE_MAX:
            logger.error(
                f"Macro number {macro_number} out of valid range "
                f"({MACRO_VARIABLE_MIN}-{MACRO_VARIABLE_MAX})"
            )
            return False, "30", None

        macro_str = f"{macro_number:03d}"
        arguments = f"{macro_str}     "[:8]
        data_payload = format_macro_set_value(value)

        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        start_time = asyncio.get_event_loop().time()
        try:
            async with machine_lock:
                success, status, _ = await self._send_multipart_command(
                    "WRTMCNM", arguments, data_payload, verbose=verbose
                )

                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                if success:
                    logger.info(
                        f"[WRITE] Macro #{macro_number} set to {value} ({duration_ms}ms)"
                    )
                else:
                    status_desc = self.get_status_description(status or "00")
                    logger.warning(f"Failed to write macro #{macro_number}: {status_desc}")

                if not success:
                    return False, status, None

                if not verify:
                    return True, status, None

                read_back = await self._fetch_macro_variable_unlocked(macro_number, verbose=verbose)
                if read_back is None:
                    logger.warning(f"Macro #{macro_number} write succeeded but read-back failed")
                    return False, "verify_failed", None

                if not macro_values_match(value, read_back):
                    logger.warning(
                        f"Macro #{macro_number} verify mismatch: wrote {value}, read {read_back}"
                    )
                    return False, "verify_mismatch", read_back

                return True, status, read_back

        except Exception as e:
            logger.error(f"Error writing macro variable #{macro_number}: {e}")
            return False, None, None

    # ------------------------------------------------------------------
    # ATC magazine operations
    # ------------------------------------------------------------------

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
            new_value: New value for the operation (tool number, type, or color)
            verbose: If True, log command details

        Returns:
            Tuple of (success, status_code)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None

        if operation_type not in ['M', 'S', 'K', 'C', 'D']:
            logger.error(f"Invalid operation_type: {operation_type} (must be M, S, K, C, or D)")
            return False, "01"

        if not isinstance(magazine_pos, int) or not 0 <= magazine_pos <= 99:
            logger.error(f"Invalid magazine position: {magazine_pos} (must be 0-99)")
            return False, "30"

        if operation_type in ['M', 'S', 'K', 'C']:
            if new_value is None or not isinstance(new_value, int):
                logger.error(f"Operation {operation_type} requires new_value")
                return False, "01"

        if operation_type == 'M':
            if not 1 <= new_value <= 999:
                logger.error(f"Tool number {new_value} out of valid range (1-999)")
                return False, "30"
            # C00 CHGMAGM uses pot(2) + tool(2) for T1-99 (e.g. pot 4 T7 → "0407").
            # Tools 100+ use a 3-digit tool field on D00-class controls (e.g. "02101").
            if new_value <= 99:
                arguments = f"{magazine_pos:02d}{new_value:02d}"
            else:
                arguments = f"{magazine_pos:02d}{new_value:03d}"

        elif operation_type == 'S':
            if not 0 <= new_value <= 999:
                logger.error(f"Spindle tool {new_value} out of valid range (0-999)")
                return False, "30"
            if magazine_pos != 0:
                logger.warning(f"Spindle tool change typically uses magazine position 0, got {magazine_pos}")
            if new_value <= 99:
                arguments = f"{magazine_pos:02d}{new_value:02d}"
            else:
                arguments = f"{magazine_pos:02d}{new_value:03d}"

        elif operation_type == 'K':
            if not 1 <= new_value <= 3:
                logger.error(f"Tool type {new_value} out of valid range (1=Standard, 2=Large, 3=Medium)")
                return False, "13"
            arguments = f"{magazine_pos:02d}{new_value}"

        elif operation_type == 'C':
            if not 0 <= new_value <= 7:
                logger.error(f"Color {new_value} out of valid range (0-7)")
                return False, "13"
            arguments = f"{magazine_pos:02d}{new_value}"

        elif operation_type == 'D':
            arguments = f"{magazine_pos:02d}"

        arguments = f"{arguments:<8}"

        machine_lock = await _get_machine_lock(self.ip_address, self.port)

        start_time = asyncio.get_event_loop().time()
        try:
            async with machine_lock:
                command_map = {
                    'M': 'CHGMAGM',
                    'S': 'CHGMAGS',
                    'K': 'CHGMAGK',
                    'C': 'CHGMAGC',
                    'D': 'CHGMAGD',
                }
                command = command_map.get(operation_type, 'CHGMAGC')
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

    # ------------------------------------------------------------------
    # Backwards-compatible convenience wrappers
    # ------------------------------------------------------------------

    async def change_atc_tool_color(
        self,
        pot_number: int,
        tool_number: int,
        color: int,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Legacy method for changing tool color. Use change_atc_tool() instead."""
        return await self.change_atc_tool(
            operation_type='C',
            magazine_pos=pot_number,
            tool_num=tool_number,
            new_value=color,
            verbose=verbose
        )

    async def change_atc_tool_assignment(
        self,
        magazine_pos: int,
        tool_num: Optional[int],
        change_type: str,
        new_value: Optional[int] = None,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Legacy method for changing tool assignments. Use change_atc_tool() instead."""
        return await self.change_atc_tool(
            operation_type=change_type,
            magazine_pos=magazine_pos,
            tool_num=tool_num,
            new_value=new_value,
            verbose=verbose
        )

    async def _read_pot_tool_number(
        self, pot_number: int, verbose: bool = False
    ) -> Optional[int]:
        """Read current tool_number for an ATC pocket from ATCTL."""
        from app.parsers.atctl_parser_v2 import parse_atctl_v2

        control = await self.detect_control_type() or "C00"
        raw = await self.get_atc_magazine_data(control_version=control, verbose=verbose)
        if not raw:
            return None
        parsed = parse_atctl_v2(raw.encode("utf-8"), control_version=control)
        for tool in parsed.get("tools", []):
            pot = tool.get("pot_number")
            if pot is None or str(pot).upper() == "SPINDLE":
                continue
            try:
                if int(pot) == pot_number:
                    return tool.get("tool_number")
            except (TypeError, ValueError):
                continue
        return None

    async def clear_cap_from_pot(
        self,
        pot_number: int,
        verbose: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Clear a cap setting (C00: tool 255, D00: 999) from a pocket via CHGMAGD.

        Also clears empty (0) and registered tools; callers should check ATCTL first
        when they only intend to remove cap.
        """
        current = await self._read_pot_tool_number(pot_number, verbose=verbose)
        cap_values = {CAP_TOOL_NUMBER_C00, CAP_TOOL_NUMBER_D00}
        if current not in cap_values:
            return True, "00"
        return await self.remove_tool_from_pot(pot_number, verbose=verbose)

    async def assign_tool_to_pot(
        self,
        pot_number: int,
        tool_number: int,
        verbose: bool = False,
        clear_cap: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Simplified wrapper: Assign a tool to an ATC pot.

        Args:
            pot_number: Pot number (1-99, not spindle)
            tool_number: Tool number to assign (1-999)
            verbose: If True, log command details
            clear_cap: If True, CHGMAGD clears cap (255/999) before CHGMAGM assign

        Returns:
            Tuple of (success, status_code)
        """
        if pot_number == 0:
            logger.error("Cannot assign to spindle (pot 0). Use change_spindle_tool() instead.")
            return False, "30"

        if clear_cap:
            ok, status = await self.clear_cap_from_pot(pot_number, verbose=verbose)
            if not ok:
                return ok, status

        return await self.change_atc_tool_assignment(
            magazine_pos=pot_number,
            tool_num=None,
            change_type='M',
            new_value=tool_number,
            verbose=verbose
        )

    async def set_cap_on_pot(
        self,
        pot_number: int,
        verbose: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Mark an ATC pocket as cap (C00: ATCTL tool 255, D00: 999).

        The machine panel displays cap as tool 0; telnet CHGMAGM uses the ATCTL value.
        """
        if pot_number == 0:
            logger.error("Cannot set cap on spindle (pot 0).")
            return False, "30"

        control = await self.detect_control_type() or "C00"
        cap_value = (
            CAP_TOOL_NUMBER_D00
            if str(control).upper().startswith("D")
            else CAP_TOOL_NUMBER_C00
        )
        cap_values = {CAP_TOOL_NUMBER_C00, CAP_TOOL_NUMBER_D00}

        current = await self._read_pot_tool_number(pot_number, verbose=verbose)
        if current in cap_values:
            return True, "00"
        if current is not None and current not in (0, *cap_values):
            ok, status = await self.remove_tool_from_pot(pot_number, verbose=verbose)
            if not ok:
                return ok, status

        return await self.change_atc_tool_assignment(
            magazine_pos=pot_number,
            tool_num=None,
            change_type='M',
            new_value=cap_value,
            verbose=verbose,
        )

    async def remove_tool_from_pot(
        self,
        pot_number: int,
        tool_number: Optional[int] = None,
        verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Simplified wrapper: Remove tool from ATC pot (CHGMAGD).

        Clears registered tools and cap settings (C00 tool 255 / D00 tool 999).

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

    # ------------------------------------------------------------------
    # Program control (CHGMODE / FLDCHG / MEMSTRT / MEMSTOP)
    # ------------------------------------------------------------------

    async def change_mode(self, mode: str, verbose: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Switch NC mode via CHGMODE.

        Args:
            mode: One of MEM, EDIT, MDI, MNL (padded to 8-byte args by _send_command)
            verbose: Log command details

        Returns:
            (success, status_code). Status 60 (already in mode) is treated as success.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None

        mode_arg = (mode or "").strip().upper()
        if mode_arg not in ("MEM", "EDIT", "MDI", "MNL"):
            logger.error(f"Invalid CHGMODE argument: {mode!r}")
            return False, "30"

        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        try:
            async with machine_lock:
                success, status, _ = await self._send_command(
                    "CHGMODE", mode_arg, verbose=verbose
                )
                if success or status == "60":
                    return True, status
                return False, status
        except Exception as e:
            logger.error(f"Error in CHGMODE {mode_arg}: {e}")
            return False, None

    async def change_folder(
        self, folder: str, verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Change telnet working folder via multipart FLDCHG.

        Args:
            folder: Folder name such as PROGRAM or /
            verbose: Log command details

        Returns:
            (success, status_code)
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None

        folder_payload = (folder or "").strip() or "/"
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        try:
            async with machine_lock:
                success, status, _ = await self._send_multipart_command(
                    "FLDCHG", "", folder_payload, verbose=verbose
                )
                return success, status
        except Exception as e:
            logger.error(f"Error in FLDCHG {folder_payload!r}: {e}")
            return False, None

    async def get_working_folder(self, verbose: bool = False) -> Optional[str]:
        """Read current telnet folder via FLDPWD."""
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return None

        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        try:
            async with machine_lock:
                success, _, data = await self._send_command("FLDPWD", "", verbose=verbose)
                if not success or not data:
                    return None
                return data.split("\r")[0].split("\n")[0].strip() or None
        except Exception as e:
            logger.error(f"Error in FLDPWD: {e}")
            return None

    async def start_memory_program(
        self, program: int, verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Start a memory program via MEMSTRT (4-digit O-number in args).

        Caller must already be in MEM mode and the correct folder (e.g. PROGRAM).
        Always restore folder to / after calling this when used for remote probing.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None

        if not 0 <= int(program) <= 9999:
            logger.error(f"Invalid MEMSTRT program number: {program}")
            return False, "30"

        prog_arg = f"{int(program):04d}"
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        try:
            async with machine_lock:
                success, status, _ = await self._send_command(
                    "MEMSTRT", prog_arg, verbose=verbose
                )
                return success, status
        except Exception as e:
            logger.error(f"Error in MEMSTRT {prog_arg}: {e}")
            return False, None

    async def memory_stop(
        self, latch_on: bool = True, verbose: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Latch or clear feed hold via MEMSTOP ON/OFF.

        MEMSTOP ON latches hold; clear with MEMSTOP OFF or the panel.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                return False, None

        arg = "ON" if latch_on else "OFF"
        machine_lock = await _get_machine_lock(self.ip_address, self.port)
        try:
            async with machine_lock:
                success, status, _ = await self._send_command(
                    "MEMSTOP", arg, verbose=verbose
                )
                return success, status
        except Exception as e:
            logger.error(f"Error in MEMSTOP {arg}: {e}")
            return False, None
