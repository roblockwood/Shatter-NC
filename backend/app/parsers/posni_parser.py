"""Parser for POSNI1.NC position/coordinate system data.

POSNI1.NC contains work offset data from the Brother CNC machine.
Format: OFFSET,X,Y,Z,A,B,C

Example:
G54,-20.3678,-1.0124,2.9996,0.000,0.000,0.000
G55,-13.9774,-7.4936,0.0000,0.000,0.000,0.000
X01,0.0000,0.0000,0.0000,0.000,0.000,0.000
"""
from typing import Dict, Any, Optional
import re


class POSNIParser:
    """Parser for POSNI1.NC work offset data."""

    def __init__(self, content: bytes, units: str = 'in'):
        """
        Initialize parser with POSNI1.NC file content.

        Args:
            content: Raw bytes from POSNI1.NC file
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
        """
        # Decode and clean content (strip null bytes)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        self.units = units

    def parse(self) -> Dict[str, Any]:
        """
        Parse POSNI1.NC and extract all work offsets.

        Returns:
            Dict containing:
                - work_offsets: Dict of G54-G59 offsets
                - extended_offsets: Dict of X01-X48 offsets (if present)
                - fixture_offsets: Dict of H01-H99 offsets (if present)
                - rotary_offsets: Dict of B01-B08 offsets (if present)
        """
        work_offsets = {}  # G54-G59
        extended_offsets = {}  # X01-X48
        fixture_offsets = {}  # H01-H99
        rotary_offsets = {}  # B01-B08

        for line in self.lines:
            # Pattern: OFFSET,X,Y,Z,A,B,C
            parts = line.split(',')
            if len(parts) < 4:
                continue

            offset_name = parts[0]
            try:
                x = float(parts[1])
                y = float(parts[2])
                z = float(parts[3])
                # Optional rotary axes (A, B, C)
                a = float(parts[4]) if len(parts) > 4 else 0.0
                b = float(parts[5]) if len(parts) > 5 else 0.0
                c = float(parts[6]) if len(parts) > 6 else 0.0

                offset_data = {
                    "x": x,
                    "y": y,
                    "z": z,
                    "a": a,
                    "b": b,
                    "c": c,
                }

                # Categorize by offset type
                if offset_name.startswith('G5'):  # G54-G59
                    # Extract number (54, 55, etc.)
                    offset_num = int(offset_name[1:])
                    work_offsets[offset_num] = offset_data
                elif offset_name.startswith('X'):  # X01-X48
                    offset_num = int(offset_name[1:])
                    extended_offsets[offset_num] = offset_data
                elif offset_name.startswith('H'):  # H01-H99
                    offset_num = int(offset_name[1:])
                    fixture_offsets[offset_num] = offset_data
                elif offset_name.startswith('B'):  # B01-B08
                    offset_num = int(offset_name[1:])
                    rotary_offsets[offset_num] = offset_data

            except (ValueError, IndexError):
                # Skip malformed lines
                continue

        return {
            "work_offsets": work_offsets,
            "extended_offsets": extended_offsets,
            "fixture_offsets": fixture_offsets,
            "rotary_offsets": rotary_offsets,
            "units": self.units,
        }

    def get_work_offset(self, offset_number: int) -> Optional[Dict[str, float]]:
        """
        Get a specific work offset (G54-G59).

        Args:
            offset_number: Offset number (54 for G54, 55 for G55, etc.)

        Returns:
            Dict with x, y, z coordinates or None if not found
        """
        parsed = self.parse()
        return parsed["work_offsets"].get(offset_number)


def parse_posni(content: bytes, units: str = 'in') -> Dict[str, Any]:
    """
    Convenience function to parse POSNI1.NC content.

    Args:
        content: Raw bytes from POSNI1.NC file
        units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.

    Returns:
        Parsed position data with units metadata
    """
    parser = POSNIParser(content, units=units)
    return parser.parse()


def get_work_offset(content: bytes, offset_number: int, units: str = 'in') -> Optional[Dict[str, float]]:
    """
    Extract a specific work offset from POSNI1.NC.

    Args:
        content: Raw bytes from POSNI1.NC file
        offset_number: Offset number (54 for G54, 55 for G55, etc.)
        units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.

    Returns:
        Dict with x, y, z coordinates or None if not found
    """
    parser = POSNIParser(content, units=units)
    return parser.get_work_offset(offset_number)
