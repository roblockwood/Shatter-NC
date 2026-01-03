"""
Schema definition for ALARM (Current Alarm) data files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.12
- D00 Control: Section 3.6.5.12

File naming: ALARM

Unit Handling:
- Method: not_applicable (ALARM data doesn't have unit-specific values)
- Conversion: no (alarm codes and messages)

Format:
- Delimited by comma (,)
- CR+LF at end of line
- Multi-line format with symbol prefixes:
  - E01-E36: Alarm/Operator messages (36 total)
  - L01-L18: Loading system alarm messages (18 total)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.schemas.cnc_data.tolni_schema import FieldDefinition, SchemaDefinition


# C00 Control Schema (Section 5.6.4.12)
# E01 line: Alarm/Operator message No.1 (10 bytes)
#   - 2 high-order digits: Category (01: EX, 02: EC, 03: SV, 04: NC, 05: IO, 06: SP, 07: SM, 08: SL, 09: CM, 10: ES, 11: FC, 90: OM)
#   - Next 4 digits: No.
#   - 4 low-order digits: Auxiliary No.
# E02-E36: Same as E01 (omitted in schema, but same format)
# L01 line: Loading system alarm message No.1 (11 bytes)
#   - First 3 digits: Category number
#   - Next 4 digits: Number
#   - Last 4 digits: Auxiliary number
# L02-L18: Same as L01 (omitted in schema, but same format)

C00_ALARM_E01_FIELDS = [
    FieldDefinition("alarm_code", 0, str, False, "Alarm/Operator message (E01)", "10 bytes: 2-digit category + 4-digit number + 4-digit auxiliary"),
]

C00_ALARM_L01_FIELDS = [
    FieldDefinition("alarm_code", 0, str, False, "Loading system alarm message (L01)", "11 bytes: 3-digit category + 4-digit number + 4-digit auxiliary"),
]

# D00 Control Schema (Section 3.6.5.12)
# E01 line: Alarm/Operator message No.1 (22 bytes)
#   - 2 high-order digits: Category (01: EX, 02: EC, 03: SV, 04: NC, 05: IO, 06: SP, 07: SM, 08: SL, 09: CM, 10: PN, 11: FN, 90: OM)
#   - Next 4 digits: No.
#   - 16 low-order digits: Auxiliary No.
# E02-E36: Same as E01 (22*35 bytes total, omitted in schema)
# L01 line: Loading system alarm message No.1 (22 bytes)
#   - First 3 digits: Category
#   - Next 4 digits: Number
#   - Last 4 digits: Auxiliary number (but field is 22 bytes, so there's more complexity)
# L02-L18: Same as L01 (22*17 bytes total, omitted in schema)

D00_ALARM_E01_FIELDS = [
    FieldDefinition("alarm_code", 0, str, False, "Alarm/Operator message (E01)", "22 bytes: 2-digit category + 4-digit number + 16-digit auxiliary"),
]

D00_ALARM_L01_FIELDS = [
    FieldDefinition("alarm_code", 0, str, False, "Loading system alarm message (L01)", "22 bytes: 3-digit category + 4-digit number + 4-digit auxiliary + additional data"),
]

C00_SCHEMA = SchemaDefinition(
    data_type="ALARM",
    file_pattern="ALARM",
    control_version="C00",
    unit_handling={
        "method": "not_applicable",
        "conversion": False
    },
    line_format={
        "structure": "delimited",
        "delimiter": "comma",
        "header_lines": 0,
        "footer_lines": 0,
        "empty_line_handling": "skip",
        "comment_lines": "none",
    },
    tool_fields=C00_ALARM_E01_FIELDS,  # Using tool_fields for E01 line
    other_line_types={
        "L01": C00_ALARM_L01_FIELDS,
        # E02-E36 and L02-L18 use same format as E01/L01
    }
)

D00_SCHEMA = SchemaDefinition(
    data_type="ALARM",
    file_pattern="ALARM",
    control_version="D00",
    unit_handling={
        "method": "not_applicable",
        "conversion": False
    },
    line_format={
        "structure": "delimited",
        "delimiter": "comma",
        "header_lines": 0,
        "footer_lines": 0,
        "empty_line_handling": "skip",
        "comment_lines": "none",
    },
    tool_fields=D00_ALARM_E01_FIELDS,  # Using tool_fields for E01 line
    other_line_types={
        "L01": D00_ALARM_L01_FIELDS,
        # E02-E36 and L02-L18 use same format as E01/L01
    }
)

# Schema registry
ALARM_SCHEMAS = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA,
}

def get_alarm_schema(control_version: str) -> SchemaDefinition:
    """
    Get ALARM schema for a specific control version.
    
    Args:
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        SchemaDefinition for the control version
        
    Raises:
        ValueError: If control_version is not supported
    """
    if control_version not in ALARM_SCHEMAS:
        raise ValueError(f"Unsupported control version: {control_version}. Supported: {list(ALARM_SCHEMAS.keys())}")
    return ALARM_SCHEMAS[control_version]

