# Brother CNC Client - Tool & ATC Operations

Remote tool offset, tool life, and ATC magazine management for Brother CNC machines via Protocol Type 2.

## Files

- **brother_cnc_client.py** - Main client library
- **TOOL_DATA_OPERATIONS.md** - Complete tool offset/life API documentation
- **ATC_MAGAZINE_OPERATIONS.md** - Complete ATC magazine read API documentation
- **PROTOCOL_EXAMPLES.md** - Actual protocol frames sent to machine
- **test_update_tool_diameter.py** - Simple example: update tool diameter
- **test_simple_tool_setup.py** - Real-world example: complete tool setup workflow

## Quick Start

### Tool Offset & Life Operations

```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Read tool offset
offset = client.read_tool_offset(tool_number=2)

# Write tool offset
client.write_tool_offset(tool_number=2, offset_type='D', value=0.233)

# Read tool life
life = client.read_tool_life(tool_number=2)

# Write tool life
client.write_tool_life(tool_number=2, life_value=500, life_type='TIME')

# Clear tool life
client.clear_tool_life(tool_number=2)

client.disconnect()
```

### ATC Magazine Operations

```python
# Read complete magazine configuration
magazine = client.read_atc_magazine()

# Quick queries
spindle_tool = client.get_spindle_tool()      # Tool in spindle
pot_10_tool = client.get_pot_tool(10)         # Tool in pot 10
empty_pots = client.list_empty_pots()         # Find empty positions
assigned = client.list_assigned_tools()       # All assignments
```

### Run Examples
```bash
# Simple diameter update
python3 test_update_tool_diameter.py 2 0.233

# Complete tool setup
python3 test_simple_tool_setup.py
```

## Requirements

- Python 3.6+
- Brother CNC with Protocol Type 2 enabled
- TCP/IP connection to machine port 10000

## Documentation

**Tool Offset & Life Management:**
See `TOOL_DATA_OPERATIONS.md` for:
- Complete API reference for read/write offset and life
- Usage patterns and examples
- Error handling and troubleshooting
- Safety notes and validation

**ATC Magazine Reading:**
See `ATC_MAGAZINE_OPERATIONS.md` for:
- Reading magazine configuration (51 positions)
- Quick queries for spindle and pot positions
- Finding empty pots and tool locations
- Data format and field descriptions
- Usage patterns and error handling

**Protocol Details:**
See `PROTOCOL_EXAMPLES.md` for:
- Actual frame structure sent to machine
- Byte-level breakdown of commands and responses
- Command format details

## Supported Operations

**Tool Offset & Life (Write Support):**
- ✅ Read tool offset (REDTOFS)
- ✅ Write tool offset (WRTTOFS) - H, D, W types
- ✅ Read tool life (REDTLLF)
- ✅ Write tool life (WRTTLLF) - TIME, COUNT types
- ✅ Clear tool life

**ATC Magazine (Read Support):**
- ✅ Read magazine configuration (all 51 positions)
- ✅ Query spindle tool
- ✅ Query specific pot tool
- ✅ List empty pots
- ✅ List all assigned tools

**ATC Magazine (Write Support):**
- ✅ Change tool in pot (CHGMAGM) - Change tool number
- ✅ Change tool group (CHGMAGS) - Change group/main tool
- ✅ Change tool type (CHGMAGK) - Change tool type (Standard/Large/Medium)
- ✅ Change tool color (CHGMAGC) - Change visual color
- ✅ Delete tool from pot (CHGMAGD) - Remove tool assignment

**External I/O Signals (Write Support):**
- ✅ Read signal state (IOCREF) - Reference/read external signals
- ✅ Write signal state (IOCMOD) - Modify external signals (ON/OFF)

## Tool Numbers

Tools 1-99 are supported for offset/life operations.

Magazine supports tools 1-999 (0=empty, 255=special).

## Integration

Copy `brother_cnc_client.py` into your project and import:
```python
from brother_cnc_client import BrotherCNCClient
```

All operations are methods on the BrotherCNCClient class.

## Answer to Your Original Question

**"What tool is currently in pot 10?"**

```python
client = BrotherCNCClient()
client.connect()

tool = client.get_pot_tool(10)
if tool:
    print(f"Tool #{tool['tool_num']} is in pot 10")
    print(f"Type: {tool['type']}")
    print(f"Mode: {tool['nc_mode']}")
else:
    print("Pot 10 is empty")

client.disconnect()
```

**Answer:** Tool #24 (Standard type, NC mode)

