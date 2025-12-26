# Tool Data Operations Guide

## Overview

Tool data operations allow you to read and write tool offset and tool life data remotely. This is essential for:
- **Automated tool setup** - Configure tools without manual intervention
- **Tool life tracking** - Monitor and manage tool wear
- **Production automation** - Integrate tool management into workflows
- **Preventive maintenance** - Clear tool life counters before they expire

## Protocol Information

**Requires:** Protocol Type 2 enabled on machine (TCP/IP port 10000)

**Commands Used:**
- **REDTOFS** - Read Tool Offset (Protocol Type 2, 7-char command)
- **WRTTOFS** - Write Tool Offset (Protocol Type 2, multi-part with data payload)
- **REDTLLF** - Read Tool Life (Protocol Type 2, 7-char command)
- **WRTTLLF** - Write Tool Life (Protocol Type 2, multi-part with data payload)
- **clear_tool_life()** - Implemented as WRTTLLF with value=0 (Protocol Type 2)

**Tool Number Range:** 1-99 (formatted as 2-digit: 01-99)

**Data Format:**
- Offsets: Decimal values with trailing spaces (9 bytes for types 0,2,4,6 | 8 bytes for types 1,3,5,7)
- Life values: 6-digit decimal (000000-999999)

## Quick Start (5 minutes)

### Read Tool Offset
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Read tool offset for tool #2
offset = client.read_tool_offset(tool_number=2)
print(f"Tool 2 offset: {offset}")
# Output: Tool 2 offset: {'raw': '0.2330\r\n07'}

client.disconnect()
```

### Write Tool Offset
```python
# Write tool diameter offset (D-type)
success = client.write_tool_offset(
    tool_number=2,
    offset_type='D',  # 'H'=Length, 'D'=Diameter, 'W'=Wear
    value=0.233
)

if success:
    print("Tool diameter offset updated to 0.233mm")
```

### Read Tool Life
```python
# Read tool life for tool #2
life = client.read_tool_life(tool_number=2)
print(f"Tool 2 life: {life}")
# Output: Tool 2 life: {'raw': '500\r\n13'}
```

### Write Tool Life
```python
# Set tool life to 500 time units
success = client.write_tool_life(
    tool_number=2,
    life_value=500,
    life_type='TIME'  # 'TIME' or 'COUNT'
)

if success:
    print("Tool life set to 500")
```

### Clear Tool Life
```python
# Clear tool life counter for tool #2
success = client.clear_tool_life(tool_number=2)
if success:
    print("Tool 2 life counter cleared")
```

## Methods Reference

### read_tool_offset()

Read tool offset data for a specific tool.

**Signature:**
```python
def read_tool_offset(self, tool_number: int) -> Optional[Dict[str, float]]:
```

**Parameters:**
- `tool_number` (int): Tool number to read (1-99)

**Returns:**
- `dict`: Raw offset data from machine (e.g., `{'raw': '0.2330\r\n07'}`)
- `None`: If read fails

**Example:**
```python
offset = client.read_tool_offset(tool_number=2)
if offset:
    print(f"Tool 2 offset data: {offset}")
    # Output: Tool 2 offset data: {'raw': '0.2330\r\n07'}
```

**Notes:**
- Tool numbers must be 1-99
- Invalid numbers are rejected with error message
- Offset data is returned as raw value with trailing checksum info
- Uses REDTOFS command (Protocol Type 2)

### write_tool_offset()

Write tool offset data for a specific tool.

**Signature:**
```python
def write_tool_offset(self, tool_number: int, offset_type: str, value: float) -> bool:
```

**Parameters:**
- `tool_number` (int): Tool number to update (1-99)
- `offset_type` (str): Type of offset:
  - `'H'` = Tool length offset (type 0)
  - `'D'` = Diameter/cutter compensation offset (type 2)
  - `'W'` = Wear offset (type 1)
- `value` (float): New offset value in mm

**Returns:**
- `True`: If write successful
- `False`: If write failed

**Example:**
```python
# Set tool 2 diameter offset to 0.233mm
success = client.write_tool_offset(
    tool_number=2,
    offset_type='D',
    value=0.233
)

# Set length offset
success = client.write_tool_offset(
    tool_number=2,
    offset_type='H',
    value=25.5
)

# Set wear offset
success = client.write_tool_offset(
    tool_number=2,
    offset_type='W',
    value=0.1
)
```

**Safety Notes:**
- Warns if offset value > 500mm (unusual)
- Validates tool number (1-99)
- Uses WRTTOFS command (Protocol Type 2)
- Data payload is padded with trailing spaces to exact byte count
- Cannot write during editing mode
- Returns status code for error diagnosis

### read_tool_life()

Read tool life data for a specific tool.

**Signature:**
```python
def read_tool_life(self, tool_number: int) -> Optional[Dict]:
```

**Parameters:**
- `tool_number` (int): Tool number to read (1-99)

**Returns:**
- `dict`: Raw tool life data from machine (e.g., `{'raw': '0\r\n08'}`)
- `None`: If read fails

**Example:**
```python
life = client.read_tool_life(tool_number=2)
if life:
    print(f"Tool 2 life data: {life}")
    # Output: Tool 2 life data: {'raw': '500\r\n13'}
