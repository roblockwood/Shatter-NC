"""
Schema-based parser for PRD3/PRDD3 (Production data 3 - Status history) data files.

This parser uses schema definitions to extract status history data from PRD3/PRDD3 files.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Extracts current status with proper status code mapping
- Maps status codes to frontend-compatible values: off, standby, operating, stopped, error
"""

from typing import Dict, Any, Optional
import re
import logging

from app.schemas.cnc_data.prd3_schema import PRD3_SCHEMAS, C00_SCHEMA, D00_SCHEMA

logger = logging.getLogger(__name__)


# Status code mapping (from PRD3 schema)
# 1: Power OFF → "off"
# 2: Standby mode → "standby"
# 3: Operating → "operating"
# 4: Stopped → "stopped"
# 5: Error → "error"
STATUS_CODE_MAP = {
    1: "off",
    2: "standby",
    3: "operating",
    4: "stopped",
    5: "error",
}


class PRD3ParserV2:
    """Schema-based parser for PRD3/PRDD3 status history data."""

    def __init__(self, content: bytes, control_version: Optional[str] = None):
        """
        Initialize parser with PRD3 file content.

        Args:
            content: Raw bytes from PRD3/PRDD3 file
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes and whitespace)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00\r\n\t ')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        
        # Determine control version (file structure wins over DIR-based guess from polling)
        if control_version and control_version in PRD3_SCHEMAS:
            self.control_version = control_version
            content_based = self._detect_control_version()
            if content_based != self.control_version:
                logger.info(
                    "PRD3: overriding control_version %s -> %s from A01/C01 structure",
                    self.control_version,
                    content_based,
                )
                self.control_version = content_based
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = PRD3_SCHEMAS.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for PRD3 parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check A01 line field count (C00: 3 fields, D00: 4 fields with file_writing_index)
        - Check C01 line field lengths (C00: 6-byte program/error, 10-byte folder; D00: 34-byte program/error, 35-byte folder)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # Find A01 line
        a01_line = None
        for line in self.lines:
            if line.startswith('A01,'):
                a01_line = line
                break
        
        if not a01_line:
            logger.warning("No A01 line found for control version detection, defaulting to C00")
            return "C00"
        
        # Remove symbol prefix
        line_data = a01_line[4:]  # Remove "A01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        # C00: A01 has 3 fields (start_pointer, end_pointer, status)
        # D00: A01 has 4 fields (start_index, end_index, status, file_writing_index)
        if len(parts) >= 4:
            logger.info("Detected D00 control version (A01 has 4 fields)")
            return "D00"
        elif len(parts) >= 3:
            logger.info("Detected C00 control version (A01 has 3 fields)")
            return "C00"
        else:
            logger.warning(f"A01 line has insufficient fields ({len(parts)}), defaulting to C00")
            return "C00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse PRD3 file and extract status history data using schema definitions.

        Returns:
            Dict containing:
                - header: Dict with start_pointer/start_index, end_pointer/end_index, status, file_writing_index (D00 only)
                - current_status: Dict with:
                    - start_date_time: Start date and time (YYYYMMDDhhmmss)
                    - current_status: Status code (1-5)
                    - status: Mapped status string (off, standby, operating, stopped, error)
                    - current_language: Language code (0=NC, 1=Conversation)
                    - program_or_error_no: Program No. (when status=3) or Error No. (when status=5)
                    - folder_name: Folder name (with quotes stripped)
                    - memory_operation_type: Memory operation type code
                - control_version: Control version detected/used
        """
        if not self.lines:
            logger.warning("No lines found in PRD3 file")
            return {
                "header": {},
                "current_status": {},
                "history": [],
                "control_version": self.control_version,
            }
        
        parsed_data = {
            "header": {},
            "current_status": {},
            "history": [],
            "control_version": self.control_version,
        }
        
        # Parse each line type
        for line in self.lines:
            line = line.strip()
            if not line:
                continue
            
            # Check line type by symbol prefix
            if line.startswith('A01,'):
                parsed_data["header"] = self._parse_a01_line(line)
            elif line.startswith('C01,'):
                # C01 represents the current status (latest entry)
                parsed_data["current_status"] = self._parse_c01_line(line)
            elif line.startswith('B'):
                # B0001-Bxxxx are historical status log entries with the same
                # structure as C01. We strip the B-index prefix and parse the
                # remaining CSV fields using the C01 schema.
                match = re.match(r'^(B(\d+)),(.*)$', line)
                if not match:
                    continue
                index_str = match.group(2)
                csv_part = match.group(3)
                try:
                    index = int(index_str)
                except (TypeError, ValueError):
                    index = None

                c01_like_line = f"C01,{csv_part}"
                history_entry = self._parse_c01_line(c01_like_line)
                if index is not None:
                    history_entry["index"] = index
                parsed_data["history"].append(history_entry)
        
        # Map status code to string for current_status
        if parsed_data["current_status"].get("current_status") is not None:
            status_code = parsed_data["current_status"]["current_status"]
            parsed_data["current_status"]["status"] = STATUS_CODE_MAP.get(status_code, "standby")
        
        # Map status codes for history entries
        for entry in parsed_data["history"]:
            code = entry.get("current_status")
            if code is not None:
                entry["status"] = STATUS_CODE_MAP.get(code, "standby")
        
        return parsed_data

    def _parse_a01_line(self, line: str) -> Dict[str, Any]:
        """Parse A01 line (header)."""
        # Remove symbol prefix
        line_data = line[4:]  # Remove "A01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        # Get field definitions from schema
        field_defs = self.schema.tool_fields  # A01 fields are in tool_fields
        
        header_data = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            
            # Convert to appropriate type
            try:
                if field_def.data_type == int:
                    header_data[field_def.name] = int(value_str)
                elif field_def.data_type == float:
                    header_data[field_def.name] = float(value_str)
                else:
                    header_data[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse {field_def.name}='{value_str}': {e}")
                if field_def.data_type == int:
                    header_data[field_def.name] = 0
                elif field_def.data_type == float:
                    header_data[field_def.name] = 0.0
                else:
                    header_data[field_def.name] = value_str
        
        return header_data

    def _parse_c01_line(self, line: str) -> Dict[str, Any]:
        """Parse C01 line (current status)."""
        # Remove symbol prefix
        line_data = line[4:]  # Remove "C01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        # Get field definitions from schema
        field_defs = self.schema.other_line_types.get("C01", [])
        
        status_data = {}
        for field_def in field_defs:
            field_idx = field_def.csv_index
            if field_idx >= len(parts):
                continue
            
            value_str = parts[field_idx].strip()
            
            # Convert to appropriate type
            try:
                if field_def.data_type == int:
                    # Some controls appear to emit non-numeric placeholders for
                    # memory_operation_type and similar fields (e.g. quoted
                    # strings like 'PROGRAM ' or just quotes/spaces). In those
                    # cases, treat the value as undefined instead of logging
                    # noisy parse warnings on every poll.
                    if field_def.name == "memory_operation_type":
                        numeric = value_str.strip().strip("'\"")
                        if not numeric or not numeric.lstrip("+-").isdigit():
                            # Leave memory_operation_type unset when not numeric
                            continue
                        status_data[field_def.name] = int(numeric)
                    else:
                        status_data[field_def.name] = int(value_str)
                elif field_def.data_type == float:
                    status_data[field_def.name] = float(value_str)
                else:
                    # Strip quotes from folder_name if present
                    if field_def.name == "folder_name" and value_str:
                        value_str = value_str.strip("'\"")
                    status_data[field_def.name] = value_str
            except (ValueError, TypeError) as e:
                # For non-critical fields we prefer to skip bad values quietly
                # rather than flood logs on every poll.
                if field_def.data_type == int or field_def.data_type == float:
                    # Skip setting the field when parsing fails
                    continue
                else:
                    status_data[field_def.name] = value_str
        
        return status_data


def parse_prd3_v2(content: bytes, control_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse PRD3/PRDD3 file content using schema-based parser.

    Args:
        content: Raw bytes from PRD3/PRDD3 file
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed PRD3 data dictionary
    """
    parser = PRD3ParserV2(content, control_version=control_version)
    return parser.parse()

