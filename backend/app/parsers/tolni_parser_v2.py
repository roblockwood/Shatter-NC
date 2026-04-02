"""
Schema-based parser for TOLNn (Tool Offset Table) data files.

This parser uses schema definitions to extract tool data from TOLNI1.NC (inches)
or TOLNM1.NC (millimeters) files based on machine configuration.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Unit-aware filename selection (TOLNI vs TOLNM)
- Comprehensive field mapping from documentation
"""

from typing import Dict, Any, List, Optional
import re
import logging

from app.schemas.cnc_data.tolni_schema import SCHEMA_REGISTRY, C00_SCHEMA, D00_SCHEMA

logger = logging.getLogger(__name__)


class TOLNIParserV2:
    """Schema-based parser for TOLNn tool table data."""

    def __init__(self, content: bytes, units: str = 'in', control_version: Optional[str] = None):
        """
        Initialize parser with TOLNn file content.

        Args:
            content: Raw bytes from TOLNI1.NC or TOLNM1.NC file
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        self.units = units
        
        # Determine control version
        if control_version and control_version in SCHEMA_REGISTRY:
            self.control_version = control_version
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = SCHEMA_REGISTRY.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for TOLNn parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check tool life field lengths (C00: 6 chars, D00: 7 chars)
        - Check for peripheral speed field (D00 only)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # Look for tool lines to analyze
        tool_lines = [line for line in self.lines if line.startswith('T') and ',' in line]
        
        if not tool_lines:
            logger.warning("No tool lines found for control version detection, defaulting to C00")
            return "C00"
        
        # Analyze first few tool lines
        c00_indicators = 0
        d00_indicators = 0
        
        for line in tool_lines[:5]:  # Check first 5 tool lines
            parts = line.split(',')
            
            # Check tool life field (index 5-7)
            # C00: 6 chars (0~999999), D00: 7 chars (0~9999999)
            if len(parts) > 8:
                # Check if tool life fields are 6 or 7 digits
                for idx in [5, 6, 7]:  # initial_tool_life, tool_life_warning, tool_life
                    if idx < len(parts) and parts[idx].strip():
                        val = parts[idx].strip()
                        if val.isdigit():
                            if len(val) <= 6:
                                c00_indicators += 1
                            elif len(val) > 6:
                                d00_indicators += 1
            
            # Check for peripheral speed field (D00 only, after tool_name at index 9)
            if len(parts) > 10:
                # In D00, peripheral_speed is at index 9 (after tool_name), rotation_feed at 10
                # In C00, rotation_feed is at index 9 (after tool_name)
                # If we see a numeric value at 9 that looks like peripheral speed (0.1~9999.9), it's D00
                if parts[9].strip() and not parts[9].strip().startswith("'"):
                    try:
                        val = float(parts[9].strip())
                        if 0.1 <= val <= 9999.9:
                            d00_indicators += 1
                    except (ValueError, AttributeError):
                        pass
        
        # Determine control version
        if d00_indicators > c00_indicators:
            logger.info(f"Detected D00 control version (indicators: {d00_indicators} D00 vs {c00_indicators} C00)")
            return "D00"
        else:
            logger.info(f"Detected C00 control version (indicators: {c00_indicators} C00 vs {d00_indicators} D00)")
            return "C00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse TOLNn file and extract all tool table entries using schema definitions.

        Returns:
            Dict containing:
                - tools: List of tool dictionaries with all available fields
                - total_tools: Number of tools found
                - units: Unit system used
                - control_version: Control version detected/used
        """
        tools = []

        for line in self.lines:
            # Skip empty lines
            if not line:
                continue
            
            # Skip non-tool lines (V##, M##, Y##)
            if not line.startswith('T'):
                continue
            
            # Parse tool line using schema
            tool = self._parse_tool_line(line)
            if tool:
                tools.append(tool)

        return {
            "tools": tools,
            "total_tools": len(tools),
            "units": self.units,
            "control_version": self.control_version
        }

    def _parse_tool_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single tool line using schema field definitions.

        Args:
            line: CSV-formatted tool line (e.g., "T01,3.4494,0.0000,...")

        Returns:
            Tool dictionary with extracted fields, or None if parsing fails
        """
        # Split CSV line
        parts = [p.strip() for p in line.split(',')]
        
        if len(parts) < 2:
            return None

        tool = {}

        # Extract tool number from T## prefix (field 0)
        tool_prefix = parts[0].upper()
        if tool_prefix.startswith('T'):
            try:
                tool['tool_number'] = int(tool_prefix[1:])
            except (ValueError, IndexError):
                logger.warning(f"Could not extract tool number from '{tool_prefix}'")
                return None
        else:
            return None

        # Extract fields using schema definitions
        # Note: CSV fields start at index 1 (after T## prefix), but schema defines indices relative to CSV field 0
        # So we need to adjust: schema index 0 = parts[1], schema index 1 = parts[2], etc.
        for field_def in self.schema.tool_fields:
            if field_def.csv_index < 0:
                # Special field (tool_number) already handled
                continue
            
            # Schema index is 0-based for CSV fields, but parts[0] is T##, so add 1
            csv_index = field_def.csv_index + 1
            if csv_index >= len(parts):
                # Field not present in this line
                if field_def.required:
                    logger.warning(f"Required field '{field_def.name}' missing at CSV index {field_def.csv_index} (parts index {csv_index}) for tool {tool['tool_number']}")
                continue
            
            field_value = parts[csv_index].strip()
            
            # Skip empty fields (unless required)
            if not field_value:
                if field_def.required:
                    logger.warning(f"Required field '{field_def.name}' is empty for tool {tool['tool_number']}")
                continue
            
            # Parse based on data type
            try:
                if field_def.data_type == int:
                    tool[field_def.name] = int(field_value)
                elif field_def.data_type == float:
                    tool[field_def.name] = float(field_value)
                elif field_def.data_type == str:
                    # Remove single quotes from tool name if present
                    if field_def.name == "tool_name" and field_value.startswith("'") and field_value.endswith("'"):
                        # Preserve internal spacing (tool tables often use fixed-width names)
                        tool[field_def.name] = field_value[1:-1]
                    else:
                        tool[field_def.name] = field_value
                else:
                    tool[field_def.name] = field_value
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse field '{field_def.name}' (index {csv_index}) for tool {tool['tool_number']}: {e}")
                if field_def.required:
                    # Required field failed to parse - skip this tool
                    return None

        # Map schema field names to expected output names for backward compatibility
        # The schema uses "cutter_compensation" but we want "diameter" in output
        if 'cutter_compensation' in tool:
            tool['diameter'] = tool['cutter_compensation']
        
        # The schema uses "tool_length_offset" but we want "length" in output
        if 'tool_length_offset' in tool:
            tool['length'] = tool['tool_length_offset']
        
        # The schema uses "tool_life" but we want "life" in output
        if 'tool_life' in tool:
            tool['life'] = tool['tool_life']

        return tool


def parse_tolni_v2(
    content: bytes,
    units: str = 'in',
    control_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to parse TOLNI1.NC or TOLNM1.NC content using schema definitions.

    Args:
        content: Raw bytes from TOLNI1.NC or TOLNM1.NC file
        units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed tool table data with units and control_version metadata
    """
    parser = TOLNIParserV2(content, units=units, control_version=control_version)
    return parser.parse()