```

**Notes:**
- Tool numbers must be 1-99
- Data is returned as raw value in time units or count
- Uses REDTLLF command (Protocol Type 2)
- Returns current life value that was previously set

### write_tool_life()

Set/write tool life value for a specific tool.

**Signature:**
```python
def write_tool_life(self, tool_number: int, life_value: int,
                   life_type: str = 'TIME') -> bool:
```

**Parameters:**
- `tool_number` (int): Tool number to update (1-99)
- `life_value` (int): New life value (0-999999)
- `life_type` (str): Type of life counter:
  - `'TIME'` = Time-based life (default, type 3)
  - `'COUNT'` = Count-based life (type 1)

**Returns:**
- `True`: If write successful
- `False`: If write failed

**Example:**
```python
# Set tool 2 time-based life to 500
success = client.write_tool_life(
    tool_number=2,
    life_value=500,
    life_type='TIME'
)

# Set tool 2 count-based life to 1000
success = client.write_tool_life(
    tool_number=2,
    life_value=1000,
    life_type='COUNT'
)
```

**Safety Notes:**
- Validates tool number (1-99)
- Validates life_value (0-999999)
- Warns if life_value > 10000 (unusual)
- Uses WRTTLLF command (Protocol Type 2)
- Data payload is formatted as 6-digit decimal value
- Cannot write during editing mode

### clear_tool_life()

Clear/reset the tool life counter for a tool.

**Signature:**
```python
def clear_tool_life(self, tool_number: int) -> bool:
```

**Parameters:**
- `tool_number` (int): Tool number to clear (1-99)

**Returns:**
- `True`: If clear successful
- `False`: If clear failed

**Example:**
```python
# Clear tool 2 life counter
success = client.clear_tool_life(tool_number=2)
if success:
    print("Tool 2 life counter cleared")
```

**Safety Notes:**
- Prints warning before clearing
- Validates tool number (1-99)
- Implemented as write_tool_life(value=0) for Protocol Type 2 compatibility
- Operation cannot be undone easily
- Resets life counter to zero immediately
- Sets life_type='TIME' by default

## Usage Patterns

### Pattern 1: Read Current State

```python
def show_tool_status(client, tool_num):
    """Display current tool status."""
    offset = client.read_tool_offset(tool_num)
    life = client.read_tool_life(tool_num)

    print(f"Tool {tool_num}:")
    print(f"  Offset: {offset}")
    print(f"  Life: {life}")
```

### Pattern 2: Update Multiple Offsets

```python
def update_tool_offsets(client, tools_data):
    """
    Update offsets for multiple tools.

    Args:
        tools_data: List of (tool_num, offset_type, value) tuples
    """
    for tool_num, offset_type, value in tools_data:
        success = client.write_tool_offset(tool_num, offset_type, value)
        if success:
            print(f"Tool {tool_num} updated")
        else:
            print(f"Tool {tool_num} update failed - check machine state")
```

### Pattern 3: Batch Life Counter Reset

```python
def reset_tool_life_batch(client, tool_numbers):
    """Reset tool life counters for multiple tools."""
    for tool_num in tool_numbers:
        print(f"Clearing tool {tool_num}...")
        if client.clear_tool_life(tool_num):
            print(f"✓ Tool {tool_num} cleared")
        else:
            print(f"✗ Tool {tool_num} failed")
        time.sleep(0.5)  # Brief delay between operations
```

### Pattern 4: Smart Tool Setup

```python
def setup_tool_for_job(client, tool_num, offset_h, offset_d, life_value):
    """Complete tool setup before job."""
    print(f"Setting up tool {tool_num}...")

    # Set length offset
    if not client.write_tool_offset(tool_num, 'H', offset_h):
        return False

    # Set diameter offset
    if not client.write_tool_offset(tool_num, 'D', offset_d):
        return False

    # Set life counter
    if not client.write_tool_life(tool_num, life_value):
        return False

    print(f"✓ Tool {tool_num} ready for job")
    return True
```

### Pattern 5: Tool Life Management

```python
def manage_tool_life(client, tool_num, threshold=20):
    """Monitor tool life and warn before expiration."""
    life = client.read_tool_life(tool_num)
    if not life:
        return False

    # Extract life value (format depends on machine)
    current_life = int(str(life).split()[-1])  # Simplified extraction

    if current_life < threshold:
        print(f"⚠ Tool {tool_num} life low: {current_life}")
        return False
    else:
        print(f"✓ Tool {tool_num} life OK: {current_life}")
        return True
