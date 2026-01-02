# Protocol Discovery - Command Format Patterns

This document captures important protocol discoveries made through testing against Brother CNC machines using Protocol Type 2 over TCP/IP.

## Key Discovery: Operation Type Embedding

The Brother CNC protocol has a subtle but critical pattern: **operation type indicators are embedded within the command name itself**, not separated as distinct parameters.

### Pattern 1: IOC Commands (External I/O Signals)

**Initial Assumption (WRONG):**
```
Command: CIOC (4 chars)
Operation: REF or MOD (3 chars)
Signal: ALMRLS (6 chars)
```

**Actual Format (CORRECT):**
```
Command: IOCREF or IOCMOD (7 chars, operation embedded)
Arguments: ALMRLS   (8 chars, signal name padded)

Full frame: %CIOCREF ALMRLS  \r\n[checksum]%\r\n
```

**Why This Matters:**
The operation (REF = reference/read, MOD = modify/write) becomes part of the 7-character command name, not a separate field.

**Discovered Commands:**
- `IOCREF` - Read/reference external signal state
- `IOCMOD` - Modify/write external signal state

**Data Format for IOCMOD:**
IOCMOD requires a multi-part command with ON/OFF value:
```
Header: %CIOCMOD SIGNALNAME\r\n
Data:   ON\r\n or OFF\r\n
Footer: [checksum]%\r\n
```

**Example - Reading ALMRLS (Alarm Release) signal:**
```python
client.send_command("IOCREF ", "ALMRLS  ")
# Returns: "OFF" or "ON"
```

**Example - Writing ALMRLS signal to ON:**
```python
client.send_multipart_command("IOCMOD ", "ALMRLS  ", "ON")
```

**Signal Name Format:**
- Signal names must be exactly 8 characters
- Pad with spaces if shorter: `"ALMRLS  "` (6 chars + 2 spaces)
- Truncate if longer: `"SOMELONG"[:8]`

### Pattern 2: CHGMAG Commands (ATC Tool Change)

**Initial Assumption (WRONG):**
```
Command: CHGMAG (6 chars)
Magazine: 09 (pot 9)
Tool: 36
```

**Actual Format (CORRECT):**
```
Command: CHGMAGM (7 chars, operation embedded - M for change tool)
Arguments: 0936     (8 chars, magazine + tool + padding)

Full frame: %CCHGMAGM0936    \r\n[checksum]%\r\n
```

**Why This Matters:**
The operation type (M, S, K, C, D) becomes part of the 7-character command name.

**Discovered Commands:**
- `CHGMAGM` - Change tool number (M = change tool)
- `CHGMAGS` - Change group/main tool (S = change group)
- `CHGMAGK` - Change tool type (K = change kind/type)
- `CHGMAGC` - Change color (C = change color)
- `CHGMAGD` - Delete tool (D = delete)

**Argument Format:**
- `mm` = Magazine number (00=spindle, 01-50=pots, format as 2-digit)
- `tt` = Tool/value number (2-digit, right-zero-padded)
- `xxxx` = Padding spaces (4 spaces to reach 8 chars)

**Examples:**
```python
# Change pot 9 to tool 36
client.send_command("CHGMAGM", "0936    ")

# Change pot 5 to tool 1
client.send_command("CHGMAGM", "0501    ")

# Change spindle to tool 42
client.send_command("CHGMAGM", "0042    ")
```

## Protocol Frame Structure

All commands follow this format:
```
%C[7-char-command][8-char-args]\r\n[checksum]%\r\n
```

### Breaking Down the Format:

1. **Protocol Start:** `%C`
2. **Command:** Exactly 7 characters (left-padded with spaces if needed)
3. **Arguments:** Exactly 8 characters (right-padded with spaces if needed)
4. **Line Ending:** `\r\n`
5. **Checksum:** Calculated checksum byte
6. **Protocol End:** `%\r\n`

### Critical Padding Rules:

- Commands MUST be exactly 7 characters (space-pad left side)
- Arguments MUST be exactly 8 characters (space-pad right side)
- This is strict - the machine will return Status 02 (Illegal command header) if padding is incorrect

## Command Name Construction

When a command has an operation type:

**Template:** `[BaseCommand][Operation]`

Examples:
- `LOD` (3 chars) → pad to 7: `LOD    ` (7 chars)
- `REDTOFS` (7 chars) → already fits: `REDTOFS` (7 chars)
- `IOC` + `REF` = `IOCREF` (6 chars) → pad to 7: `IOCREF ` (7 chars)
- `CHGMAG` + `M` = `CHGMAGM` (7 chars) → already fits: `CHGMAGM` (7 chars)

## Machine State Restrictions

Several commands are restricted based on machine state:

**Status 32 - Cannot change during operation:**
- CHGMAG (all variants) - Cannot change tools during operation
- IOCMOD (most signals) - Cannot write signals during operation
- Other write operations

**Status 36 - ATC tool change attempted during memory operation:**
- Indicates the machine is executing a program

**Workaround:**
Ensure machine is in STOP/IDLE state (not running a program) before attempting writes.

## Common Status Codes

- **00** - Normally ended (success)
- **02** - Illegal slave command header (bad command name or format)
- **32** - Cannot change during operation (machine is busy)
- **36** - ATC tool change attempted during memory operation

## Testing Methodology

To test command formats:

1. **Use exact syntax:** `%C[command][args]\r\n[checksum]%\r\n`
2. **Verify padding:** Count characters - command must be 7, args must be 8
3. **Check machine state:** Ensure not in operation before writes
4. **Compare responses:**
   - Status 00 = correct format
   - Status 02 = command/format error
   - Status 32 = correct format but restricted by machine state

## Lessons Learned

1. **Operation types embed in command names** - Not separate parameters
2. **Padding is critical** - Exact 7/8 character counts required
3. **Manual documentation format ≠ implementation** - Manual shows conceptual format, actual protocol requires strict field alignment
4. **Trial and error is necessary** - Testing revealed the actual format since it differs from manual descriptions
5. **Understand the machine, not just the documentation** - Each Brother model may have variations

## Future Command Discovery

When testing new commands:

1. Start with the manual name (e.g., CHGMAG, IOC)
2. Try with and without operation codes embedded
3. Test padding variations (spaces before/after)
4. Verify exact 7/8 character alignment
5. Check machine state (operation vs. idle)
6. If Status 02 persists, try alternative command names or formats
7. Document working format for future reference
