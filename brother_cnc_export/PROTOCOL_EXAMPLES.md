# Protocol Examples - Actual Commands Sent to Machine

This document shows the actual Protocol Type 2 frames sent to the Brother CNC machine.

## Reading Tool Length Offset

### Python Code
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Read length offset for tool #22
offset = client.read_tool_offset(tool_number=22)

client.disconnect()
```

### Actual Command Sent to Machine
```
%CREDTOFS220       \r\n
```

### Breaking Down the Frame
```
%              Start marker (ASCII 37)
C              Command indicator
REDTOFS        Command = Read tool offset (7 characters)
22             Tool number (2 digits: tool #22)
0              Type code (0 = length offset)
               5 spaces for padding (to 8 character argument field)
\r\n           Carriage return + line feed
[checksum]%\r\n Checksum and end marker
```

### Hex Representation
```
25 43 52 45 44 54 4F 46 53 32 32 30 20 20 20 20 20 20 0D 0A
%  C  R  E  D  T  O  F  S  2  2  0  _  _  _  _  _  _ \r \n
```

### Machine Response
```
%RREDTOFS220     00\r\n
25.1234\r\n
[checksum]%\r\n
```

The response contains:
- Response header with status 00 (success)
- The offset value (e.g., 25.1234 mm)
- Checksum and end marker

---

## Writing Tool Diameter Offset

### Python Code
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Write diameter offset for tool #2 = 0.233mm
success = client.write_tool_offset(
    tool_number=2,
    offset_type='D',  # D = diameter
    value=0.233
)

client.disconnect()
```

### Actual Commands Sent to Machine

**Header Frame:**
```
%CWRTTOFS02 2     \r\n
```

**Data Frame:**
```
0.2330   \r\n
```

**Checksum Frame:**
```
[checksum]%\r\n
```

### Breaking Down the Header
```
%              Start marker
C              Command indicator
WRTTOFS        Command = Write tool offset (7 characters)
02             Tool number (2 digits: tool #2)
2              Type code (2 = diameter/cutter compensation)
               5 spaces for padding
\r\n           Carriage return + line feed
```

### Breaking Down the Data
```
0.2330         Offset value with 4 decimal places
               4 trailing spaces to make exactly 9 bytes
\r\n           Line feed
```

### Machine Response
```
%RWRTTOFS02 2     00\r\n
[checksum]%\r\n
```

Status 00 = success

---

## Reading Tool Life

### Python Code
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Read tool life for tool #2
life = client.read_tool_life(tool_number=2)

client.disconnect()
```

### Actual Command Sent to Machine
```
%CREDTLLF023     \r\n
```

### Breaking Down the Frame
```
%              Start marker
C              Command indicator
REDTLLF        Command = Read tool life (7 characters)
02             Tool number (2 digits: tool #2)
3              Type code (3 = tool life value)
               5 spaces for padding
\r\n           Carriage return + line feed
```

### Machine Response
```
%RREDTLLF023     00\r\n
500\r\n
[checksum]%\r\n
```

The response contains the current tool life value (e.g., 500 time units).

---

## Writing Tool Life

### Python Code
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Write tool life for tool #2 = 500 time units
success = client.write_tool_life(
    tool_number=2,
    life_value=500,
    life_type='TIME'
)

client.disconnect()
```

### Actual Commands Sent to Machine

**Header Frame:**
```
%CWRTTLLF023     \r\n
```

**Data Frame:**
```
000500\r\n
```

**Checksum Frame:**
```
[checksum]%\r\n
```

### Breaking Down the Header
```
%              Start marker
C              Command indicator
WRTTLLF        Command = Write tool life (7 characters)
02             Tool number (2 digits: tool #2)
3              Type code (3 = tool life value)
               5 spaces for padding
\r\n           Carriage return + line feed
```

### Breaking Down the Data
```
000500         Life value as 6-digit decimal (500)
\r\n           Line feed
```

### Machine Response
```
%RWRTTLLF023     00\r\n
[checksum]%\r\n
```

Status 00 = success

---

## Offset Type Codes

When reading/writing tool offsets, use these type codes:

| Type Code | Meaning |
|-----------|---------|
| 0 | Tool length offset (H) |
| 1 | Tool wear offset (W) |
| 2 | Tool diameter/cutter compensation offset (D) |
| 3 | Cutter wear offset |
| 4 | Tool position offset (X) |
| 5 | Tool position wear offset (X) |
| 6 | Tool position offset (Y) |
| 7 | Tool position wear offset (Y) |

---

## Tool Life Type Codes

When writing tool life, use these type codes:

| Type Code | Meaning |
|-----------|---------|
| 0 | Life unit setting |
| 1 | Initial life value |
| 2 | Life warning threshold |
| 3 | Current tool life (TIME mode) |

For most use cases, you'll use type code 3 (current tool life).

---

## Data Format Notes

### Offset Values
- **Types 0, 2, 4, 6:** 9 bytes total
  - Format: `f"{value:.4f}".ljust(9)` (pad with trailing spaces)
  - Example: `"25.1234 "` (with 4 trailing spaces)

- **Types 1, 3, 5, 7:** 8 bytes total
  - Format: `f"{value:.4f}".ljust(8)` (pad with trailing spaces)
  - Example: `"0.1234 "` (with 3 trailing spaces)

### Tool Life Values
- Always 6-digit decimal format
- Format: `f"{value:06d}"`
- Example: `"000500"` for 500, `"001200"` for 1200

---

---

## Changing ATC Tool in Magazine

### Python Code
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Change pot 9 to tool 36
success = client.send_command("CHGMAGM", "0936    ")

client.disconnect()
```

### Actual Command Sent to Machine
```
%CCHGMAGM0936    \r\n
[checksum]%\r\n
```

### Breaking Down the Frame
```
%              Start marker
C              Command indicator
CHGMAGM        Command = Change Magazine with M operation (7 characters)
               M = change tool number
09             Magazine number (09 = pot 9, 00 = spindle)
36             Tool number (36)
               4 spaces for padding (to 8 character argument field)
\r\n           Carriage return + line feed
```

### Machine Response
```
%RCHGMAGM0936    00\r\n
[checksum]%\r\n
```

Status 00 = success, pot 9 now contains tool 36

### Other CHGMAG Operations

**Change tool type (K = kind/type):**
```
%CCHGMAGK0903    \r\n
Changes pot 9 tool type to 3 (Medium)
```

**Change tool group (S = group/spindle tool):**
```
%CCHGMAGS0910    \r\n
Changes pot 9 group to 10
```

**Change tool color (C = color):**
```
%CCHGMAGC0902    \r\n
Changes pot 9 color to 2 (Red)
```

**Delete tool from pot (D = delete):**
```
%CCHGMAGD09      \r\n
Removes tool from pot 9
```

---

## Reading External I/O Signal

### Python Code
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Read Alarm Release signal state
success, status, response = client.send_command("IOCREF ", "ALMRLS  ")

client.disconnect()
```

### Actual Command Sent to Machine
```
%CIOCREF ALMRLS  \r\n
[checksum]%\r\n
```

### Breaking Down the Frame
```
%              Start marker
C              Command indicator
IOCREF         Command = IOC (I/O Control) with REF operation (7 characters)
               REF = reference/read
ALMRLS         Signal name (Alarm Release), padded to 8 characters
               2 trailing spaces
\r\n           Carriage return + line feed
```

### Machine Response
```
%CIOCREF ALMRLS  00\r\n
OFF\r\n
[checksum]%\r\n
```

Status 00 = success, signal state is OFF

---

## Writing External I/O Signal

### Python Code
```python
from brother_cnc_client import BrotherCNCClient

client = BrotherCNCClient()
client.connect()

# Set Alarm Release signal to ON
success, status, response = client.send_multipart_command(
    "IOCMOD ",
    "ALMRLS  ",
    "ON"
)

client.disconnect()
```

### Actual Commands Sent to Machine

**Header Frame:**
```
%CIOCMOD ALMRLS  \r\n
```

**Data Frame:**
```
ON\r\n
```

**Checksum Frame:**
```
[checksum]%\r\n
```

### Breaking Down the Header
```
%              Start marker
C              Command indicator
IOCMOD         Command = IOC with MOD operation (7 characters)
               MOD = modify/write
ALMRLS         Signal name, padded to 8 characters
\r\n           Carriage return + line feed
```

### Breaking Down the Data
```
ON             Signal value (ON or OFF)
\r\n           Line feed
```

### Machine Response
```
%CIOCMOD ALMRLS  00\r\n
[checksum]%\r\n
```

Status 00 = success, Alarm Release signal set to ON

### Machine State Note
Some signals (especially output signals) cannot be written during machine operation. You may get Status 32 "Cannot change during operation" if attempted while a program is running. Ensure the machine is in STOP/IDLE state before modifying signals.

---

## Command Summary Table

| Operation | Command | Direction | Data Payload |
|-----------|---------|-----------|--------------|
| Read offset | REDTOFS | Read | None |
| Write offset | WRTTOFS | Write | Decimal value (8-9 bytes) |
| Read life | REDTLLF | Read | None |
| Write life | WRTTLLF | Write | 6-digit decimal |
| Change ATC tool | CHGMAGM | Write | Magazine + tool number |
| Change ATC group | CHGMAGS | Write | Magazine + group number |
| Change ATC type | CHGMAGK | Write | Magazine + type code |
| Change ATC color | CHGMAGC | Write | Magazine + color code |
| Delete ATC tool | CHGMAGD | Write | Magazine number |
| Read I/O signal | IOCREF | Read | Signal name |
| Write I/O signal | IOCMOD | Write | Signal name + ON/OFF |

---

## Status Codes

Common response status codes:

| Code | Meaning |
|------|---------|
| 00 | Success |
| 01 | Invalid data received |
| 02 | Illegal slave command header |
| 04 | Illegal checksum |
| 05 | Machine busy (in operation) |
| 07 | Data does not exist |
| 10 | Data protection enabled |
| 30 | Tool number invalid or out of range |

All successful operations return status 00.

---

## Protocol Details

- **Machine:** Brother CNC with Protocol Type 2 enabled
- **Connection:** TCP/IP port 10000
- **Encoding:** ASCII/ISO
- **Tool Numbers:** 1-99 (formatted as 2-digit: 01-99)
- **Checksum:** XOR of all bytes (modulo 16)

