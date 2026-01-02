# Export Package Manifest

**Date:** December 26, 2025
**Package Contents:** Complete Brother CNC Protocol Type 2 implementation

This package contains everything needed to integrate Brother CNC tool and ATC management into your production systems.

## Package Structure

```
brother_cnc_export/
├── README.md                          # Quick start and overview
├── EXPORT_MANIFEST.md                 # This file
├── ATC_IMPLEMENTATION_SUMMARY.md       # ATC implementation details
│
├── brother_cnc_client.py              # Core client library (55KB)
│   ├── Tool offset operations (REDTOFS, WRTTOFS)
│   ├── Tool life operations (REDTLLF, WRTTLLF)
│   ├── ATC magazine reading (ATCTL parser)
│   └── 47 completion codes
│
├── Documentation
│   ├── TOOL_DATA_OPERATIONS.md        # Tool offset/life API (13KB)
│   ├── ATC_MAGAZINE_OPERATIONS.md     # ATC magazine API (13KB)
│   └── PROTOCOL_EXAMPLES.md           # Actual protocol frames (6KB)
│
└── Test Scripts
    ├── test_update_tool_diameter.py   # Simple tool offset example
    ├── test_simple_tool_setup.py      # Complete workflow example
    └── test_atc_magazine.py           # ATC magazine testing
```

## Core Implementation

### brother_cnc_client.py (55KB)

**Classes:**
- `BrotherCNCClient` - Main client class

**Tool Offset Operations:**
- `read_tool_offset(tool_number)` - Read offset for tool
- `write_tool_offset(tool_number, offset_type, value)` - Write offset
  - `offset_type`: 'H' (length), 'D' (diameter), 'W' (wear)
  - Validates tool 1-99, value formatting, machine state

**Tool Life Operations:**
- `read_tool_life(tool_number)` - Read tool life counter
- `write_tool_life(tool_number, life_value, life_type)` - Set tool life
  - `life_type`: 'TIME' or 'COUNT'
  - Validates 0-999999 range
- `clear_tool_life(tool_number)` - Reset counter to 0

**ATC Magazine Operations (NEW):**
- `read_atc_magazine()` - Get all 51 positions
- `parse_atctl_data(content)` - Parse ATCTL file format
- `get_spindle_tool()` - Quick spindle query
- `get_pot_tool(pot_number)` - Quick pot query (1-50)
- `list_empty_pots()` - Find available slots
- `list_assigned_tools()` - Get all assignments

**Core Methods:**
- `connect()` - TCP/IP to port 10000
- `disconnect()` - Graceful disconnect
- `send_command()` - Protocol Type 2 frame construction
- `load_data(filename)` - Load machine files
- `load_panel()` - Load panel information
- `load_memory()` - Load memory data

**Error Handling:**
- 47 completion codes with descriptions
- Status code to error message mapping
- Graceful failure handling with None returns

## Documentation Files

### README.md
- Quick start examples
- Tool operations overview
- ATC magazine overview
- Integration instructions
- Answer to "What tool is in pot 10?"

### TOOL_DATA_OPERATIONS.md (13KB)
**Complete reference for tool offset and life operations:**
- API method signatures
- Return value formats
- Usage patterns (5 real-world examples)
- Error handling strategies
- Performance notes
- Safety validation
- Data format specifications

### ATC_MAGAZINE_OPERATIONS.md (13KB)
**Complete reference for ATC magazine reading:**
- Protocol and file format details
- Quick start (2 minutes)
- Method reference (5 methods)
- Return value formats and fields
- Usage patterns (5 real-world examples)
- Position mapping (M01-M51 → positions 0-50)
- Data format notes
- Error handling
- Performance optimization
- Limitations and future enhancements

