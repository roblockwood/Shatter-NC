# Tool Management Workflows

## Table of Contents

- [Overview](#overview)
- [Viewing Tool Summary](#viewing-tool-summary)
  - [Tool List Layout](#tool-list-layout)
  - [Summary Statistics](#summary-statistics)
  - [Sortable Columns](#sortable-columns)
- [Tool Detail Modal](#tool-detail-modal)
  - [Opening Tool Details](#opening-tool-details)
  - [Tool Specifications](#tool-specifications)
  - [Programs & Operations](#programs--operations)
  - [Tool-Related Alarms](#tool-related-alarms)
- [Analyzing Speed/Feed Data](#analyzing-speedfeed-data)
  - [Per-Program Comparison](#per-program-comparison)
  - [Operation Analysis](#operation-analysis)
  - [Identifying Inconsistencies](#identifying-inconsistencies)
- [Exporting Tool Data](#exporting-tool-data)
  - [CSV Export](#csv-export)
  - [JSON Export](#json-export)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **Tool Management** page provides comprehensive analysis of tool usage across all programs with detailed speed/feed data.

**Key Features:**
- Aggregated tool usage statistics
- Per-program operation analysis with all 8 feedrate types
- Tool-related alarm tracking
- CSV/JSON export capabilities

**Location:** [ToolManagement.tsx](../frontend/src/pages/ToolManagement.tsx)

**Target Users:**
- Manufacturing engineers analyzing machining parameters
- Tool room managers tracking tool usage
- Quality engineers auditing speed/feed consistency
- Production planners estimating tool requirements

---

## Viewing Tool Summary

### Tool List Layout

The main page displays all tools used across programs in a sortable table.

**Visual Layout:**

```
┌─ TOOL MANAGEMENT ──────────────────────────────────────────────┐
│  TOTAL TOOLS: 15  |  TOTAL PROGRAMS: 42  |  TOTAL RUNS: 156   │
└────────────────────────────────────────────────────────────────┘

╔═══════╦══════════╦═══════════════════╦══════════╦═════════╦═══════════════════╗
║ TOOL  ║ DIAMETER ║ DESCRIPTION       ║ PROGRAMS ║ RUNTIME ║ OPERATIONS        ║
╠═══════╬══════════╬═══════════════════╬══════════╬═════════╬═══════════════════╣
║ T1    ║ 0.25"    ║ FLAT END MILL     ║    12    ║  5h 12m ║ ADAPTIVE1, FACE2  ║
║ T3    ║ 0.50"    ║ 1/2 ENDMILL       ║     8    ║  3h 26m ║ FACE1, ADAPTIVE2  ║
║ T21   ║ 0.1181"  ║ PROBE             ║     5    ║  0h 05m ║ PROBE GEOMETRY2   ║
╚═══════╩══════════╩═══════════════════╩══════════╩═════════╩═══════════════════╝
```

### Summary Statistics

**Header Metrics:**

| Metric | Description | Source |
|--------|-------------|--------|
| **TOTAL TOOLS** | Unique tool numbers across all programs | Aggregated from program metadata |
| **TOTAL PROGRAMS** | Number of programs in library | Active programs count |
| **TOTAL RUNS** | Total production runs recorded | Sum of all production_runs |

### Sortable Columns

Click any column header to sort:

| Column | Data Type | Description |
|--------|-----------|-------------|
| **TOOL** | Number | Tool number from ATC (T1, T2, etc.) |
| **DIAMETER** | Float | Tool diameter in inches |
| **DESCRIPTION** | String | Tool description from ATC data |
| **PROGRAMS** | Integer | Number of programs using this tool |
| **RUNTIME** | Duration | Total estimated runtime (formatted as Xh Ym) |
| **OPERATIONS** | String | Comma-separated list of unique operation names |

**Click any row** to open the detailed analysis modal.

---

## Tool Detail Modal

### Opening Tool Details

**Trigger:** Click any tool row in the summary table

**Loading State:**
```
┌─ TOOL T1 ANALYSIS ──────────────────────────────────────────────┐
│                                                                  │
│                         LOADING...                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Keyboard:**
- `Escape` - Close modal
- Click outside modal - Close modal

### Tool Specifications

Top section displays tool metadata:

```
┌─ SPECIFICATIONS ───────────────────────────────────────────────┐
│                                                                 │
│  TOOL NUMBER: T1             DIAMETER: 0.25"                    │
│  DESCRIPTION: FLAT END MILL  TOTAL PROGRAMS: 3                  │
│  RUNTIME: 5h 12m             PRODUCTION RUNS: 12                │
│  MACHINES USED: Mill 1, Mill 2                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Programs & Operations

**Hierarchical Structure:**

Each program is displayed with its operations nested below. This preserves per-program context for speed/feed analysis.

```
┌─ PROGRAMS & OPERATIONS ─────────────────────────────────────────┐
│                                                                  │
│  PART_123_OP1.NC v2 │ RUNS: 8 │ LAST RUN: 2025-01-15 14:00:00  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ OPERATION  │ SPINDLE │ CUTTING │ PLUNGE │ FINISH │ ... │   │
│  ├────────────┼─────────┼─────────┼────────┼────────┼─────┤   │
│  │ ADAPTIVE1  │  5000.0 │    39.4 │   25.0 │   50.0 │ ... │   │
│  │ 2D CONTOUR1│  5000.0 │    35.0 │   20.0 │   45.0 │ ... │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  PART_456_OP2.NC v1 │ RUNS: 4 │ LAST RUN: 2025-01-14 10:30:00  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ OPERATION  │ SPINDLE │ CUTTING │ PLUNGE │ FINISH │ ... │   │
│  ├────────────┼─────────┼─────────┼────────┼────────┼─────┤   │
│  │ ADAPTIVE1  │  4500.0 │    35.0 │   22.0 │    —   │ ... │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**All 8 Feedrate Types Displayed:**

| Column | Description | Units |
|--------|-------------|-------|
| **SPINDLE** | Spindle speed | RPM |
| **CUTTING** | Cutting feedrate | IPM |
| **PLUNGE** | Z-axis plunge rate | IPM |
| **FINISH** | Finish pass feedrate | IPM |
| **ENTRY** | Entry move feedrate | IPM |
| **EXIT** | Exit move feedrate | IPM |
| **DIRECT** | Direct/rapid traverse | IPM |
| **TRANS** | Transition feedrate | IPM |

**Null Values:** Displayed as `—` when feedrate type not used in operation

### Tool-Related Alarms

Bottom section shows alarms correlated with this tool:

```
┌─ TOOL-RELATED ALARMS ───────────────────────────────────────────┐
│                                                                  │
│  PROGRAM          │ ALARM COUNT │ LAST ALARM          │ CODES  │
│  ─────────────────┼─────────────┼─────────────────────┼────────│
│  PART_123_OP1.NC  │      2      │ 2025-01-15 12:00:00 │ T101   │
│  PART_456_OP2.NC  │      1      │ 2025-01-14 09:15:00 │ T102   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Analyzing Speed/Feed Data

### Per-Program Comparison

**Use Case:** Compare same operation across different programs

**Example:**

Tool T1 uses operation "ADAPTIVE1" in two programs:
- **PART_123_OP1.NC**: Spindle 5000 RPM, Cutting 39.4 IPM
- **PART_456_OP2.NC**: Spindle 4500 RPM, Cutting 35.0 IPM

**Analysis:**
- Different programs may use different speeds/feeds for same operation
- This is intentional based on material, part geometry, or programmer preference
- Modal allows visual comparison across programs

### Operation Analysis

**Workflow:**

1. Open tool detail modal
2. Scroll through programs section
3. Compare values across all 8 feedrate columns
4. Note any null values (unused feedrate types)
5. Identify patterns or anomalies

**Key Observations:**

- **Consistent speeds** - Same spindle speed across programs indicates tool limitation
- **Variable feeds** - Different feedrates suggest material/geometry differences
- **Missing finish passes** - Null finish feedrate means no finish operation
- **High plunge rates** - May indicate aggressive settings or tool wear

### Identifying Inconsistencies

**Red Flags:**

1. **Unusually high/low values** compared to similar programs
2. **Null values** where you expect data (missing operations?)
3. **Alarm correlation** - Programs with alarms may have improper speed/feed
4. **Zero values** - Should be null, might indicate parsing error

**Actions:**

- Review G-code for suspected programs
- Consult with programmer or engineer
- Update CAM parameters if needed
- Re-validate after changes

---

## Exporting Tool Data

### CSV Export

**Workflow:**

1. Click **[Export CSV]** button (future feature)
2. Select filters (optional):
   - Specific tool numbers
   - Date range for production runs
   - Specific machines
3. Click **Export**
4. File downloads as `tools_export_YYYYMMDD_HHMMSS.csv`

**CSV Structure:**

```csv
tool_number,diameter,description,...,program_filename,operation_name,spindle_speed,feedrate_cutting,...
1,0.25,"FLAT END MILL",...,"PART_123_OP1.NC","ADAPTIVE1",5000.0,39.4,...
1,0.25,"FLAT END MILL",...,"PART_123_OP1.NC","2D CONTOUR1",5000.0,35.0,...
1,0.25,"FLAT END MILL",...,"PART_456_OP2.NC","ADAPTIVE1",4500.0,35.0,...
```

**Use Cases:**
- Import into Excel for pivot tables and charting
- Load into database for historical tracking
- Share with tool vendors for optimization recommendations
- Archive for quality documentation

### JSON Export

**Workflow:**

Same as CSV, but select **JSON** format.

**JSON Structure:**

Hierarchical format preserving program → operations nesting:

```json
{
  "export_date": "2025-01-15T14:30:00Z",
  "total_tools": 3,
  "tools": [
    {
      "tool_number": 1,
      "programs": [
        {
          "program_id": 5,
          "filename": "PART_123_OP1.NC",
          "operations": [
            {
              "operation_name": "ADAPTIVE1",
              "spindle_speed": 5000.0,
              "feedrate_cutting": 39.4,
              ...
            }
          ]
        }
      ]
    }
  ]
}
```

**Use Cases:**
- API integration with external systems
- Import into MongoDB or other NoSQL databases
- Processing with Python/JavaScript scripts
- Machine learning data preparation

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Escape` | Close tool detail modal |
| Click outside | Close tool detail modal |

---

## Common Use Cases

### 1. Tool Usage Audit

**Scenario:** Manufacturing engineer needs to verify tool usage across all programs.

**Workflow:**
1. Open Tool Management page
2. Review PROGRAMS column - shows how many programs use each tool
3. Click tools with high program count
4. Verify tool is appropriate for all applications
5. Export data for documentation

### 2. Speed/Feed Standardization

**Scenario:** Want to standardize feeds for a specific tool across all programs.

**Workflow:**
1. Open tool detail modal
2. Review operations table for all programs
3. Note variations in cutting/plunge feedrates
4. Document recommended values
5. Work with programmers to update CAM parameters
6. Re-validate after changes

### 3. Tool-Related Alarm Investigation

**Scenario:** T1 frequently triggers alarms on specific programs.

**Workflow:**
1. Open T1 detail modal
2. Scroll to Alarms section
3. Identify programs with high alarm counts
4. Compare speed/feed values to programs without alarms
5. Look for aggressive settings (high feeds, low plunge rates)
6. Adjust CAM parameters and re-test

### 4. New Tool Evaluation

**Scenario:** Considering replacing T1 with different tool.

**Workflow:**
1. Export T1 data to CSV
2. Document current usage: 12 programs, 5h runtime, specific feeds
3. Calculate tool cost vs. runtime
4. Share data with tool vendor for recommendations
5. Document decision for future reference

### 5. Production Planning

**Scenario:** Estimate tool requirements for upcoming production run.

**Workflow:**
1. Open tool detail modal
2. Note total runtime across all programs
3. Check production runs count
4. Calculate average runtime per part
5. Estimate tool life based on material and feeds
6. Order replacement tools proactively

---

## Troubleshooting

### Modal Won't Open

**Problem:** Clicking tool row doesn't open detail modal

**Solutions:**
- Check browser console for JavaScript errors
- Refresh page (Ctrl/Cmd + R)
- Verify API endpoint is accessible: `curl http://localhost:8000/api/tools/1`
- Check that tool number exists in database

### No Operations Displayed

**Problem:** Program shows in list but no operations table

**Possible Causes:**
1. Program has no operations in metadata (older programs before operation tracking)
2. Tool used in program setup but not in actual operations
3. Parsing error during program upload

**Solutions:**
- Check program metadata: `GET /api/programs/{id}`
- Re-upload program to re-parse metadata
- Verify NC parser is capturing operation data correctly

### Missing Feedrate Values

**Problem:** Many null/`—` values in operations table

**Expected Behavior:**

Not all operations use all 8 feedrate types:
- **Probing operations** - Only use direct feedrate
- **Simple contours** - May not use finish pass
- **2D operations** - May not use entry/exit moves

**Verification:**
- Review G-code to confirm which feedrates are actually used
- Null values are correct if operation doesn't use that feedrate type

### Export Button Missing

**Status:** Export functionality planned for future release

**Current Workaround:**
- Use API directly: `POST /api/tools/export`
- Example:
  ```bash
  curl -X POST http://localhost:8000/api/tools/export \
    -H "Content-Type: application/json" \
    -d '{"format": "csv", "include_operations": true}' \
    -o tools_export.csv
  ```

---

## Related Documentation

- [API Reference - Tool Management API](API_REFERENCE.md#tool-management-api) - Complete API endpoint documentation
- [Backend Architecture - ToolService](BACKEND_ARCHITECTURE.md#toolservice) - Service layer implementation
- [Frontend Architecture - Tool Management](FRONTEND_ARCHITECTURE.md#tool-management) - Component structure
- [Database Schema](DATABASE_SCHEMA.md) - Program metadata structure
