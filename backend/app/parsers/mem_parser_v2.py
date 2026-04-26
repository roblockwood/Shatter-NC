"""
Schema-based parser for MEM (Memory Operation) data files.

This parser uses schema definitions to extract memory operation data from MEM.NC files.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Extracts program_name (O-number) and other memory operation fields
"""

from typing import Dict, Any, Optional
import re
import logging

from app.schemas.cnc_data.mem_schema import MEM_SCHEMAS, C00_SCHEMA

logger = logging.getLogger(__name__)


class MEMParserV2:
    """Schema-based parser for MEM memory operation data."""

    def __init__(self, content: bytes, control_version: Optional[str] = None):
        """
        Initialize parser with MEM file content.

        Args:
            content: Raw bytes from MEM.NC file
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes and whitespace)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00\r\n\t ')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        
        # Determine control version
        if control_version and control_version in MEM_SCHEMAS:
            self.control_version = control_version
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = MEM_SCHEMAS.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for MEM parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check program_name field length (C00: 4 bytes, D00: 34 bytes)
        - Check operation_folder_name field length (C00: 10 bytes, D00: 35 bytes)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # MEM is a single line, comma-delimited
        if not self.lines:
            logger.warning("No lines found for control version detection, defaulting to C00")
            return "C00"
        
        # Parse first line - remove symbol prefix (A01, etc.) if present
        first_line = self.lines[0]
        
        # Check if line starts with symbol prefix (A01, etc.) and remove it
        # The schema documentation shows "A01" as a symbol identifier, not a data field
        if first_line.startswith('A01,'):
            first_line = first_line[4:]  # Remove "A01," prefix
        elif re.match(r'^[A-Z]\d+,\s*', first_line):
            # Remove any symbol prefix (e.g., "A01,", "B02,", etc.)
            first_line = re.sub(r'^[A-Z]\d+,\s*', '', first_line)
        
        parts = first_line.split(',')
        
        if len(parts) < 2:
            logger.warning("MEM line has insufficient fields, defaulting to C00")
            return "C00"
        
        # Check operation_folder_name field (index 0) - this is the first actual data field after removing prefix
        folder_field = parts[0].strip() if len(parts) > 0 else ""
        
        # Check program_name field (index 1)
        program_field = parts[1].strip() if len(parts) > 1 else ""
        
        # C00: program_name is 4 bytes (just O-number like "2045")
        # D00: program_name is 34 bytes (may include full path/name)
        # C00: operation_folder_name is 10 bytes
        # D00: operation_folder_name is 35 bytes
        
        c00_indicators = 0
        d00_indicators = 0
        
        # Check program_name length
        if len(program_field) <= 4:
            c00_indicators += 1
        elif len(program_field) > 4:
            d00_indicators += 1
        
        # Check operation_folder_name length
        if len(folder_field) <= 10:
            c00_indicators += 0.5
        elif len(folder_field) > 10:
            d00_indicators += 0.5
        
        # Determine control version
        if d00_indicators > c00_indicators:
            logger.info(f"Detected D00 control version (indicators: {d00_indicators:.1f} D00 vs {c00_indicators:.1f} C00)")
            return "D00"
        else:
            logger.info(f"Detected C00 control version (indicators: {c00_indicators:.1f} C00 vs {d00_indicators:.1f} D00)")
            return "C00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse MEM file and extract memory operation data using schema definitions.

        Returns:
            Dict containing:
                - program_name: O-number of active program (e.g., "O2045")
                - operation_folder_name: Operation folder name (if available)
                - operation_status: Operation status code
                - inner_pallet_status: Inner pallet status code
                - spare_tool: Spare tool status
                - mode: Mode code
                - expansion: Expansion code
                - control_version: Control version detected/used
        """
        if not self.lines:
            logger.warning("No lines found in MEM file")
            return {
                "program_name": None,
                "control_version": self.control_version
            }
        
        # MEM is a single line, comma-delimited
        # Note: The line may start with a symbol prefix like "A01," which should be skipped
        line = self.lines[0]
        
        # Check if line starts with symbol prefix (A01, etc.) and remove it
        # Format: "A01,'FOLDER',PROGRAM,..." -> "'FOLDER',PROGRAM,..."
        if line.startswith('A01,'):
            line = line[4:]  # Remove "A01," prefix
        elif re.match(r'^[A-Z]\d+,\s*', line):
            # Remove any symbol prefix (e.g., "A01,", "B02,", etc.)
            line = re.sub(r'^[A-Z]\d+,\s*', '', line)
        
        parsed_data = self._parse_mem_line(line)
        
        # Format program_name as O-number if it's not already formatted
        if parsed_data and "program_name" in parsed_data:
            program_name = parsed_data["program_name"]
            if program_name:
                # Remove any quotes and whitespace
                program_name = program_name.strip().strip("'\"")
                # Format as O-number if it's just digits
                if program_name.isdigit():
                    parsed_data["program_name"] = f"O{program_name}"
                elif not program_name.startswith('O'):
                    # Try to extract O-number from the string
                    o_match = re.search(r'O?(\d{4})', program_name, re.IGNORECASE)
                    if o_match:
                        parsed_data["program_name"] = f"O{o_match.group(1)}"
                    else:
                        parsed_data["program_name"] = program_name
                else:
                    parsed_data["program_name"] = program_name.upper()
        
        parsed_data["control_version"] = self.control_version
        return parsed_data

    def _parse_mem_line(self, line: str) -> Dict[str, Any]:
        """
        Parse a single MEM line using schema field definitions.

        Args:
            line: CSV-formatted MEM line (e.g., "'FOLDER',2045,1,0,0,0,0")

        Returns:
            Dict with MEM data
        """
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2:
            logger.warning(f"MEM line has insufficient fields: {len(parts)}")
            return {"program_name": None}
        
        # Extract fields using schema
        mem_data = {}
        
        # Get field definitions from schema
        field_defs = self.schema.tool_fields  # Reusing tool_fields structure
        
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                # Field not present
                if field_def.required:
                    logger.warning(f"Required field '{field_def.name}' missing at CSV index {field_idx}")
                continue
            
            value_str = parts[field_idx].strip()
            
            # Skip empty fields (unless required)
            if not value_str:
                if field_def.required:
                    logger.warning(f"Required field '{field_def.name}' is empty")
                continue
            
            # Parse value based on data type
            try:
                if field_def.data_type is int:
                    mem_data[field_def.name] = int(value_str)
                elif field_def.data_type is float:
                    mem_data[field_def.name] = float(value_str)
                else:
                    # String field - remove quotes if present
                    if value_str.startswith("'") and value_str.endswith("'"):
                        mem_data[field_def.name] = value_str[1:-1].strip()
                    elif value_str.startswith('"') and value_str.endswith('"'):
                        mem_data[field_def.name] = value_str[1:-1].strip()
                    else:
                        mem_data[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse {field_def.name}='{value_str}' as {field_def.data_type.__name__}: {e}")
                if field_def.required:
                    # Required field failed to parse
                    return {"program_name": None}
                # Use default for optional fields
                if field_def.data_type is float:
                    mem_data[field_def.name] = 0.0
                elif field_def.data_type is int:
                    mem_data[field_def.name] = 0
                else:
                    mem_data[field_def.name] = ""
        
        return mem_data


def parse_mem_v2(content: bytes, control_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to parse MEM.NC content using schema-based parser.

    Args:
        content: Raw bytes from MEM.NC file
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed memory data with program_name and control_version metadata
    """
    parser = MEMParserV2(content, control_version=control_version)
    return parser.parse()

