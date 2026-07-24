# Shatter User Guide

Operator-facing overview of the Shatter web UI: fleet dashboard, program files, validation, and tool analytics. For install, see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md).

---

## Beta mode

Several features require **beta mode**: rapid-click the **SHATTER v{version}** title in the header (10 clicks within 5 seconds). When active, nav shows **[ NOTIFY ]** and **[ TOOLS ]**, and machine edit exposes FTP sync and AUTO DETECT control version.

| Feature | Route / location | Beta required |
|---------|------------------|---------------|
| Tool Management | `/tools` | Yes |
| Notifications | `/notifications` | Yes |
| FTP sync (machine edit) | Dashboard → edit machine | Yes |
| Compressors, tablet kiosk | Dashboard, `/tablet/*` | No |

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
| **WS CONNECTED** | WebSocket link to backend (live updates); shows **WS DISCONNECTED** when down |

Live fleet updates use WebSocket ([WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md)). If the socket disconnects, the dashboard does **not** poll REST for machine status — you may see a loading screen (no data yet) or stale cached values until the socket reconnects. Running/online summary popups poll REST on their own while open.

### Machine cards

Each card shows:

- Connection status (online/offline) and run state from PRD3: `off`, `standby` (shown as **IDLE**), `operating`, `stopped`, `error`
- Active program name, cycle/cutting times when available
- Alarm indicators (separate from run state) and recent polling success graph
- Actions: expand panes (tools, files, sync in beta), edit machine, test connection

### Add / edit machines

From the dashboard add card or inline edit:

- **Required:** name, IP address
- **Common:** FTP username/password, poll interval, units (in/mm)
- **Validation tolerances:** diameter/length for tools; X/Y/Z for WCS — or use G-code defaults
- **FTP sync (beta):** enable **FTP SYNC** in edit form, then configure upload/download jobs (see [FTP_SYNC_EXCLUSION_RULES.md](FTP_SYNC_EXCLUSION_RULES.md))

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

Open **File Browser** from the nav (**`/files`**) or from a machine card / file manager pane. Deep links: `?machine=&file=&file_path=&path=`.

### Browse and transfer

- Navigate CNC FTP directories (breadcrumb path)
- View, download, and upload `.NC` files
- O-number programs (`O####.NC`) support validation and deployment

### Validate

1. Select an O-number file → **VALIDATE**
2. Backend downloads the file via FTP and runs the same checks as upload validation
3. Results show in the details panel: tool table, WCS offsets, pass/fail status

Validation compares **program metadata** (from G-code comments) to **live machine data** (ATC tools via telnet, work offsets via telnet POSNI).

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
- API fields: `available`, `diameter_match`, `length_sufficient` (UI shows **PASS** / **FAIL** per tool)
- Diameter, length, description compared when metadata exists in the NC file

**Tolerance source (per machine):**

- `use_machine_tool_tolerances = true` → use machine `diameter_tolerance`, `length_tolerance_plus/minus`
- `false` (default) → diameter exact match; length must be ≥ required (no upper limit)

**Work coordinate systems (WCS)**

- G54–G59 offsets from program metadata vs machine POSNI data (telnet)
- When WCS metadata is absent, UI shows **XYZ NOT PARSED** with machine G54 values for reference

**WCS tolerance source:**

- `use_machine_wcs_tolerances = true` → per-axis `tolerance_x/y/z` from machine settings
- `false` → use **E** parameter from NC verification block when present

#### Parser requirements

Programs must use the Brother Speedio post-processor comment formats Shatter extracts. See [NC_PARSER_GUIDE.md](NC_PARSER_GUIDE.md).

Implementation: [`programs.py`](../backend/app/api/programs.py), [`gcode_parser.py`](../backend/app/parsers/gcode_parser.py).

---

## Tool Management (beta)

The **Tools** page (`/tools`, beta mode required) aggregates tool usage across deployed programs.

- Sortable tool list with usage counts
- **Tool detail** modal: specs, programs/operations, related alarms
- **Speed/feed analysis** per operation (when metadata present in NC)

Tool data on machine cards comes from telnet TOLN/ATCTL polling; analytics come from stored program metadata.

---

## Compressors

Kaeser SIGMA CONTROL 2 units appear as cards on the dashboard. Add via **[ ADD COMPRESSOR ]**. Details: [COMPRESSOR_INTEGRATION.md](COMPRESSOR_INTEGRATION.md).

---

## Notifications (beta)

Configure email/SMS channels and rules at **`/notifications`** (beta mode required). Channel secrets are not shown after save. Delivery log shows send history.

---

## Related

- [NC_PARSER_GUIDE.md](NC_PARSER_GUIDE.md) — CAM post-processor requirements
- [FTP_SYNC_EXCLUSION_RULES.md](FTP_SYNC_EXCLUSION_RULES.md) — sync filename policy
- [SECURITY.md](../SECURITY.md) — network deployment model
