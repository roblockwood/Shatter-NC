# Database Schema

Complete database schema documentation for the Shatter CNC management platform.

## Overview

**Database:** PostgreSQL 15+ with TimescaleDB extension (`timescale/timescaledb:latest-pg15` in Docker compose)

**ORM:** SQLAlchemy 2.0

**Purpose:** Store machine configurations, NC programs with version control, deployment tracking, and time-series event data for production analytics.

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **RDBMS** | PostgreSQL 15+ | Relational data storage |
| **Time-Series** | TimescaleDB | Efficient time-series data storage and queries |
| **ORM** | SQLAlchemy 2.0 | Database abstraction and migrations |
| **Connection Pool** | SQLAlchemy pooling | Connection reuse and management |
| **Transactions** | ACID-compliant | Data consistency |

### Database URL

Connection string is built from `POSTGRES_*` settings in [`config.py`](../backend/app/core/config.py). See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md).

---

## Schema Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      CORE TABLES                                 │
└─────────────────────────────────────────────────────────────────┘

machines (Machine Configuration)
├── id (PK)
├── name (UNIQUE)
├── model (default: "Brother CNC")
├── ip_address
├── ftp_port, http_port
├── ftp_username, ftp_password
├── path
├── tags (JSON)
├── poll_interval_seconds
├── tool_poll_interval_seconds
├── enabled
├── units (in/mm)
├── diameter_tolerance
├── length_tolerance_plus, length_tolerance_minus
├── tolerance_x, tolerance_y, tolerance_z
├── use_machine_tool_tolerances (boolean)
├── use_machine_wcs_tolerances (boolean)
├── validate_tool_diameter, validate_tool_length (boolean)
├── control_version (C00/D00, nullable)
├── part_display_mode ('parts' | 'cycle')
├── ftp_sync_enabled (boolean)
├── layout_config (JSON, nullable) - UI pane layout configuration
├── created_at, updated_at
└── last_seen_at

programs (NC Program Library)
├── id (PK)
├── original_filename
├── content_hash (UNIQUE, SHA-256)
├── posted_date
├── version_number
├── program_metadata (JSONB)
├── file_size_bytes
├── line_count
├── estimated_runtime_seconds
├── first_seen_at
├── last_deployed_at
├── deployed_count
└── is_active

program_deployments (O-Number Tracking)
├── id (PK)
├── program_id (FK → programs.id)
├── machine_id (FK → machines.id)
├── deployed_filename (e.g., "O2000.nc")
├── deployed_path (e.g., "/PROGRAM/O2000.nc")
├── deployed_at
├── deployed_by
├── validation_results (JSONB)
├── validation_passed
├── is_current
├── replaced_at
└── replaced_by (FK → program_deployments.id)

tool_instances (Physical Tool Lifecycle Tracking)
├── id (PK)
├── machine_id (FK → machines.id)
├── tool_number
├── diameter
├── corner_radius
├── description
├── length_total
├── installed_at
├── removed_at
├── removal_reason (normal_wear, breakage, upgrade, scheduled)
├── total_runtime_seconds
├── total_parts_produced
├── total_cycles
├── is_active
├── notes
└── created_at

┌─────────────────────────────────────────────────────────────────┐
│               TIME-SERIES TABLES (TimescaleDB)                   │
└─────────────────────────────────────────────────────────────────┘

machine_status_events (Hypertable)
├── time (PK, TimescaleDB partition key)
├── machine_id (PK, FK → machines.id)
├── status
├── previous_status
├── program_name
├── o_number
└── metrics (JSONB)

alarm_events (Hypertable)
├── time (PK, TimescaleDB partition key)
├── machine_id (PK, FK → machines.id)
├── alarm_code (PK)
├── alarm_message
├── alarm_type
├── severity
├── program_id (FK → programs.id)
├── deployment_id (FK → program_deployments.id)
├── cleared_at
├── duration_seconds
├── cleared_by
└── resolution_notes

