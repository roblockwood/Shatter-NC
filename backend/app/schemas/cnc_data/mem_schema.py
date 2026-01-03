"""
Schema definition for MEM (Memory Operation) data files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.8
- D00 Control: Section 3.6.5.8

File naming: MEM

Unit Handling:
- Method: not_applicable (MEM data doesn't have unit-specific values)
- Conversion: no (metadata only)

Format:
- Delimited by comma (,)
- CR+LF at end of line
- Single line with: A01,Program No.,Operation status,Inner pallet status,Spare tool,Mode,Expansion
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.schemas.cnc_data.tolni_schema import FieldDefinition, SchemaDefinition


# C00 Control Schema (Section 5.6.4.8)
# Structure: Single line with comma-delimited fields
# A01 (Operation folder name, 10 bytes), Program No. (4 bytes), Operation status (1 byte),
# Inner pallet status (1 byte), Spare tool (1 byte), Mode (1 byte), Expansion (1 byte)
C00_MEM_FIELDS = [
    FieldDefinition("operation_folder_name", 0, str, False, "Operation folder name (A01)", "10 bytes, 8 half-width characters with single quotes"),
    FieldDefinition("program_name", 1, str, True, "Program No.", "4 bytes, O-number (e.g., '2045')"),
    FieldDefinition("operation_status", 2, int, False, "Operation status", "0: Reset, 1: Operation, 2: Temporary stop, 3: Block stop"),
    FieldDefinition("inner_pallet_status", 3, int, False, "Inner pallet status", "0: Not indexed, 1: Inner side No.1, 2: Inner side No.2"),
    FieldDefinition("spare_tool", 4, int, False, "Spare tool", "0: Not used, 1: Being used"),
    FieldDefinition("mode", 5, int, False, "Mode", "1 byte"),
    FieldDefinition("expansion", 6, int, False, "Expansion", "0: Normal, 1: Expanded"),
]

# D00 Control Schema (Section 3.6.5.8)
# Structure: Single line with comma-delimited fields
# A01 (Operation folder name, 35 bytes), Program (34 bytes), Operation status (1 byte),
# Inner pallet status (1 byte), Spare tool (1 byte), Mode (1 byte), Expansion (1 byte)
D00_MEM_FIELDS = [
    FieldDefinition("operation_folder_name", 0, str, False, "Operation folder name (A01)", "35 bytes with single quotes"),
    FieldDefinition("program_name", 1, str, True, "Program", "34 bytes, O-number or full program name"),
    FieldDefinition("operation_status", 2, int, False, "Operation status", "0: Reset, 1: Operation, 2: Temporary stop, 3: Block stop"),
    FieldDefinition("inner_pallet_status", 3, int, False, "Inner pallet status", "0: Not indexed, 1: Inner side pallet 1, 2: Inner side pallet 2"),
    FieldDefinition("spare_tool", 4, int, False, "Spare tool", "0: Not used, 1: Being used"),
    FieldDefinition("mode", 5, int, False, "Mode", "1 byte"),
    FieldDefinition("expansion", 6, int, False, "Expansion", "0: Normal, 1: Expanded"),
]

C00_SCHEMA = SchemaDefinition(
    data_type="MEM",
    file_pattern="MEM",
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
        "field_lengths": {
            "operation_folder_name": 10,
            "program_name": 4,
            "operation_status": 1,
            "inner_pallet_status": 1,
            "spare_tool": 1,
            "mode": 1,
            "expansion": 1
        }
    },
    tool_fields=C00_MEM_FIELDS,  # Reusing tool_fields structure for MEM fields
    other_line_types={}
)

D00_SCHEMA = SchemaDefinition(
    data_type="MEM",
    file_pattern="MEM",
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
        "field_lengths": {
            "operation_folder_name": 35,
            "program_name": 34,
            "operation_status": 1,
            "inner_pallet_status": 1,
            "spare_tool": 1,
            "mode": 1,
            "expansion": 1
        }
    },
    tool_fields=D00_MEM_FIELDS,  # Reusing tool_fields structure for MEM fields
    other_line_types={}
)

# Schema registry
MEM_SCHEMAS = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA,
}

def get_mem_schema(control_version: str) -> SchemaDefinition:
    """
    Get MEM schema for a specific control version.
    
    Args:
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        SchemaDefinition for the control version
        
    Raises:
        ValueError: If control_version is not supported
    """
    if control_version not in MEM_SCHEMAS:
        raise ValueError(f"Unsupported control version: {control_version}. Supported: {list(MEM_SCHEMAS.keys())}")
    return MEM_SCHEMAS[control_version]

