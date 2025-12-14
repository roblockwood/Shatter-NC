# File Browser Workflows

## Table of Contents

- [Overview](#overview)
- [Navigation Workflow](#navigation-workflow)
  - [Machine Selection](#machine-selection)
  - [Directory Browsing](#directory-browsing)
  - [Breadcrumb Path](#breadcrumb-path)
- [File Management](#file-management)
  - [Viewing Files](#viewing-files)
  - [Downloading Files](#downloading-files)
  - [Uploading Files](#uploading-files)
- [Program Validation Workflow](#program-validation-workflow)
  - [Validation Triggers](#validation-triggers)
  - [Validation Process](#validation-process)
  - [Validation Results Modal](#validation-results-modal)
  - [Tool Validation](#tool-validation)
  - [WCS Offset Validation](#wcs-offset-validation)
- [Deployment Workflow](#deployment-workflow)
  - [O-Number Assignment](#o-number-assignment)
  - [Deployment Process](#deployment-process)
  - [Deployment History](#deployment-history)
- [Re-Validation Feature](#re-validation-feature)
- [Deployment Details Panel](#deployment-details-panel)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **File Browser** provides FTP file management for CNC machines with integrated G-code validation and deployment capabilities.

**Key Features:**
- Browse FTP directories on CNC machines
- Download/upload G-code programs
- Validate programs against machine state (tools, WCS offsets)
- Deploy validated programs to O-numbers (O2000-O3999)
- View deployment history and re-validate programs
- Track program metadata (runtime, tools, line count)

**Location:** [FileBrowser.tsx](../frontend/src/pages/FileBrowser.tsx)

**Target Users:**
- CNC programmers
- Production engineers
- Setup operators

---

## Navigation Workflow

### Machine Selection

**Step 1:** Select machine from dropdown in the top bar

**Visual:**

```
╔════════════════════════════════════════════════════════════════╗
║  MACHINE: [HAAS-VF2 (192.168.1.100)  ▼] ● ONLINE              ║
╚════════════════════════════════════════════════════════════════╝
```

**Behavior:**
- Dropdown shows all configured machines with `NAME (IP)` format
- First machine auto-selected on page load
- Selecting a machine:
  1. Clears current file listing
  2. Fetches machine's configured FTP path (default: `/PROGRAM`)
  3. Loads file listing from FTP path

**Implementation:** [FileBrowser.tsx:159-187](../frontend/src/pages/FileBrowser.tsx#L159-L187)

---

### Directory Browsing

File listing displays directories and files in a table format.

**Visual:**

```
┌─ NC PROGRAMS (/CNC_MEM/) ──────────────────────────────────────┐
│                                                                │
│  NAME              │ SIZE     │ MODIFIED        │ ACTIONS     │
├────────────────────────────────────────────────────────────────┤
│  / ..              │ <DIR>    │                 │             │
│  / SUB_PROGRAMS    │ <DIR>    │ 2025-01-15 10:30│             │
│    O2000.NC        │ 15.2 KB  │ 2025-01-15 09:45│ [DL]        │
│  ► O2001.NC        │ 22.8 KB  │ 2025-01-15 10:15│ [DL]        │
│    O2002.NC        │ 8.5 KB   │ 2025-01-14 16:30│ [DL]        │
├────────────────────────────────────────────────────────────────┤
│  3 PROGRAMS │ TOTAL: 46.5 KB                                   │
└────────────────────────────────────────────────────────────────┘
```

**Sorting:**
- Directories listed first (alphabetically)
- Files listed second (alphabetically)
- Parent directory (`..`) always at top when not at root

**Icons:**
- `/` - Directory
- `►` - Selected file
- (space) - Unselected file

**Clicking Behavior:**
- **Directory** - Navigate into directory
- **`..` entry** - Navigate up one level
- **File** - Select file to show details panel

**Location:** [FileBrowser.tsx:381-400](../frontend/src/pages/FileBrowser.tsx#L381-L400)

---

### Breadcrumb Path

Currently, the path is displayed in the panel header but not clickable.

**Example:** `/CNC_MEM/SUB_PROGRAMS`

**Future Enhancement:** Clickable breadcrumbs for faster navigation:

```
┌─ NC PROGRAMS (/ > CNC_MEM > SUB_PROGRAMS) ─────────────────────┐
                   ↑          ↑
                   clickable to navigate
```

---

## File Management

### Viewing Files

**Trigger:** Click `[ VIEW CODE ]` button in file details panel

**Action:** Opens modal with full file contents

**Visual:**

```
╔════════════════════════════════════════════════════════════════╗
║  /PROGRAM/O2000.NC                                         [✕] ║
╠════════════════════════════════════════════════════════════════╣
║  SIZE: 15.23 KB  │  LINES: 523                                 ║
╠════════════════════════════════════════════════════════════════╣
║  1  %                                                           ║
║  2  O2000                                                       ║
║  3  (PROGRAM: TOP COVER)                                       ║
║  4  (POSTED: 2025-01-15)                                       ║
║  5  G90 G94 G17 G20                                            ║
║  6  G28 G91 Z0.0                                               ║
║  7  G90                                                         ║
║  ...                                                            ║
║  520  M30                                                       ║
║  521  %                                                         ║
╠════════════════════════════════════════════════════════════════╣
║  [ CLOSE ]                                                      ║
╚════════════════════════════════════════════════════════════════╝
```

**Features:**
- Line numbers
- Monospace font (terminal aesthetic)
- Scrollable content
- File size and line count statistics

**Future Enhancement:** Syntax highlighting for G-code keywords

**Location:** [FileBrowser.tsx:560-588](../frontend/src/pages/FileBrowser.tsx#L560-L588)

---

### Downloading Files

**Trigger:** Click `[DL]` button in file row OR `[ DOWNLOAD ]` button in details panel

**Action:** Downloads file to user's local machine

**Process:**
1. Click download button
2. Backend fetches file via FTP
3. File returned as blob
4. Browser download dialog opens
5. User chooses save location

**Implementation:** [FileBrowser.tsx:402-434](../frontend/src/pages/FileBrowser.tsx#L402-L434)

```typescript
const handleDownload = async (program: Program) => {
  const filePath = `${currentPath}/${program.name}`;
  const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/download?file_path=${encodeURIComponent(filePath)}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  // Create blob and download
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = program.name;
  link.click();
  window.URL.revokeObjectURL(downloadUrl);
};
```

**Error Handling:**
- FTP connection timeout → "FTP connection timeout - check machine network connectivity"
- FTP authentication failed → "FTP server connection refused - verify machine FTP service is running"
- File not found → "HTTP 404"

**Related API:** `GET /api/machines/{id}/download?file_path={path}`

---

### Uploading Files

**Trigger:** Hidden file input (not currently exposed in UI)

**Future Feature:** Upload button in toolbar

**Process:**
1. User selects local `.nc` file
2. Upload progress bar shown
3. File uploaded via FTP to machine
4. File listing refreshed
5. Uploaded file highlighted for 5 seconds

**Upload Progress Visual:**

```
╔════════════════════════════════════════════════════════════════╗
║  UPLOADING: TOP_COVER.NC  [████████░░] 80%                     ║
╚════════════════════════════════════════════════════════════════╝
```

**Implementation:** [FileBrowser.tsx:665-735](../frontend/src/pages/FileBrowser.tsx#L665-L735)

**Error Handling:**
- Network error → "Upload failed: Network error"
- FTP write permission denied → "Upload failed: Permission denied"
- Disk full → "Upload failed: No space left on device"

**Related API:** `POST /api/machines/{id}/upload?file_path={path}`

---

## Program Validation Workflow

### Validation Triggers

**Trigger 1: Manual Validation**

Click `[ VALIDATE ]` button in file details panel (O-number files only)

**Trigger 2: Upload & Validate (Dashboard)**

Upload file from Dashboard machine card → automatic validation

**O-Number Files Only:**

Validation is only available for files matching pattern: `O####.NC` (e.g., `O2000.NC`)

**Location:** [FileBrowser.tsx:590-658](../frontend/src/pages/FileBrowser.tsx#L590-L658)

---

### Validation Process

**Step-by-Step Process:**

1. **Download File** - Backend fetches G-code file via FTP
2. **Parse G-code** - Extract:
   - Tool numbers (from `T##` commands)
   - Tool diameters (from `D##` offsets)
   - Tool lengths (from `H##` offsets)
   - WCS offset number (from `G54-G59` commands)
   - WCS coordinates (from comments/parameters)
   - Estimated runtime
3. **Query Machine** - Always fetch current state (even if not in NC):
   - Tool list from HTTP endpoint (all available tools)
   - WCS offsets from POSNI1.NC file via FTP (all work offsets)
4. **Validate** - Compare program requirements against machine state:
   - **Tools** - All tools exist? Diameters match? Lengths sufficient?
   - **WCS Offsets** - WCS offset set? Coordinates within tolerance?
   - **Missing Data** - If tool/WCS not in NC, show machine data with "N/A" or "XYZ NOT PARSED" status
5. **Auto-Save** - Save validation results to database
6. **Display** - Show collapsable validation tables in file details panel
7. **Scroll to Results** - Auto-scroll to deployment section

**Performance:**
- Typical validation time: 2-5 seconds
- Depends on: File size, network latency, machine response time

**Implementation:**

```typescript
const handleValidate = async (program: Program) => {
  setValidationLoading(true);

  try {
    // Step 1-4: Validate the file
    const validateUrl = `${API_BASE_URL}/api/programs/machines/${selectedMachineId}/programs/validate-file?file_path=${encodeURIComponent(filePath)}`;
    const validateResponse = await fetch(validateUrl, { method: 'POST' });
    const validationData = await validateResponse.json();

    // Show fresh validation results
    setFreshValidation({
      validation: validationData.validation,
      gcode_content: validationData.gcode_content,
      timestamp: Date.now()
    });

    // Step 5: Save validation to database
    const deployUrl = `${API_BASE_URL}/api/programs/machines/${selectedMachineId}/programs/deploy-validated`;
    await fetch(deployUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deployed_filename: program.name,
        gcode_content: validationData.gcode_content,
        validation_results: validationData.validation
      })
    });

    // Step 6: Refresh deployment details
    await fetchDeploymentDetail(program);

    // Step 7: Scroll to results
    deploymentSectionRef.current?.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    setValidationError(`Validation failed: ${err.message}`);
  } finally {
    setValidationLoading(false);
  }
};
```

**Related Documentation:**
- See [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md) for detailed validation algorithm

---

### Validation Results Display

**Upload Flow:** Displayed in UploadConfirmationModal  
**File Browser:** Displayed inline in file details panel

**Visual (Collapsable Design):**

```
╔════════════════════════════════════════════════════════════════╗
║  TOP_COVER.NC                                    ✓ PASS  [✕]   ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  ┌─ TOOLS ─────────────────────────────────────────────────┐  ║
║  │ ST │ TOOL# │ ACTUAL │ EXPECTED │ DIFF │ TOL │ RESULT    │  ║
║  ├────────────────────────────────────────────────────────────┤ ║
║  │ ✓  │▶T01  │ Tool Name                    │ PASS        │  ║
║  │    │  Length  │ 3.25" │ 3.25" │ 0.00" │ - │ ✓         │  ║
║  │    │  Diameter│ 0.50" │ 0.50" │ 0.00" │ - │ ✓         │  ║
║  │ ⚠  │▶T05  │ Tool Name                    │ FAIL        │  ║
║  │ ✕  │  T10  │ NOT AVAILABLE               │ FAIL        │  ║
║  │ ─  │  T15  │ Ø0.25" L2.00" │ ──── │ ──── │ ─ │ N/A      │  ║
║  └────────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  ┌─ WCS OFFSET ─────────────────────────────────────────────┐   ║
║  │ ST │ OFFSET │ ACTUAL │ EXPECTED │ DIFF │ TOL │ RESULT   │   ║
║  ├────────────────────────────────────────────────────────────┤ ║
║  │ ✓  │▶G54   │ X/Y/Z Coordinates          │ PASS        │   ║
║  │    │  X     │ 10.0000"│ 10.0000"│ 0.0000"│±0.0394"│ ✓ │   ║
║  │    │  Y     │ -5.0000"│ -4.9998"│ 0.0002"│±0.0394"│ ✓ │   ║
║  │    │  Z     │ 2.0000" │ 2.0005" │ 0.0005"│±0.0394"│ ✓ │   ║
║  └────────────────────────────────────────────────────────────┘  ║
║                                                                ║
╠════════════════════════════════════════════════════════════════╣
║  [ CANCEL ]                                      [ UPLOAD ]   ║
╚════════════════════════════════════════════════════════════════╝
```

**Location:** 
- Upload: [UploadConfirmationModal.tsx](../frontend/src/components/UploadConfirmationModal.tsx)
- File Browser: [FileBrowser.tsx](../frontend/src/pages/FileBrowser.tsx#L1121-L1368)

**Sections:**

1. **Overall Status** - ✓ PASS or ✕ FAIL badge in header
2. **Program Info** - Lines, size, tools, runtime (upload flow only)
3. **Tool Validation** - Collapsable table:
   - Summary row with expand icon (▶/▼) - click to expand
   - Expanded rows show Length and Diameter breakdowns
   - Tools not in NC show "N/A" with machine actual values
4. **WCS Offset Validation** - Collapsable table:
   - Summary row with expand icon - click to expand
   - Expanded rows show X/Y/Z axis details
   - WCS not in NC shows "XYZ NOT PARSED" with machine G54 values
5. **Upload Footer** - Machine, path, O-number, buttons (upload flow only)

**Interaction:**
- Click summary rows (with ▶ icon) to expand/collapse detailed breakdowns
- Hover over clickable rows for visual feedback
- Expand icon changes: ▶ (collapsed) → ▼ (expanded)

---

### Tool Validation

**Validation Criteria:**

| Check | Description | Tolerance Source |
|-------|-------------|------------------|
| **Tool Exists** | Tool number loaded in machine ATC | N/A (must exist) |
| **Diameter Match** | Tool diameter within tolerance | **Machine database** (`diameter_tolerance` setting) |
| **Length Sufficient** | Tool length within asymmetric tolerance | **Machine database** (`length_tolerance_plus`/`length_tolerance_minus` settings) |

**Tolerance Display:**
- Tolerance values are shown in the **TOL** column when expanding tool details
- **Diameter**: Displays as `±X.XXXX"` (symmetric tolerance)
- **Length**: Displays as `+X.XXXX"/-X.XXXX"` (asymmetric tolerance)
- Values come from machine configuration, not from the NC program file

**Status Icons:**
- `✓` - Green - All checks passed
- `⚠` - Yellow - Tool exists but diameter/length mismatch
- `✕` - Red - Tool not loaded in machine
- `─` - Gray - Tool available on machine but not referenced in NC program

**Example Validations:**

**Pass:**
```
✓ T01 | Required: Ø0.5000" L3.2500" | Available: Ø0.5000" L3.2500" | ✓DIA ✓LEN
```

**Warning (tolerance exceeded):**
```
⚠ T05 | Required: Ø0.3750" L3.0000" | Available: Ø0.3755" L2.9950" | ⚠DIA ⚠LEN
  ⚠ Diameter 0.0005" over tolerance
  ⚠ Length 0.0050" under tolerance
```

**Missing:**
```
✕ T10 | Required: Ø0.1250" L2.5000" | NOT LOADED | MISSING
```

**Asymmetric Length Tolerance Rationale:**

Tools wear down (get shorter) over time. A shorter tool may not reach the workpiece, causing scrapped parts. A slightly longer tool is safer.

**Example:**
- Program expects: 3.000" length
- Tolerance: +0.02"/-0.0"
- Machine reports: 3.015" → **PASS** (within +0.02")
- Machine reports: 2.995" → **FAIL** (exceeds -0.0", too short)

**Location:** 
- Upload: [UploadConfirmationModal.tsx:305-432](../frontend/src/components/UploadConfirmationModal.tsx#L305-L432)
- File Browser: [FileBrowser.tsx:1121-1253](../frontend/src/pages/FileBrowser.tsx#L1121-L1253)

---

### WCS Offset Validation

**Work Coordinate System (WCS) Offsets:**

G-code programs reference workpiece coordinates (WCS) instead of machine coordinates. WCS offsets define the relationship between these coordinate systems.

**Common WCS Offsets:**
- **G54** - Work offset 1 (most common)
- **G55** - Work offset 2
- **G56** - Work offset 3
- **G57** - Work offset 4
- **G58** - Work offset 5
- **G59** - Work offset 6

**Validation Process:**

1. **Parse G-code** - Detect WCS offset number (e.g., `G54`) and expected coordinates
2. **Always Query Machine** - Fetch actual WCS offsets from POSNI1.NC file via FTP:
   - If WCS found in NC: Compare expected vs actual
   - If WCS NOT in NC: Display machine G54 data with "XYZ NOT PARSED" status
3. **Extract Expected Coordinates** - From comments or parameters:
   ```gcode
   (WCS G54: X10.0000 Y-5.0000 Z2.0000)
   ```
   - If not found: Show `────` for expected values, display machine actual values
4. **Compare** - Calculate difference per axis (if both available):
   ```
   difference_x = abs(expected_x - actual_x)
   ```
5. **Check Tolerance** - Difference must be within tolerance (if validation applicable)

**Validation Table:**

```
┌─ WCS OFFSET VALIDATION (G54) ────────────────────────────────┐
│ AXIS│EXPECTED │ACTUAL   │DIFF     │TOLERANCE│STATUS         │
├──────────────────────────────────────────────────────────────┤
│ X   │10.0000" │10.0000" │0.0000"  │±0.0394" │✓ OK           │
│ Y   │-5.0000" │-4.9998" │0.0002"  │±0.0394" │✓ OK           │
│ Z   │2.0000"  │2.0385"  │0.0385"  │±0.0394" │✓ OK           │
└──────────────────────────────────────────────────────────────┘
```

**Tolerance Source:**

WCS tolerances use a **priority system**:

1. **NC File E Parameter** (highest priority) - If WCS command includes `E` parameter:
   ```gcode
   G65 P8901 X10.0000 Y-5.0000 Z2.0000 E0.01 W54
   ```
   The `E0.01` value becomes the tolerance for all axes (uniform tolerance)

2. **Machine Database Settings** (fallback) - If no E parameter in NC file:
   - Uses per-axis tolerances from machine configuration
   - **X tolerance** - Default: ±0.0394"
   - **Y tolerance** - Default: ±0.0394"
   - **Z tolerance** - Default: ±0.0394"

**Tolerance Display:**
- Tolerance value shown in **TOL** column when expanding WCS details
- Displays as `±X.XXXX"` (uniform tolerance from E parameter, or max of per-axis tolerances)
- Source is indicated by whether E parameter was found in NC file

**Default Tolerance:** ±0.0394" (1 millimeter) when using machine settings

**Failure Example:**

```
┌─ WCS OFFSET VALIDATION (G54) ────────────────────────────────┐
│ AXIS│EXPECTED │ACTUAL   │DIFF     │TOLERANCE│STATUS         │
├──────────────────────────────────────────────────────────────┤
│ X   │10.0000" │10.0000" │0.0000"  │±0.0394" │✓ OK           │
│ Y   │-5.0000" │-4.9998" │0.0002"  │±0.0394" │✓ OK           │
│ Z   │2.0000"  │2.0500"  │0.0500"  │±0.0394" │✕ OUT         │
└──────────────────────────────────────────────────────────────┘

ERRORS:
✕ WCS OFFSET G54 OUT OF TOLERANCE
  Z-axis difference 0.0500" exceeds tolerance ±0.0394"
```

**Location:**
- Upload: [UploadConfirmationModal.tsx:434-625](../frontend/src/components/UploadConfirmationModal.tsx#L434-L625)
- File Browser: [FileBrowser.tsx:1255-1368](../frontend/src/pages/FileBrowser.tsx#L1255-L1368)

**Design Decision:**

WCS offset mismatches are considered **errors** (not warnings) because they can cause:
- Workpiece scrapping (incorrect zero point)
- Machine crashes (collision with fixtures)
- Safety hazards

**Related Documentation:**
- See [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md) for WCS parsing algorithm

---

## Deployment Workflow

### O-Number Assignment

**O-Number Range:** O2000 - O3999 (2000 available slots)

**Assignment Strategy:** FIFO (First In, First Out)

**How It Works:**

1. **User initiates upload/deployment** with filename
2. **Check for existing deployment** - If same filename already deployed on this machine:
   - Find most recent deployment for this filename
   - **Reuse existing O-number** (FIFO association)
   - Return `is_redeployment: true`
3. **If no existing deployment** - Find next available O-number:
   - Query for first unused O-number in range O2000-O3999
   - If pool not full: Return first available
   - If pool full: Return oldest O-number (FIFO replacement)
4. **Return O-number** to frontend with replacement info

**FIFO Association:**
- Same filename → Same O-number (reuses last deployment)
- Different filename → New O-number assignment
- Ensures consistent O-number mapping per filename per machine

**API:** `GET /api/programs/machines/{id}/next-onumber?filename={name}`

**Response (new O-number):**

```json
{
  "next_onumber": "O2005.nc",
  "onumber_int": 2005,
  "is_replacing": false,
  "replacement_info": null,
  "is_redeployment": false
}
```

**Response (reusing existing O-number for same filename):**

```json
{
  "next_onumber": "O2002.nc",
  "onumber_int": 2002,
  "is_replacing": false,
  "replacement_info": null,
  "is_redeployment": true
}
```

**Response (replacing existing):**

```json
{
  "next_onumber": "O2003.nc",
  "is_replacing": true,
  "replacement_info": {
    "original_filename": "TOP_COVER_V1.NC",
    "deployed_at": "2025-01-10T08:30:00Z",
    "deployed_filename": "O2003.nc"
  }
}
```

**UI Display:**

```
╔════════════════════════════════════════════════════════════════╗
║  O-NUMBER: [O2003.nc        ] REPLACING TOP_COVER_V1.NC        ║
╚════════════════════════════════════════════════════════════════╝
```

**Custom O-Number:**

Users can edit the O-number input before upload to choose a specific number.

**Validation:**
- Must match pattern: `O####.nc` (e.g., `O2500.nc`)
- Must be in range O2000-O3999
- If outside range or invalid format, backend rejects with error

**Location:** [ValidationResultModal.tsx:153-179](../frontend/src/components/ValidationResultModal.tsx#L153-L179)

---

### Deployment Process

**Full Deployment Workflow:**

**Step 1: Validate Program** (optional but recommended)

Click `[ VALIDATE ]` to ensure program is compatible with machine.

**Step 2: Upload & Deploy** (from Dashboard OR File Browser)

**From Dashboard:**
1. Click `[ UPLOAD & VALIDATE ]` on machine card
2. Select local `.nc` file
3. File validates automatically
4. ValidationResultModal opens

**From File Browser:**
1. Select O-number file (e.g., `O2000.NC`)
2. Click `[ VALIDATE ]`
3. Results shown in deployment panel (inline)

**Step 3: Confirm O-Number**

Review suggested O-number:
- Editable input field
- Shows "REPLACING ..." if overwriting existing program

**Step 4: Upload**

Click `[ UPLOAD ]` button in ValidationResultModal footer.

**If validation failed:**
- Confirmation modal appears
- Lists all errors and warnings
- User must confirm upload despite failures

**Step 5: Upload Progress**

Progress bar shows upload status:

```
╔════════════════════════════════════════════════════════════════╗
║  UPLOADING...                                                  ║
║  [████████████████░░░░░░] 80%                                  ║
╚════════════════════════════════════════════════════════════════╝
```

**Step 6: Success**

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ UPLOAD SUCCESSFUL                                           ║
║                                                                ║
║  DEPLOYED TO: /PROGRAM/O2005.nc                                ║
║  MACHINE:     HAAS-VF2                                         ║
║                                                                ║
║  [ AUTOCLOSE 5s ]                                              ║
╚════════════════════════════════════════════════════════════════╝
```

Modal auto-closes after 5 seconds with countdown. Click `[ PAUSE ]` to disable auto-close.

**Step 7: Database Record**

Backend creates database record:

```sql
INSERT INTO program_deployments (
  machine_id,
  program_id,
  deployed_filename,
  deployed_at,
  validation_passed,
  validation_results
) VALUES (?, ?, ?, NOW(), ?, ?)
```

**Step 8: FTP Upload**

File uploaded to machine via FTP:
- Path: `{machine.path}/{o_number}` (e.g., `/PROGRAM/O2005.nc`)
- Overwrites existing file if present
- Creates parent directories if needed

**Location:** [ValidationResultModal.tsx:181-268](../frontend/src/components/ValidationResultModal.tsx#L181-L268)

---

### Deployment History

**Access:** Select O-number file in File Browser

**Visual:**

```
┌─ DEPLOYMENT INFO ──────────────────────────────────────────────┐
│                                                                │
│  [TOP_COVER.NC (2025-01-15 10:30) - CURRENT          ▼]       │
│   TOP_COVER_V1.NC (2025-01-10 08:30)                           │
│   BRACKET.NC (2025-01-05 14:15)                                │
│                                                                │
│  DEPLOYED:      2025-01-15 10:30:45                            │
│  POSTED DATE:   2025-01-15                                     │
│  RUNTIME:       02:15:30                                       │
│  VALIDATION:    ✓ PASSED                                       │
└────────────────────────────────────────────────────────────────┘
```

**Functionality:**

1. **Dropdown** - Shows deployment history for this O-number
2. **Current Deployment** - Labeled "CURRENT"
3. **Historical Deployments** - Previous programs deployed to this O-number
4. **Select Historical** - Dropdown changes to show historical validation results

**Use Cases:**

- **Audit Trail** - See what was deployed when
- **Compare Versions** - View validation results from previous deployments
- **Rollback** - Identify previous program version to re-deploy

**Data Source:**

Query: `GET /api/programs/machines/{id}/deployments/by-onumber/{onumber}?include_history=true`

**Response:**

```json
{
  "deployment": {
    "id": 123,
    "deployed_filename": "O2000.nc",
    "deployed_at": "2025-01-15T10:30:45Z",
    "validation_passed": true,
    "validation_results": { /* full validation object */ }
  },
  "program": {
    "id": 456,
    "original_filename": "TOP_COVER.NC",
    "version_number": 3,
    "posted_date": "2025-01-15",
    "estimated_runtime_seconds": 8130
  },
  "history": [
    {
      "id": 123,
      "deployed_at": "2025-01-15T10:30:45Z",
      "is_current": true,
      "original_filename": "TOP_COVER.NC"
    },
    {
      "id": 110,
      "deployed_at": "2025-01-10T08:30:00Z",
      "is_current": false,
      "original_filename": "TOP_COVER_V1.NC"
    },
    {
      "id": 98,
      "deployed_at": "2025-01-05T14:15:30Z",
      "is_current": false,
      "original_filename": "BRACKET.NC"
    }
  ]
}
```

**Location:** [FileBrowser.tsx:272-285](../frontend/src/pages/FileBrowser.tsx#L272-L285)

---

## Re-Validation Feature

**Use Case:**

Machine state changes after initial validation:
- Tool changed/re-measured
- WCS offset adjusted
- New program uploaded to same O-number

Re-validate to ensure program is still compatible.

**Workflow:**

**Step 1:** Select O-number file (e.g., `O2000.NC`)

**Step 2:** Click `[ VALIDATE ]` button

**Step 3:** Backend process:
1. Downloads current file from machine FTP
2. Parses G-code
3. Queries current machine state (tools, WCS offsets)
4. Validates
5. Saves new validation results to database
6. Refreshes deployment panel

**Step 4:** Fresh validation results shown

**Visual:**

```
┌─ *FRESH* VALIDATION RESULTS ───────────────────────────────────┐
│  Validated: 10:45:30 AM                                        │
│                                                                │
│  STATUS:    ✓ PASSED                                           │
│                                                                │
│  TOOL DETAILS                                                  │
│  ... (validation results table) ...                            │
└────────────────────────────────────────────────────────────────┘
```

**Fresh vs Stored Results:**

- **Fresh** - Just validated, shown with green `*FRESH*` label
- **Stored** - Retrieved from database, shown in "DEPLOYMENT INFO"

**Fresh Validation Timeout:**

After 5 minutes, a warning appears:

```
! Validation is 6 minutes old. Machine state may have changed.
```

**Auto-Save Behavior:**

Fresh validation results automatically saved to database after display. This creates a new deployment record pointing to the same O-number.

**Design Decision:**

Re-validation creates a new deployment record rather than updating the existing one. This preserves the audit trail showing when each validation occurred.

**Location:** [FileBrowser.tsx:590-658](../frontend/src/pages/FileBrowser.tsx#L590-L658)

---

## Deployment Details Panel

When an O-number file is selected, the right panel shows comprehensive deployment information.

**Panel Sections:**

### 1. File Info

```
┌─ FILE INFO ────────────────────────────────────────────────────┐
│  SIZE:     15.2 KB                                             │
│  MODIFIED: 2025-01-15 10:30                                    │
└────────────────────────────────────────────────────────────────┘
```

### 2. Deployment Info

```
┌─ DEPLOYMENT INFO ──────────────────────────────────────────────┐
│  DEPLOYED:      2025-01-15 10:30:45                            │
│  POSTED DATE:   2025-01-15                                     │
│  RUNTIME:       02:15:30                                       │
│  VALIDATION:    ✓ PASSED                                       │
└────────────────────────────────────────────────────────────────┘
```

**If no deployment record:**
```
┌─ DEPLOYMENT INFO ──────────────────────────────────────────────┐
│  No deployment record found                                    │
└────────────────────────────────────────────────────────────────┘
```

### 3. Tool Details

```
┌─ TOOL DETAILS ─────────────────────────────────────────────────┐
│  T# │ REQ DIA    │ REQ LEN    │ AVAIL │ STATUS                │
├────────────────────────────────────────────────────────────────┤
│ T01 │ Ø0.5000"   │ 3.2500"    │ ✓     │ ✓ OK                  │
│ T02 │ Ø0.2500"   │ 2.7500"    │ ✓     │ ✓ OK                  │
│ T05 │ Ø0.3750"   │ 3.0000"    │ ✓     │ ⚠ WARN                │
│ T10 │ Ø0.1250"   │ 2.5000"    │ ✕     │ ✕ MISSING             │
└────────────────────────────────────────────────────────────────┘
```

### 4. WCS Offset

```
┌─ WCS OFFSET (G54) ─────────────────────────────────────────────┐
│ AXIS │ EXPECTED   │ ACTUAL     │ DIFF       │ STATUS          │
├────────────────────────────────────────────────────────────────┤
│ X    │ 10.0000"   │ 10.0000"   │ 0.0000"    │ ✓               │
│ Y    │ -5.0000"   │ -4.9998"   │ 0.0002"    │ ✓               │
│ Z    │ 2.0000"    │ 2.0005"    │ 0.0005"    │ ✓               │
└────────────────────────────────────────────────────────────────┘
```

### 5. Actions

```
[ DOWNLOAD ]  [ VIEW CODE ]  [ VALIDATE ]
```

### 6. Code Preview

```
┌─ PREVIEW (First 50 Lines) ─────────────────────────────────────┐
│  1  %                                                          │
│  2  O2000                                                      │
│  3  (PROGRAM: TOP COVER)                                       │
│  4  (POSTED: 2025-01-15)                                       │
│  ...                                                           │
└────────────────────────────────────────────────────────────────┘
```

**Location:** [FileBrowser.tsx:862-1184](../frontend/src/pages/FileBrowser.tsx#L862-L1184)

---

## Error Handling

### FTP Connection Errors

**Timeout:**
```
ERROR: FTP connection timeout - check machine network connectivity
```

**Causes:**
- Machine powered off
- Network cable disconnected
- Firewall blocking port 21
- Incorrect IP address

**Solution:** Verify network connectivity with `ping {machine_ip}`

---

**Connection Refused:**
```
ERROR: FTP server connection refused - verify machine FTP service is running
```

**Causes:**
- FTP service not enabled on machine
- FTP port changed from default 21
- Machine control software crashed

**Solution:** Enable FTP in machine control settings

---

**Authentication Failed:**
```
ERROR: FTP authentication failed - verify username/password
```

**Causes:**
- Incorrect FTP username
- Incorrect FTP password
- FTP anonymous access disabled but using "anonymous/anonymous"

**Solution:** Edit machine settings and verify credentials

---

### Validation Errors

**File Not Found:**
```
ERROR: Validation failed: HTTP 404
```

**Cause:** File was deleted or moved between selection and validation

**Solution:** Refresh file listing and try again

---

**Parse Error:**
```
ERROR: Validation failed: Failed to parse G-code
```

**Cause:** Invalid G-code syntax or unsupported format

**Solution:** Verify file is valid G-code (not a binary or compiled format)

---

**Machine Query Failed:**
```
ERROR: Validation failed: Failed to fetch machine tools
```

**Cause:** Machine HTTP endpoint not responding

**Solution:**
1. Verify machine is online
2. Test HTTP connectivity: `curl http://{machine_ip}/CURRENT/TOOL`
3. Check machine control software is running

---

### Upload Errors

**Network Error:**
```
✕ Upload failed: Network error
```

**Cause:** Connection lost during upload

**Solution:** Retry upload

---

**Permission Denied:**
```
✕ Upload failed: Permission denied
```

**Cause:** FTP user doesn't have write permission to target directory

**Solution:** Change FTP credentials to user with write access

---

**No Space Left:**
```
✕ Upload failed: No space left on device
```

**Cause:** Machine storage full

**Solution:** Delete old programs from machine to free space

---

## Troubleshooting

### File Browser Shows Empty

**Symptom:** File listing is empty when machine should have programs

**Possible Causes:**

1. **Wrong FTP path**
   - Default path: `/PROGRAM`
   - Some machines use: `/CNC_MEM`, `/USER`, `/NC_PROGRAM`
   - Solution: Edit machine and verify FTP path setting

2. **FTP root directory restriction**
   - Some machines restrict FTP to specific directories
   - Solution: Use relative path instead of absolute (e.g., `PROGRAM` not `/PROGRAM`)

3. **No programs actually exist**
   - Solution: Upload a test program to verify FTP write access

---

### Validation Always Fails

**Symptom:** All programs fail validation even though they ran successfully before

**Possible Causes:**

1. **Tolerances too tight**
   - Default diameter tolerance: ±0.010"
   - Default length tolerance: +0.02"/-0.0"
   - Default WCS tolerance: ±0.0394"
   - Solution: Edit machine tolerances to be more permissive

2. **Tool offsets not set**
   - Solution: Manually measure and set tool offsets in machine control

3. **WCS offsets not set**
   - Solution: Touch off workpiece and set WCS offsets in machine control

4. **Wrong WCS offset number**
   - Program expects G54, machine has G55 set
   - Solution: Update program to use correct WCS offset OR set offset in correct slot

---

### Upload Succeeds But File Not Visible

**Symptom:** Upload reports success, but file doesn't appear in file listing

**Possible Causes:**

1. **Uploaded to wrong directory**
   - Check FTP path setting
   - Solution: Download from expected path to verify

2. **File listing cache**
   - Solution: Change to different directory and back to refresh

3. **Machine control hasn't scanned for new files**
   - Some machines only scan on startup or manual refresh
   - Solution: Refresh file listing on machine control panel

---

### Deployment History Empty

**Symptom:** O-number file selected but deployment history shows "No deployment record found"

**Possible Causes:**

1. **File uploaded manually (not via Shatter)**
   - Files uploaded directly via FTP don't have deployment records
   - Solution: Re-validate to create deployment record

2. **Database record deleted**
   - Unlikely unless database was manually modified
   - Solution: Re-validate to create new record

3. **Wrong O-number**
   - Filename doesn't match pattern `O####.NC`
   - Solution: Rename file to valid O-number format

---

## Related Documentation

- [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md) - Detailed validation algorithm
- [API_REFERENCE.md](./API_REFERENCE.md) - Backend API endpoints
- [DASHBOARD_WORKFLOWS.md](./DASHBOARD_WORKFLOWS.md) - Dashboard features
- [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) - React components
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - Data models
- [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md) - Backend services