```

## Error Handling

### Common Errors

**Error: Tool number out of range**
```
✗ Read Tool Offset: Tool number must be 1-999, got 0
✗ Read Tool Offset: Tool number must be 1-999, got 1000
```

**Fix:** Use tool numbers between 1 and 999

**Error: Invalid offset type**
```
✗ Write Tool Offset: offset_type must be 'H', 'D', or 'W'
```

**Fix:** Use only 'H' (length), 'D' (diameter), or 'W' (wear)

**Error: Machine state issue**
```
✗ Tool Offset Write failed: Currently in editing or operation mode
```

**Fix:** Wait for operation to complete, exit editing mode

**Error: Data protection enabled**
```
✗ Tool Life Write failed: Data protection enabled
```

**Fix:** Disable data protection on machine if allowed

### Status Code Categories

Operations return completion codes that indicate:

- **00** = Success - operation completed
- **01-46** = Error - permanent issue, retry won't help
  - 05 = Machine busy (wait and retry)
  - 10 = Data protection enabled
  - 13 = Data out of range
- **60-99** = State/Condition - temporary, can retry
  - 73 = Machine resetting (wait)
  - 71-72 = Door open (close and retry)

See [COMPLETION_CODES_AT_A_GLANCE.md](COMPLETION_CODES_AT_A_GLANCE.md) for complete list.

## Recovery Strategies

### If Offset Write Fails

```python
success, status, _ = client.send_command("CWRTTOF", args)

if not success:
    category = BrotherCNCClient.get_status_category(status)

    if category == "State/Condition":
        # Temporary condition - can retry
        print("Machine busy, waiting...")
        time.sleep(2)
        retry()
    else:
        # Permanent error - fix root cause
        desc = BrotherCNCClient.get_status_description(status)
        print(f"Cannot write offset: {desc}")
        # Check machine state, data protection, etc.
```

### If Tool Life Clear Fails

```python
success = client.clear_tool_life(tool_num=42)

if not success:
    # Common causes:
    # 1. Machine in operation (status 05 or 63)
    #    Solution: Wait for operation to complete
    # 2. Tool doesn't exist (status 07)
    #    Solution: Check tool number
    # 3. Data protected (status 10)
    #    Solution: Disable protection on machine
    print("Clear failed - check machine state")
```

## Advanced Topics

### Understanding Offset Types

**H (Length) Offset:**
- Adjusts tool length in Z axis
- Used for all tools
- Typical range: 0-500mm

**D (Diameter) Offset:**
- Adjusts tool diameter compensation
- Used for turning, drilling, etc.
- Typical range: 0-50mm

**W (Wear) Offset:**
- Compensation for tool wear
- Applied on top of H offset
- Typical range: -10 to 10mm

### Life Counter Types

**TIME-based life:**
- Measured in time units
- Typical: 0-9999 minutes
- Example: 100 = 100 minutes of tool life

**COUNT-based life:**
- Measured in number of uses
- Typical: 0-9999 uses
- Example: 500 = 500 parts

### Performance Notes

- Tool data operations take ~1 second per operation
- Offset writes are atomic (all-or-nothing)
- Life counter clears are immediate
- No performance impact from read operations

## Testing

### Basic Functionality Test

```bash
python3 test_tool_operations.py
```

Validates:
- ✓ Read tool offset
- ✓ Read tool life
- ✓ Input validation
- ✓ Error handling

### Manual Testing Checklist

- [ ] Can read tool offset for tool #1
- [ ] Can read tool life for tool #1
- [ ] Offset write succeeds on test tool
- [ ] Life counter write succeeds on test tool
- [ ] Life counter clear works
- [ ] Invalid tool numbers rejected
- [ ] Extreme values produce warnings

## Related Documentation

- [COMPLETION_CODES_AT_A_GLANCE.md](COMPLETION_CODES_AT_A_GLANCE.md) - Status code reference
- [ATC_OPERATIONS.md](ATC_OPERATIONS.md) - Remote tool changer configuration
- [MACHINE_DATA_OPERATIONS.md](MACHINE_DATA_OPERATIONS.md) - Machine parameter writes
- [README_COMPLETION_CODES.md](README_COMPLETION_CODES.md) - Error handling guide

## Summary

Tool data operations enable:
- ✓ Remote tool offset management
- ✓ Tool life tracking and management
- ✓ Automated tool setup workflows
- ✓ Preventive maintenance automation
- ✓ Production data collection

With proper error handling and validation, tool data operations are safe and powerful for factory automation scenarios.
