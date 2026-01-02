# ToolsPane Data Coverage Analysis

## Currently Displayed Fields

The ToolsPane currently displays these 9 columns:
1. **POT** (`pot_number`) - From ATCTL
2. **T#** (`tool_number`) - From TOLN
3. **TOOL NAME** (`tool_name`) - From TOLN
4. **DIAMETER** (`diameter`) - From TOLN (mapped from `cutter_compensation`)
5. **LENGTH** (`length`) - From TOLN (mapped from `tool_length_offset`)
6. **GROUP** (`group`) - From ATCTL
7. **LIFE** (`life`) - From TOLN (mapped from `tool_life`)
8. **TYPE** (`tool_type`) - From ATCTL (1=STD, 2=LARGE)
9. **COLOR** (`color`) - From ATCTL

## Parsed But Not Displayed Fields

### From TOLN (Tool Offset Table):

#### Wear/Compensation Offsets:
- `tool_length_wear_offset` - Tool length wear compensation
- `cutter_wear_offset` - Cutter diameter wear compensation

#### Tool Life Details:
- `tool_life_unit` - Life unit type (1=Not counted, 2=Time (min.), 3=Drilling (holes), 4=Program (cycles), 5=Time (sec.))
- `initial_tool_life` - Initial/end of tool life value
- `tool_life_warning` - Tool life warning threshold

#### Speed/Feed Parameters:
- `rotation_feed` - Rotation feed rate
- `s_command_value` - S command (spindle speed) value
- `f_command_value` - F command (feed rate) value
- `maximum_speed` - Maximum spindle speed
- `peripheral_speed` - Peripheral speed (D00 only)

#### Tool Capabilities:
- `tool_wash` - Tool wash capability (0=Possible, 1=Not possible)
- `cts` - CTS capability (0=Possible, 1=Not possible)

#### Tool Type/Position:
- `tool_type_number` - Tool type number (different from ATCTL's `tool_type`)
- `tool_position_offset_x` - Tool position offset (X axis)
- `tool_position_wear_offset_x` - Tool position wear offset (X axis)
- `tool_position_offset_y` - Tool position offset (Y axis)
- `tool_position_wear_offset_y` - Tool position wear offset (Y axis)

## Summary

**Total fields parsed from TOLN:** ~22 fields
**Total fields displayed:** 9 fields (5 from TOLN, 4 from ATCTL)
**Fields not displayed:** ~17 fields from TOLN

## Potentially Useful Fields to Consider Displaying

### High Priority:
1. **Wear Offsets** (`tool_length_wear_offset`, `cutter_wear_offset`) - Important for tool condition monitoring
2. **Tool Life Details** (`tool_life_unit`, `initial_tool_life`, `tool_life_warning`) - Useful for life management
3. **Speed/Feed** (`s_command_value`, `f_command_value`, `maximum_speed`) - Important for machining parameters

### Medium Priority:
4. **Tool Capabilities** (`tool_wash`, `cts`) - Useful for tool selection
5. **Tool Type Number** (`tool_type_number`) - Different from ATCTL type, may be useful

### Low Priority:
6. **Position Offsets** (`tool_position_offset_x/y`, `tool_position_wear_offset_x/y`) - Specialized use cases
7. **Rotation Feed** (`rotation_feed`) - Less commonly used
8. **Peripheral Speed** (`peripheral_speed`) - D00 only, specialized

## Recommendations

1. **Add a "Details" view or expandable row** to show additional fields without cluttering the main table
2. **Add tooltip/popover** on hover to show wear offsets and life details
3. **Add a "Show Advanced Fields" toggle** to optionally display speed/feed parameters
4. **Consider a separate "Tool Details" modal** that shows all parsed fields for a selected tool

