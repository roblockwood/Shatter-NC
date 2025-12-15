"""Parser for TOLNI1.NC tool table data.

TOLNI1.NC contains the complete tool table from the Brother CNC machine.
This is separate from the ATC (Automatic Tool Changer) table which shows
only tools currently loaded in the tool changer.

Format is typically CSV-like with tool data per line.
Example format (may vary):
T01,TOOL_NAME,DIA,LENGTH,...
"""
from typing import Dict, Any, List, Optional
import re


class TOLNIParser:
    """Parser for TOLNI1.NC tool table data."""

    def __init__(self, content: bytes):
        """
        Initialize parser with TOLNI1.NC file content.

        Args:
            content: Raw bytes from TOLNI1.NC file
        """
        # Decode and clean content (strip null bytes)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]

    def parse(self) -> Dict[str, Any]:
        """
        Parse TOLNI1.NC and extract all tool table entries.

        Returns:
            Dict containing:
                - tools: List of tool dictionaries with all available fields
        """
        tools = []

        for line in self.lines:
            # Skip empty lines and comments
            if not line or line.startswith('(') or line.startswith(';'):
                continue

            # Try CSV format first (comma-separated)
            if ',' in line:
                tool = self._parse_csv_line(line)
            else:
                # Try space-separated or other formats
                tool = self._parse_space_line(line)

            if tool:
                tools.append(tool)

        return {
            "tools": tools,
            "total_tools": len(tools)
        }

    def _parse_csv_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a CSV-formatted tool line."""
        parts = [p.strip() for p in line.split(',')]
        
        if len(parts) < 2:
            return None

        tool = {}

        # First field is typically tool number (T## or just number)
        tool_num_str = parts[0].upper().replace('T', '').strip()
        try:
            tool['tool_number'] = int(tool_num_str)
        except (ValueError, TypeError):
            return None

        # Second field is often tool name
        if len(parts) > 1:
            tool['tool_name'] = parts[1] if parts[1] else None

        # Try to extract diameter (look for numeric values)
        for i, part in enumerate(parts[2:], start=2):
            try:
                val = float(part)
                # Diameter is typically larger than length, but we'll take what we can get
                if 'diameter' not in tool:
                    tool['diameter'] = val
                elif 'length' not in tool:
                    tool['length'] = val
            except (ValueError, TypeError):
                # Not a number, might be tool type, group, etc.
                if 'tool_type' not in tool and part:
                    tool['tool_type'] = part
                elif 'group' not in tool and part:
                    tool['group'] = part

        return tool

    def _parse_space_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a space-separated tool line."""
        # Try to match patterns like "T01 TOOL_NAME 0.25 3.5"
        parts = line.split()
        
        if len(parts) < 2:
            return None

        tool = {}

        # First field is tool number
        tool_num_str = parts[0].upper().replace('T', '').strip()
        try:
            tool['tool_number'] = int(tool_num_str)
        except (ValueError, TypeError):
            return None

        # Remaining fields
        for part in parts[1:]:
            # Try numeric values (diameter/length)
            try:
                val = float(part)
                if 'diameter' not in tool:
                    tool['diameter'] = val
                elif 'length' not in tool:
                    tool['length'] = val
            except (ValueError, TypeError):
                # String value (tool name, type, etc.)
                if 'tool_name' not in tool:
                    tool['tool_name'] = part
                elif 'tool_type' not in tool:
                    tool['tool_type'] = part

        return tool


def parse_tolni(content: bytes) -> Dict[str, Any]:
    """
    Convenience function to parse TOLNI1.NC content.

    Args:
        content: Raw bytes from TOLNI1.NC file

    Returns:
        Parsed tool table data
    """
    parser = TOLNIParser(content)
    return parser.parse()

