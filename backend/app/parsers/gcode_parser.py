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
        return {
            "tools": self.extract_tools(),
            "posted_date": self.extract_posted_date(),
            "estimated_runtime_seconds": self.estimate_runtime(),
            "wcs_location": self.extract_wcs_location(),
            "stock_size": self.extract_stock_size(),
            "line_count": len(self.lines),
            "file_size": len(self.content.encode('utf-8')),
        }

    def extract_tools(self) -> List[Dict[str, Any]]:
        """
        Extract tool definitions from CAM header comments.

        Expected format:
        (T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)

        Returns:
            List of dicts with tool_number, diameter, corner_radius, length_used, length_total, description
        """
        tools = []
        # Pattern: (T## D=diameter CR=corner_radius - ZMIN=... - description - L=used/total)
        pattern = r'\(T(\d+)\s+D=([\d.]+)\s+CR=([\d.]+)\s+-\s+ZMIN=([\d.]+)\s+-\s+([^-]+)\s+-\s+L=([\d.]+)/([\d.]+)\)'

        for line in self.lines:
            match = re.search(pattern, line)
            if match:
                tool_number = int(match.group(1))
                diameter = float(match.group(2))
                corner_radius = float(match.group(3))
                zmin = float(match.group(4))
                description = match.group(5).strip()
                length_used = float(match.group(6))
                length_total = float(match.group(7))

                tools.append({
                    "tool_number": tool_number,
                    "diameter": diameter,
                    "corner_radius": corner_radius,
                    "zmin": zmin,
                    "description": description,
                    "length_used": length_used,
                    "length_total": length_total,
                })

        return tools

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

    def extract_wcs_location(self) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Extract WCS (Work Coordinate System) location from header.

        Expected format:
        (WCS LOCATION)
        (X MIN -14.2875 MAX 131.7625)
        (Y MIN -121.7041 MAX -96.3041)
        (Z MIN 41.1911 MAX 53.8911)

        Returns:
            Dict with x, y, z keys containing min/max dicts, or None if not available
        """
        wcs_location = {}
        in_wcs_section = False

        # Pattern: (AXIS MIN value MAX value)
        pattern = r'\(([XYZ])\s+MIN\s+([-\d.]+)\s+MAX\s+([-\d.]+)\)'

        for line in self.lines[:100]:  # Check first 100 lines
            if '(WCS LOCATION)' in line:
                in_wcs_section = True
                continue

            if in_wcs_section:
                match = re.search(pattern, line)
                if match:
                    axis = match.group(1).lower()
                    min_val = float(match.group(2))
                    max_val = float(match.group(3))
                    wcs_location[axis] = {"min": min_val, "max": max_val}
                elif line.strip() and not line.startswith('('):
                    # End of WCS section
                    break

        return wcs_location if wcs_location else None

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
