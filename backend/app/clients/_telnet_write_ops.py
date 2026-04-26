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
            arguments = f"{magazine_pos:02d}{new_value:03d}"

        elif operation_type == 'S':
            if not 0 <= new_value <= 999:
                logger.error(f"Spindle tool {new_value} out of valid range (0-999)")
                return False, "30"
            if magazine_pos != 0:
                logger.warning(f"Spindle tool change typically uses magazine position 0, got {magazine_pos}")
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
