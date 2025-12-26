# ATC Magazine Operations

Read and manage the Automatic Tool Changer (ATC) magazine configuration remotely.

## Overview

The ATC magazine contains up to 51 tool positions:
- **Position 0**: Spindle (M01) - tool currently in spindle or spindle tool configuration
- **Positions 1-50**: Pots (M02-M51) - individual tool storage pockets

The `read_atc_magazine()` method reads the ATCTL file from the machine and parses it to provide structured access to all magazine positions and their tool configurations.

## Protocol Information

**Uses:** ATCTL file loaded via Protocol Type 2 LOD command
- **File Format:** Comma-separated values (CSV)
- **Command:** `LOD ATCTL` (loads machine's tool changer configuration)
- **Response:** Multi-line format with M01-M51 entries

**ATCTL Format (Section 5.6.4.9):**
```
M##,tool_num,nc_mode,group,type,color
```

Where:
- `M##`: Position code (M01=spindle, M02-M51=pots 1-50)
- `tool_num`: Tool number (0-999, 0=empty, 255=cap)
- `nc_mode`: 0=Conversation, 1=NC mode
- `group`: Group number (0=not set, 1-30) or Main tool (1-99)
- `type`: 1=Standard, 2=Large diameter, 3=Medium diameter
- `color`: 0=None, 1=Blue, 2=Red, 3=Purple, 4=Green, 5=Light blue, 6=Yellow, 7=White

## Quick Start (2 minutes)

### Read Full Magazine Configuration

```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Read all 51 positions
magazine = client.read_atc_magazine()

# Position 0 = spindle, 1-50 = pots
for position in sorted(magazine.keys()):
    data = magazine[position]
    if data['tool_num_set']:
        print(f"{data['position']}: Tool #{data['tool_num']} ({data['type']})")

client.disconnect()
```

### Quick Queries

```python
# What tool is in the spindle?
spindle = client.get_spindle_tool()
if spindle:
    print(f"Spindle: Tool #{spindle['tool_num']}")

# What tool is in pot 10?
tool = client.get_pot_tool(10)
if tool:
    print(f"Pot 10: Tool #{tool['tool_num']} (Type: {tool['type']})")

# List all empty pots
empty_pots = client.list_empty_pots()
print(f"Empty pots: {empty_pots}")

# List all assigned tools
assigned = client.list_assigned_tools()
for position, tool_num in sorted(assigned.items()):
    print(f"Position {position}: Tool #{tool_num}")
```

## Methods Reference

### read_atc_magazine()

Read the complete ATC magazine configuration.

**Signature:**
```python
def read_atc_magazine(self) -> Optional[Dict[int, Dict]]:
```

**Returns:**
Dictionary mapping position to tool information:
```python
{
    0: {  # Spindle
        'position': 'spindle',
        'tool_num': 0,
        'tool_num_set': False,
        'nc_mode': 'CONVERSATION',
        'group': 0,
        'type': 'STANDARD',
        'color': 'NONE',
        'raw': {'tool_num': 0, 'nc_mode': 0, 'group': 0, 'type': 1, 'color': 0}
    },
    10: {  # Pot 10 (M11)
        'position': 'pot_10',
        'tool_num': 24,
        'tool_num_set': True,
        'nc_mode': 'NC',
        'group': 0,
        'type': 'STANDARD',
        'color': 'NONE',
        'raw': {'tool_num': 24, 'nc_mode': 1, 'group': 0, 'type': 1, 'color': 0}
    },
    # ... 49 more positions
}
```

Returns `None` if read fails.

**Example:**
```python
magazine = client.read_atc_magazine()
if magazine:
    total_tools = sum(1 for d in magazine.values() if d['tool_num_set'])
    print(f"Magazine has {total_tools} tools assigned")

    # Access specific position
    spindle_data = magazine[0]
    print(f"Spindle config: {spindle_data}")
```

**Field Descriptions:**
- `position` (str): Human-readable position name ('spindle' or 'pot_N')
- `tool_num` (int): Tool number assigned to this position (0=empty)
- `tool_num_set` (bool): True if a tool is assigned (not 0 or 255)
- `nc_mode` (str): Operating mode ('CONVERSATION' or 'NC')
- `group` (int): Tool group number or main tool number
- `type` (str): Tool type ('STANDARD', 'LARGE', 'MEDIUM')
- `color` (str): Tool color for visual identification
- `raw` (dict): Raw numeric values from ATCTL file

### get_spindle_tool()

Get the tool currently in the spindle.

**Signature:**
```python
def get_spindle_tool(self) -> Optional[Dict]:
```

**Returns:**
Tool information dict if spindle has a tool assigned, `None` if empty or read fails.

**Example:**
```python
spindle_tool = client.get_spindle_tool()
if spindle_tool:
    print(f"Tool #{spindle_tool['tool_num']} in spindle")
    print(f"Type: {spindle_tool['type']}")
    print(f"Mode: {spindle_tool['nc_mode']}")
else:
    print("Spindle is empty")
```

### get_pot_tool()

Get the tool in a specific pot.

**Signature:**
```python
def get_pot_tool(self, pot_number: int) -> Optional[Dict]:
```

**Parameters:**
- `pot_number` (int): Pot position (1-50)

**Returns:**
Tool information dict if pot has a tool assigned, `None` if empty or invalid pot number.

**Example:**
```python
# Get tool in pot 10
tool = client.get_pot_tool(10)
if tool:
    print(f"Pot 10: Tool #{tool['tool_num']}")
else:
    print("Pot 10 is empty")

# Get tool in pot 1
first_tool = client.get_pot_tool(1)
```

**Validation:**
- Pot numbers must be 1-50
- Returns None for invalid pot numbers (0 or >50)

### list_empty_pots()

Get a list of all empty pot positions.

**Signature:**
```python
def list_empty_pots(self) -> Optional[List[int]]:
```

**Returns:**
List of empty pot numbers [5, 7, 8, 15, ...], or `None` if read fails.

**Example:**
```python
empty = client.list_empty_pots()
if empty:
    print(f"Empty pots ({len(empty)}): {empty}")
    # Could use for tool assignment
    next_empty = empty[0]
    print(f"Next available: pot {next_empty}")
else:
    print("All pots are full!")
```

### list_assigned_tools()

Get mapping of all assigned tools in the magazine.

**Signature:**
```python
def list_assigned_tools(self) -> Optional[Dict[int, int]]:
```

**Returns:**
Dictionary mapping position to tool number: `{0: 24, 1: 1, 2: 2, ...}`, or `None` if read fails.

Position keys:
- `0`: Spindle
- `1-50`: Pots 1-50

**Example:**
```python
assigned = client.list_assigned_tools()
if assigned:
    print(f"Total assigned tools: {len(assigned)}")

    # Show all assignments
    for position, tool_num in sorted(assigned.items()):
        if position == 0:
            print(f"  Spindle: Tool #{tool_num}")
        else:
            print(f"  Pot {position}: Tool #{tool_num}")

    # Find which pot has tool #42
    for position, tool_num in assigned.items():
        if tool_num == 42:
            pos_name = "Spindle" if position == 0 else f"Pot {position}"
            print(f"Tool #42 is in {pos_name}")
```

## Usage Patterns

### Pattern 1: Check Magazine Status

```python
def show_magazine_status(client):
    """Display current magazine configuration status."""
    assigned = client.list_assigned_tools()
    empty = client.list_empty_pots()

    if assigned:
        print(f"✓ {len(assigned)} tools assigned")
    if empty:
        print(f"✓ {len(empty)} empty pots available")

    spindle = client.get_spindle_tool()
    if spindle:
        print(f"✓ Spindle: Tool #{spindle['tool_num']}")
    else:
        print("✗ Spindle is empty")
```

### Pattern 2: Find Tool Location

```python
def find_tool(client, tool_num):
    """Find where a specific tool is located."""
    magazine = client.read_atc_magazine()

    for position, data in magazine.items():
        if data['tool_num'] == tool_num:
            return data['position']

    return None  # Tool not in magazine

# Usage
tool_location = find_tool(client, 42)
if tool_location:
    print(f"Tool #42 is in {tool_location}")
else:
    print("Tool #42 is not in the magazine")
```

### Pattern 3: Check for Required Tools

```python
def check_job_tools(client, required_tools):
    """Check if all required tools for a job are in the magazine."""
    assigned = client.list_assigned_tools()
    missing = []

    for tool_num in required_tools:
        if tool_num not in assigned.values():
            missing.append(tool_num)

    if missing:
        print(f"✗ Missing tools: {missing}")
        return False
    else:
        print(f"✓ All {len(required_tools)} required tools are loaded")
        return True

# Usage
required = [1, 2, 5, 10, 24, 42]
check_job_tools(client, required)
```

### Pattern 4: List Tools by Type

```python
def list_tools_by_type(client, tool_type):
    """List all tools of a specific type."""
    magazine = client.read_atc_magazine()
    tools = []

    for position, data in magazine.items():
        if data['type'] == tool_type:
            tools.append((position, data['tool_num']))

    return tools

# Usage
large_tools = list_tools_by_type(client, 'LARGE')
print(f"Large tools: {large_tools}")
# Output: Large tools: [(15, 42), (20, 51)]
```

### Pattern 5: Magazine Utilization Report

```python
def magazine_report(client):
    """Generate magazine utilization report."""
    magazine = client.read_atc_magazine()

    total_positions = 51
    assigned = sum(1 for d in magazine.values() if d['tool_num_set'])
    utilization = (assigned / total_positions) * 100

    # Count by type
    types = {}
    for data in magazine.values():
        if data['tool_num_set']:
            t = data['type']
            types[t] = types.get(t, 0) + 1

    print(f"Magazine Utilization: {utilization:.1f}% ({assigned}/{total_positions})")
    print("By type:")
    for tool_type, count in sorted(types.items()):
        print(f"  {tool_type}: {count}")

# Usage
magazine_report(client)
```

## Data Format Notes

### Position Numbers and Codes

The protocol uses M-codes to identify positions:
- **M01**: Spindle tool (position 0 in return dict)
- **M02-M51**: Pots 1-50 (positions 1-50 in return dict)

Formula: `position = M_number - 1`

Examples:
- M01 → position 0 (spindle)
- M11 → position 10 (pot 10)
- M51 → position 50 (pot 50)

### Tool Numbers

- **0**: Position is empty
- **1-99**: Standard tool numbers
- **100-999**: Extended tool numbers (if supported)
- **255**: Special value (cap setting)

### Tool Types

| Code | Type | Notes |
|------|------|-------|
| 1 | STANDARD | Regular tool, normal size |
| 2 | LARGE | Large diameter tool (affects adjacent positions) |
| 3 | MEDIUM | Medium diameter tool |

### NC/Conversation Mode

| Code | Mode | Notes |
|------|------|-------|
| 0 | CONVERSATION | Traditional carousel tool changer mode |
| 1 | NC | CNC program-based tool selection |

### Colors

Used for visual identification on the machine display:

| Code | Color | Hex |
|------|-------|-----|
| 0 | NONE | Gray |
| 1 | BLUE | #0000FF |
| 2 | RED | #FF0000 |
| 3 | PURPLE | #800080 |
| 4 | GREEN | #00AA00 |
| 5 | LIGHT_BLUE | #00FFFF |
| 6 | YELLOW | #FFFF00 |
| 7 | WHITE | #FFFFFF |

## Error Handling

### Common Errors

**Error: ATCTL file not found**
```
✗ Read ATC Magazine: Could not load ATCTL file
```
Solution: Machine may not have ATC, or file access is restricted.

**Error: Invalid pot number**
```
✗ Get Pot Tool: Pot number must be 1-50, got 51
```
Solution: Use pot numbers in range 1-50 (spindle is position 0).

**Error: Parse error**
```
✗ Parse ATCTL: Error - list index out of range
```
Solution: ATCTL file format may have changed. Check with machine manual.

### Return Values

Methods return:
- **Valid dict**: Operation successful, data is available
- **None**: Operation failed or data unavailable
- **Empty dict**: No tools assigned (unlikely, but possible)

Always check return value before accessing data:
```python
tool = client.get_pot_tool(10)
if tool:
    print(f"Pot 10: Tool #{tool['tool_num']}")
else:
    print("Pot 10 is empty or read failed")
```

## Performance Notes

- Read operation: ~1 second (loads and parses ATCTL file)
- All convenience methods call `read_atc_magazine()` internally
- For multiple queries, use `read_atc_magazine()` once then query the result:

```python
# Efficient: Read once
magazine = client.read_atc_magazine()
spindle = magazine[0] if 0 in magazine else None
pot_10 = magazine[10] if 10 in magazine else None

# Less efficient: Multiple reads
spindle = client.get_spindle_tool()  # Reads ATCTL
pot_10 = client.get_pot_tool(10)     # Reads ATCTL again
```

## Safety and Validation

All methods include validation:
- Pot numbers checked (1-50)
- Empty positions return None gracefully
- Invalid data handled with error messages
- File format errors caught and reported

The ATCTL parser follows the documented schema from Section 5.6.4.9 of the Brother manual and validates all numeric fields.

## Limitations

**Current Implementation:**
- Read-only: Uses LOD command to read ATCTL file
- No write support: Cannot modify magazine via WRTTOF/CCHGMAG (not supported in Protocol Type 2)
- No real-time updates: Returns snapshot of current state when called

**Potential Future Enhancements:**
- Monitor ATCTL changes with polling
- Cache results for faster repeat queries
- Integrate with tool tracking database
- Real-time magazine change notifications

## Related Operations

- [TOOL_DATA_OPERATIONS.md](TOOL_DATA_OPERATIONS.md) - Tool offset and life management
- [PROTOCOL_EXAMPLES.md](PROTOCOL_EXAMPLES.md) - Protocol frame details

## Summary

The ATC magazine operations provide complete read access to the machine's tool changer configuration through:
- **read_atc_magazine()** - Full magazine snapshot
- **get_spindle_tool()** - Quick spindle query
- **get_pot_tool()** - Quick pot query
- **list_empty_pots()** - Find available positions
- **list_assigned_tools()** - Summary of all assignments

With proper parsing of the ATCTL file according to the documented schema, all tool location and configuration information is available for application integration, tool tracking systems, and manufacturing workflows.