production_runs (Hypertable)
├── id (PK)
├── started_at (TimescaleDB index)
├── ended_at
├── machine_id (FK → machines.id)
├── program_id (FK → programs.id)
├── deployment_id (FK → program_deployments.id)
├── program_name
├── o_number
├── cycle_count
├── parts_produced
├── duration_seconds
├── actual_cycle_time_seconds
├── estimated_cycle_time_seconds
├── efficiency_percent
├── completion_status
├── abort_reason
├── alarm_count
└── total_downtime_seconds

polling_events (Hypertable)
├── time (PK, TimescaleDB partition key)
├── machine_id (PK, FK → machines.id)
├── success
├── response_time_ms
└── error_message

compressors (Compressor Configuration)
├── id (PK), name, ip_address, kaeser_connect_base_url, kaeser_username, kaeser_password
├── poll_interval_seconds, enabled, tags, layout_config, last_seen_at, timestamps

compressor_status_events (Hypertable) — status transitions
compressor_status_samples (Hypertable) — high-frequency telemetry
compressor_status_samples_1min (continuous aggregate)

ftp_sync_configs, ftp_sync_runs, ftp_sync_run_items, ftp_sync_file_states

notification_channels, notification_rules, notification_log

prd3_status_history, macro_history, tool_table_history, panel_history, counter_history (Hypertables)

