# Dashboard Workflows

## Table of Contents

- [Overview](#overview)
- [Fleet Overview Bar](#fleet-overview-bar)
  - [Overview Bar Layout](#overview-bar-layout)
  - [Hover Popups](#hover-popups)
  - [WebSocket Connection Status](#websocket-connection-status)
- [Machine Cards](#machine-cards)
  - [Card Layout](#card-layout)
  - [Status Display](#status-display)
  - [Alarm Indicators](#alarm-indicators)
  - [Tool Summary](#tool-summary)
  - [Polling Graph](#polling-graph)
  - [Action Buttons](#action-buttons)
- [Adding Machines](#adding-machines)
  - [Workflow Steps](#workflow-steps)
  - [Required Fields](#required-fields)
  - [Default Values](#default-values)
  - [Form Validation](#form-validation)
- [Editing Machines](#editing-machines)
  - [Enable Edit Mode](#enable-edit-mode)
  - [Inline Edit Form](#inline-edit-form)
  - [Network Configuration](#network-configuration)
  - [Validation Tolerances](#validation-tolerances)
  - [Test Connection](#test-connection)
  - [Save Changes](#save-changes)
- [Deleting Machines](#deleting-machines)
  - [Delete Workflow](#delete-workflow)
  - [Confirmation Modal](#confirmation-modal)
- [Summary Features](#summary-features)
  - [Running Summary](#running-summary)
  - [Online Summary](#online-summary)
  - [Offline Summary](#offline-summary)
  - [Time Range Selection](#time-range-selection)
- [Real-Time Updates](#real-time-updates)
  - [WebSocket Integration](#websocket-integration)
  - [Update Frequency](#update-frequency)
  - [Auto-Reconnect](#auto-reconnect)
- [Empty State](#empty-state)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **Dashboard** is the primary interface for monitoring CNC machine fleet status in real-time. It provides:

- **Fleet-wide statistics** - Total machines, running count, online count
- **Individual machine cards** - Status, cycle time, part counts, alarms
- **Real-time WebSocket updates** - Live data updates every 5 seconds
- **Machine management** - Add, edit, delete machines
- **Summary modals** - Detailed running/online/offline statistics

**Location:** [Dashboard.tsx](../frontend/src/pages/Dashboard.tsx)

**Target Users:**
- CNC machine operators
- Production supervisors
- Manufacturing engineers

---

## Fleet Overview Bar

### Overview Bar Layout

The Fleet Overview Bar displays aggregate statistics for all configured machines.

**Visual Layout:**

```
╔════════════════════════════════════════════════════════════════════╗
║  MACHINES: 5  |  RUNNING: 3  |  ONLINE: 4  |  ● WS CONNECTED      ║
╚════════════════════════════════════════════════════════════════════╝
```

**Metrics:**

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **MACHINES** | Total configured machines | Count of all machines in database |
| **RUNNING** | Machines currently running | Count where `is_online === true` AND `status` includes "Running" |
| **ONLINE** | Machines connected | Count where `is_online === true` |
| **WS CONNECTED** | WebSocket status | Green `●` if connected, Red `○` blinking if disconnected |

**Implementation:** [Dashboard.tsx:105-120](../frontend/src/pages/Dashboard.tsx#L105-L120)

```typescript
const onlineCount = machines.filter(m => m.is_online === true).length;
const runningCount = machines.filter(m =>
  m.is_online === true && m.status?.includes('Running')
).length;
```

---

### Hover Popups

Hovering over each metric displays a **detailed popup** with machine-specific information.

#### MACHINES Popup

Shows all machines with their current status and health metrics.

**Headers:** `MACHINE | DURATION | POLLING (1H) | UPTIME (8H) | HEALTH | POLLS`

**Example:**
```
╔═══════════════════════════════════════════════════════════════╗
║  MACHINE STATUS (4/5 ONLINE)                                  ║
╠═══════════════════════════════════════════════════════════════╣
║  MACHINE    | DURATION  | POLLING | UPTIME  | HEALTH | POLLS ║
╠═══════════════════════════════════════════════════════════════╣
║  HAAS-VF2   | 2h 15m    | ▓▓▓░    | 95.2%   | 99%    | 720  ║
║  HAAS-VF3   | 45m       | ▓▓▓▓    | 100.0%  | 100%   | 540  ║
║  BROTHER-S  | 1h 30m    | ▓▓░░    | 85.0%   | 90%    | 360  ║
║  DMG-DMU   | OFFLINE   | ░░░░    | 0.0%    | 0%     | 0    ║
╚═══════════════════════════════════════════════════════════════╝
```

**Metrics Explained:**
- **DURATION** - Time in current state (online/offline)
- **POLLING (1H)** - Visual graph of polling success in last hour
- **UPTIME (8H)** - Percentage of time online in last 8 hours
- **HEALTH** - Overall connection health percentage
- **POLLS** - Total successful polls in time window

**Location:** [SummaryPopup.tsx:149](../frontend/src/components/modals/SummaryPopup.tsx#L149)

---

#### RUNNING Popup

Shows machines that have been in "Running" status in the last 24 hours.

**Headers:** `MACHINE | RUN TIME | PERCENTAGE | LAST ACTIVE`

**Example:**
```
╔═══════════════════════════════════════════════════════════════╗
║  RUNNING MACHINES (24H)                                       ║
╠═══════════════════════════════════════════════════════════════╣
║  MACHINE    | RUN TIME | PERCENTAGE | LAST ACTIVE            ║
╠═══════════════════════════════════════════════════════════════╣
║  HAAS-VF2   | 18h 30m  | 77.1%      | 2m ago                 ║
║  HAAS-VF3   | 12h 15m  | 51.0%      | Running now            ║
║  BROTHER-S  | 6h 45m   | 28.1%      | 15m ago                ║
╚═══════════════════════════════════════════════════════════════╝
```

**Metrics Explained:**
- **RUN TIME** - Total time in "Running" status in last 24 hours
- **PERCENTAGE** - (Run time / 24 hours) × 100
- **LAST ACTIVE** - Time since last "Running" status or "Running now"

**Location:** [SummaryPopup.tsx:188-194](../frontend/src/components/modals/SummaryPopup.tsx#L188-L194)

---

#### ONLINE Popup

Shows currently connected machines with health metrics.

**Headers:** `MACHINE | ONLINE | HEALTH | SERVICES`

**Example:**
```
╔═══════════════════════════════════════════════════════════════╗
║  ONLINE MACHINES                                              ║
╠═══════════════════════════════════════════════════════════════╣
║  MACHINE    | ONLINE  | HEALTH | SERVICES                    ║
╠═══════════════════════════════════════════════════════════════╣
║  HAAS-VF2   | 2h 30m  | 99%    | HTTP ✓ FTP ✓               ║
║  HAAS-VF3   | 1h 15m  | 100%   | HTTP ✓ FTP ✓               ║
║  BROTHER-S  | 45m     | 95%    | HTTP ✓ FTP ✓               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Metrics Explained:**
- **ONLINE** - Duration machine has been continuously online
- **HEALTH** - Percentage of successful polls in current online session
- **SERVICES** - HTTP and FTP service status (✓ = working, ✕ = failed)

**Location:** [SummaryPopup.tsx:172-178](../frontend/src/components/modals/SummaryPopup.tsx#L172-L178)

---

### WebSocket Connection Status

The connection status indicator shows WebSocket connection state.

**States:**

| State | Display | Color | Meaning |
|-------|---------|-------|---------|
| Connected | `● WS CONNECTED` | Green | Receiving real-time updates |
| Disconnected | `○ WS DISCONNECTED` | Red (blinking) | Reconnecting in 5 seconds |

**Auto-Reconnect:**
- On disconnect, automatically reconnects after **5 seconds**
- Continues attempting until successful
- No manual intervention required

**Implementation:** [useWebSocket.ts:40-47](../frontend/src/hooks/useWebSocket.ts#L40-L47)

```typescript
ws.onclose = () => {
  console.log('[WS] Disconnected. Reconnecting in 5s...');
  setIsConnected(false);
  setTimeout(connect, 5000); // Auto-reconnect
};
```

---

## Machine Cards

### Card Layout

Each machine is displayed as a card showing real-time status.

**Example Card (Online, Running):**

```
╔══════════════════════════════════════════════════════════════╗
║  HAAS-VF2 (Running - Green Text)                     [=] [X] ║
├──────────────────────────────────────────────────────────────┤
║  STATUS:    Running (Green)                                  ║
║  PROGRAM:   O2045.NC                                         ║
║  CYCLE/PARTS: 01:23:45/1250                                  ║
║  ATC TOOLS: 12                                               ║
║  TOOL:      T05                                              ║
║  ALARMS:    0                                                ║
║  ────────────────────────────────────                        ║
║  [ UPLOAD & VALIDATE ]                                       ║
║  ────────────────────────────────────                        ║
║  POLLING GRAPH (1H):                                         ║
║  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░▓▓▓▓▓▓▓▓▓▓                              ║
║  ────────────────────────────────────                        ║
║  LAST UPDATE: 10:30:45 AM                                    ║
╚══════════════════════════════════════════════════════════════╝
```

**Note:** All status rows (STATUS, PROGRAM, CYCLE/PARTS, ATC TOOLS, ALARMS) are **hoverable and clickable**:
- **Hover** - Shows preview pane with relevant data (non-interactive)
- **Click** - Expands machine card to detail view and scrolls to relevant pane

**Example Card (Offline):**

```
╔══════════════════════════════════════════════════════════════╗
║  DMG-DMU (Offline - Red Text)                        [=] [X] ║
├──────────────────────────────────────────────────────────────┤
║  OFFLINE (Red)                                               ║
║  Connection timeout                                          ║
║  ────────────────────────────────────                        ║
║  LAST SEEN: 9:15:30 AM                                       ║
╚══════════════════════════════════════════════════════════════╝
```

**Location:** [MachineCard.tsx:269-678](../frontend/src/components/MachineCard.tsx#L269-L678)

---

### Status Display

Machine name color changes based on status:

| Status | Color | Condition |
|--------|-------|-----------|
| **Running** | Green (glowing) | `is_online === true` AND `status` includes "Running" |
| **Idle** | Gray (muted) | `is_online === true` AND `status` does NOT include "Running" |
| **Offline** | Red (error) | `is_online === false` |
| **Error** | Red (error) | `is_online === true` AND `status` includes "Error" |

**Implementation:** [MachineCard.tsx:221-226](../frontend/src/components/MachineCard.tsx#L221-L226)

```typescript
const getStatusType = () => {
  if (!machine.is_online) return 'offline';
  if (machine.status?.includes('Error')) return 'error';
  if (machine.status?.includes('Running')) return 'running';
  return 'idle';
};
```

**Status Fields (in order):**

- **STATUS** - Current machine status (e.g., "Running", "Stopped", "Error")
  - **Hover:** Shows compressed StatusTimeline preview
  - **Click:** Expands card, scrolls to status timeline pane
- **PROGRAM** - Current program name (e.g., "O2045.NC" or "NONE")
  - **Hover:** Shows CurrentProgramPane preview
  - **Click:** Expands card, scrolls to current program pane
- **CYCLE/PARTS** - Cycle time (format: `HH:MM:SS`) and part counter value (format: `HH:MM:SS/nnnn`)
  - **Hover:** Shows CycleHistoryPane preview
  - **Click:** Expands card, scrolls to cycle history pane
- **ATC TOOLS** - Tool count in ATC (e.g., "12")
  - **Hover:** Shows ToolsPane preview
  - **Click:** Expands card, scrolls to tools pane
- **TOOL** - Current active tool (format: `T##`, shown if available)
- **ALARMS** - Active alarm count (e.g., "0" or "3", displayed in red if >0)
  - **Hover:** Shows AlarmPane preview (if alarms > 0)
  - **Click:** Expands card, scrolls to alarm pane

---

### Alarm Display

When a machine has active alarms, the alarm count is displayed in the lower section of the card.

**Visual:**

```
║  ALARMS:    3                                                ║
```

The alarm count is displayed in **red** when there are active alarms (>0).

**Hover Behavior:**
- If alarms > 0, hovering shows AlarmPane preview (non-interactive)
- Positioned dynamically to stay within viewport

**Click Behavior:**
- Expands machine card to detail view (if not already expanded)
- Scrolls to alarm pane in expanded view
- Highlights alarm pane briefly with green glow animation

**Implementation:** [MachineCard.tsx:1132-1200](../frontend/src/components/MachineCard.tsx#L1132-L1200)

---

### Tool Summary

If the machine has tools loaded in the ATC (Automatic Tool Changer), a tool summary is displayed in the main status section.

**Visual:**

```
TOOLS: 12 IN ATC [VIEW]
```

**Hover Behavior:**
- Shows **ToolsPane** preview (non-interactive)
- Displays tool table with search, sort, and ATC/Table source toggle
- Positioned dynamically to stay within viewport

**Click Behavior:**
- Expands machine card to detail view (if not already expanded)
- Scrolls to tools pane in expanded view
- Highlights tools pane briefly with green glow animation

**Location:** [MachineCard.tsx:1030-1171](../frontend/src/components/MachineCard.tsx#L1030-L1171)

**Related:** See [Machine Detail View](#machine-detail-view) for expanded tools pane features

---

### Polling Graph

A 30-character ASCII visualization showing polling success/failure in the last hour.

**Visual:**

```
POLLING GRAPH (1H):
▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░▓▓▓▓▓▓▓▓▓▓
```

**Symbols:**
- `▓` - Successful poll
- `░` - Failed poll / timeout

**Time Window:** Last 60 minutes (1 poll every 2 minutes = 30 characters)

**Purpose:**
- Quickly visualize connection stability
- Identify intermittent connection issues
- Spot patterns (e.g., network congestion at certain times)

**Design Decision:**
- 30 characters chosen for compact display
- 2-minute granularity provides good overview without clutter

---

### Action Buttons

#### Upload & Validate Button

**Location:** Machine card (online machines only)

**Action:** Opens file picker to upload G-code file for validation

**Workflow:**
1. Click `[ UPLOAD & VALIDATE ]` button
2. Select `.nc` or `.NC` file from local filesystem
3. File automatically uploads and validates against machine state
4. **UploadConfirmationModal** opens with collapsable validation results
5. Review validation and click `[ UPLOAD ]` to deploy with FIFO O-number assignment

**Validation Process:**
1. Parse G-code to extract tools and WCS offsets
2. **Always query machine** for current tool list and WCS offsets (even if not found in NC)
3. Validate:
   - All tools in program exist in machine
   - Tool diameters match within tolerance (from machine database settings)
   - Tool lengths match within tolerance (from machine database settings)
   - WCS offsets match within tolerance (from NC file E parameter, or machine settings)
4. Display validation results in collapsable tables:
   - **Tools**: Summary row with expand icon (▶/▼), click to see Length/Diameter details
   - **WCS**: Summary row with expand icon, click to see X/Y/Z axis details
   - **Missing Data**: Shows "XYZ NOT PARSED" for WCS or "N/A" for tools not referenced in NC, with machine actual values displayed
5. Display errors, warnings, and validation summary

**Validation Display:**
- **Collapsable Tables**: Click tool or WCS rows to expand/collapse detailed breakdowns
- **Machine Data Always Shown**: Even when NC doesn't contain tool/WCS data, machine values are displayed for reference
- **Status Indicators**: ✓ (pass), ⚠ (warning), ✕ (fail), ─ (not in NC)

**Related Documentation:**
- See [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md) for validation algorithm
- See [FILE_BROWSER_WORKFLOWS.md](./FILE_BROWSER_WORKFLOWS.md) for file browser validation

**Implementation:** [MachineCard.tsx:228-262](../frontend/src/components/MachineCard.tsx#L228-L262)

---

#### Edit Button ([=])

**Location:** Machine card header (only in edit mode)

**Action:** Transform card into inline edit form

**Workflow:** See [Editing Machines](#editing-machines) section

---

#### Delete Button ([X])

**Location:** Machine card header (only in edit mode)

**Action:** Delete machine from database and stop monitoring

**Workflow:** See [Deleting Machines](#deleting-machines) section

---

## Adding Machines

### Workflow Steps

**Step 1: Enable Edit Mode**

Click the `[ EDIT MODE ]` button in the Dashboard toolbar.

**Step 2: Click Add Machine Card**

A special "Add Machine" card appears at the end of the machine grid:

```
╔══════════════════════════════════════════════════════════════╗
║                            +                                 ║
║                      [ ADD MACHINE ]                         ║
╚══════════════════════════════════════════════════════════════╝
```

Click the card to activate the add machine form.

**Step 3: Fill Form**

The card transforms into an editable form:

```
╔══════════════════════════════════════════════════════════════╗
║  NEW MACHINE                                         [✓] [X] ║
├──────────────────────────────────────────────────────────────┤
║  IP:           192.168.1.100                                 ║
║  FTP USER:     anonymous                                     ║
║  FTP PASS:     ••••••••••                                    ║
║  FTP PATH:     /PROGRAM                                      ║
║  FTP PORT:     21          HTTP PORT:     80                 ║
║  POLL INTERVAL: 5 seconds  [✓] ENABLED                       ║
║                                                              ║
║  [ CANCEL ]                              [ SAVE ]            ║
╚══════════════════════════════════════════════════════════════╝
```

**Step 4: Save**

- Click `[✓]` button in header OR `[ SAVE ]` button at bottom
- Machine is created in database
- Polling service automatically starts monitoring
- Card appears in main grid with "Offline" status initially
- First poll happens within 5 seconds

**Step 5: Verify Connection**

Wait for first poll (5 seconds). Machine should transition from "Offline" to "Online" if configured correctly.

**Location:** [AddMachineCard.tsx:24-289](../frontend/src/components/AddMachineCard.tsx#L24-L289)

---

### Required Fields

| Field | Description | Example | Validation |
|-------|-------------|---------|------------|
| **Machine Name** | Unique identifier | `HAAS-VF2` | Required, must be unique |
| **IP Address** | Machine IPv4/IPv6 | `192.168.1.100` | Required, valid IP format |
| **FTP Username** | FTP login username | `anonymous` | Required |
| **FTP Password** | FTP login password | `anonymous` | Required |

---

### Default Values

Pre-filled defaults for optional fields:

| Field | Default | Reason |
|-------|---------|--------|
| **FTP Port** | `21` | Standard FTP port |
| **HTTP Port** | `80` | Standard HTTP port |
| **FTP Path** | `/PROGRAM` | Common CNC program directory |
| **Poll Interval** | `5` seconds | Balance between freshness and load |
| **Enabled** | `true` | Start monitoring immediately |
| **Model** | `Brother CNC` | Default machine model |

**Location:** [AddMachineCard.tsx:28-39](../frontend/src/components/AddMachineCard.tsx#L28-L39)

---

### Form Validation

**Client-Side Validation:**

```typescript
const isFormValid = formData.name &&
                   formData.ip_address &&
                   formData.ftp_username &&
                   formData.ftp_password;
```

- **Required fields** must be non-empty
- Save button disabled until form is valid
- Visual feedback: disabled button appears grayed out

**Server-Side Validation:**

- **Unique name** - Enforced by database unique constraint
- **Valid IP format** - Validated by backend
- **Connectivity** - Not validated on create (use Test Connection)

**Error Handling:**

If save fails:
1. Error message displayed in card: `ERROR: Failed to create machine - Duplicate name`
2. Form remains editable
3. User can correct and retry

**Location:** [AddMachineCard.tsx:41-98](../frontend/src/components/AddMachineCard.tsx#L41-L98)

---

## Editing Machines

### Enable Edit Mode

**Step 1:** Click `[ EDIT MODE ]` button in Dashboard toolbar

**Effect:**
- All machine cards show `[=]` (edit) and `[X]` (delete) buttons
- "Add Machine" card appears

**Step 2:** Click `[=]` button on a machine card

**Effect:**
- Card transforms into inline edit form
- All fields become editable
- Machine continues being polled in background (no interruption)

---

### Inline Edit Form

The machine card transforms into a comprehensive edit form with two sections:

#### Section 1: Network Configuration

```
╔══════════════════════════════════════════════════════════════╗
║  HAAS-VF2                                            [✓] [X] ║
├──────────────────────────────────────────────────────────────┤
║  NETWORK CONFIGURATION                                       ║
║                                                              ║
║  IP:           192.168.1.100                                 ║
║  FTP USER:     haas                                          ║
║  FTP PASS:     ••••••••                                      ║
║  FTP PATH:     /PROGRAM                                      ║
║  FTP PORT:     21          HTTP PORT:     80                 ║
║  POLL INTERVAL: 5 seconds  [✓] ENABLED                       ║
╚══════════════════════════════════════════════════════════════╝
```

#### Section 2: Validation Tolerances

```
╔══════════════════════════════════════════════════════════════╗
║  VALIDATION TOLERANCES (inches)                              ║
║                                                              ║
║  TOOL DIAMETER                                               ║
║    (±): 0.010                                                ║
║                                                              ║
║  TOOL LENGTH                                                 ║
║    (+): 0.02          (-): 0.0                               ║
║                                                              ║
║  WCS OFFSET                                                  ║
║    X (±): 0.0394     Y (±): 0.0394     Z (±): 0.0394         ║
║                                                              ║
║  [ TEST CONNECTION ]      [ CANCEL ]           [ SAVE ]      ║
╚══════════════════════════════════════════════════════════════╝
```

**Location:** [MachineCard.tsx:329-555](../frontend/src/components/MachineCard.tsx#L329-L555)

---

### Network Configuration

**Editable Fields:**

| Field | Type | Purpose |
|-------|------|---------|
| **IP Address** | Text | Machine network address |
| **FTP Username** | Text | FTP server login |
| **FTP Password** | Password | FTP server password (masked) |
| **FTP Path** | Text | Root directory for programs (default: `/PROGRAM`) |
| **FTP Port** | Number (1-65535) | FTP server port (default: 21) |
| **HTTP Port** | Number (1-65535) | HTTP server port (default: 80) |
| **Poll Interval** | Number (1-300 seconds) | How often to poll machine (default: 5) |
| **Enabled** | Checkbox | Whether to actively monitor this machine |

**Port Validation:**
- Range: 1-65535
- Common defaults: FTP=21, HTTP=80

**Poll Interval Limits:**
- Minimum: 1 second (not recommended - high load)
- Maximum: 300 seconds (5 minutes)
- Recommended: 5-10 seconds

---

### Validation Tolerances

Tolerances used when validating G-code programs against machine state.

**Tolerance Source Control:**

Each machine can be configured to use either machine-defined tolerances or G-code defaults, controlled by toggle checkboxes in the machine configuration:

- **Use Machine Settings (checked)**: Use tolerance values defined in the machine configuration
- **Use G-code Defaults (unchecked)**: Use validation rules from the G-code program

**Tool Tolerances:**
- **Machine Settings**: Uses `diameter_tolerance`, `length_tolerance_plus`, `length_tolerance_minus` from machine configuration
- **G-code Defaults**: 
  - Diameter: Exact match required (difference < 0.0001")
  - Length: Tool must be at least as long as required (length ≥ required, no upper limit)

**WCS Tolerances:**
- **Machine Settings**: Uses `tolerance_x`, `tolerance_y`, `tolerance_z` from machine configuration
- **G-code Defaults**: Uses E parameter from WCS validation macro in G-code (e.g., `G65 P8901 ... E0.01 ...`). If E parameter is missing, validation fails with a warning.

**Default Behavior:** New machines start with both tolerance overrides disabled (unchecked), meaning G-code defaults are used by default.

#### Tool Diameter Tolerance

```
TOOL DIAMETER
  (±): 0.010
```

**Purpose:** Allow small deviations in tool diameter measurements

**Example:**
- Program expects: 0.5000" diameter
- Machine reports: 0.4995" diameter
- Difference: 0.0005" < 0.010" tolerance → **PASS**

---

#### Tool Length Tolerance

```
TOOL LENGTH
  (+): 0.02          (-): 0.0
```

**Purpose:** Allow asymmetric tolerance (tools can be longer, not shorter)

**Example:**
- Program expects: 3.000" length
- Machine reports: 3.015" length
- Difference: +0.015" < +0.02" tolerance → **PASS**
- Machine reports: 2.995" length
- Difference: -0.005" > -0.0" tolerance → **FAIL** (too short)

**Rationale:** Tools wear down (get shorter) over time. A shorter tool may not reach the workpiece, causing scrapped parts. A slightly longer tool is safer.

---

#### WCS Offset Tolerance

```
WCS OFFSET
  X (±): 0.0394     Y (±): 0.0394     Z (±): 0.0394
```

**Purpose:** Allow small deviations in work coordinate system offsets

**Default:** ±0.0394" (1 millimeter converted to inches)

**Example:**
- Program expects: X = 10.0000"
- Machine reports: X = 10.0385"
- Difference: 0.0385" < 0.0394" tolerance → **PASS**

**Per-Axis Tolerance:** Different tolerances can be set for X, Y, Z axes if needed.

**Location:** [MachineCard.tsx:443-524](../frontend/src/components/MachineCard.tsx#L443-L524)

---

### Test Connection

Before saving changes, test connectivity to ensure configuration is valid.

**Button:** `[ TEST CONNECTION ]`

**Action:**
1. Sends `POST /api/machines/{id}/test` request
2. Backend tests both HTTP and FTP connectivity
3. Returns success/failure for each service

**Success Response:**

```
Connection successful!
```

**Failure Response:**

```
Connection test failed: HTTP: Connection timeout, FTP: Authentication failed
```

**Implementation:** [MachineCard.tsx:179-219](../frontend/src/components/MachineCard.tsx#L179-L219)

```typescript
const handleEditTestConnection = async () => {
  setIsEditTesting(true);
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}/test`, {
      method: 'POST',
    });

    if (response.ok) {
      const result = await response.json();

      if (result.overall_status === 'online') {
        setEditTestResult(result);
      } else {
        const errors = [];
        if (!result.http?.success) {
          errors.push(`HTTP: ${result.http?.error || 'Connection failed'}`);
        }
        if (!result.ftp?.success) {
          errors.push(`FTP: ${result.ftp?.error || 'Connection failed'}`);
        }
        setEditError(`Connection test failed: ${errors.join(', ')}`);
      }
    }
  } catch (err) {
    setEditError(`Test failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
  } finally {
    setIsEditTesting(false);
  }
};
```

**Related API Endpoint:** [API_REFERENCE.md - Test Connection](./API_REFERENCE.md#post-apimachinesmachine_idtest)

---

### Save Changes

**Button:** `[ SAVE ]` or `[✓]` (header)

**Action:**
1. Validate all required fields are filled
2. Send `PUT /api/machines/{id}` request with updated configuration
3. Backend updates database
4. PollingService automatically picks up new configuration on next poll
5. Display success message: `Machine updated successfully!`
6. Auto-close edit form after 1.5 seconds

**Error Handling:**

If save fails:
1. Display error in form: `Save failed: Duplicate name`
2. Form remains open for corrections
3. User can retry or cancel

**Implementation:** [MachineCard.tsx:121-153](../frontend/src/components/MachineCard.tsx#L121-L153)

```typescript
const handleEditSave = async () => {
  if (!editFormValid) {
    setEditError('Please fill in all required fields');
    return;
  }

  setIsEditSaving(true);
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editFormData),
    });

    if (!response.ok) {
      throw new Error(`Update failed: ${response.statusText}`);
    }

    setEditSuccess(true);
    setTimeout(() => {
      setIsEditing(false);
      setEditSuccess(false);
    }, 1500);
  } catch (error) {
    setEditError(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    setIsEditSaving(false);
  }
};
```

---

## Deleting Machines

### Delete Workflow

**Step 1: Enable Edit Mode**

Click `[ EDIT MODE ]` button in Dashboard toolbar.

**Step 2: Click Delete Button**

Click `[X]` button on machine card header.

**Step 3: Confirmation Modal**

A dramatic confirmation modal appears:

---

### Confirmation Modal

**Visual:**

```
╔════════════════════════════════════════════════════════════════╗
║  ⚠ CONFIRM DELETION ⚠                                          ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║            _.-^^---....,,--                                    ║
║        _--                  --_                                ║
║       <                        >)                              ║
║       |                         |                              ║
║        \._                   _./                               ║
║           ```--. . , ; .--'''                                  ║
║                 | |   |                                        ║
║              .-=||  | |=-.                                     ║
║              `-=#$%&%$#=-'                                     ║
║                 | ;  :|                                        ║
║        _____.,-#%&$@%#&#~,._____                               ║
║                                                                ║
║            DEFCON 1 - MACHINE TERMINATION                      ║
║                                                                ║
║  TARGET: "HAAS-VF2"                                            ║
║                                                                ║
║  WARNING: THIS ACTION CANNOT BE UNDONE.                        ║
║  MACHINE WILL STOP BEING MONITORED IMMEDIATELY.                ║
║                                                                ║
║  PROCEED WITH DELETION?                                        ║
║                                                                ║
║  [ CANCEL ]                              [ DELETE ]            ║
╚════════════════════════════════════════════════════════════════╝
```

**ASCII Art Variations:**

The modal randomly displays one of 5 different ASCII art nuclear bomb/explosion scenes:
1. Mushroom cloud nuke
2. Dr. Strangelove riding the bomb
3. Explosion impact
4. Missile launch
5. Target crosshairs with nuke

**Location:** [DeleteConfirmModal.tsx:11-100](../frontend/src/components/DeleteConfirmModal.tsx#L11-L100)

**Step 4: Confirm or Cancel**

- **Cancel** - Close modal, no changes
- **Delete** - Permanently delete machine

**Delete Action:**
1. Send `DELETE /api/machines/{id}` request
2. Backend deletes machine from database
3. PollingService stops monitoring this machine
4. Machine card removed from Dashboard
5. WebSocket broadcasts removal to all clients

**Effects:**
- **Database** - Machine record deleted (CANNOT be undone)
- **History** - Machine status events retained in TimescaleDB for historical analysis
- **Programs** - Program deployments for this machine are orphaned but retained

**Implementation:** [DeleteConfirmModal.tsx:102-167](../frontend/src/components/DeleteConfirmModal.tsx#L102-L167)

**Design Decision:**

The dramatic confirmation modal with nuclear bomb ASCII art is intentionally over-the-top to:
1. Make users think twice before deleting
2. Add personality to the terminal aesthetic
3. Prevent accidental deletions

---

## Summary Features

### Running Summary

Displays machines that have been in "Running" status over a selected time range.

**Access:**
- Click `RUNNING: 3` in Fleet Overview Bar
- Hover popup appears (quick view)
- Click for full modal

**Time Ranges:**
- Last Hour
- Last 4 Hours
- Last 8 Hours
- Last 24 Hours (default)
- Last Week

**Data Displayed:**

| Column | Description | Example |
|--------|-------------|---------|
| **MACHINE** | Machine name | `HAAS-VF2` |
| **RUN TIME** | Total time in "Running" status | `18h 30m` |
| **PERCENTAGE** | (Run time / Time range) × 100 | `77.1%` |
| **LAST ACTIVE** | Time since last "Running" status | `2m ago` or `Running now` |
| **PROGRAM** | Active program O-number | `O2005` |

**Calculation:**

```typescript
// Query TimescaleDB machine_status_events
SELECT
  machine_id,
  SUM(duration) AS total_run_time
FROM machine_status_events
WHERE
  status LIKE '%Running%'
  AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY machine_id
ORDER BY total_run_time DESC
```

**Location:** [SummaryModal.tsx:146-153](../frontend/src/components/modals/SummaryModal.tsx#L146-L153)

**Related API:** `GET /api/summary/running?time_range=24h`

---

### Online Summary

Displays currently connected machines with health metrics.

**Access:**
- Click `ONLINE: 4` in Fleet Overview Bar
- Hover popup appears (quick view)
- Click for full modal

**Data Displayed:**

| Column | Description | Example |
|--------|-------------|---------|
| **MACHINE** | Machine name | `HAAS-VF2` |
| **ONLINE** | Duration continuously online | `2h 30m` |
| **HEALTH** | Successful poll percentage | `99%` |
| **SERVICES** | HTTP/FTP status | `HTTP ✓ FTP ✓` |
| **LAST SEEN** | Timestamp of last successful poll | `10:30:45 AM` |

**Health Calculation:**

```
Health = (Successful Polls / Total Poll Attempts) × 100
```

**Service Status:**
- `HTTP ✓` - HTTP endpoint responding
- `HTTP ✕` - HTTP endpoint failed
- `FTP ✓` - FTP server accessible
- `FTP ✕` - FTP authentication or connection failed

**Location:** [SummaryModal.tsx:155-161](../frontend/src/components/modals/SummaryModal.tsx#L155-L161)

**Related API:** `GET /api/summary/online`

---

### Offline Summary

Displays machines that are currently offline.

**Access:**
- Click offline count in Fleet Overview Bar (if any machines offline)
- Hover popup appears (quick view)
- Click for full modal

**Data Displayed:**

| Column | Description | Example |
|--------|-------------|---------|
| **MACHINE** | Machine name | `DMG-DMU` |
| **OFFLINE** | Duration continuously offline | `3h 15m` |
| **OFFLINE SINCE** | Timestamp when went offline | `7:15:30 AM` |
| **SERVICE ERRORS** | HTTP/FTP failure reasons | `HTTP: Timeout, FTP: Auth failed` |
| **LAST STATUS** | Last known status before offline | `Running` |

**Location:** [SummaryModal.tsx:163-169](../frontend/src/components/modals/SummaryModal.tsx#L163-L169)

**Related API:** `GET /api/summary/offline`

---

### Time Range Selection

**Available for:** Running Summary only

**Options:**
- `1h` - Last Hour
- `4h` - Last 4 Hours
- `8h` - Last 8 Hours
- `24h` - Last 24 Hours (default)
- `7d` - Last Week

**UI:**

```
[ 1H ]  [ 4H ]  [ 8H ]  [ 24H* ]  [ 7D ]
```

Active selection highlighted with `*`.

**Implementation:** [TimeRangeSelector.tsx](../frontend/src/components/modals/summary/TimeRangeSelector.tsx)

**Related Documentation:**
- See [DASHBOARD_SUMMARIES.md](./DASHBOARD_SUMMARIES.md) for detailed summary feature guide

---

## Real-Time Updates

### WebSocket Integration

The Dashboard receives real-time machine status updates via WebSocket.

**Connection:**
- Established on Dashboard mount: `useWebSocket(WS_URL)`
- WebSocket URL: `ws://localhost:8000/api/ws`
- Single connection shared across all Dashboard components

**Message Types:**

1. **initial_status** - Sent immediately on connect with all machines
2. **status_update** - Sent every poll interval (default 5 seconds) per machine

**Example Message:**

```json
{
  "type": "status_update",
  "timestamp": "2025-01-15T10:30:05.000Z",
  "data": {
    "machine_id": 1,
    "machine_name": "HAAS-VF2",
    "is_online": true,
    "status": "Running",
    "cycle_time": "0123:45:30.5",
    "power_on_hours": "12345:30:15.0",
    "counters": [{"counter_number": 1, "count": 1250}],
    "tools": [...],
    "current_tool": 5,
    "alarms": [],
    "poll_timestamp": "2025-01-15T10:30:05.000Z"
  }
}
```

**Location:** [useWebSocket.ts](../frontend/src/hooks/useWebSocket.ts)

**Related Documentation:**
- See [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md) for full protocol spec
- See [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) for WebSocket hook details

---

### Update Frequency

- **Default poll interval:** 5 seconds per machine
- **WebSocket broadcast:** Immediately after each poll completes
- **UI re-render:** Immediate (React state change triggers re-render)

**Performance:**
- 10 machines × 5-second interval = 2 updates/second
- Negligible impact on browser performance
- No throttling or debouncing currently implemented

---

### Auto-Reconnect

If WebSocket disconnects:

1. **UI Update** - Connection indicator changes to `○ WS DISCONNECTED` (red, blinking)
2. **Reconnect Attempt** - After 5 seconds
3. **Retry Loop** - Continues attempting every 5 seconds until successful
4. **Reconnect Success** - Receives `initial_status` message with all machines
5. **UI Update** - Connection indicator changes to `● WS CONNECTED` (green)

**No data loss** - Machines continue being polled on backend, updates resume once reconnected

**Location:** [useWebSocket.ts:40-47](../frontend/src/hooks/useWebSocket.ts#L40-L47)

---

## Empty State

When no machines are configured, an ASCII art empty state is displayed.

**Visual:**

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                        ___                                     ║
║                       /   \                                    ║
║                      |     |                                   ║
║                      |     |                                   ║
║                      |     |                                   ║
║                       \___/                                    ║
║                                                                ║
║                  NO MACHINES CONFIGURED                        ║
║                                                                ║
║     Click [ EDIT MODE ] and then [ ADD MACHINE ] to begin     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

**Location:** [AsciiEmptyState.tsx](../frontend/src/components/AsciiEmptyState.tsx)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Escape` | Close any open modal |
| `Escape` | Cancel edit/add machine form |

**Future Enhancements:**
- `Ctrl+E` - Toggle edit mode
- `Ctrl+A` - Add new machine
- Arrow keys - Navigate between machine cards

---

## Troubleshooting

### Machine Shows "Offline" But Should Be Online

**Possible Causes:**

1. **Network connectivity issue**
   - Check machine is powered on
   - Ping machine IP address: `ping 192.168.1.100`
   - Verify network cable connected

2. **Incorrect IP address**
   - Click `[=]` to edit machine
   - Verify IP address is correct
   - Click `[ TEST CONNECTION ]` to verify

3. **FTP credentials incorrect**
   - Edit machine and verify username/password
   - Try connecting manually with FTP client

4. **HTTP port incorrect**
   - Haas machines typically use port 80
   - Brother machines may use different ports
   - Check machine documentation

**Solution:** Edit machine configuration and test connection.

---

### Machine Status Not Updating

**Possible Causes:**

1. **WebSocket disconnected**
   - Check connection indicator: `● WS CONNECTED`
   - If red, wait 5 seconds for auto-reconnect

2. **Machine disabled**
   - Edit machine and verify `ENABLED` checkbox is checked

3. **Poll interval too long**
   - Default is 5 seconds
   - Edit machine to reduce interval (minimum 1 second)

**Solution:** Verify WebSocket connected and machine enabled.

---

### "Failed to create machine" Error When Adding

**Possible Causes:**

1. **Duplicate name**
   - Machine names must be unique
   - Try a different name

2. **Invalid IP address**
   - Must be valid IPv4 or IPv6 format
   - Example: `192.168.1.100`

3. **Database connection error**
   - Check backend logs
   - Verify PostgreSQL is running

**Solution:** Use unique name and valid IP format.

---

### Validation Failing for Known-Good Program

**Possible Causes:**

1. **Tolerances too tight**
   - Default diameter tolerance: ±0.010"
   - Default length tolerance: +0.02"/-0.0"
   - Edit machine to increase tolerances

2. **Tool offset not set in machine**
   - Manually measure and set tool offsets in machine control
   - Re-validate program

3. **WCS offset not set**
   - Set work coordinate system offsets in machine control
   - Re-validate program

**Solution:** Adjust tolerances or verify machine offsets are set correctly.

---

### Summary Modal Shows No Data

**Possible Causes:**

1. **No machines in requested state**
   - Running summary: No machines have been in "Running" status in time range
   - Online summary: All machines offline
   - Offline summary: All machines online

2. **Time range too narrow**
   - Try longer time range (24h or 7d)

3. **TimescaleDB data retention**
   - Status events older than 90 days are automatically deleted
   - Cannot query historical data beyond retention period

**Solution:** Adjust time range or verify machines are actually running/online/offline.

---

## Machine Detail View

Clicking on any status row (STATUS, PROGRAM, CYCLE/PARTS, TOOLS) or clicking the machine card itself expands it to a full detail view.

### Expanded Card Layout

The expanded card replaces the machine card in the grid and spans the full width of the dashboard.

**Layout Structure:**

```
╔═══════════════════════════════════════════════════════════════════════╗
║  HAAS-VF2                                           [COLLAPSE]        ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  ┌─ STATUS TIMELINE ───────────────────────────────────────────────┐  ║
║  │ [Oscilloscope visualization - see UX_DESIGN_GUIDE.md]          │  ║
║  └──────────────────────────────────────────────────────────────────┘  ║
║                                                                        ║
║  ┌─ ALARMS ───────────────┐  ┌─ CURRENT PROGRAM ──────────────────┐  ║
║  │ [Alarm list]            │  │ [Program info]                     │  ║
║  └─────────────────────────┘  └────────────────────────────────────┘  ║
║                                                                        ║
║  ┌─ TOOLS ────────────────┐  ┌─ CYCLE HISTORY ────────────────────┐  ║
║  │ [Tool table]           │  │ [Production runs]                   │  ║
║  └────────────────────────┘  └────────────────────────────────────┘  ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

### Panes

1. **Status Timeline** (Full width, top)
   - Oscilloscope visualization of status history
   - Configurable time ranges: 1H, 8H, 24H, 7D
   - See [UX_DESIGN_GUIDE.md](./UX_DESIGN_GUIDE.md#oscilloscope-display-status-timeline) for details

2. **Alarms Pane** (Left, top)
   - Two-column layout: Levels 2/3/4 (left), Level 1 info (right)
   - Color-coded by severity
   - Dense display with scrollable content
   - Expandable to modal for full view

3. **Current Program Pane** (Right, top)
   - Shows currently deployed program
   - Deployment timestamp and validation status
   - Expandable to modal for full view

4. **Tools Pane** (Left, bottom)
   - HTML table with search and sort
   - Toggle between ATC (HTTP) and Table (FTP TOLNI1.NC) sources
   - Expandable in-place to full screen
   - See [TOOL_MANAGEMENT_WORKFLOWS.md](./TOOL_MANAGEMENT_WORKFLOWS.md) for details

5. **Cycle History Pane** (Right, bottom)
   - Production run history
   - Aggregated stats and recent runs
   - Expandable to modal for full view

### Hover Previews

On the collapsed machine card, hovering over status rows shows preview panes:
- **STATUS** → StatusTimeline preview
- **PROGRAM** → CurrentProgramPane preview
- **CYCLE/PARTS** → CycleHistoryPane preview
- **ATC TOOLS** → ToolsPane preview
- **ALARMS** → AlarmPane preview (if alarms > 0)

All preview panes are non-interactive and positioned dynamically to stay within viewport.

### Navigation

- **Click status row** → Expands card, scrolls to relevant pane, highlights briefly
- **Click card** → Expands to detail view
- **Click [COLLAPSE]** → Returns to collapsed card view
- **Click [EXPAND] on pane** → Opens pane content in modal (for Alarms, Program, History) or expands in-place (for Tools)

**Location:** [MachineCard.tsx:375-455](../frontend/src/components/MachineCard.tsx#L375-L455)

---

## Related Documentation

- [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) - React components and architecture
- [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md) - G-code validation algorithm
- [DASHBOARD_SUMMARIES.md](./DASHBOARD_SUMMARIES.md) - Summary feature detailed guide
- [FILE_BROWSER_WORKFLOWS.md](./FILE_BROWSER_WORKFLOWS.md) - File management workflows
- [API_REFERENCE.md](./API_REFERENCE.md) - Backend API endpoints
- [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md) - Real-time communication protocol
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - Data models and schema
