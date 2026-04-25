"""
Schema definition for ATCTL (ATC Tool) data files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.9
- D00 Control: Section 3.6.5.9

File naming:
- C00: ATCTL
- D00: ATCTLD

Unit Handling:
- Method: not_applicable (ATC data doesn't have unit-specific values)
- Conversion: no (tool numbers and metadata only)
"""


from app.schemas.cnc_data.tolni_schema import FieldDefinition, SchemaDefinition


# C00 Control Schema (Section 5.6.4.9)
# Structure: M01 (Spindle) + M02-M51 (Pot 1-50)
# Each entry: Tool No., Conversation/NC, Group No./Main tool No., Type, Graph color
C00_ATC_FIELDS = [
    FieldDefinition("tool_number", 0, int, True, "Tool number", "0: Not set, 1-99: Tool No., 255: Cap setting (C00)"),
    FieldDefinition("conversation_nc", 1, int, True, "Conversation/NC", "0: Conversation, 1: NC"),
    FieldDefinition("group_or_main_tool", 2, int, False, "Group No. (NC) / Main tool No. (Conversation)", "Group No.: 0 (Not set), 1-30; Main tool No.: 0 (Not set), 1-99"),
    FieldDefinition("tool_type", 3, int, False, "Tool type", "1: Standard, 2: Large diameter, 3: Medium diameter (C00)"),
    FieldDefinition("graph_color", 4, int, False, "Graph color", "0: No color, 1: Blue, 2: Red, 3: Purple, 4: Green, 5: Light blue, 6: Yellow, 7: White"),
]

# D00 Control Schema (Section 3.6.5.9)
# Structure: M01 (Spindle) + M02-M51 (Pot 1-50) + R01-R51 (Right stocker) + L01-L51 (Left stocker) + W01 + E01
# Each entry: Tool No., Conversation/NC, Group No./Main tool No., Type, Graph color, Store tool stocker
D00_ATC_FIELDS = [
    FieldDefinition("tool_number", 0, int, True, "Tool number", "0: Not set, 1-99: Tool No., 201-299: Tool No., 999: Cap setting"),
    FieldDefinition("conversation_nc", 1, int, True, "Conversation/NC", "0: Conversation, 1: NC"),
    FieldDefinition("group_or_main_tool", 2, int, False, "Group No. (NC) / Main tool No. (Conversation)", "Group No.: 0 (Not set), 1-30; Main tool No.: 0 (Not set), 1-99"),
    FieldDefinition("tool_type", 3, int, False, "Tool type", "1: Standard, 2: Large diameter"),
    FieldDefinition("graph_color", 4, int, False, "Graph color", "0: No color, 1: Blue, 2: Red, 3: Purple, 4: Green, 5: Light blue, 6: Yellow, 7: White"),
    FieldDefinition("store_tool_stocker", 5, int, False, "Store tool stocker", "0: Possible, 1: Not possible"),
]

C00_SCHEMA = SchemaDefinition(
    data_type="ATCTL",
    file_pattern="ATCTL",
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
        "comment_lines": "none"
    },
    tool_fields=C00_ATC_FIELDS,  # Reusing tool_fields structure for ATC entries
    other_line_types={
        "M01": "Spindle",
        "M02-M51": "Pot 1-50"
    }
)

D00_SCHEMA = SchemaDefinition(
    data_type="ATCTL",
    file_pattern="ATCTLD",
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
        "comment_lines": "none"
    },
    tool_fields=D00_ATC_FIELDS,
    other_line_types={
        "M01": "Spindle",
        "M02-M51": "Pot 1-50",
        "R01-R51": "Right stocker 1-50",
        "L01-L51": "Left stocker 1-50",
        "W01": "Stocker attributes (right)",
        "E01": "Stocker attributes (left)"
    }
)

# Schema registry
SCHEMA_REGISTRY = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA
}

