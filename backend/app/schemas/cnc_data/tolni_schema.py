"""
Schema definition for TOLNn (Tool Offset Table) data files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.19
- D00 Control: Section 3.6.5.18

File naming: TOLNun
- u: Unit system (M: Metric, I: Inch)
- n: Data bank number (0-9, where "0" represents "10")

Unit Handling:
- Method: filename_based
- TOLNI1.NC = inches
- TOLNM1.NC = millimeters
- Conversion: no (values stored in native units)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class FieldDefinition:
    """Definition for a single field in the schema."""
    name: str
    csv_index: int  # CSV field index (0-based, -1 for tool_number from prefix)
    data_type: type  # int, float, str
    required: bool
    description: str
    validation: Optional[str] = None  # Validation rule description
    notes: Optional[str] = None


@dataclass
class SchemaDefinition:
    """Complete schema definition for a data type."""
    data_type: str
    file_pattern: str
    control_version: str  # C00 or D00
    unit_handling: Dict[str, Any]
    line_format: Dict[str, Any]
    tool_fields: List[FieldDefinition]  # Fields for T01-T99 lines
    other_line_types: Dict[str, str]  # V##, M##, Y## line handling


# C00 Control Schema (Section 5.6.4.19)
C00_TOOL_FIELDS = [
    FieldDefinition("tool_number", -1, int, True, "Tool number (extracted from T## prefix)", "1-99"),
    FieldDefinition("tool_length_offset", 0, float, True, "Tool length offset", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    FieldDefinition("tool_length_wear_offset", 1, float, False, "T length wear offset", "-99.999~99.999 (inch) or -9.9999~9.9999 (mm)"),
    FieldDefinition("cutter_compensation", 2, float, True, "Cutter compensation (diameter)", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    FieldDefinition("cutter_wear_offset", 3, float, False, "Cutter wear offset", "-99.999~99.999 (inch) or -9.9999~9.9999 (mm)"),
    FieldDefinition("tool_life_unit", 4, int, False, "Tool life unit", "1-4"),
    FieldDefinition("initial_tool_life", 5, int, False, "Initial tool life / End of tool life", "0~999999"),
    FieldDefinition("tool_life_warning", 6, int, False, "Tool life warning", "0~999999"),
    FieldDefinition("tool_life", 7, int, False, "Tool life", "0~999999"),
    FieldDefinition("tool_name", 8, str, False, "Tool name (with single quotes)", "16 chars, first/last are quotes"),
    FieldDefinition("rotation_feed", 9, float, False, "Rotation feed (optional, may be empty)", "0.01~9.99 (inch) or 0.001~0.999 (mm)"),
    FieldDefinition("s_command_value", 10, int, False, "S command value (optional, may be empty)", "1~99999"),
    FieldDefinition("f_command_value", 11, float, False, "F command value (optional, may be empty)", "0.01~999999.99 (inch) or 0.001~99999.999 (mm)"),
    FieldDefinition("maximum_speed", 12, int, False, "Maximum speed (optional, may be empty)", "0-999999 (0 = rotation not possible)"),
    # Fields 9-14: Optional fields that may be empty (rotation_feed, s_command_value, f_command_value, maximum_speed, tool_wash, cts)
    FieldDefinition("rotation_feed", 9, float, False, "Rotation feed (optional, may be empty)", "0.01~9.99 (inch) or 0.001~0.999 (mm)"),
    FieldDefinition("s_command_value", 10, int, False, "S command value (optional, may be empty)", "1~99999"),
    FieldDefinition("f_command_value", 11, float, False, "F command value (optional, may be empty)", "0.01~999999.99 (inch) or 0.001~99999.999 (mm)"),
    FieldDefinition("maximum_speed", 12, int, False, "Maximum speed (optional, may be empty)", "0-999999 (0 = rotation not possible)"),
    # Fields 9-14: Optional fields that may be empty (rotation_feed, s_command_value, f_command_value, maximum_speed, tool_wash, cts)
    FieldDefinition("rotation_feed", 9, float, False, "Rotation feed (optional, may be empty)", "0.01~9.99 (inch) or 0.001~0.999 (mm)"),
    FieldDefinition("s_command_value", 10, int, False, "S command value (optional, may be empty)", "1~99999"),
    FieldDefinition("f_command_value", 11, float, False, "F command value (optional, may be empty)", "0.01~999999.99 (inch) or 0.001~99999.999 (mm)"),
    FieldDefinition("maximum_speed", 12, int, False, "Maximum speed (optional, may be empty)", "0-999999 (0 = rotation not possible)"),
    FieldDefinition("tool_wash", 13, int, False, "Tool wash (optional, may be empty)", "0: Possible, 1: Not possible"),
    FieldDefinition("cts", 14, int, False, "CTS (optional, may be empty)", "0: Possible, 1: Not possible"),
    # Fields 15-16: Additional optional fields (may be tool_type_number, tool_wash, cts, or other)
    FieldDefinition("tool_type_number", 15, int, False, "Tool type number (optional, may be empty)", "0-99999999 (0 = not set)"),
    # Field 16: Additional field (may be empty or contain data)
    # Field 17: May be empty separator
    FieldDefinition("tool_position_offset_x", 18, float, False, "Tool position offset (X) (optional)", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    FieldDefinition("tool_position_wear_offset_x", 19, float, False, "Tool position wear offset (X) (optional)", "-99.999~99.999 (inch) or -9.9999~9.9999 (mm)"),
    FieldDefinition("tool_position_offset_y", 20, float, False, "Tool position offset (Y) (optional)", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    FieldDefinition("tool_position_wear_offset_y", 21, float, False, "Tool position wear offset (Y) (optional)", "-99.999~99.999 (inch) or -9.9999~9.9999 (mm)"),
]

# D00 Control Schema (Section 3.6.5.18)
# Differences from C00:
# - Tool life fields are 7 chars instead of 6 (0~9999999 instead of 0~999999)
# - Tool life unit has 5 options instead of 4 (adds "5: Time (sec.)")
# - Adds "Peripheral speed" field after tool_name
# - F command value is 14 chars instead of 9
D00_TOOL_FIELDS = [
    FieldDefinition("tool_number", -1, int, True, "Tool number (extracted from T## prefix)", "1-99"),
    FieldDefinition("tool_length_offset", 0, float, True, "Tool length offset", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    FieldDefinition("tool_length_wear_offset", 1, float, False, "T length wear offset", "-99.999~99.999 (inch) or -9.9999~9.9999 (mm)"),
    FieldDefinition("cutter_compensation", 2, float, True, "Cutter compensation (diameter)", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    FieldDefinition("cutter_wear_offset", 3, float, False, "Cutter wear offset", "-99.999~99.999 (inch) or -9.9999~9.9999 (mm)"),
    FieldDefinition("tool_life_unit", 4, int, False, "Tool life unit", "1: Not counted, 2: Time (min.), 3: Drilling (holes), 4: Program (cycles), 5: Time (sec.)"),
    FieldDefinition("initial_tool_life", 5, int, False, "Initial tool life / End of tool life", "0~9999999"),
    FieldDefinition("tool_life_warning", 6, int, False, "Tool life warning", "0~9999999"),
    FieldDefinition("tool_life", 7, int, False, "Tool life", "0~9999999"),
    FieldDefinition("tool_name", 8, str, False, "Tool name (with single quotes)", "16 chars, first/last are quotes"),
    FieldDefinition("peripheral_speed", 9, float, False, "Peripheral speed (D00 only)", "0.1~9999.9"),
    FieldDefinition("rotation_feed", 10, float, False, "Rotation feed", "0.01~9.99 (inch) or 0.001~0.999 (mm)"),
    FieldDefinition("s_command_value", 11, int, False, "S command value", "1~99999"),
    FieldDefinition("f_command_value", 12, float, False, "F command value (14 chars in D00)", "0.01~999999.99 (inch) or 0.001~99999.999 (mm), 14 chars"),
    FieldDefinition("maximum_speed", 13, int, False, "Maximum speed", "0-999999 (0 = rotation not possible)"),
    FieldDefinition("tool_wash", 14, int, False, "Tool wash", "0: Possible, 1: Not possible"),
    FieldDefinition("cts", 15, int, False, "CTS", "0: Possible, 1: Not possible"),
    FieldDefinition("tool_type_number", 16, int, False, "Tool type number", "0-99999999 (0 = not set)"),
    FieldDefinition("tool_position_offset_x", 17, float, False, "Tool position offset (X)", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    FieldDefinition("tool_position_wear_offset_x", 18, float, False, "Tool position wear offset (X)", "-99.999~99.999 (inch) or -9.9999~9.9999 (mm)"),
    FieldDefinition("tool_position_offset_y", 19, float, False, "Tool position offset (Y)", "-999.999~999.999 (inch) or -99.9999~99.9999 (mm)"),
    # Note: D00 documentation cuts off, but structure appears similar to C00
]

C00_SCHEMA = SchemaDefinition(
    data_type="TOLNn",
    file_pattern="TOLNI1.NC (inches), TOLNM1.NC (millimeters)",
    control_version="C00",
    unit_handling={
        "method": "filename_based",
        "inch_pattern": "TOLNI*.NC",
        "mm_pattern": "TOLNM*.NC",
        "conversion": False
    },
    line_format={
        "structure": "delimited",
        "delimiter": "comma",
        "header_lines": 0,
        "footer_lines": 0,
        "empty_line_handling": "skip",
        "comment_lines": "none"
    },
    tool_fields=C00_TOOL_FIELDS,
    other_line_types={
        "V##": "Variable data (skip)",
        "M##": "Magazine data (skip)",
        "Y##": "Tool group data (skip)"
    }
)

D00_SCHEMA = SchemaDefinition(
    data_type="TOLNn",
    file_pattern="TOLNI1.NC (inches), TOLNM1.NC (millimeters)",
    control_version="D00",
    unit_handling={
        "method": "filename_based",
        "inch_pattern": "TOLNI*.NC",
        "mm_pattern": "TOLNM*.NC",
        "conversion": False
    },
    line_format={
        "structure": "delimited",
        "delimiter": "comma",
        "header_lines": 0,
        "footer_lines": 0,
        "empty_line_handling": "skip",
        "comment_lines": "none"
    },
    tool_fields=D00_TOOL_FIELDS,
    other_line_types={
        "V##": "Variable data (skip)",
        "M##": "Magazine data (skip)",
        "Y##": "Tool group data (skip)"
    }
)

# Schema registry
SCHEMA_REGISTRY = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA
}