schema_migrations — applied SQL migration filenames
```

---

## Core Tables

### machines

Machine configuration and metadata.

**Table:** `machines`

**Location:** [machine.py](../backend/app/models/machine.py)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | AUTO | Primary key |
| `name` | String(255) | No | - | Unique machine name |
| `model` | String(100) | No | "Brother CNC" | Machine model |
| `ip_address` | String(45) | No | - | IPv4/IPv6 address |
| `ftp_port` | Integer | No | 21 | FTP port |
| `http_port` | Integer | No | 80 | HTTP port |
| `ftp_username` | String(255) | No | "anonymous" | FTP username |
| `ftp_password` | String(255) | No | "anonymous" | FTP password |
| `path` | String(255) | No | `/` (SQL init default `/program`) | Default FTP path |
| `tags` | JSON | Yes | NULL | Machine tags (e.g., ["production", "floor-a"]) |
| `poll_interval_seconds` | Integer | No | 5 | Fast status polling interval (seconds) |
| `tool_poll_interval_seconds` | Integer | No | 30 | Tool table / ATC polling interval |
| `enabled` | Boolean | No | TRUE | Enable/disable polling |
| `units` | String(2) | No | "in" | Units of measurement (in/mm) |
| `diameter_tolerance` | Float | No | 0.010 | Tool diameter tolerance (±inches) |
| `length_tolerance_plus` | Float | No | 0.02 | Tool length tolerance + (inches) |
| `length_tolerance_minus` | Float | No | 0.0 | Tool length tolerance - (inches) |
| `tolerance_x` | Float | No | 0.0394 | WCS X tolerance (±inches, ±1mm) |
| `tolerance_y` | Float | No | 0.0394 | WCS Y tolerance (±inches, ±1mm) |
| `tolerance_z` | Float | No | 0.0394 | WCS Z tolerance (±inches, ±1mm) |
| `use_machine_tool_tolerances` | Boolean | No | FALSE | When TRUE, use machine-defined tool tolerances. When FALSE, use G-code defaults (exact diameter match, length ≥ required) |
| `use_machine_wcs_tolerances` | Boolean | No | FALSE | When TRUE, use machine-defined WCS tolerances. When FALSE, use E parameter from G-code if present |
| `validate_tool_diameter` | Boolean | No | TRUE | Include diameter in tool validation |
| `validate_tool_length` | Boolean | No | TRUE | Include length in tool validation |
| `control_version` | String(3) | Yes | NULL | `C00`, `D00`, or NULL (auto-detect) |
| `part_display_mode` | String(20) | No | "parts" | UI counter display: `parts` or `cycle` |
| `ftp_sync_enabled` | Boolean | No | FALSE | Enable FTP sync UI/jobs for this machine |
| `layout_config` | JSON | Yes | NULL | UI pane layout configuration (custom layout for machine detail view) |
| `created_at` | DateTime(TZ) | No | NOW() | Record creation time |
| `updated_at` | DateTime(TZ) | Yes | - | Last update time |
| `last_seen_at` | DateTime(TZ) | Yes | NULL | Last successful poll time |

**Relationships:**
- **One-to-Many:** `program_deployments` (deployments on this machine)

**Indexes:**
- `PRIMARY KEY (id)`
- `UNIQUE (name)`

**Constraints:**
- `name` must be unique across all machines

**Example Record:**
```sql
INSERT INTO machines (name, ip_address, enabled)
VALUES ('Mill 1', '192.168.1.100', TRUE);
```

---

### programs

NC program library with automatic version control.

**Table:** `programs`

**Location:** [program.py:9-62](../backend/app/models/program.py#L9-L62)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | AUTO | Primary key |
| `original_filename` | String(500) | No | - | Original filename (e.g., "PART_123_OP1.NC") |
| `content_hash` | String(64) | No | - | SHA-256 hash of G-code content (UNIQUE) |
| `posted_date` | DateTime(TZ) | Yes | - | Program posted date (from G-code comment) |
| `version_number` | Integer | No | - | Version number (per filename) |
| `program_metadata` | JSONB | No | {} | Parsed metadata (tools, WCS, stock size) |
| `file_size_bytes` | Integer | No | - | File size in bytes |
| `line_count` | Integer | No | - | Number of lines |
| `estimated_runtime_seconds` | Float | Yes | - | Estimated runtime |
| `first_seen_at` | DateTime(TZ) | No | NOW() | First upload time |
| `last_deployed_at` | DateTime(TZ) | Yes | - | Last deployment time |
| `deployed_count` | Integer | No | 0 | Number of times deployed |
| `is_active` | Boolean | No | TRUE | Active/archived status |

**Relationships:**
- **One-to-Many:** `deployments` (where this program is deployed)
- **One-to-Many:** `production_runs` (production history)
- **One-to-Many:** `alarm_events` (alarms during runs)

**Indexes:**
- `PRIMARY KEY (id)`
- `UNIQUE (content_hash)` - Prevents duplicate content
- `INDEX (original_filename)` - For version queries
- `INDEX (is_active)` - For active program queries

**Constraints:**
- `CHECK (version_number > 0)` - Version must be positive

**program_metadata Structure:**
```json
{
  "tools": [
    {
      "tool_number": 1,
      "diameter": 0.25,
      "corner_radius": 0.0,
      "length_total": 3.5,
      "description": "1/4 ENDMILL"
    }
  ],
  "wcs_offset": {
    "x": 0.0,
    "y": 0.0,
    "z": -5.0,
    "work_offset": 54,
    "tolerance": 0.001
  },
  "stock_size": {
    "x": 146.05,
    "y": 25.4,
    "z": 12.7
  }
}
```

**Content Hash Deduplication:**
```python
# Identical content → same hash → no duplicate
content_hash = hashlib.sha256(gcode_content.encode('utf-8')).hexdigest()
```

**Version Numbering:**
- Per-filename versioning: `PART_123.nc` → v1, v2, v3...
- Version = MAX(existing versions for filename) + 1
- First version = v1

**Example Query:**
```sql
-- Get all versions of a program
SELECT version_number, posted_date, content_hash
FROM programs
WHERE original_filename = 'PART_123_OP1.NC'
ORDER BY version_number DESC;
```

---

### program_deployments

Tracks deployment of programs to machines with O-number mapping.

**Table:** `program_deployments`

**Location:** [program.py:65-100](../backend/app/models/program.py#L65-L100)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | AUTO | Primary key |
| `program_id` | Integer | No | - | FK → programs.id |
| `machine_id` | Integer | No | - | FK → machines.id |
| `deployed_filename` | String(500) | No | - | O-number format (e.g., "O2000.nc") |
| `deployed_path` | String(500) | No | - | Full path (e.g., "/PROGRAM/O2000.nc") |
| `deployed_at` | DateTime(TZ) | No | NOW() | Deployment timestamp |
| `deployed_by` | String(255) | Yes | - | User who deployed (future) |
| `validation_results` | JSONB | Yes | - | Validation results at deploy time |
| `validation_passed` | Boolean | No | TRUE | Overall validation status |
| `is_current` | Boolean | No | TRUE | Current deployment for this O-number |
| `replaced_at` | DateTime(TZ) | Yes | - | When this deployment was replaced |
| `replaced_by` | Integer | Yes | - | FK → program_deployments.id (replacement) |

**Relationships:**
- **Many-to-One:** `program` (the deployed program)
- **Many-to-One:** `machine` (target machine)
- **One-to-Many:** `production_runs` (runs of this deployment)
- **One-to-Many:** `alarm_events` (alarms during deployment)

**Indexes:**
- `PRIMARY KEY (id)`
- `INDEX (program_id)`
- `INDEX (machine_id)`
- `INDEX (deployed_at)` - For history queries
- `INDEX (is_current)` - For current deployment queries

**Foreign Keys:**
- `program_id` → `programs.id` ON DELETE CASCADE
- `machine_id` → `machines.id` ON DELETE CASCADE
- `replaced_by` → `program_deployments.id` ON DELETE SET NULL

**O-Number Reuse Tracking:**

When an O-number is reused:
1. Previous deployment: `is_current = FALSE`, `replaced_at = NOW()`, `replaced_by = <new deployment ID>`
2. New deployment: `is_current = TRUE`

**Example:**
```sql
-- Get current deployment for O2000 on Machine 1
SELECT d.deployed_filename, d.deployed_at, p.original_filename, p.version_number
FROM program_deployments d
JOIN programs p ON d.program_id = p.id
WHERE d.machine_id = 1
  AND d.deployed_filename = 'O2000.nc'
  AND d.is_current = TRUE;

