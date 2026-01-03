"""
Schema definition for MONTR (Machine Monitor) data files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.15
- D00 Control: Section 3.6.5.14

File naming: MONTR

Unit Handling:
- Method: not_applicable (MONTR data doesn't have unit-specific values)
- Conversion: no (time and counter data)

Format:
- Delimited by comma (,)
- CR+LF at end of line
- Multi-line format with symbol prefixes:
  - P01: Program information (operation program, edit program, folders)
  - T01: Time information (total operation time, power on time, operation time)
  - C01-C04: Workpiece counters (count, current, end, end warning)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.schemas.cnc_data.tolni_schema import FieldDefinition, SchemaDefinition


# C00 Control Schema (Section 5.6.4.15)
# P01 line: Operation program No. (4), Edit program No. (4), Operation folder name (258), Edit folder name (10)
# T01 line: Total operation time (9), Power on time (9), Operation time (9)
# C01-C04 lines: Count (3), Current (6), End (6), End warning (6)

C00_MONTR_P01_FIELDS = [
    FieldDefinition("operation_program_no", 0, str, False, "Operation program No. (P01)", "4 bytes, O-number"),
    FieldDefinition("edit_program_no", 1, str, False, "Edit program No. (P01)", "4 bytes, O-number"),
    FieldDefinition("operation_folder_name", 2, str, False, "Operation folder name (P01)", "258 bytes, 256 half-width characters with single quotes"),
    FieldDefinition("edit_folder_name", 3, str, False, "Edit folder name (P01)", "10 bytes, 8 half-width characters with single quotes"),
]

C00_MONTR_T01_FIELDS = [
    FieldDefinition("total_operation_time", 0, str, False, "Total operation time (T01)", "9 bytes, format: HHMMSSMMM"),
    FieldDefinition("power_on_time", 1, str, False, "Power on time (T01)", "9 bytes, format: HHMMSSMMM"),
    FieldDefinition("operation_time", 2, str, False, "Operation time (T01)", "9 bytes, format: HHMMSSMMM"),
]

C00_MONTR_C01_FIELDS = [
    FieldDefinition("count", 0, int, False, "Workpiece counter count (C01)", "3 bytes"),
    FieldDefinition("current", 1, int, False, "Workpiece counter current (C01)", "6 bytes"),
    FieldDefinition("end", 2, int, False, "Workpiece counter end (C01)", "6 bytes"),
    FieldDefinition("end_warning", 3, int, False, "Workpiece counter end warning (C01)", "6 bytes"),
]

# D00 Control Schema (Section 3.6.5.14)
# P01 line: Operation program No. (34), Edit program No. (34), Operation folder name (258), Edit folder name (35)
# T01 line: Total operation time (9), Power on time (9), Operation time (9)
# C01-C04 lines: Count (3), Current (6), End (6), End warning (6)

D00_MONTR_P01_FIELDS = [
    FieldDefinition("operation_program_no", 0, str, False, "Operation program No. (P01)", "34 bytes, O-number or full program name"),
    FieldDefinition("edit_program_no", 1, str, False, "Edit program No. (P01)", "34 bytes, O-number or full program name"),
    FieldDefinition("operation_folder_name", 2, str, False, "Operation folder name (P01)", "258 bytes with single quotes"),
    FieldDefinition("edit_folder_name", 3, str, False, "Edit folder name (P01)", "35 bytes with single quotes"),
]

D00_MONTR_T01_FIELDS = [
    FieldDefinition("total_operation_time", 0, str, False, "Total operation time (T01)", "9 bytes, format: HHMMSSMMM"),
    FieldDefinition("power_on_time", 1, str, False, "Power on time (T01)", "9 bytes, format: HHMMSSMMM"),
    FieldDefinition("operation_time", 2, str, False, "Operation time (T01)", "9 bytes, format: HHMMSSMMM"),
]

D00_MONTR_C01_FIELDS = [
    FieldDefinition("count", 0, int, False, "Workpiece counter count (C01)", "3 bytes"),
    FieldDefinition("current", 1, int, False, "Workpiece counter current (C01)", "6 bytes"),
    FieldDefinition("end", 2, int, False, "Workpiece counter end (C01)", "6 bytes"),
    FieldDefinition("end_warning", 3, int, False, "Workpiece counter end warning (C01)", "6 bytes"),
]

C00_SCHEMA = SchemaDefinition(
    data_type="MONTR",
    file_pattern="MONTR",
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
    tool_fields=C00_MONTR_P01_FIELDS,  # Using tool_fields for P01 line
    other_line_types={
        "T01": C00_MONTR_T01_FIELDS,
        "C01": C00_MONTR_C01_FIELDS,
        "C02": C00_MONTR_C01_FIELDS,
        "C03": C00_MONTR_C01_FIELDS,
        "C04": C00_MONTR_C01_FIELDS,
    }
)

D00_SCHEMA = SchemaDefinition(
    data_type="MONTR",
    file_pattern="MONTR",
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
    tool_fields=D00_MONTR_P01_FIELDS,  # Using tool_fields for P01 line
    other_line_types={
        "T01": D00_MONTR_T01_FIELDS,
        "C01": D00_MONTR_C01_FIELDS,
        "C02": D00_MONTR_C01_FIELDS,
        "C03": D00_MONTR_C01_FIELDS,
        "C04": D00_MONTR_C01_FIELDS,
    }
)

# Schema registry
MONTR_SCHEMAS = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA,
}

def get_montr_schema(control_version: str) -> SchemaDefinition:
    """
    Get MONTR schema for a specific control version.
    
    Args:
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        SchemaDefinition for the control version
        
    Raises:
        ValueError: If control_version is not supported
    """
    if control_version not in MONTR_SCHEMAS:
        raise ValueError(f"Unsupported control version: {control_version}. Supported: {list(MONTR_SCHEMAS.keys())}")
    return MONTR_SCHEMAS[control_version]

