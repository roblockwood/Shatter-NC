"""
Schema-based parser for POSNn (Workpiece Coordinate Zero) data files.

This parser uses schema definitions to extract position/offset data from POSNI1.NC (inches)
or POSNM1.NC (millimeters) files based on machine configuration.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Unit-aware filename selection (POSNI vs POSNM)
- Categorizes offsets: work_offsets (G54-G59), extended_offsets (X01-X48/X001-X300), 
  fixture_offsets (H01), rotary_offsets (B01)
"""

from typing import Dict, Any, Optional
import re
import logging

from app.schemas.cnc_data.posni_schema import POSN_SCHEMAS, C00_SCHEMA

logger = logging.getLogger(__name__)


class POSNIParserV2:
    """Schema-based parser for POSNn position/offset data."""

    def __init__(self, content: bytes, units: str = 'in', control_version: Optional[str] = None):
        """
        Initialize parser with POSNn file content.

        Args:
            content: Raw bytes from POSNI1.NC or POSNM1.NC file
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        self.units = units
        
        # Determine control version
        if control_version and control_version in POSN_SCHEMAS:
            self.control_version = control_version
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = POSN_SCHEMAS.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for POSNn parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check offset name format (C00: G54, X01; D00: G054, X001)
        - Check field lengths (C00: 9 chars, D00: 11 chars)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # Look for offset lines to analyze
        offset_lines = [line for line in self.lines if ',' in line]
        
        if not offset_lines:
            logger.warning("No offset lines found for control version detection, defaulting to C00")
            return "C00"
        
        # Analyze first few offset lines
        c00_indicators = 0
        d00_indicators = 0
        
        for line in offset_lines[:10]:  # Check first 10 offset lines
            parts = line.split(',')
            if len(parts) < 4:
                continue
            
            offset_name = parts[0].strip()
            
            # Check offset name format
            # C00: G54, X01 (2-digit after prefix)
            # D00: G054, X001 (3-digit after prefix)
            if re.match(r'^G5[4-9]$', offset_name):
                c00_indicators += 1
            elif re.match(r'^G05[4-9]$', offset_name):
                d00_indicators += 1
            elif re.match(r'^X0?[1-9]\d?$', offset_name):  # X01-X48 (C00)
                c00_indicators += 1
            elif re.match(r'^X\d{3}$', offset_name):  # X001-X300 (D00)
                d00_indicators += 1
            
            # Check field lengths (X, Y, Z values)
            # C00: 9 chars max, D00: 11 chars max
            for idx in [1, 2, 3]:  # X, Y, Z
                if idx < len(parts):
                    val = parts[idx].strip()
                    if val and val.replace('-', '').replace('.', '').isdigit():
                        # Count significant digits (excluding decimal point and minus)
                        digits = len(val.replace('-', '').replace('.', ''))
                        if digits <= 9:
                            c00_indicators += 0.5  # Weak indicator
                        elif digits > 9:
                            d00_indicators += 0.5  # Weak indicator
        
        # Determine control version
        if d00_indicators > c00_indicators:
            logger.info(f"Detected D00 control version (indicators: {d00_indicators:.1f} D00 vs {c00_indicators:.1f} C00)")
            return "D00"
        else:
            logger.info(f"Detected C00 control version (indicators: {c00_indicators:.1f} C00 vs {d00_indicators:.1f} D00)")
            return "C00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse POSNn file and extract all offset entries using schema definitions.

        Returns:
            Dict containing:
                - work_offsets: Dict of G54-G59 offsets (key: offset number 54-59)
                - extended_offsets: Dict of X01-X48 (C00) or X001-X300 (D00) offsets
                - fixture_offsets: Dict of H01 offsets (C00 only)
                - rotary_offsets: Dict of B01 offsets (C00 only)
                - units: Unit system used
                - control_version: Control version detected/used
        """
        work_offsets = {}  # G54-G59
        extended_offsets = {}  # X01-X48 (C00) or X001-X300 (D00)
        fixture_offsets = {}  # H01 (C00 only)
        rotary_offsets = {}  # B01 (C00 only)

        for line in self.lines:
            # Skip empty lines
            if not line:
                continue
            
            # Parse offset line using schema
            offset_data = self._parse_offset_line(line)
            if not offset_data:
                continue
            
            offset_name = offset_data.get("offset_name", "")
            
            # Categorize by offset type
            if offset_name.startswith('G5') or offset_name.startswith('G05'):
                # Work offset: G54-G59 (C00) or G054-G059 (D00)
                # Extract number (54, 55, etc.)
                if offset_name.startswith('G05'):
                    # D00 format: G054 -> 54
                    offset_num = int(offset_name[2:])
                else:
                    # C00 format: G54 -> 54
                    offset_num = int(offset_name[1:])
                work_offsets[offset_num] = {
                    "x": offset_data.get("x", 0.0),
                    "y": offset_data.get("y", 0.0),
                    "z": offset_data.get("z", 0.0),
                    "a": offset_data.get("a", 0.0),
                    "b": offset_data.get("b", 0.0),
                    "c": offset_data.get("c", 0.0),
                }
            elif offset_name.startswith('X'):
                # Extended offset: X01-X48 (C00) or X001-X300 (D00)
                # Extract number (1, 2, etc.)
                offset_num = int(offset_name[1:])
                extended_offsets[offset_num] = {
                    "x": offset_data.get("x", 0.0),
                    "y": offset_data.get("y", 0.0),
                    "z": offset_data.get("z", 0.0),
                    "a": offset_data.get("a", 0.0),
                    "b": offset_data.get("b", 0.0),
                    "c": offset_data.get("c", 0.0),
                }
            elif offset_name.startswith('H'):
                # Fixture offset: H01 (C00 only)
                offset_num = int(offset_name[1:])
                fixture_offsets[offset_num] = {
                    "x": offset_data.get("x", 0.0),
                    "y": offset_data.get("y", 0.0),
                    "z": offset_data.get("z", 0.0),
                    "a": offset_data.get("a", 0.0),
                    "b": offset_data.get("b", 0.0),
                    "c": offset_data.get("c", 0.0),
                }
            elif offset_name.startswith('B'):
                # Rotary fixture offset: B01 (C00 only)
                # Note: B01 has additional fields (reference angles and offsets)
                # For now, store basic structure
                offset_num = int(offset_name[1:])
                rotary_offsets[offset_num] = {
                    "x": offset_data.get("x", 0.0),
                    "y": offset_data.get("y", 0.0),
                    "z": offset_data.get("z", 0.0),
                    "a": offset_data.get("a", 0.0),
                    "b": offset_data.get("b", 0.0),
                    "c": offset_data.get("c", 0.0),
                }

        return {
            "work_offsets": work_offsets,
            "extended_offsets": extended_offsets,
            "fixture_offsets": fixture_offsets,
            "rotary_offsets": rotary_offsets,
            "units": self.units,
            "control_version": self.control_version
        }

    def _parse_offset_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single offset line using schema field definitions.

        Args:
            line: CSV-formatted offset line (e.g., "G54,-20.3678,-1.0124,2.9996,0.000,0.000,0.000")

        Returns:
            Dict with offset data or None if parsing fails
        """
        parts = line.split(',')
        if len(parts) < 4:
            return None
        
        offset_name = parts[0].strip()
        if not offset_name:
            return None
        
        # Extract fields using schema
        offset_data = {"offset_name": offset_name}
        
        # Get field definitions from schema
        field_defs = self.schema.tool_fields  # Reusing tool_fields structure
        
        for field_def in field_defs:
            if field_def.csv_index == -1:
                # Special case: offset_name is already extracted
                continue
            
            # CSV index: 0=X, 1=Y, 2=Z, etc.
            # But parts[0] is offset_name, so parts[1]=X, parts[2]=Y, etc.
            # So we need to add 1 to the csv_index
            field_idx = field_def.csv_index + 1
            if field_idx < len(parts):
                value_str = parts[field_idx].strip()
                
                if not value_str:
                    # Empty field - use default based on required flag
                    if field_def.required:
                        logger.warning(f"Required field {field_def.name} is empty in offset {offset_name}")
                        return None
                    else:
                        # Optional field - use default value
                        if field_def.data_type is float:
                            offset_data[field_def.name] = 0.0
                        elif field_def.data_type is int:
                            offset_data[field_def.name] = 0
                        else:
                            offset_data[field_def.name] = ""
                    continue
                
                # Parse value based on data type
                try:
                    if field_def.data_type is float:
                        offset_data[field_def.name] = float(value_str)
                    elif field_def.data_type is int:
                        offset_data[field_def.name] = int(value_str)
                    else:
                        offset_data[field_def.name] = value_str
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse {field_def.name}='{value_str}' as {field_def.data_type.__name__}: {e}")
                    if field_def.required:
                        return None
                    # Use default for optional fields
                    if field_def.data_type is float:
                        offset_data[field_def.name] = 0.0
                    elif field_def.data_type is int:
                        offset_data[field_def.name] = 0
                    else:
                        offset_data[field_def.name] = ""
        
        return offset_data


def parse_posni_v2(content: bytes, units: str = 'in', control_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to parse POSNn content using schema-based parser.

    Args:
        content: Raw bytes from POSNI1.NC or POSNM1.NC file
        units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed position data with units and control_version metadata
    """
    parser = POSNIParserV2(content, units=units, control_version=control_version)
    return parser.parse()