-- Get deployment history for O2000
SELECT d.deployed_at, d.is_current, p.original_filename, p.version_number
FROM program_deployments d
JOIN programs p ON d.program_id = p.id
WHERE d.machine_id = 1
  AND d.deployed_filename = 'O2000.nc'
ORDER BY d.deployed_at DESC;
```

---

### tool_instances

Physical tool instance tracking for lifecycle management.

**Table:** `tool_instances`

**Location:** [tool_instance.py:8-57](../backend/app/models/tool_instance.py#L8-L57)

**Purpose:** Tracks individual physical tools installed in machines, enabling tool life analysis, replacement history, cost tracking, and premature failure detection.

**Note:** Initially unpopulated - infrastructure for future enhancement.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | AUTO | Primary key |
| `machine_id` | Integer | No | - | FK → machines.id |
| `tool_number` | Integer | No | - | Tool number in machine |
| `diameter` | Float | No | - | Tool diameter |
| `corner_radius` | Float | No | 0.0 | Corner radius |
| `description` | String(500) | Yes | - | Tool description |
| `length_total` | Float | Yes | - | Total tool length |
| `installed_at` | DateTime(TZ) | No | NOW() | Installation timestamp |
| `removed_at` | DateTime(TZ) | Yes | - | Removal timestamp |
| `removal_reason` | String(100) | Yes | - | Removal reason: 'normal_wear', 'breakage', 'upgrade', 'scheduled' |
| `total_runtime_seconds` | Integer | No | 0 | Total runtime in seconds |
| `total_parts_produced` | Integer | No | 0 | Total parts produced |
| `total_cycles` | Integer | No | 0 | Total cycles |
| `is_active` | Boolean | No | TRUE | Active/removed status |
| `notes` | Text | Yes | - | Additional notes |
| `created_at` | DateTime(TZ) | No | NOW() | Record creation time |

**Relationships:**
- **Many-to-One:** `machine` (the machine this tool is installed in)

**Indexes:**
- `PRIMARY KEY (id)`
- `INDEX (machine_id)`
- `INDEX (is_active)`

**Constraints:**
- `CHECK (removed_at IS NULL OR removed_at >= installed_at)` - Valid removal date

**Foreign Keys:**
- `machine_id` → `machines.id` ON DELETE CASCADE

**Example:**
```sql
-- Get active tools for a machine
SELECT tool_number, diameter, description, installed_at, total_runtime_seconds
FROM tool_instances
WHERE machine_id = 1 AND is_active = TRUE
ORDER BY tool_number;
```

---

## Time-Series Tables (TimescaleDB Hypertables)

### machine_status_events

Machine status change events (running, stopped, idle, alarm).

**Table:** `machine_status_events` (Hypertable)

**Location:** [event.py:8-37](../backend/app/models/event.py#L8-L37)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `time` | DateTime(TZ) | No (PK) | - | Event timestamp (partition key) |
| `machine_id` | Integer | No (PK) | - | FK → machines.id |
| `status` | String(50) | No | - | Status value (`off`, `standby`, `operating`, `stopped`, `error`, etc.) |
| `previous_status` | String(50) | Yes | - | Previous status (for transitions) |
| `program_name` | String(500) | Yes | - | Program name at time of event |
| `o_number` | String(50) | Yes | - | O-number at time of event |
| `metrics` | JSONB | Yes | - | Snapshot of metrics |

**TimescaleDB Partitioning:**
- **Partition Key:** `time`
- **Chunk Interval:** 7 days
- **Retention:** 1 year (see `database/init/02-add-program-tracking.sql`)

**Composite Primary Key:**
```sql
PRIMARY KEY (time, machine_id)
```

**Indexes:**
- `INDEX (machine_id)` - For machine-specific queries
- `INDEX (status)` - For status filtering

**metrics Structure:**
```json
{
  "cycle_time_seconds": 3845,
  "cutting_time_seconds": 2712,
  "power_on_hours": 1068.1
}
```

**Logged Events:**
- Status transitions (e.g., stopped → running)
- Tracked in-memory by PollingService to avoid database queries

**Example Query:**
```sql
-- Get status history for last 24 hours
SELECT time, status, previous_status, program_name
FROM machine_status_events
WHERE machine_id = 1
  AND time > NOW() - INTERVAL '24 hours'
