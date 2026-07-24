# Shatter User Guide

Operator-facing overview of the Shatter web UI: fleet dashboard, program files, validation, and tool analytics. For install, see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md).

---

## Dashboard

### Fleet header

```
MACHINES: 5  │  RUNNING: 3  │  ONLINE: 4/5  │  WS CONNECTED
```

| Control | Action |
|---------|--------|
| **MACHINES** | Collapse expanded machine/compressor cards |
| **RUNNING** | Click opens **Running Summary** modal; hover shows quick popup |
| **ONLINE: n/total** | Hover shows **Machine Status** popup (duration + polling graph) |
| **WS CONNECTED** | WebSocket link to backend (live updates) |

Live updates use WebSocket ([WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md)). If disconnected, the UI falls back to REST polling.

### Machine cards

Each card shows:

- Connection status (online/offline) and run state (operating, idle, alarm, etc.)
- Active program name, cycle/cutting times when available
- Alarm indicators and recent polling success graph
- Actions: expand panes (tools, files, sync), edit machine, test connection

### Add / edit machines

From the dashboard add card or inline edit:

- **Required:** name, IP address
- **Common:** FTP username/password, poll interval, units (in/mm)
- **Validation tolerances:** diameter/length for tools; X/Y/Z for WCS — or use G-code defaults
- **FTP sync:** per-machine upload/download configs (see [FTP_SYNC_EXCLUSION_RULES.md](FTP_SYNC_EXCLUSION_RULES.md))

Use **Test Connection** before saving. Telnet (port 10000) is used for status; FTP for files.

### Summaries

**Running Summary** (click RUNNING):

- Time ranges: `1h`, `8h`, `24h`, `7d`
- Per machine: run time, percentage of window, polling visualization
- API: `GET /api/summary/running?time_range=24h`

**Machine Status popup** (hover ONLINE):

- Online/offline duration per machine/compressor
- Polling history for selected window
- API: `GET /api/summary/machines?time_range=8h`

If summaries are empty: confirm machines ran programs in the range, polling is enabled, and `GET /health` returns healthy.

---

## Programs and Files

Open **File Browser** from a machine card.

### Browse and transfer

- Navigate CNC FTP directories (breadcrumb path)
- View, download, and upload `.NC` files
- O-number programs (`O####.NC`) support validation and deployment

### Validate

1. Select an O-number file → **VALIDATE**
2. Backend downloads the file via FTP and runs the same checks as upload validation
3. Results show in the details panel: tool table, WCS offsets, pass/fail status

Validation compares **program metadata** (from G-code comments) to **live machine data** (ATC tools via telnet, work offsets via POSNI).

### Deploy

After successful validation:

- **Deploy** writes the program to the machine (or records deployment history)
- **Deploy-validated** saves validation results with the deployment record
- Deployment history shows prior runs and validation snapshots

Re-validation is useful when tools or offsets change on the machine since the last upload.

### Validation algorithm

#### What is checked

**Tools**

- Each tool referenced in the program (T1, T2, …) vs ATC/tool table
- Status: `found`, `missing`, `mismatch`, `not_in_nc` (on machine but not in program)
- Diameter, length, description compared when metadata exists in the NC file

**Tolerance source (per machine):**

- `use_machine_tool_tolerances = true` → use machine `diameter_tolerance`, `length_tolerance_plus/minus`
- `false` (default) → diameter exact match; length must be ≥ required (no upper limit)

**Work coordinate systems (WCS)**

- G54–G59 offsets from program metadata vs machine POSNI data
- Status includes `found`, `mismatch`, or `xyz_not_parsed` when WCS not embedded in NC

**WCS tolerance source:**

- `use_machine_wcs_tolerances = true` → per-axis `tolerance_x/y/z` from machine settings
- `false` → use **E** parameter from NC verification block when present

#### Parser requirements

Programs must use the Brother Speedio post-processor comment formats Shatter extracts. See [NC_PARSER_GUIDE.md](NC_PARSER_GUIDE.md).

Implementation: [`programs.py`](../backend/app/api/programs.py), [`gcode_parser.py`](../backend/app/parsers/gcode_parser.py).

---

## Tool Management

The **Tools** page aggregates tool usage across deployed programs.

- Sortable tool list with usage counts
- **Tool detail** modal: specs, programs/operations, related alarms
- **Speed/feed analysis** per operation (when metadata present in NC)

Tool data on machine cards comes from telnet TOLN/ATCTL polling; analytics come from stored program metadata.

---

## Compressors

Kaeser SIGMA CONTROL 2 units appear as cards on the dashboard. Add via **[ ADD COMPRESSOR ]**. Details: [COMPRESSOR_INTEGRATION.md](COMPRESSOR_INTEGRATION.md).

---

## Notifications

Configure email/SMS channels and rules in Settings. Channel secrets are not shown after save. Delivery log shows send history.

---

## Related

- [NC_PARSER_GUIDE.md](NC_PARSER_GUIDE.md) — CAM post-processor requirements
- [FTP_SYNC_EXCLUSION_RULES.md](FTP_SYNC_EXCLUSION_RULES.md) — sync filename policy
- [SECURITY.md](../SECURITY.md) — network deployment model
