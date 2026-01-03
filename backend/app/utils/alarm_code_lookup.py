"""
Alarm code lookup utility.

Loads alarm code lists from JSON files and provides lookup functionality
to get alarm descriptions, causes, and remedies based on alarm codes.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Path to alarm code list JSON files
# __file__ is backend/app/utils/alarm_code_lookup.py
# Go to backend/app/data/alarm_codes: backend/app/utils -> backend/app -> backend/app/data/alarm_codes
_app_dir = Path(__file__).parent.parent
ALARM_CODE_LIST_C00 = _app_dir / "data" / "alarm_codes" / "section_11_7_alarm_code_list_c00.json"
ALARM_CODE_LIST_D00 = _app_dir / "data" / "alarm_codes" / "section_2_13_alarm_code_list_d00.json"

# Cache for loaded alarm code dictionaries
# Note: Cache is cleared on module reload, so changes to alarm code files require restart
_alarm_code_cache: Dict[str, Dict[str, Dict[str, any]]] = {}


def _parse_alarm_code_range(code_str: str) -> list[str]:
    """
    Parse alarm code string which may be a range or single code.
    
    Examples:
        "EX0000\n:\nEX0089" -> ["EX0000", "EX0001", ..., "EX0089"]
        "IO0518" -> ["IO0518"]
        "SV0015" -> ["SV0015"]
    
    Returns:
        List of alarm codes
    """
    # Remove newlines and whitespace
    code_str = code_str.replace('\n', '').strip()
    
    # Check if it's a range (contains ":")
    if ':' in code_str:
        parts = code_str.split(':')
        if len(parts) == 2:
            start_code = parts[0].strip()
            end_code = parts[1].strip()
            
            # Extract prefix (e.g., "EX") and number parts
            start_match = re.match(r'([A-Z]+)(\d+)', start_code)
            end_match = re.match(r'([A-Z]+)(\d+)', end_code)
            
            if start_match and end_match:
                prefix = start_match.group(1)
                start_num = int(start_match.group(2))
                end_num = int(end_match.group(2))
                
                # Generate all codes in range
                codes = []
                for num in range(start_num, end_num + 1):
                    # Format with same zero-padding as start code
                    num_str = str(num).zfill(len(start_match.group(2)))
                    codes.append(f"{prefix}{num_str}")
                return codes
    
    # Single code
    return [code_str.strip()]


def _load_alarm_code_list(json_path: Path, control_version: str) -> Dict[str, Dict[str, any]]:
    """
    Load alarm code list from JSON file and create lookup dictionary.
    
    Args:
        json_path: Path to alarm code list JSON file
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        Dictionary mapping alarm codes to their information:
        {
            "IO0518": {
                "stop_level": "4",
                "reset_level": "2",
                "message": "Tool washing liquid surface sensor is faulty.",
                "cause": "...",
                "solution": "..."
            },
            ...
        }
    """
    if not json_path.exists():
        logger.warning(f"Alarm code list file not found: {json_path}")
        return {}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        alarm_dict = {}
        
        # Process all tables in the JSON
        for table in data.get("tables", []):
            rows = table.get("rows", [])
            
            for row in rows:
                if len(row) < 6:
                    continue
                
                # Extract fields: [No., Stop level, Reset level, Alarm message, Cause, Solution]
                code_str = row[0].strip()
                stop_level = row[1].strip() if len(row) > 1 else ""
                reset_level = row[2].strip() if len(row) > 2 else ""
                message = row[3].strip() if len(row) > 3 else ""
                cause = row[4].strip() if len(row) > 4 else ""
                solution = row[5].strip() if len(row) > 5 else ""
                
                # Parse alarm code(s) - may be a range or single code
                codes = _parse_alarm_code_range(code_str)
                
                # Store information for each code in the range
                for code in codes:
                    alarm_dict[code] = {
                        "stop_level": stop_level,
                        "reset_level": reset_level,
                        "message": message,
                        "cause": cause,
                        "solution": solution,
                    }
        
        logger.info(f"Loaded {len(alarm_dict)} alarm codes from {control_version} alarm code list")
        return alarm_dict
        
    except Exception as e:
        logger.error(f"Error loading alarm code list from {json_path}: {e}")
        return {}


def get_alarm_code_lookup(control_version: str = "C00") -> Dict[str, Dict[str, any]]:
    """
    Get alarm code lookup dictionary for a control version.
    
    Args:
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        Dictionary mapping alarm codes to their information
    """
    # Check cache first
    if control_version in _alarm_code_cache:
        return _alarm_code_cache[control_version]
    
    # Load from JSON file
    if control_version == "C00":
        json_path = ALARM_CODE_LIST_C00
    elif control_version == "D00":
        json_path = ALARM_CODE_LIST_D00
    else:
        logger.warning(f"Unknown control version: {control_version}, defaulting to C00")
        json_path = ALARM_CODE_LIST_C00
    
    alarm_dict = _load_alarm_code_list(json_path, control_version)
    
    # Cache it
    _alarm_code_cache[control_version] = alarm_dict
    
    return alarm_dict


def lookup_alarm_code(alarm_code: str, control_version: str = "C00") -> Optional[Dict[str, any]]:
    """
    Look up alarm code information.
    
    Args:
        alarm_code: Alarm code (e.g., "IO0518", "SV0015")
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        Dictionary with alarm information, or None if not found:
        {
            "stop_level": "4",
            "reset_level": "2",
            "message": "Tool washing liquid surface sensor is faulty.",
            "cause": "...",
            "solution": "..."
        }
    """
    lookup = get_alarm_code_lookup(control_version)
    return lookup.get(alarm_code)


def enrich_alarm_with_lookup(alarm: Dict[str, any], control_version: str = "C00") -> Dict[str, any]:
    """
    Enrich alarm dictionary with lookup information.
    
    Args:
        alarm: Alarm dictionary from parser (must have "code" field)
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        Enriched alarm dictionary with lookup information added
    """
    alarm_code = alarm.get("code", "")
    if not alarm_code:
        return alarm
    
    # Look up alarm code information
    lookup_info = lookup_alarm_code(alarm_code, control_version)
    
    if lookup_info:
        alarm["description"] = lookup_info.get("message", "")
        alarm["cause"] = lookup_info.get("cause", "")
        alarm["solution"] = lookup_info.get("solution", "")
        # Set stop_level/reset_level from lookup (they should always be present in lookup data)
        alarm["stop_level"] = lookup_info.get("stop_level", "")
        alarm["reset_level"] = lookup_info.get("reset_level", "")
    else:
        # No lookup info found - set empty strings so frontend knows they're missing
        alarm["stop_level"] = ""
        alarm["reset_level"] = ""
    
    return alarm