ORDER BY time DESC;
```

**TimescaleDB Creation:**
```sql
-- Create hypertable
SELECT create_hypertable('machine_status_events', 'time');

-- Set chunk interval
SELECT set_chunk_time_interval('machine_status_events', INTERVAL '7 days');

-- Add compression policy
ALTER TABLE machine_status_events SET (
  timescaledb.compress,
  timescaledb.compress_orderby = 'time DESC'
);

-- Add retention policy (1 year — see database/init/02-add-program-tracking.sql)
SELECT add_retention_policy('machine_status_events', INTERVAL '1 year');
```

---

### alarm_events

Alarm occurrence tracking.

**Table:** `alarm_events` (Hypertable)

**Location:** [event.py:40-73](../backend/app/models/event.py#L40-L73)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `time` | DateTime(TZ) | No (PK) | - | Alarm occurrence time (partition key) |
| `machine_id` | Integer | No (PK) | - | FK → machines.id |
| `alarm_code` | String(50) | No (PK) | - | Alarm code (e.g., "P504") |
| `alarm_message` | Text | No | - | Alarm message |
| `alarm_type` | String(50) | Yes | - | Alarm type |
| `severity` | String(20) | Yes | - | Severity level ("info", "warning", "error", "critical") |
| `program_id` | Integer | Yes | - | FK → programs.id (program running during alarm) |
| `deployment_id` | Integer | Yes | - | FK → program_deployments.id |
| `cleared_at` | DateTime(TZ) | Yes | - | When alarm was cleared |
| `duration_seconds` | Integer | Yes | - | Alarm duration |
| `cleared_by` | String(255) | Yes | - | Who cleared the alarm (future) |
| `resolution_notes` | Text | Yes | - | Resolution notes (future) |

**Composite Primary Key:**
```sql
PRIMARY KEY (time, machine_id, alarm_code)
```

**Indexes:**
- `INDEX (machine_id)` - Machine-specific queries
- `INDEX (alarm_code)` - Alarm type queries
- `INDEX (cleared_at)` - Active alarms (WHERE cleared_at IS NULL)

**Foreign Keys:**
- `machine_id` → `machines.id` ON DELETE CASCADE
- `program_id` → `programs.id`
- `deployment_id` → `program_deployments.id`

**Deduplication Logic:**
```sql
-- Check if alarm already exists and is active
SELECT * FROM alarm_events
WHERE machine_id = 1
  AND alarm_code = 'P504'
  AND cleared_at IS NULL;
