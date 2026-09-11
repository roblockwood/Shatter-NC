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
| REDMCNM | `get_macro_variable*` | Macros 100–999 (common + job; writes remain 500–999) |

---

## Implemented Write Commands

### Tool table

| Command | Method | Purpose |
|---------|--------|---------|
| WRTTOFS | `write_tool_offset()` | Tool offset |
| WRTTLLF | `write_tool_life()` | Tool life |
| CLRTLLF | `clear_tool_life()` | Clear tool life |
| *(FTP TOLN)* | `write_tool_names_via_ftp()` | Tool name (no telnet `WRT*`; patch `TOLNI1`/`TOLNM1` + upload). **Backs up and restores `ATCTL`/`ATCTLD` around the upload** — replacing TOLN clears magazine assignments on the control. |
| WRTMCNM | `write_macro_variable()` | Macro variables 500–999 |

### Program control / folders (productized for probe cycle)

| Command | Method | Purpose |
|---------|--------|---------|
| CHGMODE | `change_mode()` | Switch MEM / EDIT / MDI / MNL (status `60` = already in mode → success) |
| FLDCHG | `change_folder()` | Multipart cwd change (`PROGRAM`, `/`) |
| FLDPWD | `get_working_folder()` | Read telnet cwd |
| MEMSTRT | `start_memory_program()` | Start memory O-number (4-digit args) |
| MEMSTOP | `memory_stop()` | Latch/clear feed hold (`ON` / `OFF`) |

**Product API:** `GET/POST /api/machines/{id}/probe/*` — see [probe cycle](#probe-cycle-api) below. Orchestration: [`probe_cycle_service.py`](../backend/app/services/probe_cycle_service.py).

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

To **set cap** on an empty pocket, use **CHGMAGM** with tool **255** (C00) or **999** (D00).
The machine panel displays cap as tool **0**; Shatter maps UI `0` on empty-pot rows to this write
(`set_cap_on_pot`).

### Other writes

| Command | Purpose |
|---------|---------|
| WRTREL | Preset relative position |
| IOCMOD | Write I/O signal (multipart) |

---

## Program control & folders

Client wrappers live in [`_telnet_write_ops.py`](../backend/app/clients/_telnet_write_ops.py). Layouts below were confirmed on a C00 Brother control. Frame format is the usual `%C` + 7-char command + 8-char args (see `_build_command`).

### Mode / program select / start / stop

| Command | Args (8-byte field) | Notes |
|---------|---------------------|-------|
| `CHGMODE` | `MEM`, `EDIT`, `MDI`, `MNL` (space-padded) | Status `60` if already in that mode |
| `CHGOPTS` | `ON` / `OFF` | Optional stop (OP.STP). Same layout family as `CHGMODE`. Sibling keys (not all smoke-tested): `CHGDRYR`, `CHGSNGL`, `CHGBLKS`, `CHGMACL` |
| `CHGPROG` | 4-digit O-number, e.g. `8112` | **Folder-scoped.** Only finds programs in the current telnet data directory. Not available during operation; Edit mode may return `31`. Not yet a named client method (scripts only). |
| `MEMSTRT` | Optional 4-digit O-number, e.g. `8100` | Starts memory operation; with a number, bypasses external PRO select signals |
| `MEMSTOP` | `ON` / `OFF` | Latches feed-hold when `ON` — must send `OFF` (or clear on panel) to resume |
| `MEMQTST` | Optional 4-digit O-number | External start variant (pallet-param fallback if omitted); not smoke-tested |

### Folder ops (multipart)

| Command | Form | Notes |
|---------|------|-------|
| `FLDPWD` | Single-part, empty args | Returns cwd, e.g. `/\r\n…` or `/PROGRAM\r\n…` |
| `FLDCHG` | **Multipart**: empty args + payload folder name (`PROGRAM`) or `/` | Changes telnet data cwd. **Must restore `/` after** — otherwise `LOD MEM` fails with status `07` |

**Remote measure / probe sequence (stepped):** Shatter **EXECUTE** wizard confirms each stage in one dialog.
1. `POST .../probe/write` — write job macros only (no MEMSTRT)
2. Operator confirms success, then next step
3. `POST .../probe/start` — `CHGMODE MEM` → `FLDCHG PROGRAM` → `MEMSTRT` catalog target → `FLDCHG /`
4. Operator confirms motion started, then next step
5. `POST .../probe/collect` — wait idle → read `#100–#107` → poison (salt)

Live scripts:

- [`backend/scripts/test_chgprog.py`](../backend/scripts/test_chgprog.py) — `CHGMODE` / `FLDCHG` / `CHGPROG` (no start)
- [`backend/scripts/test_measure_tools.py`](../backend/scripts/test_measure_tools.py) — sequential `#920` + `MEMSTRT` measure cycles
- [`backend/scripts/test_optstop.py`](../backend/scripts/test_optstop.py) — `CHGOPTS` ON/OFF (PANEL `opt_stop`)

### Probe cycle API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/machines/{id}/probe/catalog` | Blum routine catalog (`#900–#907`, O81xx/O82xx) |
| `POST` | `/api/machines/{id}/probe/write` | Write job macros only — **no motion** |
| `POST` | `/api/machines/{id}/probe/start` | **MEMSTRT** catalog target O-number (allowlisted). Machine moves. |
| `POST` | `/api/machines/{id}/probe/collect` | Wait idle, read `#100–#107`, poison |
| `POST` | `/api/machines/{id}/probe/poison` | Force sentinel macros (`#900=0`, `#901–#907=999`, `#908=0`, `#920=0`) |

Catalog source: [`backend/app/data/probe_catalog.json`](../backend/app/data/probe_catalog.json) (mirrored in frontend). UI: **Probes** pane — **EXECUTE** opens a confirm wizard (write macros → start motion → collect + salt). O8099 gate/M98 is abandoned (`docs/nc/O8099.NC` kept as archive only).

**Live smoke (C00):** stop backend, `POST .../probe/write`, confirm, `POST .../probe/start` for target O81xx, then `POST .../probe/collect`. Restart backend afterward.

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

Telnet file upload (SAV), auto-notification (SNC/SND), and most directory variants (DRQSEL, DRQPRAL). File upload/download in Shatter uses **FTP**, not telnet SAV.

`CHGPROG` / `CHGOPTS` and related panel-key commands remain script-validated only (not probe-cycle product APIs).

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
