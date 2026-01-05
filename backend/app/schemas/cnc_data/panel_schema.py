"""
Schema definition for PANEL (Operation Panel Data) files.

Based on Brother CNC documentation:
- C00 Control: Section 5.6.4.10
- D00 Control: Section 3.6.5.10

File naming: PANEL

Unit Handling:
- Method: not_applicable (PANEL data doesn't have unit-specific values)
- Conversion: no (all values are status/configuration codes)

Format:
- Delimited by comma (,)
- CR+LF at end of line
- Multi-line format with symbol prefixes:
  - D01: Door status (outer, inner, side)
  - K01: Mode, screen, and machine function switches
  - S01: Override settings and system status
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.schemas.cnc_data.tolni_schema import FieldDefinition, SchemaDefinition


# C00 Control Schema (Section 5.6.4.10)
# D01 line: Outer door (1), Inner door (1), Side door (1)
# K01 line: Mode (1), Screen (1), Block skip (1), OPT stop (1), Single block (1), Dry run (1), Machine lock (1), Coolant pump (1), Chip shower (1), Machine light (1), Pallet select key (1)
# S01 line: Rapid traverse override (1), Feedrate override (3), Spindle override (3), Emergency stop (1), Door interlock (1), Data protection (1), [MASTER ON] (1)

C00_PANEL_D01_FIELDS = [
    FieldDefinition("outer_door", 0, int, False, "Outer door status (D01)", "0: Close, 1: Open"),
    FieldDefinition("inner_door", 1, int, False, "Inner door status (D01)", "0: Close, 1: Open"),
    FieldDefinition("side_door", 2, int, False, "Side door status (D01)", "0: Close, 1: Open"),
]

C00_PANEL_K01_FIELDS = [
    FieldDefinition("mode", 0, int, False, "Mode (K01)", "0: Manual, 1: MDI operation, 2: Memory operation, 3: Program edit, 4: MDI manual, 5: Operating edit"),
    FieldDefinition("screen", 1, int, False, "Screen (K01)", "0: Display OFF, 1: Alarm, 2: Data bank, 3: ATC tool, 4: Program, 5: Manual conditions, 6: Position, 7: I/O, 8: Monitor, 9: Graph"),
    FieldDefinition("block_skip", 2, int, False, "Block skip (K01)", "0: OFF, 1: ON"),
    FieldDefinition("opt_stop", 3, int, False, "OPT stop (K01)", "0: OFF, 1: ON"),
    FieldDefinition("single_block", 4, int, False, "Single block (K01)", "0: OFF, 1: ON"),
    FieldDefinition("dry_run", 5, int, False, "Dry run (K01)", "0: OFF, 1: ON"),
    FieldDefinition("machine_lock", 6, int, False, "Machine lock (K01)", "0: OFF, 1: ON"),
    FieldDefinition("coolant_pump", 7, int, False, "Coolant pump (K01)", "0: OFF, 1: ON"),
    FieldDefinition("chip_shower", 8, int, False, "Chip shower (K01)", "0: OFF, 1: ON"),
    FieldDefinition("machine_light", 9, int, False, "Machine light (K01)", "0: OFF, 1: ON"),
    FieldDefinition("pallet_select_key", 10, int, False, "Pallet select key (K01)", "0: OFF, 1: 1, 2: 2, 3: 1-2"),
]

C00_PANEL_S01_FIELDS = [
    FieldDefinition("rapid_traverse_override", 0, int, False, "Rapid traverse override (S01)", "0: Speed 1, 1: Speed 2, 2: Speed 3, 3: Speed 4, 4: 100%, 5: 0%, 9: Override prohibited"),
    FieldDefinition("feedrate_override", 1, int, False, "Feedrate override (S01)", "% display, 999: Override prohibited"),
    FieldDefinition("spindle_override", 2, int, False, "Spindle override (S01)", "% display, 999: Override prohibited"),
    FieldDefinition("emergency_stop", 3, int, False, "Emergency stop (S01)", "0: ON, 1: OFF"),
    FieldDefinition("door_interlock", 4, int, False, "Door interlock (S01)", "0: OFF, 1: ON"),
    FieldDefinition("data_protection", 5, int, False, "Data protection (S01)", "0: Enabled, 1: Disabled"),
    FieldDefinition("master_on", 6, int, False, "[MASTER ON] (S01)", "0: OFF, 1: ON"),
]

# D00 Control Schema (Section 3.6.5.10)
# D01 line: Outer door (1), Inner door (1), Side door (1) - same as C00
# K01 line: Mode (1), Block skip (1), OPT stop (1), Single block (1), Dry run (1), Machine lock (1), Coolant pump (1), Chip shower (1), Machine light (1), Pallet select key (1), Table light (1), Door unlock 1 (1), Door unlock 2 (1)
# S01 line: Rapid traverse override (1), Feedrate override (3), Spindle override (3), Emergency stop (1), Data protection (1), Door interlock mode (right) (1), Door interlock mode (left) (1), Enable (1), [MASTER ON] (1)

D00_PANEL_D01_FIELDS = [
    FieldDefinition("outer_door", 0, int, False, "Outer door status (D01)", "0: Close, 1: Open"),
    FieldDefinition("inner_door", 1, int, False, "Inner door status (D01)", "0: Close, 1: Open"),
    FieldDefinition("side_door", 2, int, False, "Side door status (D01)", "0: Close, 1: Open"),
]

D00_PANEL_K01_FIELDS = [
    FieldDefinition("mode", 0, int, False, "Mode (K01)", "0: Manual, 1: MDI operation, 2: Memory operation, 3: Program edit, 4: MDI manual, 5: Operating edit"),
    FieldDefinition("block_skip", 1, int, False, "Block skip (K01)", "0: OFF, 1: ON"),
    FieldDefinition("opt_stop", 2, int, False, "OPT stop (K01)", "0: OFF, 1: ON"),
    FieldDefinition("single_block", 3, int, False, "Single block (K01)", "0: OFF, 1: ON"),
    FieldDefinition("dry_run", 4, int, False, "Dry run (K01)", "0: OFF, 1: ON"),
    FieldDefinition("machine_lock", 5, int, False, "Machine lock (K01)", "0: OFF, 1: ON"),
    FieldDefinition("coolant_pump", 6, int, False, "Coolant pump (K01)", "0: OFF, 1: ON"),
    FieldDefinition("chip_shower", 7, int, False, "Chip shower (K01)", "0: OFF, 1: ON"),
    FieldDefinition("machine_light", 8, int, False, "Machine light (K01)", "0: OFF, 1: ON"),
    FieldDefinition("pallet_select_key", 9, int, False, "Pallet select key (K01)", "0: OFF, 1: 1, 2: 2, 3: 1-2"),
    FieldDefinition("table_light", 10, int, False, "Table light (K01)", "0: OFF, 1: ON"),
    FieldDefinition("door_unlock_1", 11, int, False, "Door unlock 1 (K01)", "0: OFF, 1: ON"),
    FieldDefinition("door_unlock_2", 12, int, False, "Door unlock 2 (K01)", "0: OFF, 1: ON"),
]

D00_PANEL_S01_FIELDS = [
    FieldDefinition("rapid_traverse_override", 0, int, False, "Rapid traverse override (S01)", "0: Speed 1, 1: Speed 2, 2: Speed 3, 3: Speed 4, 4: 100%, 5: 0%, 9: Override prohibited"),
    FieldDefinition("feedrate_override", 1, int, False, "Feedrate override (S01)", "% display, 999: Override prohibited"),
    FieldDefinition("spindle_override", 2, int, False, "Spindle override (S01)", "% display, 999: Override prohibited"),
    FieldDefinition("emergency_stop", 3, int, False, "Emergency stop (S01)", "0: OFF, 1: ON"),
    FieldDefinition("data_protection", 4, int, False, "Data protection (S01)", "0: Enabled, 1: Disabled"),
    FieldDefinition("door_interlock_mode_right", 5, int, False, "Door interlock mode (right) (S01)", "0: OFF, 1: ON"),
    FieldDefinition("door_interlock_mode_left", 6, int, False, "Door interlock mode (left) (S01)", "0: OFF, 1: ON"),
    FieldDefinition("enable", 7, int, False, "Enable (S01)", "0: OFF, 1: Main operation, 2: Handle, 3: Pendant, 4: Magazine, 5: Pallet start"),
    FieldDefinition("master_on", 8, int, False, "[MASTER ON] (S01)", "0: OFF, 1: ON"),
]

C00_SCHEMA = SchemaDefinition(
    data_type="PANEL",
    file_pattern="PANEL",
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
    tool_fields=[],  # PANEL doesn't use tool_fields
    other_line_types={
        "D01": C00_PANEL_D01_FIELDS,
        "K01": C00_PANEL_K01_FIELDS,
        "S01": C00_PANEL_S01_FIELDS,
    }
)

D00_SCHEMA = SchemaDefinition(
    data_type="PANEL",
    file_pattern="PANEL",
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
    tool_fields=[],  # PANEL doesn't use tool_fields
    other_line_types={
        "D01": D00_PANEL_D01_FIELDS,
        "K01": D00_PANEL_K01_FIELDS,
        "S01": D00_PANEL_S01_FIELDS,
    }
)

# Schema registry
PANEL_SCHEMAS = {
    "C00": C00_SCHEMA,
    "D00": D00_SCHEMA,
}

def get_panel_schema(control_version: str) -> SchemaDefinition:
    """
    Get PANEL schema for a specific control version.
    
    Args:
        control_version: Control version ('C00' or 'D00')
        
    Returns:
        SchemaDefinition for the control version
        
    Raises:
        ValueError: If control_version is not supported
    """
    if control_version not in PANEL_SCHEMAS:
        raise ValueError(f"Unsupported control version: {control_version}. Supported versions: {list(PANEL_SCHEMAS.keys())}")
    return PANEL_SCHEMAS[control_version]