```

**Example Query:**
```sql
-- Get all active alarms
SELECT time, machine_id, alarm_code, alarm_message, severity
FROM alarm_events
WHERE cleared_at IS NULL
ORDER BY time DESC;

-- Get alarm history for last week
SELECT time, alarm_code, alarm_message, duration_seconds
FROM alarm_events
WHERE machine_id = 1
  AND time > NOW() - INTERVAL '7 days'
ORDER BY time DESC;
```

**Retention:** 1 year

---

### production_runs

Production run tracking (program start/end, cycle counts, efficiency).

**Table:** `production_runs` (Hypertable)

**Location:** [event.py:76-124](../backend/app/models/event.py#L76-L124)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No (PK) | AUTO | Primary key |
| `started_at` | DateTime(TZ) | No | - | Run start time (TimescaleDB index) |
| `ended_at` | DateTime(TZ) | Yes | - | Run end time |
| `machine_id` | Integer | No | - | FK → machines.id |
| `program_id` | Integer | Yes | - | FK → programs.id |
| `deployment_id` | Integer | Yes | - | FK → program_deployments.id |
| `program_name` | String(500) | Yes | - | Program name (cached) |
| `o_number` | String(50) | Yes | - | O-number (cached) |
| `cycle_count` | Integer | No | 0 | Number of cycles completed |
| `parts_produced` | Integer | No | 0 | Parts produced |
| `duration_seconds` | Integer | Yes | - | Total run duration |
| `actual_cycle_time_seconds` | Float | Yes | - | Actual cycle time |
| `estimated_cycle_time_seconds` | Float | Yes | - | Estimated cycle time |
| `efficiency_percent` | Float | Yes | - | Efficiency (actual/estimated × 100) |
| `completion_status` | String(50) | Yes | - | "completed", "stopped", "idle", "alarm" |
| `abort_reason` | String(500) | Yes | - | Reason for abort |
| `alarm_count` | Integer | No | 0 | Number of alarms during run |
| `total_downtime_seconds` | Integer | No | 0 | Total downtime |

**Indexes:**
- `PRIMARY KEY (id)`
- `INDEX (started_at)` - Time-based queries
- `INDEX (ended_at)` - Active runs (WHERE ended_at IS NULL)
- `INDEX (machine_id)` - Machine-specific queries
- `INDEX (program_id)` - Program-specific queries
- `INDEX (completion_status)` - Status filtering

**Constraints:**
- `CHECK (ended_at IS NULL OR ended_at >= started_at)` - Valid time range

**Run Detection:**

**Start:** status == "running" AND program_name != "----" AND no active run
**End:** status in ["stopped", "idle", "alarm"] AND active run exists

**Example Query:**
```sql
-- Get active production runs
SELECT id, machine_id, program_name, started_at
FROM production_runs
WHERE ended_at IS NULL;

-- Get production history for last 24 hours
SELECT machine_id, program_name, duration_seconds, completion_status
FROM production_runs
WHERE started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC;

-- Calculate average run time for a program
SELECT AVG(duration_seconds) AS avg_duration
FROM production_runs
WHERE program_id = 1
  AND completion_status = 'completed';
