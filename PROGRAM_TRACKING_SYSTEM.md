# Program Tracking and Event Logging System

## Overview

The Shatter CNC Management Platform now includes a comprehensive program tracking and event logging system that automatically monitors NC program deployments, machine status changes, alarms, and production runs.

## Architecture

### 1. Program Tracking

#### Versioning Strategy

- **Identity**: Programs are identified by `original_filename` (e.g., "PART_123_OP1.NC")
- **Deduplication**: Content is hashed with SHA-256; identical content is never stored twice
- **Versioning**: Automatic version numbering (1, 2, 3...) per filename
- **Deployment**: Programs are deployed to machines with O-number format (e.g., "O2000.nc")

#### Versioning Example

```
Upload "PART_123_OP1.NC" → Program v1 (ID=1)
Upload "PART_123_OP1.NC" (identical) → Returns v1 (deduplication)
Upload "PART_123_OP1.NC" (different content) → Program v2 (ID=2)
Upload "PART_123_OP1.NC" (3rd version) → Program v3 (ID=3)
```

#### O-Number Deployment

```
Deploy Program v1 to Machine X as O2000
  → Deployment record created, is_current=true

Deploy Program v2 to Machine X as O2000
  → New deployment created
  → Old deployment marked: is_current=false, replaced_at=NOW, replaced_by=new_id

Deploy Program v1 to Machine X as O2001
  → New deployment (independent O-number)
  → O2000 still points to v2, O2001 points to v1
```

### 2. Event Logging

#### Status Events (MachineStatusEvent)

Automatically logged when machine status changes:
- `idle` → `running`: Program start
- `running` → `stopped`: Program complete
- `running` → `alarm`: Machine alarm triggered
- Any other transitions

**Tracked data:**
- Machine ID, status, previous_status
- Program name, O-number
- Performance metrics (cycle time, cutting time, power on hours)

#### Alarm Events (AlarmEvent)

Logged only when machine status = "alarm":
- Alarm code, message, type, severity
- Timestamp of occurrence
- Program context (if applicable)
- Can be marked as cleared with duration and resolution notes

**Deduplication:** Only new uncleared alarms are logged (prevents duplicate logging)

#### Production Runs (ProductionRun)

Automatically tracked based on machine status:
- **Start**: When status changes to `running` with valid program_name (not "----")
- **End**: When status changes to `stopped`, `idle`, or `alarm`

**Tracked data:**
- Machine ID, program name, O-number
- Start and end timestamps, duration
- Completion status (completed, idle, alarm)
- Part counts, cycle times, efficiency metrics

### 3. Non-Blocking Event Processing

Event logging is performed **asynchronously** in background tasks:

```
Polling → get_status_overview() → broadcast to WebSocket →
create_task(_log_events_async) → [returns immediately]
  ↓ [continues in background]
  Create separate DB session
  Log status event
  Log alarms (if applicable)
  Log production run
  Commit or rollback
```

Benefits:
- WebSocket broadcasts are never blocked
- Failed event logging doesn't interrupt polling
- Each machine poller has its own async event task
- Errors are logged but don't crash the system

## Database Schema

### Programs Table
```sql
id SERIAL PRIMARY KEY
original_filename VARCHAR(500) NOT NULL UNIQUE(filename, version)
content_hash VARCHAR(64) NOT NULL UNIQUE
posted_date TIMESTAMPTZ              -- From CAM header
version_number INTEGER NOT NULL
program_metadata JSONB               -- tools, wcs_offset, stock_size
file_size_bytes INTEGER
line_count INTEGER
estimated_runtime_seconds FLOAT
first_seen_at TIMESTAMPTZ DEFAULT NOW()
last_deployed_at TIMESTAMPTZ
deployed_count INTEGER
is_active BOOLEAN DEFAULT TRUE
```

### Program Deployments Table
```sql
id SERIAL PRIMARY KEY
program_id INTEGER REFERENCES programs(id) ON DELETE CASCADE
machine_id INTEGER REFERENCES machines(id) ON DELETE CASCADE
deployed_filename VARCHAR(500)       -- "O2000.nc"
deployed_path VARCHAR(500)           -- "/PROGRAM/O2000.nc"
deployed_at TIMESTAMPTZ DEFAULT NOW()
validation_results JSONB
validation_passed BOOLEAN DEFAULT TRUE
is_current BOOLEAN DEFAULT TRUE      -- Current deployment for this O-number
replaced_at TIMESTAMPTZ
replaced_by INTEGER                  -- Reference to replacement deployment
```

### TimescaleDB Hypertables

All event tables use TimescaleDB hypertables for optimal time-series performance:

#### machine_status_events
- **Retention**: 1 year
- **Compression**: After 7 days
- Indexes on (machine_id, time DESC), status

#### alarm_events
- **Retention**: 2 years
- **Compression**: After 30 days
- Indexes on (machine_id, time DESC), alarm_code, cleared_at

#### production_runs
- **Retention**: 5 years
- **Compression**: After 90 days
- Indexes on (machine_id, started_at DESC), completion_status

## API Endpoints

### Program Management

**List all programs**
```
GET /api/machines/programs
Query params: filename, is_active, limit=100, offset=0
```

