"""
Schema definition for POSNn (Workpiece Coordinate Zero) data files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.17
- D00 Control: Section 3.6.5.16

File naming: POSNun
- u: Unit system (M: Metric, I: Inch)
- n: Data bank number (0-9, where "0" represents "10")

Unit Handling:
- Method: filename_based
- POSNI1.NC = inches
- POSNM1.NC = millimeters
- Conversion: no (values stored in native units)

Format:
- Delimited by comma (,)
- CR+LF at end of each offset line
- Each offset: OFFSET_NAME,X,Y,Z,A,B,C
"""


from app.schemas.cnc_data.tolni_schema import FieldDefinition, SchemaDefinition


# C00 Control Schema (Section 5.6.4.17)
# Structure: G54-G59, X01-X48, H01, B01
# Each offset: OFFSET_NAME,X,Y,Z,A,B,C
# Field lengths: 9 chars for X,Y,Z,A,B,C
C00_OFFSET_FIELDS = [
    FieldDefinition("offset_name", -1, str, True, "Offset name (G54-G59, X01-X48, H01, B01)", "Extracted from line prefix"),
    FieldDefinition("x", 0, float, True, "X-axis", "-9999.9999~9999.9999 (inch) or -999.99999~999.99999 (mm)"),
    FieldDefinition("y", 1, float, True, "Y-axis", "-9999.9999~9999.9999 (inch) or -999.99999~999.99999 (mm)"),
    FieldDefinition("z", 2, float, True, "Z-axis", "-9999.9999~9999.9999 (inch) or -999.99999~999.99999 (mm)"),
    FieldDefinition("a", 3, float, False, "A-axis", "-9999.999~9999.999"),
    FieldDefinition("b", 4, float, False, "B-axis", "-9999.999~9999.999"),
    FieldDefinition("c", 5, float, False, "C-axis", "-9999.999~9999.999"),
]

# D00 Control Schema (Section 3.6.5.16)
# Structure: G054-G059, X001-X300
# Each offset: OFFSET_NAME,X,Y,Z,A,B,C
# Field lengths: 11 chars for X,Y,Z,A,B,C
# Note: D00 uses 3-digit format (G054, X001) vs C00 2-digit (G54, X01)
D00_OFFSET_FIELDS = [
    FieldDefinition("offset_name", -1, str, True, "Offset name (G054-G059, X001-X300)", "Extracted from line prefix, 3-digit format"),
    FieldDefinition("x", 0, float, True, "X-axis", "-999999.999~999999.999 (inch) or -99999.9999~99999.9999 (mm)"),
    FieldDefinition("y", 1, float, True, "Y-axis", "-999999.999~999999.999 (inch) or -99999.9999~99999.9999 (mm)"),
    FieldDefinition("z", 2, float, True, "Z-axis", "-999999.999~999999.999 (inch) or -99999.9999~99999.9999 (mm)"),
    FieldDefinition("a", 3, float, False, "A-axis", "-999999.999~999999.999"),
    FieldDefinition("b", 4, float, False, "B-axis", "-999999.999~999999.999"),
    FieldDefinition("c", 5, float, False, "C-axis", "-999999.999~999999.999"),
]

C00_SCHEMA = SchemaDefinition(
    data_type="POSN",
    file_pattern="POSNI*|POSNM*",
    control_version="C00",
    unit_handling={
        "method": "filename_based",
        "filename_pattern": "POSN{unit}{bank}",
        "unit_codes": {"I": "in", "M": "mm"},
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
            "x": 9,
            "y": 9,
            "z": 9,
            "a": 9,
            "b": 9,
            "c": 9
        }
    },
    tool_fields=C00_OFFSET_FIELDS,  # Reusing tool_fields structure for offset entries
    other_line_types={
        "G54-G59": "Work offsets",
        "X01-X48": "Extended workpiece coordinate system",
        "H01": "External workpiece coordinate system",
        "B01": "Reference rotary fixture offset"
    }
)

D00_SCHEMA = SchemaDefinition(
    data_type="POSN",
    file_pattern="POSNI*|POSNM*",
    control_version="D00",
    unit_handling={
        "method": "filename_based",
        "filename_pattern": "POSN{unit}{bank}",
        "unit_codes": {"I": "in", "M": "mm"},
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
            "x": 11,
            "y": 11,
            "z": 11,
            "a": 11,
            "b": 11,
            "c": 11
        }
    },
    tool_fields=D00_OFFSET_FIELDS,  # Reusing tool_fields structure for offset entries
    other_line_types={
        "G054-G059": "Work offsets (3-digit format)",
        "X001-X300": "Extended workpiece coordinate system (3-digit format, up to 300 offsets)"
    }
)

# Schema registry
POSN_SCHEMAS = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA,
}

def get_posn_schema(control_version: str) -> SchemaDefinition:
    """
    Get POSN schema for a specific control version.
    
    Args:
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        SchemaDefinition for the control version
        
    Raises:
        ValueError: If control_version is not supported
    """
    if control_version not in POSN_SCHEMAS:
        raise ValueError(f"Unsupported control version: {control_version}. Supported: {list(POSN_SCHEMAS.keys())}")
    return POSN_SCHEMAS[control_version]

