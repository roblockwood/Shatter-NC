# Telnet ATC Write Operations Documentation

## Overview

This document describes how to edit ATC (Automatic Tool Changer) pot assignments using the Telnet protocol (Port 10000). **Note: This functionality is planned for Phase 6 and is not yet implemented in the backend `CNCTelnetClient`.**

## Status

- **Phase 6: Enable Writes** - ✅ **IN PROGRESS** (ATC tool color changes implemented)
- **Reference Implementation**: Available in `brother_cnc_export/brother_cnc_client.py`
- **Backend Implementation**: `CHGMAGC` implemented in `backend/app/clients/telnet_client.py`
- **Semaphore Serialization**: All read/write operations use per-machine semaphore locks to prevent conflicts
- **Connection Pooling**: Persistent connections are reused across operations for improved stability and reliability

## ATC Write Commands

The Brother CNC protocol supports several commands for modifying ATC magazine configuration:

### CHGMAGM - Change Tool Number Assignment

**Purpose**: Assign or change a tool number in a specific magazine pot.

**Command Format**:
```
CHGMAGM [magazine_pos][tool_num][new_tool_num]
```

**Arguments** (8 bytes total):
- `magazine_pos`: Magazine position (2 bytes: 00-99, where 00=spindle, 01-99=pots)
- `tool_num`: Current tool number for verification (2 bytes: 01-99, optional)
- `new_tool_num`: New tool number to assign (2 bytes: 01-99)
- Padding: Remaining bytes padded with spaces

**Example**:
- Assign tool #42 to pot #5: `CHGMAGM 05 00 42` (or `CHGMAGM 05    42`)
- Change tool in pot #1 from tool #10 to tool #20: `CHGMAGM 01 10 20`

### CHGMAGS - Change Spindle/Main Tool

**Purpose**: Change the tool currently in the spindle.

**Command Format**:
```
CHGMAGS [magazine_pos][tool_num][spindle_tool]
```

**Arguments**:
- `magazine_pos`: Must be 00 (spindle)
- `tool_num`: Current tool number in spindle (for verification)
- `spindle_tool`: New tool number for spindle

### CHGMAGK - Change Tool Type

**Purpose**: Change the tool type classification for a pot.

**Command Format**:
```
CHGMAGK [magazine_pos][tool_num][tool_type]
```

**Tool Type Values**:
- `1` = Standard Tool
- `2` = Large Tool
- `3` = Medium Tool

**Example**:
- Set pot #5 to Large Tool type: `CHGMAGK 05 42 02`

### CHGMAGC - Change Tool Color

**Purpose**: Change the color classification for a pot.

**Command Format**:
```
CHGMAGC [magazine_pos][tool_num][color]
```

**Color Values**:
- `0` = No color
- `1` = Blue
- `2` = Red
- `3` = Purple
- `4` = Green
- `5` = Light Blue
- `6` = Yellow
- `7` = White

**Example**:
- Set pot #5 to Red: `CHGMAGC 05 42 02`

### CHGMAGD - Delete/Remove Tool

**Purpose**: Remove a tool from a magazine position.

**Command Format**:
```
CHGMAGD [magazine_pos][tool_num]
```

**Arguments**:
- `magazine_pos`: Magazine position (00-99)
- `tool_num`: Tool number to remove (for verification)

**Example**:
- Remove tool from pot #5: `CHGMAGD 05 42`

## Reference Implementation

The reference implementation in `brother_cnc_export/brother_cnc_client.py` provides a working example:

```python
def change_atc_tool(self, magazine_pos: int, tool_num: int = None,
                   change_type: str = 'M', new_value: int = None) -> bool:
    """
    Change tool configuration in ATC magazine.

    Args:
        magazine_pos: Magazine position (0=spindle, 1-99=pots)
        tool_num: Current tool number in position (for verification)
        change_type: Type of change:
            'M' = Change tool number (new_value = new tool number)
            'S' = Change spindle/main tool (new_value = spindle tool)
            'K' = Change tool type (new_value: 1=Standard, 2=Large, 3=Medium)
            'C' = Change color (new_value: 0=None, 1=Blue, 2=Red, 3=Purple, 4=Green, 5=Light blue)
            'D' = Delete/remove tool (new_value not needed)
        new_value: New value for the change (tool number, type, or color)

    Returns:
        bool: True if successful, False otherwise
    """
    # Implementation details...
```

### Convenience Methods

The reference implementation also provides simplified wrapper methods:

```python
def assign_tool_to_magazine(self, magazine_pos: int, tool_num: int) -> bool:
    """
    Simplified wrapper: Assign a tool to a magazine position.

    Args:
        magazine_pos: Magazine position (1-99, not spindle)
        tool_num: Tool number to assign (1-999)

    Returns:
        bool: True if successful

    Example:
        client.assign_tool_to_magazine(1, 42)  # Put tool #42 in pot #1
        client.assign_tool_to_magazine(5, 17)  # Put tool #17 in pot #5
    """
    return self.change_atc_tool(magazine_pos, tool_num=tool_num, change_type='M', new_value=tool_num)

def remove_tool_from_magazine(self, magazine_pos: int) -> bool:
    """
    Simplified wrapper: Remove tool from magazine position.

    Args:
        magazine_pos: Magazine position (0-99)
    """
    return self.change_atc_tool(magazine_pos, change_type='D')
```

## Safety Considerations

### Validation Rules

