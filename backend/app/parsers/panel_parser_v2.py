"""
Schema-based parser for PANEL (Operation Panel Data) files.

This parser uses schema definitions to extract panel data from PANEL.NC files.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Extracts door status, mode/screen, and override settings
"""

from typing import Dict, Any, Optional
import re
import logging

from app.schemas.cnc_data.panel_schema import PANEL_SCHEMAS, C00_SCHEMA, D00_SCHEMA

logger = logging.getLogger(__name__)


class PANELParserV2:
    """Schema-based parser for PANEL operation panel data."""

    def __init__(self, content: bytes, control_version: Optional[str] = None):
        """
        Initialize parser with PANEL file content.

        Args:
            content: Raw bytes from PANEL.NC file
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes and whitespace)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00\r\n\t ')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        
        # Determine control version
        if control_version and control_version in PANEL_SCHEMAS:
            self.control_version = control_version
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = PANEL_SCHEMAS.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for PANEL parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check K01 line field count (C00: 11 fields, D00: 13 fields including table_light and door_unlock)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # Find K01 line
        k01_line = None
        for line in self.lines:
            if line.startswith('K01,'):
                k01_line = line
                break
        
        if not k01_line:
            logger.warning("No K01 line found for control version detection, defaulting to C00")
            return "C00"
        
        # Remove symbol prefix
        line_data = k01_line[4:]  # Remove "K01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        # C00: K01 has 11 fields (mode through pallet_select_key)
        # D00: K01 has 13 fields (adds table_light, door_unlock_1, door_unlock_2, removes screen)
        if len(parts) >= 13:
            logger.info("Detected D00 control version (13+ fields in K01)")
            return "D00"
        elif len(parts) >= 11:
            logger.info("Detected C00 control version (11 fields in K01)")
            return "C00"
        else:
            logger.warning(f"K01 line has unexpected field count ({len(parts)}), defaulting to C00")
            return "C00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse PANEL file and extract panel data using schema definitions.

        Returns:
            Dict containing:
                - doors: Dict with outer_door, inner_door, side_door
                - mode_and_functions: Dict with mode, screen (C00 only), switches, etc.
                - overrides: Dict with override settings and system status
                - control_version: Control version detected/used
        """
        if not self.lines:
            logger.warning("No lines found in PANEL file")
            return {
                "doors": {},
                "mode_and_functions": {},
                "overrides": {},
                "control_version": self.control_version
            }
        
        parsed_data = {
            "doors": {},
            "mode_and_functions": {},
            "overrides": {},
            "control_version": self.control_version
        }
        
        # Parse each line type
        for line in self.lines:
            line = line.strip()
            if not line:
                continue
            
            # Check line type by symbol prefix
            if line.startswith('D01,'):
                parsed_data["doors"] = self._parse_d01_line(line)
            elif line.startswith('K01,'):
                parsed_data["mode_and_functions"] = self._parse_k01_line(line)
            elif line.startswith('S01,'):
                parsed_data["overrides"] = self._parse_s01_line(line)
        
        return parsed_data

    def _parse_d01_line(self, line: str) -> Dict[str, Any]:
        """Parse D01 line (door status)."""
        # Remove symbol prefix
        line_data = line[4:]  # Remove "D01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        if len(parts) < 3:
            logger.warning(f"D01 line has insufficient fields: {len(parts)}")
            return {}
        
        # Get field definitions from schema
        field_defs = self.schema.other_line_types.get("D01", [])
        
        door_data = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            if not value_str:
                continue
            
            # Parse value based on data type
            try:
                if field_def.data_type == int:
                    door_data[field_def.name] = int(value_str)
                elif field_def.data_type == float:
                    door_data[field_def.name] = float(value_str)
                else:
                    door_data[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse {field_def.name}='{value_str}': {e}")
        
        return door_data

    def _parse_k01_line(self, line: str) -> Dict[str, Any]:
        """Parse K01 line (mode and machine functions)."""
        # Remove symbol prefix
        line_data = line[4:]  # Remove "K01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        # Get field definitions from schema
        field_defs = self.schema.other_line_types.get("K01", [])
        
        if len(parts) < len(field_defs):
            logger.warning(f"K01 line has insufficient fields: {len(parts)} (expected at least {len(field_defs)})")
        
        mode_data = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            if not value_str:
                continue
            
            # Parse value based on data type
            try:
                if field_def.data_type == int:
                    mode_data[field_def.name] = int(value_str)
                elif field_def.data_type == float:
                    mode_data[field_def.name] = float(value_str)
                else:
                    mode_data[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse {field_def.name}='{value_str}': {e}")
        
        return mode_data

    def _parse_s01_line(self, line: str) -> Dict[str, Any]:
        """Parse S01 line (override settings and system status)."""
        # Remove symbol prefix
        line_data = line[4:]  # Remove "S01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        # Get field definitions from schema
        field_defs = self.schema.other_line_types.get("S01", [])
        
        if len(parts) < len(field_defs):
            logger.warning(f"S01 line has insufficient fields: {len(parts)} (expected at least {len(field_defs)})")
        
        override_data = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            if not value_str:
                continue
            
            # Parse value based on data type
            try:
                if field_def.data_type == int:
                    override_data[field_def.name] = int(value_str)
                elif field_def.data_type == float:
                    override_data[field_def.name] = float(value_str)
                else:
                    override_data[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse {field_def.name}='{value_str}': {e}")
        
        return override_data


def parse_panel_v2(content: bytes, control_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to parse PANEL.NC content using schema-based parser.

    Args:
        content: Raw bytes from PANEL.NC file
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed panel data with doors, mode_and_functions, overrides, and control_version metadata
    """
    parser = PANELParserV2(content, control_version=control_version)
    return parser.parse()

