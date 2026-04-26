"""
Schema-based parser for MONTR (Machine Monitor) data files.

This parser uses schema definitions to extract monitor data from MONTR.NC files.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Extracts program info, time data, and workpiece counters
"""

from typing import Dict, Any, Optional
import re
import logging

from app.schemas.cnc_data.montr_schema import MONTR_SCHEMAS, C00_SCHEMA

logger = logging.getLogger(__name__)


class MONTRParserV2:
    """Schema-based parser for MONTR machine monitor data."""

    def __init__(self, content: bytes, control_version: Optional[str] = None):
        """
        Initialize parser with MONTR file content.

        Args:
            content: Raw bytes from MONTR.NC file
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes and whitespace)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00\r\n\t ')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        
        # Determine control version
        if control_version and control_version in MONTR_SCHEMAS:
            self.control_version = control_version
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = MONTR_SCHEMAS.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for MONTR parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check P01 line field lengths (C00: 4-byte program names, D00: 34-byte program names)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # Find P01 line
        p01_line = None
        for line in self.lines:
            if line.startswith('P01,'):
                p01_line = line
                break
        
        if not p01_line:
            logger.warning("No P01 line found for control version detection, defaulting to C00")
            return "C00"
        
        # Remove symbol prefix
        line_data = p01_line[4:]  # Remove "P01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        if len(parts) < 2:
            logger.warning("P01 line has insufficient fields, defaulting to C00")
            return "C00"
        
        # Check operation_program_no field length (index 0)
        program_field = parts[0].strip() if len(parts) > 0 else ""
        
        # C00: program_name is 4 bytes (just O-number like "2045")
        # D00: program_name is 34 bytes (may include full path/name)
        
        if len(program_field) <= 4:
            logger.info("Detected C00 control version (4-byte program name)")
            return "C00"
        else:
            logger.info("Detected D00 control version (34-byte program name)")
            return "D00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse MONTR file and extract monitor data using schema definitions.

        Returns:
            Dict containing:
                - program_info: Dict with operation_program_no, edit_program_no, folders
                - time_info: Dict with total_operation_time, power_on_time, operation_time
                - counters: List of 4 counter dicts (count, current, end, end_warning)
                - control_version: Control version detected/used
        """
        if not self.lines:
            logger.warning("No lines found in MONTR file")
            return {
                "program_info": {},
                "time_info": {},
                "counters": [],
                "control_version": self.control_version
            }
        
        parsed_data = {
            "program_info": {},
            "time_info": {},
            "counters": [],
            "control_version": self.control_version
        }
        
        # Parse each line type
        for line in self.lines:
            line = line.strip()
            if not line:
                continue
            
            # Check line type by symbol prefix
            if line.startswith('P01,'):
                parsed_data["program_info"] = self._parse_p01_line(line)
            elif line.startswith('T01,'):
                parsed_data["time_info"] = self._parse_t01_line(line)
            elif line.startswith('C01,'):
                parsed_data["counters"].append({
                    "counter_number": 1,
                    **self._parse_c01_line(line)
                })
            elif line.startswith('C02,'):
                parsed_data["counters"].append({
                    "counter_number": 2,
                    **self._parse_c01_line(line)
                })
            elif line.startswith('C03,'):
                parsed_data["counters"].append({
                    "counter_number": 3,
                    **self._parse_c01_line(line)
                })
            elif line.startswith('C04,'):
                parsed_data["counters"].append({
                    "counter_number": 4,
                    **self._parse_c01_line(line)
                })
        
        # Format program names as O-numbers if needed
        if parsed_data["program_info"].get("operation_program_no"):
            parsed_data["program_info"]["operation_program_no"] = self._format_program_name(
                parsed_data["program_info"]["operation_program_no"]
            )
        if parsed_data["program_info"].get("edit_program_no"):
            parsed_data["program_info"]["edit_program_no"] = self._format_program_name(
                parsed_data["program_info"]["edit_program_no"]
            )
        
        return parsed_data

    def _format_program_name(self, program_name: str) -> str:
        """Format program name as O-number if it's just digits."""
        if not program_name:
            return program_name
        
        program_name = program_name.strip().strip("'\"")
        
        # If it's just digits, format as O-number
        if program_name.isdigit():
            return f"O{program_name}"
        elif not program_name.startswith('O'):
            # Try to extract O-number from the string
            o_match = re.search(r'O?(\d{4})', program_name, re.IGNORECASE)
            if o_match:
                return f"O{o_match.group(1)}"
            else:
                return program_name
        else:
            return program_name.upper()

    def _parse_p01_line(self, line: str) -> Dict[str, Any]:
        """Parse P01 line (program information)."""
        # Remove symbol prefix
        line_data = line[4:]  # Remove "P01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        if len(parts) < 4:
            logger.warning(f"P01 line has insufficient fields: {len(parts)}")
            return {}
        
        # Get field definitions from schema
        field_defs = self.schema.tool_fields  # P01 fields are in tool_fields
        
        program_info = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            if not value_str:
                continue
            
            # Parse value based on data type
            try:
                if field_def.data_type is int:
                    program_info[field_def.name] = int(value_str)
                elif field_def.data_type is float:
                    program_info[field_def.name] = float(value_str)
                else:
                    # String field - remove quotes if present
                    if value_str.startswith("'") and value_str.endswith("'"):
                        program_info[field_def.name] = value_str[1:-1].strip()
                    elif value_str.startswith('"') and value_str.endswith('"'):
                        program_info[field_def.name] = value_str[1:-1].strip()
                    else:
                        program_info[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse {field_def.name}='{value_str}': {e}")
        
        return program_info

    def _parse_t01_line(self, line: str) -> Dict[str, Any]:
        """Parse T01 line (time information)."""
        # Remove symbol prefix
        line_data = line[4:]  # Remove "T01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        if len(parts) < 3:
            logger.warning(f"T01 line has insufficient fields: {len(parts)}")
            return {}
        
        # Get field definitions from schema
        field_defs = self.schema.other_line_types.get("T01", [])
        
        time_info = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            if not value_str:
                continue
            
            # Time fields are strings (format: HHMMSSMMM)
            time_info[field_def.name] = value_str
        
        return time_info

    def _parse_c01_line(self, line: str) -> Dict[str, Any]:
        """Parse C01-C04 line (workpiece counter)."""
        # Remove symbol prefix (C01, C02, C03, or C04)
        line_data = re.sub(r'^C\d+,\s*', '', line)
        parts = [p.strip() for p in line_data.split(',')]
        
        if len(parts) < 4:
            logger.warning(f"Counter line has insufficient fields: {len(parts)}")
            return {}
        
        # Get field definitions from schema (C01 fields apply to all counters)
        field_defs = self.schema.other_line_types.get("C01", [])
        
        counter_data = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            if not value_str:
                continue
            
            # Parse value based on data type
            try:
                if field_def.data_type is int:
                    counter_data[field_def.name] = int(value_str)
                elif field_def.data_type is float:
                    counter_data[field_def.name] = float(value_str)
                else:
                    counter_data[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse {field_def.name}='{value_str}': {e}")
        
        return counter_data


def parse_montr_v2(content: bytes, control_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to parse MONTR.NC content using schema-based parser.

    Args:
        content: Raw bytes from MONTR.NC file
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed monitor data with program_info, time_info, counters, and control_version metadata
    """
    parser = MONTRParserV2(content, control_version=control_version)
    return parser.parse()