### PROTOCOL_EXAMPLES.md (6KB)
**Actual protocol frames with byte-level breakdown:**
- Tool offset read example (tool #22 length)
- Tool offset write example (tool #2 diameter)
- Tool life read/write examples
- Frame structure breakdown
- Checksum calculation
- Hex representation
- Response format

### ATC_IMPLEMENTATION_SUMMARY.md
**Technical implementation details:**
- Architecture overview
- ATCTL parsing logic
- Position mapping formula
- Test results and verification
- Protocol discovery process
- Answer to original question
- Integration examples
- Quality metrics

## Test Scripts

### test_update_tool_diameter.py
**Simple example - update tool diameter offset**
- Command line: `python3 test_update_tool_diameter.py 2 0.233`
- Tests: Read → Write → Read (verify)
- Output: Simple pass/fail
- Duration: ~5 seconds

### test_simple_tool_setup.py
**Real-world example - complete tool setup workflow**
- Shows: Connect → Read → Configure → Verify → Disconnect
- Tests: Set diameter and life counter
- Output: Formatted setup status
- Duration: ~10 seconds

### test_atc_magazine.py
**Comprehensive ATC testing**
- Test 1: Read full magazine (51 positions)
- Test 2: Get spindle tool
- Test 3: Get specific pot (pot 10)
- Test 4: List empty pots
- Test 5: List all assignments
- Output: Detailed results per test
- Duration: ~5 seconds

## Integration Instructions

### 1. Copy the Client
```bash
cp brother_cnc_client.py /path/to/your/project/
```

### 2. Import and Use
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Use any method from the API
tool = client.get_pot_tool(10)  # Tool in pot 10

client.disconnect()
```

### 3. Review Documentation
- Start with `README.md` for overview
- Check specific docs (TOOL_DATA_OPERATIONS.md, ATC_MAGAZINE_OPERATIONS.md)
- Review PROTOCOL_EXAMPLES.md for protocol details

### 4. Run Examples
```bash
python3 test_atc_magazine.py      # Verify ATC reading works
python3 test_simple_tool_setup.py  # Verify tool operations work
```

## API Summary

### All Available Methods

**Connection Management:**
- `connect()` - Connect to machine
- `disconnect()` - Disconnect from machine

**Tool Offset (Read/Write):**
- `read_tool_offset(tool_number)` - Get offset for tool
- `write_tool_offset(tool_number, offset_type, value)` - Set offset

**Tool Life (Read/Write):**
- `read_tool_life(tool_number)` - Get tool life counter
- `write_tool_life(tool_number, life_value, life_type)` - Set tool life
- `clear_tool_life(tool_number)` - Reset tool life to 0

**ATC Magazine (Read-Only):**
- `read_atc_magazine()` - Get all 51 positions
- `get_spindle_tool()` - Get spindle tool
- `get_pot_tool(pot_number)` - Get pot tool (1-50)
- `list_empty_pots()` - Find empty positions
- `list_assigned_tools()` - Get all assignments

**Data Loading (Read-Only):**
- `load_data(filename)` - Load machine file
- `load_panel()` - Load panel information
- `load_memory()` - Load memory data

**Status/Error Handling:**
- `get_status_description(code)` - Get human-readable status
- `get_status_category(code)` - Categorize error type
- `is_error_permanent(code)` - Check if retryable

## Requirements

**Python:**
- Python 3.6 or higher
- Standard library only (socket, typing, time)
- No external dependencies

**Machine:**
- Brother CNC model with Protocol Type 2
- TCP/IP port 10000 enabled
- Network connectivity to machine

**Tool Operations:**
- Tools 1-99 supported
- Offset values: -999 to +999 mm
- Life values: 0 to 999,999

**ATC Magazine:**
- 51 total positions (1 spindle + 50 pots)
- Tool numbers: 0 (empty) to 999
- Machine file ATCTL required

## Data Formats

### Tool Offset Values
- Length (H): 9 bytes, trailing spaces
  - Example: `25.1234   ` (with 4 trailing spaces)
- Wear (W): 8 bytes, trailing spaces
  - Example: `0.1234  ` (with 3 trailing spaces)
- Diameter (D): 9 bytes, trailing spaces
  - Example: `5.5000    ` (with 4 trailing spaces)

### Tool Life Values
- 6-digit decimal, zero-padded
  - Example: `000500` for 500, `001200` for 1200

### ATC Magazine
- M01: Spindle tool
- M02-M51: Pots 1-50
- Format: `M##,tool,nc_mode,group,type,color`

## Known Limitations

**ATC Operations (By Design):**
- Read-only access (no write support)
- Snapshot at query time (no real-time updates)
- CCHGMAG and CREDMAG not supported in Protocol Type 2
- Uses ATCTL file loading instead (workaround)

**Tool Operations:**
- Cannot write during machine operation
- Cannot write while in editing mode
- Cannot write if data protection enabled
- Limited to tools 1-99 (machine limitation)

## Performance Characteristics

| Operation | Duration | Notes |
|-----------|----------|-------|
| Connect | ~100ms | TCP/IP handshake |
| Disconnect | ~50ms | Graceful close |
| Read tool offset | ~1 second | Network + machine |
| Write tool offset | ~1 second | Network + machine |
| Read tool life | ~1 second | Network + machine |
| Write tool life | ~1 second | Network + machine |
| Clear tool life | ~1 second | Network + machine |
| Read ATC magazine | ~1 second | Load ATCTL file + parse |
| Quick pot query | ~1 second | Calls read_atc_magazine() |

**Optimization:** Cache `read_atc_magazine()` result for multiple pot queries.

## Success Checklist

Before deploying to production:

- [ ] Machine has Protocol Type 2 enabled
- [ ] TCP/IP port 10000 is accessible
- [ ] Network connectivity verified
- [ ] `test_atc_magazine.py` passes
- [ ] `test_simple_tool_setup.py` passes
- [ ] Tool numbers 1-99 tested
- [ ] Offset values in expected range
- [ ] Read operations return valid data
- [ ] Write operations update machine state
- [ ] Clear operation tested safely

## Support and Troubleshooting

**Connection Issues:**
- Verify machine is powered on
- Check TCP/IP settings on machine
- Verify network connectivity (ping 192.168.86.89)
- Confirm port 10000 is open

**ATC Reading Issues:**
- Verify ATCTL file exists on machine
- Check machine file permissions
- Test with `load_data("ATCTL")` directly

**Tool Operations Issues:**
- Verify Protocol Type 2 is enabled (not Type 1)
- Check machine is not in operation mode
- Verify not in editing mode
- Check tool numbers are 1-99

**Data Format Issues:**
- Offset values: ±999.9999 mm range
- Life values: 0-999999 range
- Tool numbers: 1-99 for offset/life operations

## Files Included

Total size: ~95 KB

- `brother_cnc_client.py` - 55 KB (main implementation)
- `README.md` - 3.6 KB
- `ATC_MAGAZINE_OPERATIONS.md` - 13 KB
- `TOOL_DATA_OPERATIONS.md` - 13 KB
- `PROTOCOL_EXAMPLES.md` - 6.2 KB
- `ATC_IMPLEMENTATION_SUMMARY.md` - 8 KB
- `EXPORT_MANIFEST.md` - This file
- `test_atc_magazine.py` - 4.7 KB
- `test_simple_tool_setup.py` - 2.8 KB
- `test_update_tool_diameter.py` - 3.7 KB

## Ready for Production

✅ **Implementation Complete:**
- All tool operations fully functional
- ATC magazine reading implemented
- Comprehensive documentation included
- Test suite validates functionality
- Error handling robust
- Protocol compliant

✅ **Tested and Verified:**
- All methods tested against live machine
- Test results documented
- Example workflows provided
- Performance characteristics measured

✅ **Production Ready:**
- Clean code with no debug output
- Proper error handling
- Input validation
- Resource cleanup
- Graceful failures

**Ready to migrate to your production repository!**