```

**Retention:** Indefinite (production data)

---

### polling_events

Telnet poll attempt tracking (success/failure, response time).

**Table:** `polling_events` (Hypertable)

**Location:** [event.py:127-145](../backend/app/models/event.py#L127-L145)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `time` | DateTime(TZ) | No (PK) | - | Poll timestamp (partition key) |
| `machine_id` | Integer | No (PK) | - | FK → machines.id |
| `success` | Boolean | No | - | Poll success/failure |
| `response_time_ms` | Integer | Yes | - | Response time in milliseconds |
| `error_message` | String(500) | Yes | - | Error message if failed |

**Composite Primary Key:**
```sql
PRIMARY KEY (time, machine_id)
```

**Indexes:**
- `INDEX (machine_id)` - Machine-specific queries
- `INDEX (success)` - Success rate calculations

**Example Query:**
```sql
-- Calculate uptime percentage for last 8 hours
SELECT
  machine_id,
  COUNT(*) AS total_polls,
  SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successful_polls,
  ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) AS uptime_percent
FROM polling_events
WHERE machine_id = 1
  AND time > NOW() - INTERVAL '8 hours'
GROUP BY machine_id;

-- Get polling history for visualization
SELECT time, success, response_time_ms
FROM polling_events
WHERE machine_id = 1
  AND time > NOW() - INTERVAL '1 hour'
ORDER BY time ASC;
```

**Retention:** 1 year (see `database/init/05-add-polling-events.sql`)

---

## Entity Relationships

### ER Diagram

```
machines (1) ──┬─< (N) program_deployments (N) ──> (1) programs
               │
               ├─< (N) machine_status_events
               │
               ├─< (N) alarm_events
               │
               ├─< (N) production_runs
               │
               └─< (N) polling_events

programs (1) ──┬─< (N) program_deployments
               │
               ├─< (N) production_runs
               │
               └─< (N) alarm_events

program_deployments (1) ──┬─< (N) production_runs
                          │
                          └─< (N) alarm_events
