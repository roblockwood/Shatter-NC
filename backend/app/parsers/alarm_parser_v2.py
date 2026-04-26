"""
Schema-based parser for ALARM (Current Alarm) data files.

This parser uses schema definitions to extract alarm data from ALARM.NC files.

Features:
- Schema-based field extraction (C00 and D00 control versions)
- Automatic control version detection
- Extracts alarm/operator messages (E01-E36) and loading system alarms (L01-L18)
- Parses alarm codes into category, number, and auxiliary components
"""

from typing import Dict, Any, Optional, List
import re
import logging

from app.schemas.cnc_data.alarm_schema import ALARM_SCHEMAS, C00_SCHEMA
from app.utils.alarm_code_lookup import enrich_alarm_with_lookup

logger = logging.getLogger(__name__)


# Alarm category mappings
ALARM_CATEGORIES = {
    "01": "EX",  # External
    "02": "EC",  # External Communication
    "03": "SV",  # Servo
    "04": "NC",  # NC
    "05": "IO",  # I/O
    "06": "SP",  # Spindle
    "07": "SM",  # Spindle Motor
    "08": "SL",  # Spindle Loader
    "09": "CM",  # Communication
    "10": "ES",  # Emergency Stop (C00) / PN (D00)
    "11": "FC",  # Function (C00) / FN (D00)
    "90": "OM",  # Operator Message
}


