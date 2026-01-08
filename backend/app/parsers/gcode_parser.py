"""G-code parser for Brother CNC programs.

Extracts:
- Tool information (number, diameter, corner radius, length)
- Posted date from CAM header
- Runtime estimation based on move distances and feedrates
- WCS location (when available in post-processor output)
"""
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import math


class GCodeParser:
    """Parser for Brother CNC G-code programs."""

    def __init__(self, content: str):
        """
        Initialize parser with G-code content.

        Args:
            content: Full G-code program as string
        """
        self.content = content
        self.lines = content.split('\n')

    def parse(self) -> Dict[str, Any]:
        """
        Parse G-code and extract all relevant information.

        Returns:
            Dict containing:
                - tools: List of tool definitions
                - posted_date: Date program was posted from CAM
                - estimated_runtime_seconds: Estimated cycle time
                - wcs_location: Work coordinate system location (if available)
                - stock_size: Stock dimensions (if available)
                - line_count: Number of lines
                - file_size: Content size in bytes
        """
        # Extract tool metadata from header (gracefully handle failures)
        try:
            tools = self.extract_tools()
        except Exception:
            tools = []

        # Extract operation data (gracefully handle failures)
        try:
            tool_operations = self.extract_tool_operations()
        except Exception:
            tool_operations = {}

        # Merge operation data into tool metadata
        for tool in tools:
            tool_num = tool["tool_number"]
            if tool_num in tool_operations:
                tool["operations"] = tool_operations[tool_num]
            else:
                tool["operations"] = []

        # Extract other metadata (gracefully handle failures)
        try:
            posted_date = self.extract_posted_date()
        except Exception:
            posted_date = None

        try:
            estimated_runtime = self.estimate_runtime()
        except Exception:
            estimated_runtime = 0.0

        try:
            wcs_offset = self.extract_wcs_offset()
        except Exception:
            wcs_offset = None

        try:
            stock_size = self.extract_stock_size()
        except Exception:
            stock_size = None

        return {
            "tools": tools,
            "posted_date": posted_date,
            "estimated_runtime_seconds": estimated_runtime,
            "wcs_offset": wcs_offset,  # Actual WCS validation data
            "stock_size": stock_size,
            "line_count": len(self.lines),
            "file_size": len(self.content.encode('utf-8')),
        }

    def extract_tools(self) -> List[Dict[str, Any]]:
        """
        Extract tool definitions from CAM header comments.

        Expected format:
        (T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)
        (T02 D=0.25 CR=0.125 - ZMIN=-1.9677 - BALL END MILL - L=1.25/2.3917)

        Returns:
            List of dicts with tool_number, diameter, corner_radius, length_used, length_total, description
        """
        tools = []
        # Pattern: (T## D=diameter CR=corner_radius - ZMIN=... - description - L=used/total)
        # Note: ZMIN can be negative
        pattern = r'\(T(\d+)\s+D=([\d.]+)\s+CR=([\d.]+)\s+-\s+ZMIN=([-\d.]+)\s+-\s+([^-]+)\s+-\s+L=([\d.]+)/([\d.]+)\)'

        for line in self.lines:
            match = re.search(pattern, line)
            if match:
                tool_number = int(match.group(1))
                diameter = float(match.group(2))
                corner_radius = float(match.group(3))
                # zmin = float(match.group(4))  # Not used for validation
                description = match.group(5).strip()
                # length_used = float(match.group(6))  # Stick-out, not needed
                length_total = float(match.group(7))  # Required for validation

                tools.append({
                    "tool_number": tool_number,
                    "diameter": diameter,
                    "corner_radius": corner_radius,
                    "description": description,
                    "length_total": length_total,  # Required tool length
                })

        return tools

    def extract_tool_operations(self) -> Dict[int, List[Dict[str, Any]]]:
        """
        Extract tool operation data (spindle speeds and feedrates).

        Scans G-code for operation patterns:
        1. Operation name from comments: (OPERATION_NAME)
        2. Tool call lines: N## G100 T## ... S#### M3
        3. Feedrate macros: #500=39.4 (CUTTING)

        Handles both:
        - Operations with explicit tool calls (creates operation on G100)
        - Operations without tool calls (creates operation when feedrate macros found)

        Returns:
            Dict mapping tool_number to list of operation dicts:
            {
                1: [
                    {
                        "operation_name": "ADAPTIVE1",
                        "spindle_speed": 5000,
                        "feedrate_cutting": 39.4,
                        ...
                    }
                ]
            }
        """
        # Pattern definitions
        OPERATION_NAME_PATTERN = r'^\(([A-Z0-9_\s]+)\)$'
        TOOL_CALL_PATTERN = r'N\d+\s+G100\s+T(\d+)(?:.*S(\d+))?'
        FEEDRATE_MACRO_PATTERN = r'#(50[0-9])=([\d.]+)'

        # Macro to field mapping
        FEEDRATE_MACROS = {
            '500': 'feedrate_cutting',
            '502': 'feedrate_finish',
            '503': 'feedrate_entry',
            '504': 'feedrate_exit',
            '505': 'feedrate_direct',
            '507': 'feedrate_plunge',
            '508': 'feedrate_plunge',
            '509': 'feedrate_transition'
        }

        tool_operations: Dict[int, List[Dict[str, Any]]] = {}

        # Track modal state
        tool_modal_spindle: Dict[int, Optional[int]] = {}
        current_tool: Optional[int] = None  # Track active tool
        current_operation_name: Optional[str] = None
        i = 0

        while i < len(self.lines):
            line = self.lines[i].strip()

            # Check for operation name comment
            op_match = re.match(OPERATION_NAME_PATTERN, line)
            if op_match:
                current_operation_name = op_match.group(1).strip()
                i += 1
                continue

            # Check for tool call line
            tool_match = re.search(TOOL_CALL_PATTERN, line)
            if tool_match:
                tool_number = int(tool_match.group(1))
                current_tool = tool_number  # Update active tool

                # Handle modal spindle speed
                if tool_match.group(2):
                    # New spindle speed specified - update modal value
                    spindle_speed = int(tool_match.group(2))
                    tool_modal_spindle[tool_number] = spindle_speed
                else:
                    # No spindle speed specified - use modal value for this tool
                    spindle_speed = tool_modal_spindle.get(tool_number, None)

                # Initialize operation dict
                operation = {
                    "operation_name": current_operation_name,
                    "spindle_speed": spindle_speed,
                    "feedrate_cutting": None,
                    "feedrate_finish": None,
                    "feedrate_entry": None,
                    "feedrate_exit": None,
                    "feedrate_direct": None,
                    "feedrate_plunge": None,
                    "feedrate_transition": None
                }

                # Scan next 30 lines for feedrate macros
                scan_end = min(i + 30, len(self.lines))
                for j in range(i + 1, scan_end):
                    macro_line = self.lines[j].strip()
                    macro_match = re.search(FEEDRATE_MACRO_PATTERN, macro_line)
                    if macro_match:
                        macro_num = macro_match.group(1)
                        macro_value = float(macro_match.group(2))

                        if macro_num in FEEDRATE_MACROS:
                            field_name = FEEDRATE_MACROS[macro_num]
                            operation[field_name] = macro_value

                    # Stop scanning if we hit another operation or tool call
                    if re.match(OPERATION_NAME_PATTERN, macro_line) or \
                       re.search(TOOL_CALL_PATTERN, macro_line):
                        break

                # Add operation to tool's list
                if tool_number not in tool_operations:
                    tool_operations[tool_number] = []
                tool_operations[tool_number].append(operation)

                # Reset operation name (operations are one-time use)
                current_operation_name = None
                i += 1
                continue

            # Check for feedrate macros (operation without tool call)
            # This handles cases where the tool is modal and operation just has feedrates
            macro_match = re.search(FEEDRATE_MACRO_PATTERN, line)
            if macro_match and current_operation_name and current_tool is not None:
                # Found feedrate macro with pending operation name and active tool
                # Create operation for the current modal tool
                operation = {
                    "operation_name": current_operation_name,
                    "spindle_speed": tool_modal_spindle.get(current_tool, None),
                    "feedrate_cutting": None,
                    "feedrate_finish": None,
                    "feedrate_entry": None,
                    "feedrate_exit": None,
                    "feedrate_direct": None,
                    "feedrate_plunge": None,
                    "feedrate_transition": None
                }

                # Collect all feedrate macros for this operation
                scan_end = min(i + 30, len(self.lines))
                for j in range(i, scan_end):
                    scan_line = self.lines[j].strip()
                    scan_macro = re.search(FEEDRATE_MACRO_PATTERN, scan_line)
                    if scan_macro:
                        macro_num = scan_macro.group(1)
                        macro_value = float(scan_macro.group(2))

                        if macro_num in FEEDRATE_MACROS:
                            field_name = FEEDRATE_MACROS[macro_num]
                            operation[field_name] = macro_value

                    # Stop if we hit another operation or tool call
                    if re.match(OPERATION_NAME_PATTERN, scan_line) or \
                       re.search(TOOL_CALL_PATTERN, scan_line):
                        break

                # Add operation to tool's list
                if current_tool not in tool_operations:
                    tool_operations[current_tool] = []
                tool_operations[current_tool].append(operation)

                # Reset operation name
                current_operation_name = None

            i += 1

        return tool_operations

    def extract_posted_date(self) -> Optional[datetime]:
        """
        Extract posted date from CAM header.

        Expected format:
        (DATE: SUN NOV 30 04:57:32 2025)

        Returns:
            datetime object or None if not found
        """
        # Pattern: (DATE: DAY MON DD HH:MM:SS YYYY)
        pattern = r'\(DATE:\s+\w+\s+(\w+)\s+(\d+)\s+([\d:]+)\s+(\d+)\)'

        for line in self.lines[:50]:  # Check first 50 lines only
            match = re.search(pattern, line)
            if match:
                month_str = match.group(1)
                day = int(match.group(2))
                time_str = match.group(3)
                year = int(match.group(4))

                # Parse time
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                second = int(time_parts[2])

                # Convert month name to number
                months = {
                    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
                    'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
                    'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                }
                month = months.get(month_str.upper())

                if month:
                    return datetime(year, month, day, hour, minute, second)

        return None

    def extract_wcs_offset(self) -> Optional[Dict[str, Any]]:
        """
        Extract WCS (Work Coordinate System) offset for validation.

        Expected format:
        G65 P8901 X-21.9975 Y-2.8563 Z-15.8976 E0.01 W54

        Where:
        - X, Y, Z: Expected offset coordinates
        - W##: Work offset number (54 = G54, 55 = G55, etc.)
        - E: Tolerance value for comparison

        Returns:
            Dict with x, y, z coordinates, work_offset number, and tolerance
            None if not found in program
        """
        # Pattern: G65 P8901 X... Y... Z... E... W##
        pattern = r'G65\s+P8901\s+X([-\d.]+)\s+Y([-\d.]+)\s+Z([-\d.]+)\s+E([-\d.]+)\s+W(\d+)'

        for line in self.lines[:100]:  # Check first 100 lines
            match = re.search(pattern, line)
            if match:
                return {
                    "x": float(match.group(1)),
                    "y": float(match.group(2)),
                    "z": float(match.group(3)),
                    "tolerance": float(match.group(4)),
                    "work_offset": int(match.group(5)),  # 54 = G54, 55 = G55, etc.
                }

        return None

    def extract_stock_size(self) -> Optional[Dict[str, float]]:
        """
        Extract stock size from header.

        Expected format:
        (STOCK SIZE)
        (X146.05 Y25.4 Z12.7)

        Returns:
            Dict with x, y, z dimensions or None
        """
        # Pattern: (STOCK SIZE) followed by (X... Y... Z...)
        pattern = r'\(X([\d.]+)\s+Y([\d.]+)\s+Z([\d.]+)\)'

        in_stock_section = False
        for line in self.lines[:100]:
            if '(STOCK SIZE)' in line:
                in_stock_section = True
                continue

            if in_stock_section:
                match = re.search(pattern, line)
                if match:
                    return {
                        "x": float(match.group(1)),
                        "y": float(match.group(2)),
                        "z": float(match.group(3)),
                    }

        return None

    def estimate_runtime(self, rapid_feedrate: float = 2000.0) -> float:
        """
        Estimate program runtime based on move distances and feedrates.

        Analyzes:
        - G0 (rapid) moves - uses rapid_feedrate parameter
        - G1 (linear) moves with F (feedrate)
        - G2/G3 (arc) moves with F (feedrate)
        - G4 (dwell) commands
        - M-codes with known delays

        Args:
            rapid_feedrate: Rapid traverse speed in ipm (default 2000 for Brother CNC)

        Returns:
            Estimated runtime in seconds
        """
        total_time = 0.0
        current_feedrate = 100.0  # Default feedrate (ipm)
        current_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        current_plane = "G17"  # XY plane default
        modal_g_code = None  # Track modal G-code (G0, G1, etc.)

        for line in self.lines:
            # Remove comments and whitespace
            line = re.sub(r'\(.*?\)', '', line).strip()
            if not line:
                continue
            
            # Skip macro variable assignments and conditional logic (not executable G-code)
            # Patterns: #100 = ..., IF[...], GOTO..., N## (line numbers without G-code)
            # Also skip lines that are only variable assignments or macro syntax
            if re.match(r'^#\d+\s*=', line) or re.match(r'^IF\[', line) or \
               re.match(r'^GOTO\d+', line) or re.match(r'^N\d+\s*$', line) or \
               re.match(r'^N\d+\s*#', line) or re.search(r'#\d+\s*=\s*#\[', line):
                continue

            # Extract feedrate if present (F word)
            feedrate_match = re.search(r'F([\d.]+)', line)
            if feedrate_match:
                current_feedrate = float(feedrate_match.group(1))

            # Track plane selection (G17=XY, G18=XZ, G19=YZ)
            if 'G17' in line:
                current_plane = "G17"
            elif 'G18' in line:
                current_plane = "G18"
            elif 'G19' in line:
                current_plane = "G19"

            # Dwell command (G4 P seconds)
            dwell_match = re.search(r'G4\s+P([\d.]+)', line)
            if dwell_match:
                total_time += float(dwell_match.group(1))
                continue

            # Check for G-code movement commands
            if 'G0' in line or 'G00' in line:
                modal_g_code = 'G0'
            elif 'G1' in line or 'G01' in line:
                modal_g_code = 'G1'
            elif 'G2' in line or 'G02' in line:
                modal_g_code = 'G2'
            elif 'G3' in line or 'G03' in line:
                modal_g_code = 'G3'

            # Parse coordinates
            x_match = re.search(r'X([-\d.]+)', line)
            y_match = re.search(r'Y([-\d.]+)', line)
            z_match = re.search(r'Z([-\d.]+)', line)

            new_position = current_position.copy()
            if x_match:
                new_position["x"] = float(x_match.group(1))
            if y_match:
                new_position["y"] = float(y_match.group(1))
            if z_match:
                new_position["z"] = float(z_match.group(1))

            # Calculate move time based on modal G-code
            if modal_g_code == 'G0':
                # Rapid move
                distance = self._calculate_distance(current_position, new_position)
                if distance > 0:
                    time = (distance / rapid_feedrate) * 60  # Convert ipm to seconds
                    total_time += time

            elif modal_g_code == 'G1':
                # Linear feed move
                distance = self._calculate_distance(current_position, new_position)
                if distance > 0:
                    time = (distance / current_feedrate) * 60  # Convert ipm to seconds
                    total_time += time

            elif modal_g_code in ['G2', 'G3']:
                # Arc move - estimate using chord distance (approximation)
                # For accurate arc length, would need to parse I, J, K or R
                i_match = re.search(r'I([-\d.]+)', line)
                j_match = re.search(r'J([-\d.]+)', line)
                k_match = re.search(r'K([-\d.]+)', line)
                r_match = re.search(r'R([-\d.]+)', line)

                if r_match:
                    # Radius format
                    radius = float(r_match.group(1))
                    chord_distance = self._calculate_distance(current_position, new_position)
                    # Estimate arc length using chord and radius
                    if radius > 0 and chord_distance > 0:
                        arc_length = self._estimate_arc_length_from_radius(chord_distance, radius)
                    else:
                        arc_length = chord_distance
                elif i_match or j_match or k_match:
                    # Center format (I, J, K)
                    i = float(i_match.group(1)) if i_match else 0.0
                    j = float(j_match.group(1)) if j_match else 0.0
                    k = float(k_match.group(1)) if k_match else 0.0
                    arc_length = self._estimate_arc_length_from_center(
                        current_position, new_position, i, j, k, current_plane
                    )
                else:
                    # Fall back to chord distance
                    arc_length = self._calculate_distance(current_position, new_position)

                if arc_length > 0:
                    time = (arc_length / current_feedrate) * 60
                    total_time += time

            current_position = new_position

        # Add overhead for tool changes (estimate 10 seconds per tool)
        tool_changes = len(re.findall(r'T\d+', self.content))
        total_time += tool_changes * 10

        # Add overhead for spindle starts (estimate 1 second each)
        spindle_starts = len(re.findall(r'M0*3\b', self.content))
        total_time += spindle_starts * 1

        return total_time

    def _calculate_distance(self, pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
        """Calculate 3D distance between two positions."""
        dx = pos2["x"] - pos1["x"]
        dy = pos2["y"] - pos1["y"]
        dz = pos2["z"] - pos1["z"]
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def _estimate_arc_length_from_radius(self, chord_distance: float, radius: float) -> float:
        """
        Estimate arc length from chord distance and radius.

        Uses formula: arc_length = 2 * radius * arcsin(chord / (2 * radius))
        """
        if radius <= 0 or chord_distance <= 0:
            return chord_distance

        # Prevent domain error in arcsin
        ratio = chord_distance / (2 * radius)
        if ratio > 1.0:
            ratio = 1.0

        angle = 2 * math.asin(ratio)
        arc_length = radius * angle
        return arc_length

    def _estimate_arc_length_from_center(
        self,
        start: Dict[str, float],
        end: Dict[str, float],
        i: float,
        j: float,
        k: float,
        plane: str
    ) -> float:
        """
        Estimate arc length from center offset (I, J, K).

        This is an approximation using the chord distance.
        For production use, would calculate actual arc angle and radius.
        """
        # Simplified: use chord distance as approximation
        # Full implementation would calculate center point, radius, and sweep angle
        return self._calculate_distance(start, end) * 1.2  # Rough approximation factor


def parse_gcode(content: str) -> Dict[str, Any]:
    """
    Convenience function to parse G-code.

    Args:
        content: G-code program content

    Returns:
        Parsed program data
    """
    parser = GCodeParser(content)
    return parser.parse()
