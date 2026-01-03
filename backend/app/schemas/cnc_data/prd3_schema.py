"""
Schema definition for PRD3/PRDD3 (Production data 3 - Status history) data files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.6 (PRD3)
- D00 Control: Section 3.6.5.6 (PRDD3)

File naming:
- C00: PRD3
- D00: PRDD3

Unit Handling:
- Method: not_applicable (PRD3 data doesn't have unit-specific values)
- Conversion: no (status and timestamp data)

Format:
- Delimited by comma (,)
- CR+LF at end of line
- Multi-line format with symbol prefixes:
  - A01: Header (start/end pointers, status)
  - C01: Current status (date/time, status code, program/error, folder, memory type)
  - B0001-B3500 (C00) or B0001-B40000 (D00): Status log entries (same structure as C01)

Status Codes:
- 1: Power OFF
- 2: Standby mode
- 3: Operating
- 4: Stopped
- 5: Error
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.schemas.cnc_data.tolni_schema import FieldDefinition, SchemaDefinition


# C00 Control Schema (Section 5.6.4.6)
# A01 line: Start pointer (4), End pointer (4), Status (1)
# C01 line: Start date/time (14), Status (1), Language (1), Program/Error No. (6), Folder name (10), Memory type (1)

C00_PRD3_A01_FIELDS = [
    FieldDefinition("start_pointer", 0, int, False, "Start pointer (A01)", "4 bytes"),
    FieldDefinition("end_pointer", 1, int, False, "End pointer (A01)", "4 bytes"),
    FieldDefinition("status", 2, int, False, "Status (A01)", "1 byte"),
]

C00_PRD3_C01_FIELDS = [
    FieldDefinition("start_date_time", 0, str, False, "Current (Start date and time) (C01)", "14 bytes, format: YYYYMMDDhhmmss"),
    FieldDefinition("current_status", 1, int, False, "Current (Status) (C01)", "1 byte: 1=Power OFF, 2=Standby, 3=Operating, 4=Stopped, 5=Error"),
    FieldDefinition("current_language", 2, int, False, "Current status (Language) (C01)", "1 byte: 0=NC, 1=Conversation"),
    FieldDefinition("program_or_error_no", 3, str, False, "Current status (Program No. / Error No.) (C01)", "6 bytes: Program No. when status=3, Error No. when status=5"),
    FieldDefinition("folder_name", 4, str, False, "Current status (Folder name) (C01)", "10 bytes with single quotes"),
    FieldDefinition("memory_operation_type", 5, int, False, "Memory operation type (C01)", "1 byte: 0=Internal memory, 1=Tape (General), 2=Tape (Memory card)"),
]

# D00 Control Schema (Section 3.6.5.6)
# A01 line: Start index (4), End index (4), Status (1), File writing index (5)
# C01 line: Start date/time (14), Status (1), Language (1), Program/Error No. (34), Folder name (35), Memory type (1)

D00_PRD3_A01_FIELDS = [
    FieldDefinition("start_index", 0, int, False, "Start index (A01)", "4 bytes"),
    FieldDefinition("end_index", 1, int, False, "End index (A01)", "4 bytes"),
    FieldDefinition("status", 2, int, False, "Status (A01)", "1 byte"),
    FieldDefinition("file_writing_index", 3, int, False, "File writing index (A01)", "5 bytes"),
]

D00_PRD3_C01_FIELDS = [
    FieldDefinition("start_date_time", 0, str, False, "Current (Start date and time) (C01)", "14 bytes, format: YYYYMMDDhhmmss"),
    FieldDefinition("current_status", 1, int, False, "Current (Status) (C01)", "1 byte: 1=Power OFF, 2=Standby, 3=Operating, 4=Stopped, 5=Error"),
    FieldDefinition("current_language", 2, int, False, "Current status (Language) (C01)", "1 byte: 0=NC, 1=Conversation"),
    FieldDefinition("program_or_error_no", 3, str, False, "Current status (Program No. / Error No.) (C01)", "34 bytes: Program No. when status=3, Error No. when status=5 (first 2 digits=category, last 4=number)"),
    FieldDefinition("folder_name", 4, str, False, "Current status (Folder name) (C01)", "35 bytes with single quotes"),
    FieldDefinition("memory_operation_type", 5, int, False, "Memory operation type (C01)", "1 byte: 0=Internal memory, 1=Tape (General), 2=Tape (Memory card), 3=FTP load operation"),
]

C00_SCHEMA = SchemaDefinition(
    data_type="PRD3",
    file_pattern="PRD3",
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
    tool_fields=C00_PRD3_A01_FIELDS,  # Using tool_fields for A01 line
    other_line_types={
        "C01": C00_PRD3_C01_FIELDS,
    }
)

D00_SCHEMA = SchemaDefinition(
    data_type="PRDD3",
    file_pattern="PRDD3",
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
    tool_fields=D00_PRD3_A01_FIELDS,  # Using tool_fields for A01 line
    other_line_types={
        "C01": D00_PRD3_C01_FIELDS,
    }
)

# Schema registry
PRD3_SCHEMAS = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA,
}

def get_prd3_schema(control_version: str) -> SchemaDefinition:
    """
    Get PRD3 schema for a specific control version.
    
    Args:
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        SchemaDefinition for the control version
        
    Raises:
        ValueError: If control_version is not supported
    """
    if control_version not in PRD3_SCHEMAS:
        raise ValueError(f"Unsupported control version: {control_version}. Supported: {list(PRD3_SCHEMAS.keys())}")
    return PRD3_SCHEMAS[control_version]