class ALARMParserV2:
    """Schema-based parser for ALARM current alarm data."""

    def __init__(self, content: bytes, control_version: Optional[str] = None):
        """
        Initialize parser with ALARM file content.

        Args:
            content: Raw bytes from ALARM.NC file
            control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.
        """
        # Decode and clean content (strip null bytes and whitespace)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00\r\n\t ')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]
        
        # Determine control version
        if control_version and control_version in ALARM_SCHEMAS:
            self.control_version = control_version
        else:
            self.control_version = self._detect_control_version()
        
        # Get schema for this control version
        self.schema = ALARM_SCHEMAS.get(self.control_version, C00_SCHEMA)
        logger.debug(f"Using {self.control_version} schema for ALARM parsing")

    def _detect_control_version(self) -> str:
        """
        Detect control version (C00 vs D00) from file content.

        Detection strategy:
        - Check E01 line field length (C00: 10 bytes, D00: 22 bytes)
        - Default to C00 if uncertain

        Returns:
            'C00' or 'D00'
        """
        # Find E01 line
        e01_line = None
        for line in self.lines:
            if line.startswith('E01,'):
                e01_line = line
                break
        
        if not e01_line:
            logger.warning("No E01 line found for control version detection, defaulting to C00")
            return "C00"
        
        # Remove symbol prefix
        line_data = e01_line[4:]  # Remove "E01,"
        parts = [p.strip() for p in line_data.split(',')]
        
        if len(parts) < 1:
            logger.warning("E01 line has insufficient fields, defaulting to C00")
            return "C00"
        
        # Check alarm_code field length (index 0)
        alarm_field = parts[0].strip() if len(parts) > 0 else ""
        
        # C00: alarm_code is 10 bytes
        # D00: alarm_code is 22 bytes
        
        if len(alarm_field) <= 10:
            logger.info("Detected C00 control version (10-byte alarm code)")
            return "C00"
        else:
            logger.info("Detected D00 control version (22-byte alarm code)")
            return "D00"

    def parse(self) -> Dict[str, Any]:
        """
        Parse ALARM file and extract alarm data using schema definitions.

        Returns:
            Dict containing:
                - alarms: List of alarm dicts (from E01-E36)
                - loading_alarms: List of loading system alarm dicts (from L01-L18)
                - control_version: Control version detected/used
        """
        if not self.lines:
            logger.warning("No lines found in ALARM file")
            return {
                "alarms": [],
                "loading_alarms": [],
                "control_version": self.control_version
            }
        
        parsed_data = {
            "alarms": [],
            "loading_alarms": [],
            "control_version": self.control_version
        }
        
        # Parse each line type
        for line in self.lines:
            line = line.strip()
            if not line:
                continue
            
            # Check line type by symbol prefix
            # E01-E36: Alarm/Operator messages (all on E01 line, comma-separated)
            if re.match(r'^E\d+,\s*', line):
                alarms = self._parse_e01_line(line)
                parsed_data["alarms"].extend(alarms)
            # L01-L18: Loading system alarms (all on L01 line, comma-separated)
            elif re.match(r'^L\d+,\s*', line):
                loading_alarms = self._parse_l01_line(line)
                parsed_data["loading_alarms"].extend(loading_alarms)
        
        return parsed_data

    def _parse_e01_line(self, line: str) -> List[Dict[str, Any]]:
        """
        Parse E01 line (contains E01-E36 alarm/operator messages, comma-separated).
        
        Returns:
            List of alarm dicts (one per alarm code found)
        """
        alarms = []
        
        # Remove symbol prefix (E01, E02, etc.)
        line_data = re.sub(r'^E\d+,\s*', '', line)
        parts = [p.strip() for p in line_data.split(',')]
        
        # Parse each comma-separated alarm code
        for alarm_code_str in parts:
            alarm_code_str = alarm_code_str.strip()
            # Skip empty values (spaces only)
            if not alarm_code_str or alarm_code_str.isspace():
                continue
            
            # Parse alarm code based on control version
            if self.control_version == "C00":
                # C00: 10 bytes - 2-digit category + 4-digit number + 4-digit auxiliary
                # Trim to 10 chars (remove trailing spaces)
                alarm_code_str = alarm_code_str[:10].ljust(10, '0')
                
                category_code = alarm_code_str[0:2]
                alarm_number = alarm_code_str[2:6]
                auxiliary = alarm_code_str[6:10]
            else:  # D00
                # D00: 22 bytes - 2-digit category + 4-digit number + 16-digit auxiliary
                # Trim to 22 chars (remove trailing spaces)
                alarm_code_str = alarm_code_str[:22].ljust(22, '0')
                
                category_code = alarm_code_str[0:2]
                alarm_number = alarm_code_str[2:6]
                auxiliary = alarm_code_str[6:22]
            
            # Map category code to category name
            category = ALARM_CATEGORIES.get(category_code, f"UNKNOWN({category_code})")
            
            # Build alarm code string (e.g., "NC1234" or "SV0056")
            formatted_code = f"{category}{alarm_number}"
            
            alarm = {
                "code": formatted_code,
                "raw_code": alarm_code_str,
                "category": category,
                "category_code": category_code,
                "number": alarm_number,
                "auxiliary": auxiliary,
                "type": "alarm" if category_code != "90" else "operator_message",
            }
            
            # Enrich with lookup information (description, cause, solution)
            alarm = enrich_alarm_with_lookup(alarm, self.control_version)
            
            alarms.append(alarm)
        
        return alarms

    def _parse_l01_line(self, line: str) -> List[Dict[str, Any]]:
        """
        Parse L01 line (contains L01-L18 loading system alarm messages, comma-separated).
        
        Returns:
            List of loading system alarm dicts (one per alarm code found)
        """
        loading_alarms = []
        
        # Remove symbol prefix (L01, L02, etc.)
        line_data = re.sub(r'^L\d+,\s*', '', line)
        parts = [p.strip() for p in line_data.split(',')]
        
        # Parse each comma-separated alarm code
        for alarm_code_str in parts:
            alarm_code_str = alarm_code_str.strip()
            # Skip empty values (spaces only)
            if not alarm_code_str or alarm_code_str.isspace():
                continue
            
            # Parse alarm code based on control version
            if self.control_version == "C00":
                # C00: 11 bytes - 3-digit category + 4-digit number + 4-digit auxiliary
                # Trim to 11 chars (remove trailing spaces)
                alarm_code_str = alarm_code_str[:11].ljust(11, '0')
                
                category_code = alarm_code_str[0:3]
                alarm_number = alarm_code_str[3:7]
                auxiliary = alarm_code_str[7:11]
            else:  # D00
                # D00: 22 bytes - 3-digit category + 4-digit number + 4-digit auxiliary + additional data
                # Trim to 22 chars (remove trailing spaces)
                alarm_code_str = alarm_code_str[:22].ljust(22, '0')
                
                category_code = alarm_code_str[0:3]
                alarm_number = alarm_code_str[3:7]
                auxiliary = alarm_code_str[7:11]
                # Additional data in remaining bytes (11-22)
            
            # Build alarm code string (e.g., "LS001234")
            formatted_code = f"LS{alarm_number}"
            
            loading_alarms.append({
                "code": formatted_code,
                "raw_code": alarm_code_str,
                "category": category_code,
                "number": alarm_number,
                "auxiliary": auxiliary,
                "type": "loading_system",
            })
        
        return loading_alarms


def parse_alarm_v2(content: bytes, control_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to parse ALARM.NC content using schema-based parser.

    Args:
        content: Raw bytes from ALARM.NC file
        control_version: Control version ('C00' or 'D00'). If None, attempts auto-detection.

    Returns:
        Parsed alarm data with alarms, loading_alarms, and control_version metadata
    """
    parser = ALARMParserV2(content, control_version=control_version)
    return parser.parse()

