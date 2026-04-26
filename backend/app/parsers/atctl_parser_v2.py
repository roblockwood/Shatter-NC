"""
Schema-based parser for ATCTL (ATC Tool) data files.

This parser uses schema definitions to extract ATC tool data from ATCTL (C00)
or ATCTLD (D00) files via Telnet.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Handles spindle, pots, and stockers (D00)
- Maps to expected output format (pot_number, tool_number, etc.)
"""

from typing import Dict, Any, Optional
import re
import logging

from app.schemas.cnc_data.atctl_schema import SCHEMA_REGISTRY, C00_SCHEMA

logger = logging.getLogger(__name__)


class ATCTLParserV2:
    """Schema-based parser for ATCTL tool data."""

    def __init__(self, content: bytes, control_version: Optional[str] = None):
        """
        Initialize parser with ATCTL/ATCTLD file content.

        Args:
            content: Raw bytes from ATCTL or ATCTLD file
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        
        # Determine control version
        if control_version and control_version in SCHEMA_REGISTRY:
            self.control_version = control_version
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = SCHEMA_REGISTRY.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for ATCTL parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check for R## or L## lines (D00 only - right/left stockers)
        - Check for W## or E## lines (D00 only - stocker attributes)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # Look for D00-specific line prefixes
        d00_indicators = 0
        for line in self.lines:
            if line.startswith('R') or line.startswith('L') or line.startswith('W') or line.startswith('E'):
                d00_indicators += 1
        
        if d00_indicators > 0:
            logger.info(f"Detected D00 control version (found {d00_indicators} D00-specific lines)")
            return "D00"
        else:
            logger.info("Detected C00 control version (no D00-specific lines found)")
            return "C00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse ATCTL/ATCTLD file and extract all ATC tool entries.

        Returns:
            Dict containing:
                - tools: List of tool dictionaries with pot_number, tool_number, etc.
                - total_tools: Number of tools found
                - control_version: Control version detected/used
        """
        tools = []
        spindle_tool = None

        for line in self.lines:
            # Skip empty lines
            if not line:
                continue
            
            # Parse line based on prefix
            if line.startswith('M'):
                # M01 = Spindle, M02-M51 = Pot 1-50
                entry = self._parse_entry_line(line, entry_type='pot')
                if entry:
                    if line.startswith('M01'):
                        # Spindle (current tool)
                        spindle_tool = entry
                        entry['pot_number'] = 'SPINDLE'
                    else:
                        # Extract pot number from M02-M51
                        pot_match = re.match(r'M(\d+)', line)
                        if pot_match:
                            pot_num = int(pot_match.group(1))
                            entry['pot_number'] = pot_num - 1  # M02 = Pot 1, M03 = Pot 2, etc.
                        tools.append(entry)
            elif self.control_version == 'D00':
                # D00: R## = Right stocker, L## = Left stocker
                # For now, we'll skip stockers as they're not in the main ATC table
                # but we could add them later if needed
                pass

        # Add spindle tool if found
        if spindle_tool:
            tools.insert(0, spindle_tool)

        return {
            "tools": tools,
            "total_tools": len(tools),
            "control_version": self.control_version
        }

    def _parse_entry_line(self, line: str, entry_type: str = 'pot') -> Optional[Dict[str, Any]]:
        """
        Parse a single ATC entry line using schema field definitions.

        Args:
            line: CSV-formatted entry line (e.g., "M01,1,1,0,1,0")
            entry_type: Type of entry ('pot', 'stocker', etc.)

        Returns:
            Tool dictionary with extracted fields, or None if parsing fails
        """
        # Remove prefix (M##, R##, L##) and split CSV
        parts = [p.strip() for p in line.split(',')]
        
        if len(parts) < 2:
            return None

        # First part is the prefix (M01, M02, etc.), skip it
        # Fields start from index 1
        tool = {}

        # Extract fields using schema definitions
        for field_def in self.schema.tool_fields:
            csv_index = field_def.csv_index + 1  # +1 because we skip the prefix
            
            if csv_index >= len(parts):
                # Field not present in this line
                if field_def.required:
                    logger.warning(f"Required field '{field_def.name}' missing at CSV index {field_def.csv_index}")
                continue
            
            field_value = parts[csv_index].strip()
            
            # Skip empty fields (unless required)
            if not field_value:
                if field_def.required:
                    logger.warning(f"Required field '{field_def.name}' is empty")
                continue
            
            # Parse based on data type
            try:
                if field_def.data_type is int:
                    tool[field_def.name] = int(field_value)
                elif field_def.data_type is float:
                    tool[field_def.name] = float(field_value)
                elif field_def.data_type is str:
                    tool[field_def.name] = field_value
                else:
                    tool[field_def.name] = field_value
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse field '{field_def.name}' (index {csv_index}) for entry: {e}")
                if field_def.required:
                    return None

        # Map schema field names to expected output names for backward compatibility
        # The HTTP parser returns: pot_number, tool_number, tool_name, diameter, length, group, life, tool_type, color
        # We need to map our fields to match this structure
        
        # tool_number is already correct
        # group_or_main_tool -> group
        if 'group_or_main_tool' in tool:
            tool['group'] = tool['group_or_main_tool']
        
        # tool_type is already correct
        # graph_color -> color
        if 'graph_color' in tool:
            tool['color'] = tool['graph_color']
        
        # Note: ATC data doesn't have diameter, length, or tool_name - those come from TOLN
        # We'll leave those as None/undefined

        return tool


def parse_atctl_v2(
    content: bytes,
    control_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to parse ATCTL/ATCTLD content using schema definitions.

    Args:
        content: Raw bytes from ATCTL or ATCTLD file
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed ATC tool data with control_version metadata
    """
    parser = ATCTLParserV2(content, control_version=control_version)
    return parser.parse()