**Get program details**
```
GET /api/machines/programs/{id}
```

**Get all versions of a program**
```
GET /api/machines/programs/by-filename/{filename}
```

**Upload new program**
```
POST /api/machines/programs/upload
{
  "gcode_content": "...",
  "original_filename": "PART_123_OP1.NC",
  "machine_id": 1,              # optional
  "deployed_filename": "O2000.nc",  # optional, required if machine_id set
  "validate_before_upload": true
}
Response: { program, is_new_version, deployment, validation_results }
```

**Deploy existing program**
```
POST /api/machines/{machine_id}/programs/{program_id}/deploy
{
  "deployed_filename": "O2000.nc",
  "validate_before_upload": true
}
```

### History and Analytics

**Machine status history**
```
GET /api/machines/{id}/status-history
Query params: start_time, end_time, limit=500
```

**Machine alarms**
```
GET /api/machines/{id}/alarms
Query params: start_time, end_time, active_only=false, limit=100
```

**Active alarms across all machines**
```
GET /api/alarms/active
```

**Production history**
```
GET /api/machines/{id}/production-runs
GET /api/programs/{id}/production-runs
Query params: start_time, end_time, limit=100
```

**Deployment history**
```
GET /api/machines/{id}/deployments
GET /api/programs/{id}/deployments
Query params: limit=100
```

## Data Models

### SQLAlchemy Models

- **Program**: NC program with version tracking
- **ProgramDeployment**: O-number deployment record
- **MachineStatusEvent**: Status change history
- **AlarmEvent**: Alarm occurrence and resolution
- **ProductionRun**: Program execution tracking

### Pydantic Schemas

All models have corresponding Pydantic schemas for API validation:
- Request schemas: `*Create`, `*Request`
- Response schemas: `*Response`

## Testing

Comprehensive test suite validates all functionality:

```bash
python test_program_tracking.py
```

### Test Coverage

1. **Database Models**: Table creation, relationships, constraints
2. **Program Versioning**: Upload, deduplication, version detection
3. **Deployment**: O-number mapping, replacement tracking, history
4. **Event Models**: Status, alarm, and production run creation

**Result**: ✓ All 4/4 tests pass

## Migration Steps

1. Run the database migration:
   ```bash
   psql -U shatter_user -d shatter -f database/init/02-add-program-tracking.sql
   ```

2. The migration creates:
   - 5 new tables (programs, program_deployments, machine_status_events, alarm_events, production_runs)
   - Indexes for efficient querying
   - TimescaleDB hypertables with retention policies
   - Permissions for shatter_user

3. Verify with test suite:
   ```bash
   python test_program_tracking.py
   ```

## Configuration

### Environment Variables

```bash
# Database connection (already set)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=shatter
POSTGRES_USER=shatter_user
POSTGRES_PASSWORD=changeme

# Polling interval (default 5 seconds)
DEFAULT_POLL_INTERVAL=5
```

### Polling Configuration

Event logging is automatically integrated into the existing polling service:
- Runs every 5 seconds (configurable)
- Logs events asynchronously in background
- Non-blocking to WebSocket clients
- Automatic cleanup of inactive machines

## Performance Considerations

### TimescaleDB Hypertables

- Automatic partitioning by time
- Compression reduces storage by 90%+
- Efficient time-range queries
- Retention policies prevent unbounded growth

### Indexes

```sql
-- Optimized for common queries
idx_programs_filename      -- Program versions by name
idx_programs_hash          -- Content deduplication
idx_programs_metadata_gin  -- Metadata search

idx_deployments_program    -- Deployments of a program
idx_deployments_machine    -- Deployments on a machine
idx_deployments_current    -- Current O-number mapping

idx_status_machine_time    -- Machine status history
idx_alarms_machine_time    -- Machine alarm history
idx_runs_machine_time      -- Machine production history
```

### Background Processing

- Each machine has one async event task
- Separate DB session prevents blocking main polling thread
- Errors are logged but don't crash the system
- Memory efficient: only last_status is kept in-memory per poller

## Future Enhancements

- [ ] Program validation rules (tool availability, stock size)
- [ ] User tracking (who deployed program, who cleared alarm)
- [ ] Deployment approval workflow
- [ ] Real-time analytics dashboard
- [ ] Performance metrics aggregation
- [ ] Alert rules based on event patterns
- [ ] Integration with MES/ERP systems

## Support and Monitoring

### Health Endpoint

```bash
curl http://localhost:8000/health
{
  "status": "healthy",
  "polling_service": {
    "running": true,
    "active_machines": 3,
    "websocket_connections": 2
  }
}
```

### Logging

Event logging errors are logged but don't interrupt operations:
```
logger.error(f"Failed to log events for machine {machine_id}: {error}")
```

### Database Monitoring

Monitor TimescaleDB hypertable compression:
```sql
SELECT * FROM timescaledb_information.hypertables;
SELECT * FROM timescaledb_information.compression_settings;
```

## References

- [Program Versioning Strategy](./PROGRAM_VERSIONING.md)
- [API Documentation](./API.md)
- [Database Schema](./database/init/02-add-program-tracking.sql)
- [Test Suite](./test_program_tracking.py)
