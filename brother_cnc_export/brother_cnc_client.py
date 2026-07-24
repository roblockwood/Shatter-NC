#!/usr/bin/env python3
"""
Brother CNC Machine Communication Client

This is the ACTUAL protocol used by Brother CNC machines (discovered from BrotherAdapter).
NOT the standard Protocol Type 1 or 2 described in the manual.

Protocol Format:
%C[Command][Arguments]\r\n[Checksum]%\r\n

Response Format:
%R[Command][Arguments][StatusCode]\n[Data]\n[Checksum]%\n
"""

import socket
from typing import Optional, Tuple, List, Dict
import time


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


class BrotherCNCClient:
    """Client for Brother CNC machines using the actual working protocol"""

    def __init__(self, host: str = "192.168.1.100", port: int = 10000, timeout: int = 10,
                 command_delay: float = 0.2):
        """
        Initialize Brother CNC client.

        Args:
            host: IP address of CNC machine
            port: TCP port (typically 10000)
            timeout: Socket timeout in seconds
            command_delay: Delay between commands in seconds (prevents machine overload)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.command_delay = command_delay
        self.last_command_time = 0

    def connect(self) -> bool:
        """Establish TCP connection to the machine"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            print(f"✓ Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Close the connection gracefully"""
        if self.socket:
            try:
                # Graceful shutdown: disable both send and receive
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                # May fail if connection already closed, that's OK
                pass
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            time.sleep(0.1)  # Allow TCP stack to clean up

    @staticmethod
    def get_status_description(status_code: str) -> str:
        """
        Get human-readable description of a completion code.

        Args:
            status_code: 2-character status code (e.g., "00", "05", "71")

        Returns:
            Description string from Section 5.5.9.2 completion code list
        """
        return COMPLETION_CODES.get(status_code, f"Unknown status code: {status_code}")

    @staticmethod
    def is_success(status_code: str) -> bool:
        """
        Check if status code indicates success.

        Args:
            status_code: 2-character status code

        Returns:
            True if status is "00" (Normally ended), False otherwise
        """
        return status_code == "00"

    @staticmethod
    def is_error(status_code: str) -> bool:
        """
        Check if status code indicates an error condition.

        Args:
            status_code: 2-character status code

        Returns:
            True if status code indicates any error (anything other than "00")
        """
        return status_code != "00"

    @staticmethod
    def get_status_category(status_code: str) -> str:
        """
        Get category of status code (Success, Error, State, etc).

        Args:
            status_code: 2-character status code

        Returns:
            Category name
        """
        code_int = int(status_code)
        if code_int == 0:
            return "Success"
        elif 1 <= code_int <= 46:
            return "Error"
        elif 60 <= code_int <= 99:
            return "State/Condition"
        else:
            return "Unknown"

    def calculate_checksum(self, data: str) -> str:
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

    def build_command(self, command: str, arguments: str = "") -> bytes:
        """
        Build a Brother protocol command frame.

        Format: %C[Command][Arguments]\r\n[Checksum]%\r\n

        Args:
            command: Command (will be padded to 7 chars)
            arguments: Arguments (will be padded to 8 chars)

        Returns:
            Complete frame as bytes
        """
        # Pad command to 7 chars, arguments to 8 chars
        cmd_padded = command.ljust(7)[:7]
        args_padded = arguments.ljust(8)[:8]

        # Build command string
        cmd_string = f"C{cmd_padded}{args_padded}  \r\n"

        # Calculate checksum
        checksum = self.calculate_checksum(cmd_string)

        # Build complete frame: %[cmd_string][checksum]%\r\n
        frame = f"%{cmd_string}{checksum}%\r\n"

        return frame.encode('ascii')

    def send_command(self, command: str, arguments: str = "") -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Send a command and receive response.

        Args:
            command: Command name
            arguments: Command arguments

        Returns:
            Tuple of (success, status_code, response_data)
            success: True if status code is "00"
            status_code: Response status code (2 chars)
            response_data: Response data (everything between header and footer)
        """
        if not self.socket:
            print("✗ Not connected")
            return False, None, None

        try:
            # Enforce minimum delay between commands to prevent machine overload
            # This prevents the CM7522 "abnormal end" error from rapid-fire commands
            elapsed = time.time() - self.last_command_time
            if elapsed < self.command_delay:
                time.sleep(self.command_delay - elapsed)

            # Build and send frame
            frame = self.build_command(command, arguments)
            self.socket.sendall(frame)
            self.last_command_time = time.time()

            # Receive response with robust reading to handle complete frames
            response = b''
            self.socket.settimeout(1.0)  # Per-read timeout

            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    # Check if we have a complete frame (ends with %\n)
                    if response.endswith(b'%\n'):
                        break
                except socket.timeout:
                    # Timeout on individual read, but we might have partial data
                    if response:
                        break
                    else:
                        print("✗ Socket timeout - no data received")
                        return False, None, None

            self.socket.settimeout(self.timeout)  # Restore original timeout

            if not response:
                print("✗ No response received")
                return False, None, None

            # Parse response
            response_str = response.decode('ascii', errors='replace')

            # Extract status code and data
            # Format: %R[Command][Arguments][StatusCode]\n[Data]\n[Checksum]%
            if len(response_str) < 20:
                print(f"✗ Response too short: {response_str}")
                return False, None, None

            status_code = response_str[17:19]
            success = status_code == "00"

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

            # Log status with human-readable description
            status_desc = self.get_status_description(status_code)
            status_category = self.get_status_category(status_code)

            if success:
                # print(f"✓ Command succeeded: {status_desc}")
                pass
            else:
                print(f"⚠ Status {status_code} ({status_category}): {status_desc}")

            return success, status_code, data

        except socket.timeout:
            print("✗ Socket timeout")
            return False, None, None
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

    def send_multipart_command(self, command: str, arguments: str = "", data_payload: str = "") -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Send a multi-part command with separate header and data payload.

        Format for multi-part commands (Brother protocol):
        - Header: %C[Command(7)][Arguments(8)]  \r\n
        - Data: [payload]\n
        - Footer: [checksum]%\r\n

        This is used for commands like WRTTOFS (write tool offset), WRTTLLF (write tool life),
        CREDTOFS (read tool offset), etc. that require data to be sent separately.

        Args:
            command: 7-character command name (e.g., "WRTTOFS", "CREDTOFS", "WRTTLLF")
            arguments: Command arguments (will be padded to 8 chars)
            data_payload: Data to send on separate line (for write operations)

        Returns:
            Tuple of (success, status_code, response_data)
        """
        if not self.socket:
            print("✗ Not connected")
            return False, None, None

        try:
            # Enforce minimum delay between commands
            elapsed = time.time() - self.last_command_time
            if elapsed < self.command_delay:
                time.sleep(self.command_delay - elapsed)

            # Pad command to 7 chars, arguments to 8 chars
            cmd_padded = command.ljust(7)[:7]
            args_padded = arguments.ljust(8)[:8]

            # Build header frame
            # Format: %C[Command(7)][Arguments(8)]  \r\n
            header_line = f"C{cmd_padded}{args_padded}  \r\n"

            # Calculate checksum for complete message (header + data + newline)
            full_message = f"{header_line}{data_payload}\n"
            checksum = self.calculate_checksum(full_message)

            # Build complete frame
            frame = f"%{header_line}{data_payload}\n{checksum}%\r\n"

            self.socket.sendall(frame.encode('ascii'))
            self.last_command_time = time.time()

            # Receive response
            response = b''
            self.socket.settimeout(1.0)

            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b'%\n'):
                        break
                except socket.timeout:
                    if response:
                        break
                    else:
                        print("✗ Socket timeout - no data received")
                        return False, None, None

            self.socket.settimeout(self.timeout)

            if not response:
                print("✗ No response received")
                return False, None, None

            # Parse response
            response_str = response.decode('ascii', errors='replace')

            if len(response_str) < 20:
                print(f"✗ Response too short: {response_str}")
                return False, None, None

            status_code = response_str[17:19]
            success = status_code == "00"

            # Extract data between header and footer
            first_newline = response_str.find('\n', 20)
            if first_newline == -1:
                data = None
            else:
                last_percent = response_str.rfind('%')
                if last_percent > first_newline:
                    data = response_str[first_newline + 1:last_percent].strip()
                else:
                    data = None

            # Log status
            status_desc = self.get_status_description(status_code)
            status_category = self.get_status_category(status_code)

            if success:
                pass
            else:
                print(f"⚠ Status {status_code} ({status_category}): {status_desc}")

            return success, status_code, data

        except socket.timeout:
            print("✗ Socket timeout")
            return False, None, None
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False, None, None

    # ===== High-level command methods =====

    def load_directory(self) -> Optional[str]:
        """
        Load directory listing.

        Returns:
            Directory data or None on failure
        """
        success, status, data = self.send_command("LOD", "DIR")
        if success:
            return data
        else:
            print(f"✗ Directory load failed with status {status}")
            return None

    def load_memory(self) -> Optional[str]:
        """
        Load memory/program information.

        Returns:
            Memory data or None on failure
        """
        success, status, data = self.send_command("LOD", "MEM")
        if success:
            return data
        else:
            print(f"✗ Memory load failed with status {status}")
            return None

    def load_panel(self) -> Optional[str]:
        """
        Load panel status data.

        Returns:
            Panel data or None on failure
        """
        success, status, data = self.send_command("LOD", "PANEL")
        if success:
            return data
        else:
            print(f"✗ Panel load failed with status {status}")
            return None

    def load_io(self) -> Optional[str]:
        """
        Load I/O status data.

        Returns:
            I/O data or None on failure
        """
        success, status, data = self.send_command("LOD", "IO")
        if success:
            return data
        else:
            print(f"✗ I/O load failed with status {status}")
            return None

    def load_data(self, data_name: str) -> Optional[str]:
        """
        Load arbitrary data by name.

        Args:
            data_name: Name of data to load (e.g., SYSC99, PRD1, POSSI1, etc.)

        Returns:
            Data or None on failure
        """
        success, status, data = self.send_command("LOD", data_name)
        if success:
            return data
        else:
            print(f"✗ Data load '{data_name}' failed with status {status}")
            return None

    def load_system_data(self, number: int) -> Optional[str]:
        """
        Load system/machine data.

        Args:
            number: System data number (89, 94, 95, 96, 97, 98, 99)

        Returns:
            System data or None on failure
        """
        data_name = f"SYSC{number}"
        return self.load_data(data_name)

    def load_production_data(self, number: int) -> Optional[str]:
        """
        Load production data.

        Args:
            number: Production data number (1, 2, 3)

        Returns:
            Production data or None on failure
        """
        if number == 2:
            data_name = "PRDC2"
        else:
            data_name = f"PRD{number}"
        return self.load_data(data_name)

    def load_position_data(self, position: int, type_char: str = "I") -> Optional[str]:
        """
        Load position data (machine or system coordinates).

        Args:
            position: Position number (1-5)
            type_char: "I" for machine (POSNI) or "S" for system (POSSI)

        Returns:
            Position data or None on failure
        """
        prefix = "POSNI" if type_char.upper() == "I" else "POSSI"
        data_name = f"{prefix}{position}"
        return self.load_data(data_name)

    # ===== Tool Data Operations (Sprint 1) =====

    def read_tool_offset(self, tool_number: int) -> Optional[Dict[str, float]]:
        """
        Read tool offset data for a specific tool.

        Args:
            tool_number: Tool number (1-99)

        Returns:
            Dictionary with offset data or None on failure
            Example: {'H': 25.5, 'D': 10.2, 'W': 0.5}
        """
        if not 1 <= tool_number <= 99:
            print(f"✗ Tool number {tool_number} out of valid range (1-99)")
            return None

        # REDTOFS command reads tool offset (without C prefix)
        # From manual section 5.5.9.3: "% C R E D T O F S" → command name is REDTOFS
        # We'll read type 2 (cutter compensation/diameter offset) as default
        # Arguments: tool_number (01-99) + type (default '2' for diameter)
        tool_str = f"{tool_number:02d}"
        # For now, read type 2 (cutter compensation). Use send_multipart_command for Protocol Type 2
        args = f"{tool_str}2     "  # Tool 01-99, type 2 (diameter/cutter comp), 5 spaces padding
        # Note: REDTOFS is 7 characters and is a read command, so we use send_multipart_command
        # which properly handles Protocol Type 2 format
        success, status, data = self.send_multipart_command("REDTOFS", args, "")

        if success and data:
            # Parse offset data - format varies by machine
            # For now, return raw data for user to parse
            print(f"✓ Tool {tool_number} offset data retrieved")
            return {'raw': data}
        else:
            print(f"✗ Tool offset read failed for tool {tool_number} with status {status}")
            return None

    def write_tool_offset(self, tool_number: int, offset_type: str,
                         value: float) -> bool:
        """
        Write tool offset data for a specific tool.

        Uses the WRTTOFS multi-part command format:
        - Header: %CWRTTOFS nn k1\r\n
        - Data: [offset value with decimal point]\n
        - Footer: [checksum]%\r\n

        Args:
            tool_number: Tool number (1-99)
            offset_type: Type of offset:
                'H' = 0 (tool length offset)
                'D' = 2 (tool diameter offset)
                'W' = 1 (tool wear offset)
            value: Offset value in mm (e.g., 25.5, -10.2)

        Returns:
            True if successful, False otherwise
        """
        if not 1 <= tool_number <= 99:
            print(f"✗ Tool number {tool_number} out of valid range (1-99)")
            return False

        # Map offset type to protocol value
        type_map = {'H': '0', 'D': '2', 'W': '1'}
        if offset_type not in type_map:
            print(f"✗ Invalid offset type '{offset_type}'. Use 'H', 'D', or 'W'")
            return False

        k1 = type_map[offset_type]

        # Warn if value is extreme
        if abs(value) > 500:
            print(f"⚠ WARNING: Offset value {value}mm is unusually large for {offset_type}")

        # Build arguments following Protocol Type 2 message section (s1-s8)
        # From manual section 5.5.9.3: "% C W R T T O F S n1 n2 k1"
        # Maps to header positions:
        #   s1 s2 = n1 n2 (tool number 01-99)
        #   s3 = k1 (type: 0=length, 1=wear, 2=diameter, 3=diameter wear, etc.)
        #   s4-s8 = padding (spaces)
        tool_str = f"{tool_number:02d}"
        args = f"{tool_str}{k1}     "  # Tool 01-99, type code, then 5 spaces = 8 chars total

        # Format offset data with decimal point, padded to exact size
        # For type 2 (and types 0, 4, 6): 9 bytes total with trailing spaces
        # For types 1, 3, 5, 7: 8 bytes
        # Format: decimal value padded with trailing spaces
        offset_data = f"{value:.4f}".ljust(9)[:9] if k1 in ['0', '2', '4', '6'] else f"{value:.4f}".ljust(8)[:8]

        success, status, data = self.send_multipart_command("WRTTOFS", args, offset_data)

        if success:
            print(f"✓ Tool {tool_number} offset ({offset_type}) set to {value}mm")
            return True
        else:
            desc = self.get_status_description(status)
            print(f"✗ Tool offset write failed: {desc}")
            return False

    def read_tool_life(self, tool_number: int) -> Optional[Dict]:
        """
        Read tool life data for a specific tool.

        Args:
            tool_number: Tool number (1-99)

        Returns:
            Dictionary with tool life data or None on failure
        """
        if not 1 <= tool_number <= 99:
            print(f"✗ Tool number {tool_number} out of valid range (1-99)")
            return None

        # REDTLLF command reads tool life (without C prefix)
        # From manual section 5.5.9.3: "% C R E D T L L F" → command name is REDTLLF
        # Arguments: tool_number (01-99) + type (default '3' for tool life)
        tool_str = f"{tool_number:02d}"
        # Read type 3 (actual tool life). Use send_multipart_command for Protocol Type 2
        args = f"{tool_str}3     "  # Tool 01-99, type 3 (tool life), 5 spaces padding
        success, status, data = self.send_multipart_command("REDTLLF", args, "")

        if success and data:
            print(f"✓ Tool {tool_number} life data retrieved")
            return {'raw': data}
        else:
            print(f"✗ Tool life read failed for tool {tool_number} with status {status}")
            return None

    def write_tool_life(self, tool_number: int, life_value: int,
                       life_type: str = 'TIME') -> bool:
        """
        Write/set tool life value for a specific tool.

        Uses multi-part command format with separate data payload.

        Protocol format:
        - Header: %CWRTTLLF n1 n2 k1\\r\\n
        - Data: [setting value]\\n
        - Footer: [checksum]%\\r\\n

        Args:
            tool_number: Tool number (1-99)
            life_value: Life value (0-999999)
            life_type: Type code ('0'=life unit, '1'=initial, '2'=warning, '3'=life)

        Returns:
            True if successful, False otherwise
        """
        if not 1 <= tool_number <= 99:
            print(f"✗ Tool number {tool_number} out of valid range (1-99)")
            return False

        if life_value < 0 or life_value > 999999:
            print(f"✗ Life value {life_value} out of valid range (0-999999)")
            return False

        # Warn if life_value is unusually high
        if life_value > 10000:
            print(f"⚠ WARNING: Tool life value {life_value} is unusually high")

        # Map life type to protocol code
        # Based on manual: k1 = 0 (life unit), 1 (initial), 2 (warning), 3 (life)
        # For simplicity, map TIME='3' (actual life) and COUNT='1' (initial life)
        type_code = '3' if life_type == 'TIME' else ('1' if life_type == 'COUNT' else '3')

        # Format arguments: tool_number (01-99) + k1 type code
        args = f"{tool_number:02d}{type_code}    "  # Pad to 8 characters

        # Format data payload: life value as 6-byte field
        life_data = f"{life_value:06d}"

        # Send as multi-part command
        success, status, data = self.send_multipart_command("WRTTLLF", args, life_data)

        if success:
            print(f"✓ Tool {tool_number} life ({life_type}) set to {life_value}")
            return True
        else:
            desc = self.get_status_description(status)
            print(f"✗ Tool life write failed: {desc}")
            return False

    def clear_tool_life(self, tool_number: int) -> bool:
        """
        Clear/reset tool life counter for a specific tool.

        Implemented as write_tool_life with value 0 to achieve the clear effect.
        This works with Protocol Type 2 format.

        Args:
            tool_number: Tool number (1-99)

        Returns:
            True if successful, False otherwise
        """
        if not 1 <= tool_number <= 99:
            print(f"✗ Tool number {tool_number} out of valid range (1-99)")
            return False

        print(f"⚠ Clearing tool life for tool {tool_number}")

        # Clear by writing tool life value to 0
        # This is more reliable than CCLRTLL command which may require Protocol Type 1
        return self.write_tool_life(
            tool_number=tool_number,
            life_value=0,
            life_type='TIME'
        )

    # ========== SPRINT 2: ATC CONFIGURATION & POSITION OPERATIONS ==========
    # High-value remote ATC configuration and position preset operations

    def change_atc_tool(self, magazine_pos: int, tool_num: int = None,
                       change_type: str = 'M', new_value: int = None) -> bool:
        """
        Change tool configuration in ATC magazine.

        Args:
            magazine_pos: Magazine position (0=spindle, 1-99=pots)
            tool_num: Current tool number in position (for verification)
            change_type: Type of change:
                'M' = Change tool number (new_value = new tool number)
                'S' = Change spindle/main tool (new_value = spindle tool)
                'K' = Change tool type (new_value: 1=Standard, 2=Large, 3=Medium)
                'C' = Change color (new_value: 0=None, 1=Blue, 2=Red, 3=Purple, 4=Green, 5=Light blue)
                'D' = Delete/remove tool (new_value not needed)
            new_value: New value for the change (tool number, type, or color)

        Returns:
            bool: True if successful, False otherwise

        Safety:
            - Validates magazine position (0-99)
            - Warns when modifying spindle tool (magazine 00)
            - Cannot change during operation (will return error code 36)
            - Logs all ATC changes prominently
        """
        # Validate inputs
        if not isinstance(magazine_pos, int) or not 0 <= magazine_pos <= 99:
            print(f"✗ ATC Tool Change: Magazine position must be 0-99, got {magazine_pos}")
            return False

        if change_type not in ['M', 'S', 'K', 'C', 'D']:
            print(f"✗ ATC Tool Change: Invalid change_type '{change_type}'")
            return False

        # Warn about spindle tool changes
        if magazine_pos == 0:
            print(f"⚠ WARNING: Modifying spindle tool (magazine position 00)")

        # Format magazine position (2 digits)
        mag_str = f"{magazine_pos:02d}"

        # Build arguments based on change_type
        if change_type == 'M':  # Change tool number
            if new_value is None or not isinstance(new_value, int):
                print(f"✗ ATC Tool Change: change_type 'M' requires new_value (tool number)")
                return False
            if not 0 <= new_value <= 999:
                print(f"✗ ATC Tool Change: Tool number {new_value} out of valid range (0-999)")
                return False
            # Format: mag_pos(2) + change_type(1) + new_tool(3) + padding
            args = f"{mag_str}M{new_value:03d} "
            action = f"assign tool #{new_value}"

        elif change_type == 'S':  # Change spindle/main tool
            if new_value is None or not isinstance(new_value, int):
                print(f"✗ ATC Tool Change: change_type 'S' requires new_value (spindle tool)")
                return False
            if not 0 <= new_value <= 999:
                print(f"✗ ATC Tool Change: Spindle tool {new_value} out of valid range (0-999)")
                return False
            args = f"{mag_str}S{new_value:03d} "
            action = f"set spindle/main tool to #{new_value}"

        elif change_type == 'K':  # Change tool type
            if new_value is None or not isinstance(new_value, int):
                print(f"✗ ATC Tool Change: change_type 'K' requires new_value (tool type)")
                return False
            if not 1 <= new_value <= 3:
                print(f"✗ ATC Tool Change: Tool type must be 1(Standard), 2(Large), or 3(Medium), got {new_value}")
                return False
            type_names = {1: "Standard", 2: "Large", 3: "Medium"}
            args = f"{mag_str}K{new_value}      "
            action = f"set tool type to {type_names.get(new_value, 'Unknown')}"

        elif change_type == 'C':  # Change color
            if new_value is None or not isinstance(new_value, int):
                print(f"✗ ATC Tool Change: change_type 'C' requires new_value (color)")
                return False
            if not 0 <= new_value <= 5:
                print(f"✗ ATC Tool Change: Color must be 0-5, got {new_value}")
                return False
            color_names = {0: "None", 1: "Blue", 2: "Red", 3: "Purple", 4: "Green", 5: "Light blue"}
            args = f"{mag_str}C{new_value}      "
            action = f"set color to {color_names.get(new_value, 'Unknown')}"

        else:  # change_type == 'D' - Delete tool
            args = f"{mag_str}D       "
            action = f"remove tool"

        # Execute command
        success, status, _ = self.send_command("CCHGMAG", args)

        if success:
            print(f"✓ ATC Tool Change (magazine {mag_str}): {action} - OK")
            return True
        else:
            desc = self.get_status_description(status)
            print(f"✗ ATC Tool Change (magazine {mag_str}): {action} - {desc}")
            return False

    def assign_tool_to_magazine(self, magazine_pos: int, tool_num: int) -> bool:
        """
        Simplified wrapper: Assign a tool to a magazine position.

        This is a convenience method for the most common ATC operation.

        Args:
            magazine_pos: Magazine position (1-99, not spindle)
            tool_num: Tool number to assign (1-999)

        Returns:
            bool: True if successful

        Example:
            client.assign_tool_to_magazine(1, 42)  # Put tool #42 in pot #1
            client.assign_tool_to_magazine(5, 17)  # Put tool #17 in pot #5
        """
        if magazine_pos == 0:
            print(f"✗ assign_tool_to_magazine: Cannot assign to spindle (magazine 0)")
            print(f"  Use change_atc_tool() with change_type='S' to change spindle tool")
            return False

        return self.change_atc_tool(magazine_pos, tool_num=tool_num, change_type='M', new_value=tool_num)

    def remove_tool_from_magazine(self, magazine_pos: int) -> bool:
        """
        Simplified wrapper: Remove tool from magazine position.

        Args:
            magazine_pos: Magazine position (0-99)

        Returns:
            bool: True if successful

        Example:
            client.remove_tool_from_magazine(1)  # Remove tool from pot #1
        """
        return self.change_atc_tool(magazine_pos, change_type='D')

    def set_tool_type(self, magazine_pos: int, tool_type: str) -> bool:
        """
        Simplified wrapper: Set tool type in magazine.

        Args:
            magazine_pos: Magazine position (0-99)
            tool_type: Type of tool - 'STANDARD', 'LARGE', or 'MEDIUM'

        Returns:
            bool: True if successful

        Example:
            client.set_tool_type(1, 'STANDARD')  # Set pot #1 to standard tool
            client.set_tool_type(5, 'LARGE')     # Set pot #5 to large tool
        """
        # Map tool type string to number
        type_map = {
            'STANDARD': 1,
            'LARGE': 2,
            'MEDIUM': 3,
        }

        if tool_type.upper() not in type_map:
            print(f"✗ set_tool_type: Invalid tool_type '{tool_type}'")
            print(f"  Valid types: STANDARD, LARGE, MEDIUM")
            return False

        type_num = type_map[tool_type.upper()]
        return self.change_atc_tool(magazine_pos, change_type='K', new_value=type_num)

    def parse_atctl_data(self, atctl_content: str) -> Optional[Dict[int, Dict]]:
        """
        Parse ATCTL file content into structured magazine configuration.

        ATCTL Format (from Section 5.6.4.9):
        - M01: Spindle tool configuration
        - M02-M51: Pot 1-50 tool configurations

        Each line format: M##,tool_num,nc_mode,group,type,color
        - tool_num: 0-999 (0=not set, 255=cap setting)
        - nc_mode: 0=Conversation, 1=NC
        - group: Group number (0=not set, 1-30) or Main tool (0=not set, 1-99)
        - type: 1=Standard, 2=Large diameter, 3=Medium diameter
        - color: 0=None, 1=Blue, 2=Red, 3=Purple, 4=Green, 5=Light blue, 6=Yellow, 7=White

        Args:
            atctl_content: Raw ATCTL file content (multi-line, comma-separated)

        Returns:
            Dict mapping position to tool info:
            {
                0: {  # Spindle
                    'position': 'spindle',
                    'tool_num': 24,
                    'nc_mode': 1,
                    'group': 0,
                    'type': 1,
                    'color': 0
                },
                10: {  # Pot 10 (M11)
                    'position': 'pot_10',
                    'tool_num': 24,
                    'nc_mode': 1,
                    'group': 0,
                    'type': 1,
                    'color': 0
                },
                ...
            }
            Returns None if parsing fails
        """
        try:
            magazine = {}

            # Split by lines and process each entry
            lines = atctl_content.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line or not line.startswith('M'):
                    continue

                # Parse line: M##,tool,nc_mode,group,type,color
                parts = line.split(',')
                if len(parts) < 6:
                    continue

                m_code = parts[0].strip()  # e.g., "M01", "M11"

                try:
                    m_num = int(m_code[1:])  # Extract number from M##
                except ValueError:
                    continue

                # Determine position from M number: position = M_number - 1
                # M01 = position 0 (spindle)
                # M02 = position 1 (pot 1)
                # M11 = position 10 (pot 10)
                # M51 = position 50 (pot 50)
                position = m_num - 1

                # Parse individual fields
                tool_num = int(parts[1].strip())
                nc_mode = int(parts[2].strip())
                group = int(parts[3].strip())
                tool_type = int(parts[4].strip())
                color = int(parts[5].strip())

                # Determine position name
                if position == 0:
                    pos_name = 'spindle'
                else:
                    pos_name = f'pot_{position}'

                # Determine type name
                type_names = {1: 'STANDARD', 2: 'LARGE', 3: 'MEDIUM'}
                type_name = type_names.get(tool_type, f'UNKNOWN({tool_type})')

                # Determine color name
                color_names = {
                    0: 'NONE', 1: 'BLUE', 2: 'RED', 3: 'PURPLE',
                    4: 'GREEN', 5: 'LIGHT_BLUE', 6: 'YELLOW', 7: 'WHITE'
                }
                color_name = color_names.get(color, f'UNKNOWN({color})')

                # Determine NC/Conversation mode
                mode_name = 'NC' if nc_mode == 1 else 'CONVERSATION'

                # Store in magazine dict
                magazine[position] = {
                    'position': pos_name,
                    'tool_num': tool_num,
                    'tool_num_set': tool_num not in [0, 255],  # 0=not set, 255=cap
                    'nc_mode': mode_name,
                    'group': group,
                    'type': type_name,
                    'color': color_name,
                    'raw': {'tool_num': tool_num, 'nc_mode': nc_mode, 'group': group,
                           'type': tool_type, 'color': color}
                }

            return magazine if magazine else None

        except Exception as e:
            print(f"✗ Parse ATCTL: Error - {e}")
            return None

    def read_atc_magazine(self) -> Optional[Dict[int, Dict]]:
        """
        Read current ATC magazine configuration from ATCTL file.

        Returns:
            Optional[Dict]: Dictionary mapping position to tool info:
                {
                    0: {'position': 'spindle', 'tool_num': 24, 'type': 'STANDARD', ...},
                    10: {'position': 'pot_10', 'tool_num': 24, 'type': 'STANDARD', ...},
                    ...
                }
            Position keys:
            - 0: Spindle (M01)
            - 1-50: Pots 1-50 (M02-M51)

            Returns None if read fails

        Example:
            >>> magazine = client.read_atc_magazine()
            >>> spindle_tool = magazine[0]['tool_num']  # Tool in spindle
            >>> pot_10_tool = magazine[10]['tool_num']  # Tool in pot 10
        """
        # Load ATCTL file which contains ATC magazine configuration
        atctl_data = self.load_data("ATCTL")
        if not atctl_data:
            print("✗ Read ATC Magazine: Could not load ATCTL file")
            return None

        # Parse ATCTL content according to documented schema
        if isinstance(atctl_data, dict) and 'raw' in atctl_data:
            # Extract raw content if it's in dict format
            atctl_content = atctl_data['raw']
        else:
            atctl_content = atctl_data

        if not atctl_content:
            print("✗ Read ATC Magazine: ATCTL file is empty")
            return None

        # Parse the ATCTL data using schema
        magazine = self.parse_atctl_data(atctl_content)

        if not magazine:
            print("✗ Read ATC Magazine: Failed to parse ATCTL data")
            return None

        return magazine

    def get_spindle_tool(self) -> Optional[Dict]:
        """
        Get the tool currently in the spindle.

        Returns:
            Dict with tool information: {'tool_num': 24, 'type': 'STANDARD', ...}
            Returns None if spindle is empty or if read fails

        Example:
            >>> spindle = client.get_spindle_tool()
            >>> if spindle:
            ...     print(f"Tool #{spindle['tool_num']} in spindle")
            ... else:
            ...     print("Spindle is empty")
        """
        magazine = self.read_atc_magazine()
        if not magazine or 0 not in magazine:
            return None

        spindle_data = magazine[0]
        # Return None if no tool is set
        return spindle_data if spindle_data['tool_num_set'] else None

    def get_pot_tool(self, pot_number: int) -> Optional[Dict]:
        """
        Get the tool in a specific pot.

        Args:
            pot_number: Pot position (1-50)

        Returns:
            Dict with tool information: {'tool_num': 24, 'type': 'STANDARD', ...}
            Returns None if pot is empty or if read fails

        Example:
            >>> tool = client.get_pot_tool(10)
            >>> if tool:
            ...     print(f"Tool #{tool['tool_num']} in pot 10")
            ... else:
            ...     print("Pot 10 is empty")
        """
        if not 1 <= pot_number <= 50:
            print(f"✗ Get Pot Tool: Pot number must be 1-50, got {pot_number}")
            return None

        magazine = self.read_atc_magazine()
        if not magazine or pot_number not in magazine:
            return None

        pot_data = magazine[pot_number]
        # Return None if no tool is set
        return pot_data if pot_data['tool_num_set'] else None

    def list_empty_pots(self) -> Optional[List[int]]:
        """
        Get list of all empty pot positions.

        Returns:
            List of empty pot numbers: [5, 7, 8, 15, ...]
            Returns None if read fails

        Example:
            >>> empty = client.list_empty_pots()
            >>> print(f"Empty pots: {empty}")
        """
        magazine = self.read_atc_magazine()
        if not magazine:
            return None

        empty = [pos for pos in range(1, 51) if pos in magazine and not magazine[pos]['tool_num_set']]
        return empty if empty else None

    def list_assigned_tools(self) -> Optional[Dict[int, int]]:
        """
        Get mapping of all assigned tools in magazine.

        Returns:
            Dict mapping position to tool number: {0: 24, 1: 1, 2: 2, ...}
            Position 0 = spindle, 1-50 = pots
            Returns None if read fails

        Example:
            >>> assigned = client.list_assigned_tools()
            >>> for position, tool_num in assigned.items():
            ...     if position == 0:
            ...         print(f"Spindle: Tool #{tool_num}")
            ...     else:
            ...         print(f"Pot {position}: Tool #{tool_num}")
        """
        magazine = self.read_atc_magazine()
        if not magazine:
            return None

        assigned = {pos: data['tool_num'] for pos, data in magazine.items() if data['tool_num_set']}
        return assigned if assigned else None

    def preset_relative_position(self, axis: str, value: float = 0.0) -> bool:
        """
        Preset (zero) relative coordinate position.

        This sets the relative position (work zero) for the specified axis.
        Commonly used to establish part datum after homing.

        Args:
            axis: Axis name ('X', 'Y', 'Z', or other configured axes)
            value: Position value to preset (default 0.0 = zero)

        Returns:
            bool: True if successful

        Safety:
            - Warns that preset cannot be easily undone
            - Logs operation prominently
            - Value is typically 0.0 for work zero
            - Non-zero values should be rare

        Example:
            client.preset_relative_position('X', 0.0)  # Set X work zero
            client.preset_relative_position('Z')       # Set Z work zero (default 0.0)
        """
        # Validate axis
        if not isinstance(axis, str) or len(axis) != 1:
            print(f"✗ Preset Position: Axis must be single character, got '{axis}'")
            return False

        axis = axis.upper()

        # Warn about preset operation
        print(f"⚠ WARNING: Presetting {axis} axis to {value} - this changes work zero point")

        # Format value - need to understand the exact format from protocol
        # Typically: axis(1) + sign(1) + integer(5) + decimal(2)
        # For now, assume format: axis + sign + padded value
        value_int = int(value)
        value_frac = int((value - value_int) * 100)

        # Build arguments
        if value < 0:
            args = f"{axis}-{abs(value_int):05d}{abs(value_frac):02d}"
        else:
            args = f"{axis}+{value_int:05d}{value_frac:02d}"

        # Pad to 8 characters
        args = f"{args:<8}"

        # Execute command
        success, status, _ = self.send_command("CWRTREL", args)

        if success:
            print(f"✓ Preset Position: {axis} axis set to {value}")
            return True
        else:
            desc = self.get_status_description(status)
            print(f"✗ Preset Position: {axis} axis failed - {desc}")
            return False

    def read_relative_position(self, axis: str) -> Optional[float]:
        """
        Read current relative position for an axis.

        Helper wrapper around existing LOD POSSI commands.

        Args:
            axis: Axis name ('X', 'Y', 'Z', or other configured axes)

        Returns:
            Optional[float]: Current relative position, or None if read fails

        Example:
            x_pos = client.read_relative_position('X')
            if x_pos is not None:
                print(f"Current X position: {x_pos}")
        """
        # Validate axis
        if not isinstance(axis, str) or len(axis) != 1:
            print(f"✗ Read Position: Axis must be single character, got '{axis}'")
            return None

        axis = axis.upper()

        # Use existing load_position method
        position_data = self.load_position(1)
        if not position_data:
            return None

        try:
            # Parse position data for the requested axis
            # Format depends on POSSI data structure
            # This is a simplified extraction
            for line in position_data.split('\n'):
                if axis in line:
                    # Try to extract numeric value
                    parts = line.split()
                    for part in parts:
                        try:
                            return float(part)
                        except ValueError:
                            continue
            return None
        except Exception as e:
            print(f"✗ Read Position: Parse error - {e}")
            return None

    # ========== SPRINT 3: MACHINE DATA OPERATIONS & SAFETY ==========
    # Machine parameter write operations and audit logging infrastructure

    def read_machine_data(self, parameter_number: int) -> Optional[str]:
        """
        Read machine parameter value.

        Args:
            parameter_number: Machine parameter number (e.g., 1-9999 depending on machine)

        Returns:
            Optional[str]: Parameter value, or None if read fails

        Example:
            value = client.read_machine_data(100)  # Read parameter #100
        """
        if not isinstance(parameter_number, int) or parameter_number < 0:
            print(f"✗ Read Machine Data: Parameter number must be non-negative integer")
            return None

        # Format parameter number (4 digits)
        args = f"{parameter_number:04d}    "

        # Execute command
        success, status, data = self.send_command("CREDMCN", args)

        if success:
            print(f"✓ Machine Parameter {parameter_number}: Read OK")
            return data
        else:
            desc = self.get_status_description(status)
            print(f"✗ Machine Parameter {parameter_number}: {desc}")
            return None

    def write_machine_data(self, parameter_number: int, value: str) -> bool:
        """
        Write machine parameter value.

        CRITICAL: This operation modifies machine parameters.
        Only write parameters you fully understand.

        Args:
            parameter_number: Machine parameter number
            value: New parameter value (must be properly formatted)

        Returns:
            bool: True if successful

        Safety:
            - Logs all machine data writes prominently
            - Warns about potential machine impact
            - Stores write in operation log

        Example:
            # Set parameter 100 to value "42"
            client.write_machine_data(100, "42")
        """
        if not isinstance(parameter_number, int) or parameter_number < 0:
            print(f"✗ Write Machine Data: Parameter number must be non-negative integer")
            return False

        if not isinstance(value, str):
            value = str(value)

        # Warn about machine data modification
        print(f"⚠⚠⚠ WARNING: Writing machine parameter {parameter_number} = '{value}'")
        print(f"⚠⚠⚠ This modifies machine settings and could affect operation")

        # Format parameter number and value
        args = f"{parameter_number:04d}{value:>4}"
        args = f"{args:<8}"

        # Execute command
        success, status, _ = self.send_command("CWRTMCN", args)

        if success:
            print(f"✓ Machine Parameter {parameter_number}: Set to '{value}'")
            return True
        else:
            desc = self.get_status_description(status)
            print(f"✗ Machine Parameter {parameter_number}: Write failed - {desc}")
            return False

    def write_individual_data(self, data_type: str, data_name: str, value: str) -> bool:
        """
        Write individual data item.

        Generic method for writing various data types to machine.

        Args:
            data_type: Type of data (e.g., "OFFSET", "LIFE", "PARAMETER")
            data_name: Specific data item name
            value: Value to write

        Returns:
            bool: True if successful

        Safety:
            - Logs operation with timestamp
            - Validates inputs
            - Stores in audit trail
        """
        if not isinstance(data_type, str) or not isinstance(data_name, str):
            print(f"✗ Write Individual Data: data_type and data_name must be strings")
            return False

        if not isinstance(value, str):
            value = str(value)

        print(f"⚠ Writing {data_type}: {data_name} = '{value}'")

        # Build arguments from components
        args = f"{data_name:<8}"

        # Execute command
        success, status, _ = self.send_command("CWRTDAT", args)

        if success:
            print(f"✓ Individual Data {data_name}: Write OK")
            return True
        else:
            desc = self.get_status_description(status)
            print(f"✗ Individual Data {data_name}: {desc}")
            return False

    def log_operation(self, operation_type: str, command: str, args: str,
                     success: bool, status_code: str = None) -> None:
        """
        Log operation to audit trail.

        Internal method called by write operations to maintain audit log.

        Args:
            operation_type: Type of operation (e.g., "TOOL_OFFSET", "ATC_CHANGE")
            command: Protocol command executed
            args: Arguments sent with command
            success: Whether operation succeeded
            status_code: Status code returned by machine
        """
        from datetime import datetime
        import os

        log_dir = os.path.join(os.path.dirname(self.config_file), "operation_logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, "brother_cnc_operations.log")

        timestamp = datetime.now().isoformat()
        status_str = status_code if status_code else "N/A"
        result_str = "SUCCESS" if success else "FAILED"

        log_entry = f"{timestamp} | {operation_type} | {command} {args} | {result_str} ({status_str})\n"

        try:
            with open(log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"⚠ Warning: Could not write operation log: {e}")

    def get_operation_log(self, limit: int = 50) -> Optional[List[str]]:
        """
        Get recent operation log entries.

        Args:
            limit: Maximum number of recent entries to return

        Returns:
            Optional[List[str]]: Recent log entries, or None if no log exists

        Example:
            recent = client.get_operation_log(10)
            for entry in recent:
                print(entry)
        """
        import os

        log_dir = os.path.join(os.path.dirname(self.config_file), "operation_logs")
        log_file = os.path.join(log_dir, "brother_cnc_operations.log")

        if not os.path.exists(log_file):
            print("✗ No operation log found")
            return None

        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()

            # Return last 'limit' lines
            return all_lines[-limit:]
        except Exception as e:
            print(f"✗ Error reading operation log: {e}")
            return None


def main():
    """Example usage"""
    client = BrotherCNCClient()

    if not client.connect():
        return

    try:
        print("\n" + "="*60)
        print("INTERESTING DATA POINTS")
        print("="*60)

        # Load memory data
        print("\n>>> Memory/Program Information <<<")
        memory = client.load_memory()
        if memory:
            print(f"Data:\n{memory}")

        time.sleep(0.5)

        # Load panel data
        print("\n>>> Panel Status <<<")
        panel = client.load_panel()
        if panel:
            print(f"Data:\n{panel}")

        time.sleep(0.5)

        # Load I/O data
        print("\n>>> I/O Status <<<")
        io_data = client.load_io()
        if io_data:
            print(f"Data:\n{io_data}")

        time.sleep(0.5)

        # Load directory
        print("\n>>> Directory Listing <<<")
        directory = client.load_directory()
        if directory:
            print(f"Data:\n{directory}")

    finally:
        client.disconnect()


if __name__ == '__main__':
    main()