Before implementing write operations, the following validation should be performed:

1. **Magazine Position Validation**:
   - Must be 0-99 (0 = spindle, 1-99 = pots)
   - Verify pot exists on machine configuration

2. **Tool Number Validation**:
   - Must be 1-99 (or 1-999 depending on machine)
   - Verify tool is registered in TOLN data

3. **Machine State Validation**:
   - Machine must NOT be in operation mode
   - Machine must NOT be in editing mode
   - ATC must NOT be in the middle of a tool change
   - Status code `36`: "ATC tool change attempted during memory operation"
   - Status code `37`: "ATC tool change attempted during MDI operation"
   - Status code `63`: "During tool change"

4. **Adjacent Pot Validation**:
   - Status code `35`: "Pot adjacent to specified pot contains large tool"
   - Large tools may prevent assignment to adjacent pots

5. **Tool Registration Validation**:
   - Status code `39`: "Unregistered tool registration attempted"
   - Tool must exist in TOLN data before assignment

### Error Codes

Common error codes for ATC write operations:

| Code | Description | Resolution |
|------|-------------|------------|
| `00` | Success | Operation completed normally |
| `30` | Program/data/tool number invalid or out of range | Check tool number and pot number |
| `32` | Cannot change during operation or editing | Wait for machine to be idle |
| `34` | Magazine item change without tool number | Provide tool number in command |
| `35` | Pot adjacent to specified pot contains large tool | Choose different pot |
| `36` | ATC tool change attempted during memory operation | Stop program first |
| `37` | ATC tool change attempted during MDI operation | Exit MDI mode first |
| `38` | Unspecified error during ATC tool change | Check machine state |
| `39` | Unregistered tool registration attempted | Register tool in TOLN first |
| `40` | Conflict due to communication using other port | Close other connections |
| `46` | Tool unable to change group/main tool/type/color in ATC | Check tool configuration |
| `63` | During tool change | Wait for tool change to complete |
| `92` | Pot is not at the top end | Move magazine to correct position |

## Planned Implementation (Phase 6)

When Phase 6 is implemented, the backend `CNCTelnetClient` should include:

### Methods to Add

```python
async def change_atc_tool_assignment(
    self,
    magazine_pos: int,
    tool_num: Optional[int] = None,
    change_type: str = 'M',
    new_value: Optional[int] = None,
    verbose: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Change tool configuration in ATC magazine.

    Args:
        magazine_pos: Magazine position (0=spindle, 1-99=pots)
        tool_num: Current tool number for verification (optional)
        change_type: Type of change ('M', 'S', 'K', 'C', 'D')
        new_value: New value for the change
        verbose: If True, log command details

    Returns:
        Tuple of (success, status_code)
    """
    # CRITICAL: Acquire semaphore lock for this machine
    machine_lock = await _get_machine_lock(self.ip_address, self.port)
    
    async with machine_lock:
        # Use longer timeout for write operations (5 seconds)
        success, status, _ = await self._send_command(
            f"CHGMAG{change_type}", arguments, verbose=verbose, read_timeout=5.0
        )
        return success, status

async def assign_tool_to_pot(
    self,
    pot_number: int,
    tool_number: int,
    verbose: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Simplified wrapper: Assign a tool to a pot.
    
    Note: This method calls change_atc_tool_assignment, which handles
    semaphore locking internally. No need to acquire lock here.

    Args:
        pot_number: Pot number (1-99)
        tool_number: Tool number to assign (1-99)
        verbose: If True, log command details

    Returns:
        Tuple of (success, status_code)
    """
    return await self.change_atc_tool_assignment(
        magazine_pos=pot_number,
        tool_num=tool_number,
        change_type='M',
        new_value=tool_number,
        verbose=verbose
    )

async def remove_tool_from_pot(
    self,
    pot_number: int,
    tool_number: Optional[int] = None,
    verbose: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Simplified wrapper: Remove tool from pot.

    Args:
        pot_number: Pot number (1-99)
        tool_number: Tool number for verification (optional)
        verbose: If True, log command details

    Returns:
        Tuple of (success, status_code)
    """
    return await self.change_atc_tool_assignment(
        magazine_pos=pot_number,
        tool_num=tool_number,
        change_type='D',
        new_value=None,
        verbose=verbose
    )
```

### API Endpoints to Add

```python
@router.put("/{machine_id}/tools/atc/pot/{pot_number}")
async def assign_tool_to_pot(
    machine_id: int,
    pot_number: int,
    tool_number: int,
    db: Session = Depends(get_db)
):
    """
    Assign a tool to an ATC pot.

    Args:
        machine_id: Machine ID
        pot_number: Pot number (1-99)
        tool_number: Tool number to assign (1-99)
    """
    # Implementation with validation, safety checks, audit logging...
```

## Related Documentation

- **Migration Plan**: `docs/BACKEND_TELNET_MIGRATION_PLAN.md` - Phase 6 details
- **Command Coverage**: `docs/TELNET_COMMAND_COVERAGE.md` - All Telnet commands
- **Reference Implementation**: `brother_cnc_export/brother_cnc_client.py` - Working example

## Notes

- All ATC write operations require the machine to be in a safe state (not operating, not editing)
- Changes are immediate and affect the machine's ATC configuration
- Consider implementing audit logging for all ATC changes
- Frontend should require confirmation for destructive operations
- Rate limiting should be enforced to prevent rapid-fire commands

