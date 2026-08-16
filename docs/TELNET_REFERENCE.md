# Telnet Reference (Brother CNC Port 10000)

Protocol reference for Shatter's telnet client ([`telnet_client.py`](../backend/app/clients/telnet_client.py)). FTP remains used for file transfer; HTTP port 80 is legacy and not used for polling.

**Locks:** Per-machine `asyncio` locks in [`_telnet_state.py`](../backend/app/clients/_telnet_state.py) serialize telnet operations. Use `create_fresh_connection()` for each operation batch.

**Directory naming / FTP sync:** C00 vs D00 rules — [FTP_SYNC_EXCLUSION_RULES.md](FTP_SYNC_EXCLUSION_RULES.md).

---

## Implemented Read Commands

### LOD — load data file

| Method | Data | Purpose |
|--------|------|---------|
| `get_memory_data()` | MEM | Active program |
| `get_tool_table_data()` | TOLNI1 / TOLNM1 | Tool table |
| `get_position_data()` | POSNI1 / POSNM1 | Work offsets |
| `get_atc_magazine_data()` | ATCTL (C00) / ATDTL (D00) | ATC magazine |
| `load_data(name)` | arbitrary | Generic LOD |

### DRQALL — directory listing

- `get_directory_listing()` — list CNC data files
- `parse_directory_listing()` — C00 (11-byte entries) or D00 (18-byte entries)
- `detect_control_type()` — infer C00 vs D00 from PRDC/SYSC vs PRDD/SYSD patterns

### RED — read individual values

| Command | Method | Notes |
|---------|--------|-------|
| REDPRGN | `get_current_program_info()` | Running program O-number, block |
| REDPRG | `get_current_program_content()` | Program text by char count |
| REDFILE | `get_file_control_data()` | Memory / registration info |
| REDDATE | `get_date_time()` | Machine clock |
| REDPLCD / REDPLCR | `get_plc_signal*` | PLC signals |
| REDCDBN / REDCDSL | `get_*_data_bank*` | Data bank names |
| REDTOFS | `get_tool_compensation()` | Tool comp |
| REDTLLF | `get_tool_life()` | Tool life |
| REDTOFM | `get_hd_modal()` | H/D modal |
| REDMCNM | `get_macro_variable*` | Macros 500–999 |

---

## Implemented Write Commands

### Tool table

| Command | Method | Purpose |
|---------|--------|---------|
| WRTTOFS | `write_tool_offset()` | Tool offset |
| WRTTLLF | `write_tool_life()` | Tool life |
| CLRTLLF | `clear_tool_life()` | Clear tool life |
| *(FTP TOLN)* | `write_tool_names_via_ftp()` | Tool name (no telnet `WRT*`; patch `TOLNI1`/`TOLNM1` + upload) |
| WRTMCNM | `write_macro_variable()` | Macro variables 500–999 |

### ATC magazine (CHGMAG*)

Implemented in [`_telnet_write_ops.py`](../backend/app/clients/_telnet_write_ops.py):

| Type | Command | Purpose |
|------|---------|---------|
| M | CHGMAGM | Assign/change tool number in pot |
| S | CHGMAGS | Spindle tool |
| K | CHGMAGK | Tool type (1=std, 2=large, 3=medium) |
| C | CHGMAGC | Tool color (0–7) |
| D | CHGMAGD | Remove tool from pot |

**Argument layout (8-char field, space-padded):**

| Type | Example | Payload | Meaning |
|------|---------|---------|---------|
| M | CHGMAGM | `0407` | Pot 4 → tool 7 (C00: 2-digit tool) |
| M | CHGMAGM | `02101` | Pot 2 → tool 101 (D00: 3-digit tool) |
| S | CHGMAGS | `0012` | Spindle → tool 12 |
| C | CHGMAGC | `023` | Pot 2 → color 3 |
| K | CHGMAGK | `022` | Pot 2 → type 2 (Large) |
| D | CHGMAGD | `05` | Clear pot 5 |

Pots marked **Cap (255)** in ATCTL are not empty — run **CHGMAGD** first (`remove_tool_from_pot` /
`clear_cap_from_pot`), then **CHGMAGM** to assign a tool. `assign_tool_to_pot(clear_cap=True)` does
this automatically.

### Other writes

| Command | Purpose |
|---------|---------|
| WRTREL | Preset relative position |
| IOCMOD | Write I/O signal (multipart) |

---

## ATC Write Status Codes

| Code | Meaning |
|------|---------|
| 00 | Success |
| 30 | Invalid tool/pot number |
| 32 | Machine busy (operation/editing) |
| 35 | Adjacent pot large-tool conflict |
| 36 | Memory operation in progress |
| 37 | MDI active |
| 39 | Tool not registered in TOLN |
| 40 | Other port holds connection |
| 63 | Tool change in progress |

Writes use extended read timeout (~5s) and hold the machine lock for the full operation.

---

## Not Implemented (future / out of scope)

Folder ops (FLDPWD, FLDCHG), telnet file upload (SAV), program control (MEMSTRT, MEMSTOP, CHGPROG), auto-notification (SNC/SND), and most directory variants (DRQSEL, DRQPRAL). File upload/download in Shatter uses **FTP**, not telnet SAV.

---

## Control Version Detection

C00 vs D00 affects directory entry size and FTP sync filename rules. Auto-detection parses DRQALL in both formats and scores indicator files (PRDC/SYSC vs PRDD/SYSD).

---

## Client Usage Pattern

```python
from app.clients.telnet_client import create_fresh_connection

client = await create_fresh_connection(ip_address, port=10000, timeout=10)
try:
    tools = await client.get_tool_table_data(units="in")
    success, status = await client.change_atc_tool(
        operation_type="C", magazine_pos=2, tool_num=2, new_value=4
    )
finally:
    await client.disconnect()
```

---

## Related

- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) — polling integration
- [FTP_SYNC_EXCLUSION_RULES.md](FTP_SYNC_EXCLUSION_RULES.md) — sync policy