```

### Cascade Behavior

**Machine Deletion:**
- Cascades to: `program_deployments`, `machine_status_events`, `alarm_events`, `production_runs`, `polling_events`
- Effect: All machine data deleted

**Program Deletion:**
- Cascades to: `program_deployments`, `production_runs`, `alarm_events`
- Effect: All deployment and run data for program deleted

**Deployment Deletion:**
- Cascades to: `production_runs`, `alarm_events`
- Effect: All run and alarm data for deployment deleted

---

## Data Retention Policies

### TimescaleDB Retention

Applied in `database/init/*.sql` (representative values):

```sql
-- machine_status_events: 1 year (02-add-program-tracking.sql)
-- alarm_events: 2 years (02-add-program-tracking.sql)
-- production_runs: 5 years (02-add-program-tracking.sql)
-- polling_events: 1 year (05-add-polling-events.sql)
-- prd3_status_history, macro/tool/panel/counter history: 1 year (11–12)
-- compressor_status_events: 1 year (15-add-compressors.sql)
-- compressor_status_samples raw: 14 days (19-compressor-samples-rollup.sql)
-- compressor_status_samples_1min: 400 days (19-compressor-samples-rollup.sql)
```

### Compression Policies

```sql
-- Compress chunks older than 7 days
SELECT add_compression_policy('machine_status_events', INTERVAL '7 days');
SELECT add_compression_policy('alarm_events', INTERVAL '7 days');
SELECT add_compression_policy('polling_events', INTERVAL '7 days');
```

**Compression Benefits:**
- 90%+ storage reduction
- Faster queries (compressed data)
- Lower I/O

---

## TimescaleDB Configuration

### Hypertable Creation

```sql
-- Create hypertables (run AFTER table creation)
SELECT create_hypertable('machine_status_events', 'time');
SELECT create_hypertable('alarm_events', 'time');
SELECT create_hypertable('production_runs', 'started_at');
SELECT create_hypertable('polling_events', 'time');
```

### Chunk Intervals

```sql
-- Set chunk intervals (default: 7 days)
SELECT set_chunk_time_interval('machine_status_events', INTERVAL '7 days');
SELECT set_chunk_time_interval('alarm_events', INTERVAL '7 days');
SELECT set_chunk_time_interval('production_runs', INTERVAL '7 days');
SELECT set_chunk_time_interval('polling_events', INTERVAL '1 day');
```

**Why 7 days?**
- Balance between chunk count and query performance
- ~52 chunks per year for status events (with compression)
- Allows efficient retention policy application

### Continuous Aggregates

**Implemented:** `compressor_status_samples_1min` — 1-minute rollup of compressor telemetry (migration 19). Chart API uses raw samples for recent windows and the aggregate for longer spans.

Example pattern for future CNC aggregates:

```sql
-- Example (not deployed): hourly machine utilization
CREATE MATERIALIZED VIEW machine_utilization_hourly
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', time) AS bucket,
  machine_id,
  COUNT(*) FILTER (WHERE status = 'operating') AS operating_count,
  COUNT(*) AS total_count
FROM machine_status_events
GROUP BY bucket, machine_id;
```

---

## Migration Strategy

### Current Approach

**Numbered SQL files** in [`database/init/`](../database/init/) applied on every backend startup by [`run_migrations.py`](../backend/scripts/run_migrations.py). Applied filenames are recorded in **`schema_migrations`**.

See [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md).

### Alembic

Not used. Migrations are numbered SQL files plus `run_migrations.py`. A future switch to Alembic could add up/down migrations and autogenerate from models (see [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md)).

---

## Connection Pooling

### SQLAlchemy Pool Configuration

```python
# Default configuration
engine = create_engine(
    database_url,
    pool_size=5,          # Maintain 5 idle connections
    max_overflow=10,      # Allow 10 additional connections under load
    pool_pre_ping=True,   # Verify connection health before use
    pool_recycle=3600,    # Recycle connections after 1 hour
)
```

**Pool Sizing:**
- Base pool: 5 connections
- Max concurrent: 15 connections (5 + 10 overflow)
- Sufficient for typical load (~100 req/s)

**Health Checks:**
- `pool_pre_ping` prevents "connection closed" errors
- Validates connection before use

---

## Indexes and Performance

### Recommended Indexes

```sql
-- Core tables
CREATE INDEX idx_machines_enabled ON machines(enabled);
CREATE INDEX idx_programs_filename ON programs(original_filename);
CREATE INDEX idx_programs_active ON programs(is_active);
CREATE INDEX idx_deployments_current ON program_deployments(machine_id, is_current);

-- Time-series tables
CREATE INDEX idx_status_events_machine ON machine_status_events(machine_id);
CREATE INDEX idx_alarm_events_active ON alarm_events(machine_id, cleared_at);
CREATE INDEX idx_production_runs_active ON production_runs(machine_id, ended_at);
CREATE INDEX idx_polling_events_success ON polling_events(machine_id, success);
```

### Query Performance

**Example: Recent status events for machine**
```sql
EXPLAIN ANALYZE
SELECT time, status, program_name
FROM machine_status_events
WHERE machine_id = 1
  AND time > NOW() - INTERVAL '24 hours'
ORDER BY time DESC
LIMIT 100;
```

**Expected Performance:**
- < 10ms for recent data (cached)
- < 50ms for compressed chunks
- TimescaleDB automatically uses chunk exclusion

---

## Backup and Recovery

### Backup Strategy

**pg_dump:**
```bash
# Backup entire database
pg_dump -h localhost -U shatter_user -d shatter > backup.sql

# Backup specific table
pg_dump -h localhost -U shatter_user -d shatter -t machines > machines.sql
```

**TimescaleDB Backup:**
```bash
# Backup with TimescaleDB metadata
pg_dump -h localhost -U shatter_user -Fc -d shatter > backup.dump

# Restore
pg_restore -h localhost -U shatter_user -d shatter backup.dump
```

### Recovery

```bash
# Drop and recreate database
dropdb -h localhost -U postgres shatter
createdb -h localhost -U postgres shatter

# Restore from backup
psql -h localhost -U shatter_user -d shatter < backup.sql

# Recreate TimescaleDB hypertables (if needed)
psql -h localhost -U shatter_user -d shatter -f create_hypertables.sql
```

---

## Related Documentation

- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) - Service layer and data flow
- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) - Services using this schema
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - Database configuration
- [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) - Backup and volumes
