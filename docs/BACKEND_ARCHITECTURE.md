# Backend Architecture

Comprehensive documentation of the Shatter backend architecture, services, and data flow.

## Overview

The Shatter backend is built on FastAPI, a modern Python web framework optimized for asynchronous operations and automatic API documentation. The architecture is designed for real-time CNC monitoring with concurrent polling, WebSocket broadcasting, and efficient data storage.

Kaeser / SIGMA CONTROL 2 **compressors** (kaeser-sc2-api sidecar + MQTT/REST, separate from CNC Telnet) are documented in [COMPRESSOR_INTEGRATION.md](COMPRESSOR_INTEGRATION.md).

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI 0.100+ | Async HTTP API, auto-generated docs |
| **ORM** | SQLAlchemy 2.0 | Database modeling and queries |
| **Database** | PostgreSQL 14 + TimescaleDB | Relational + time-series data |
| **Cache/Coordination** | In-process | Locks, caching, rate limiting (no Redis) |
| **Async Runtime** | asyncio | Concurrent I/O operations |
| **Telnet Client** | asyncio streams | Primary protocol for data polling (Port 10000) |
| **HTTP Client** | Raw sockets | Legacy Brother CNC HTTP protocol (deprecated for polling) |
| **FTP Client** | ftplib (stdlib) | File operations via FTP (file upload/download only) |
| **Settings** | Pydantic Settings | Type-safe configuration |
| **Logging** | Python logging | Structured application logs |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│                    WebSocket + REST API Calls                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Routers (API Endpoints)                                  │   │
│  │  - machines.py    - status.py      - programs.py         │   │
│  │  - history.py     - summary.py     - tools.py            │   │
│  │  - websocket.py                                           │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 │                                                │
│  ┌──────────────▼───────────────────────────────────────────┐   │
│  │ Services (Business Logic)                                │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐ │   │
│  │  │ PollingService  │  │ ProgramService  │  │ WS Mgr   │ │   │
│  │  │ (Background)    │  │ (Versioning)    │  │(Real-time│ │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────┬─────┘ │   │
│  │  ┌─────────────────┐                                     │   │
│  │  │ ToolService     │                                     │   │
│  │  │ (Analytics)     │                                     │   │
│  │  └────────┬────────┘                                     │   │
│  │           │                    │                 │       │   │
│  └───────────┼────────────────────┼─────────────────┼───────┘   │
│              │                    │                 │           │
│  ┌───────────▼────────────────────▼─────────────────▼───────┐   │
│  │ CNC Clients                                              │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │   │
│  │  │CNCTelnetClient│  │ CNCHttpClient │  │ CNCFtpClient │ │   │
│  │  │ (Primary)     │  │ (Legacy)      │  │ (File Ops)   │ │   │
│  │  └───────┬───────┘  └───────┬───────┘  └──────┬───────┘ │   │
│  └──────────┼──────────────────┼─────────────────┼──────────┘   │
└─────────────┼──────────────────┼─────────────────┼──────────────┘
              │                   │                 │
              ▼                   ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Brother CNC Machines                          │
│  Telnet (Port 10000): MONTR, PRD3, ALARM, tools, MEM, POSN     │
│  FTP Server (Port 21): File upload/download/list                │
│  HTTP (Port 80): Legacy endpoints (deprecated for polling)      │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│               PostgreSQL + TimescaleDB                           │
│  - machines (config)        - programs (G-code)                  │
│  - program_deployments      - machine_status_events              │
│  - alarm_events             - production_runs                    │
│  - polling_events                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Application Entry Point

The application is initialized and configured in [main.py](../backend/app/main.py).

### Application Initialization

```python
# Global service instances created at module level
websocket_manager = WebSocketManager()
polling_service = PollingService(websocket_manager)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CNC Management Platform for Brother CNC Machines",
)
```

**Location:** [main.py:13-20](../backend/app/main.py#L13-L20)

**Key Design Decision:** Services are instantiated at module level (not per-request) to maintain state across the application lifetime. This enables:
- Single polling loop shared across all requests
- Persistent WebSocket connection management
- Cached machine status accessible to all API endpoints

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Location:** [main.py:23-29](../backend/app/main.py#L23-L29)

**Default Origins:** Development (localhost:3000, localhost:5173), Production (localhost:80), Wildcard (for isolated networks)

**Configuration:** See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for CORS_ORIGINS settings

### Router Registration

```python
app.include_router(machines.router, prefix="/api/machines", tags=["machines"])
app.include_router(status.router, prefix="/api/machines", tags=["status"])
app.include_router(programs.router, prefix="/api/programs", tags=["programs"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(summary.router, prefix="/api", tags=["summary"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
```

**Location:** [main.py:56-61](../backend/app/main.py#L56-L61)

**Design Pattern:** Routers are organized by resource type (machines, programs) and functionality (status, history, summary). Each router file contains related endpoints.

See [API_REFERENCE.md](API_REFERENCE.md) for complete endpoint documentation.

### Service Injection

Services are injected into routers that need access to global state:

```python
# Inject websocket manager into websocket router
websocket.set_websocket_manager(websocket_manager)

# Inject polling service into summary router
summary.set_polling_service(polling_service)
```

**Location:** [main.py:64-67](../backend/app/main.py#L64-L67)

**Why:** Routers need access to service instances to:
- WebSocket router: Accept connections and send messages
- Summary router: Query cached polling status from PollingService

## Application Lifecycle

### Startup Event

```python
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    print("Starting background polling service...")
    await polling_service.start()
    print("Polling service started - monitoring all enabled machines")
```

**Location:** [main.py:106-119](../backend/app/main.py#L106-L119)

**Startup Flow:**
1. Application initialized by uvicorn/gunicorn
2. FastAPI runs startup event handlers
3. **Polling service started**
4. PollingService.start() launches background polling loop
5. Polling begins for all enabled machines in database
6. API becomes ready to accept requests

**Important:** 
- Locks, cache, and rate limiting are in-process (no external service required)
- The polling service starts BEFORE the first HTTP request arrives. This ensures real-time data is available immediately

### Shutdown Event

```python
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print(f"Shutting down {settings.APP_NAME}")
    print("Stopping background polling service...")
    await polling_service.stop()
    
    print("Polling service stopped")
```

**Location:** [main.py:122-143](../backend/app/main.py#L122-L143)

**Shutdown Flow:**
1. SIGTERM/SIGINT signal received (e.g., Ctrl+C, Docker stop)
2. FastAPI runs shutdown event handlers
3. PollingService.stop() cancels background tasks
4. Active polling tasks complete gracefully
5. WebSocket connections closed
6. Polling service stopped
7. Application exits

**Graceful Shutdown:** The polling service cancels its asyncio task and waits for in-flight polls to complete before exiting.

## Core Services

### PollingService

The PollingService manages background polling for all CNC machines, broadcasting real-time status updates via WebSocket.

**Location:** [polling.py:277-396](../backend/app/services/polling.py#L277-L396)

#### Initialization

```python
class PollingService:
    """Manages background polling for all machines."""

    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.pollers: Dict[int, MachinePoller] = {}  # machine_id -> poller
        self.polling_task: Optional[asyncio.Task] = None
        self.is_running = False
```

**Location:** [polling.py:280-284](../backend/app/services/polling.py#L280-L284)

**State Management:**
- `pollers`: Dict mapping machine ID to MachinePoller instance
- `polling_task`: Background asyncio task running the poll loop
- `is_running`: Boolean flag to control loop execution

#### Polling Loop

```python
async def _poll_loop(self):
    """Main polling loop."""
    while self.is_running:
        try:
            await self._poll_all_machines()

            # Wait for next polling interval (default 5 seconds)
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            await asyncio.sleep(5)
```

**Location:** [polling.py:307-320](../backend/app/services/polling.py#L307-L320)

**Flow:**
1. Poll all enabled machines concurrently
2. Sleep for 5 seconds (configurable via DEFAULT_POLL_INTERVAL)
3. Repeat until stopped

**Error Handling:** Exceptions in the loop are logged and don't crash the service. The loop continues after a 5-second delay.

#### Concurrent Machine Polling

```python
async def _poll_all_machines(self):
    """Poll all enabled machines concurrently."""
    db = SessionLocal()
    try:
        # Get all enabled machines from database
        machines = db.query(Machine).filter(Machine.enabled == True).all()

        if not machines:
            logger.debug("No enabled machines to poll")
            return

        # Update pollers for current machines
        current_machine_ids = {m.id for m in machines}

        # Remove pollers for deleted/disabled machines
        for machine_id in list(self.pollers.keys()):
            if machine_id not in current_machine_ids:
                del self.pollers[machine_id]
                logger.info(f"Removed poller for machine {machine_id}")

        # Add pollers for new machines
        for machine in machines:
            if machine.id not in self.pollers:
                self.pollers[machine.id] = MachinePoller(machine, self.websocket_manager)
                logger.info(f"Added poller for machine {machine.id} ({machine.name})")
            else:
                # Update machine reference with fresh DB data
                self.pollers[machine.id].machine = machine

        # Poll all machines concurrently
        poll_tasks = [
            self.pollers[machine.id].poll()
            for machine in machines
        ]

        results = await asyncio.gather(*poll_tasks, return_exceptions=True)

        # Broadcast results to WebSocket clients
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Polling task failed: {result}")
                continue

            await self.websocket_manager.broadcast_status(result)

        logger.debug(f"Polled {len(machines)} machines")

    finally:
        db.close()
```

**Location:** [polling.py:322-375](../backend/app/services/polling.py#L322-L375)

**Concurrency Model:**
1. Query database for all enabled machines (single query)
2. Update `pollers` dict:
   - Remove pollers for deleted/disabled machines
   - Add pollers for new machines
   - Update machine config for existing pollers
3. Create list of poll tasks (one per machine)
4. Execute all polls concurrently with `asyncio.gather()`
5. Broadcast all results to WebSocket clients

**Performance:** Concurrent polling means N machines are polled in parallel, not sequentially. Total poll time ≈ slowest machine response time, not sum of all response times.

**Dynamic Updates:** The service automatically picks up:
- New machines added to database
- Machines disabled/re-enabled
- IP address changes (fresh machine object on each poll)

### MachinePoller

Each machine has a dedicated MachinePoller instance that handles polling and event logging.

**Location:** [polling.py:16-420](../backend/app/services/polling.py#L16-L420)

**Protocol Migration Status:** The polling service has been migrated to Telnet (Port 10000) for all data operations. HTTP endpoints are deprecated for polling. See [archive/BACKEND_TELNET_MIGRATION_PLAN.md](archive/BACKEND_TELNET_MIGRATION_PLAN.md) for migration details.

#### Poll Execution

**Note:** The polling service has been migrated to use Telnet (Port 10000) as the primary protocol for data fetching. HTTP endpoints are deprecated for polling (though HTTP client code remains for legacy support).

The polling service now uses Telnet to fetch:
- **MONTR** - Machine monitor data (program info, time data, workpiece counters)
- **PRD3/PRDD3** - Production data (machine status determination)
- **ALARM** - Current alarm data
- **PANEL** - Panel status data
- **Tool Data** - Both ATC (ATCTL) and TABLE (TOLNI1/TOLNM1) sources
- **MEM** - Memory/program information (on-demand)

```python
async def poll(self) -> Dict[str, Any]:
    """Poll machine status and return data."""
    # Uses Telnet client with per-poll connections
    from app.clients.telnet_client import create_fresh_connection

    telnet_client = await create_fresh_connection(
        ip_address=self.machine.ip_address,
        port=10000,
        timeout=10
    )
    
    # Fetch MONTR data (replaces HTTP /running_log and /work_counter)
    montr_data = await telnet_client.get_monitor_data(verbose=False)
    
    # Fetch PRD3 data (replaces status inference from HTTP)
    prd3_data = await telnet_client.get_prd3_data(control_version=control_version, verbose=False)
    
    # Fetch ALARM data (replaces HTTP /alarm_log)
    alarm_data = await telnet_client.get_alarm_data(verbose=False)
    
    # Fetch tool data via Telnet (replaces HTTP /tool and FTP TOLNI1.NC)
    tool_table_content = await telnet_client.get_tool_table_data(units=self.machine.units, verbose=False)
    atc_data = await telnet_client.get_atc_magazine_data(control_version=None, verbose=False)
    
    # ... parse and merge data ...
```

**Location:** [polling.py:72-377](../backend/app/services/polling.py#L72-L377)

**Flow:**
1. Create fresh Telnet connection for machine
2. Fetch MONTR data (program info, time data, counters)
3. Fetch PRD3 data (machine status)
4. Fetch ALARM data (active alarms)
5. Fetch tool data (ATC and TABLE sources)
6. Parse and merge all data sources
7. Calculate response time and update poller state
8. Launch background task to log events to database
9. Return status data (for WebSocket broadcast)
10. Connection is automatically cleaned up (per-poll connections)

**Non-Blocking Design:** Event logging is launched as a background task (`asyncio.create_task()`) so it doesn't block the poll loop. This ensures slow database writes don't delay polling.

#### Event Logging

```python
async def _log_events_async(self, status_data: Dict[str, Any], poll_timestamp: datetime, response_time_ms: int, success: bool):
    """
    Log events to database in background (non-blocking).

    Events logged:
    - Polling event (success/failure with response time)
    - Status transitions (running → stopped, etc.)
    - Alarms (only when status == 'alarm')
    - Production run start/end
    - Updates machine.last_seen_at to track successful polls
    """
    db = SessionLocal()
    try:
        # Log polling event
        polling_event = PollingEvent(
            time=poll_timestamp,
            machine_id=self.machine.id,
            success=success,
            response_time_ms=response_time_ms,
        )
        db.add(polling_event)

        # Update last_seen_at to track successful polling
        machine = db.query(Machine).filter(Machine.id == self.machine.id).first()
        if machine:
            machine.last_seen_at = poll_timestamp
            db.add(machine)

        current_status = status_data.get("status")

        # Log status transition (in-memory tracking)
        if self.last_status != current_status:
            await self._log_status_event(db, status_data, current_status)
            self.last_status = current_status

        # Log alarms only when status indicates alarm
        if current_status == "alarm":
            await self._log_alarms(db, status_data)

        # Log production run start/end
        await self._log_production_run(db, status_data)

        db.commit()
    except Exception as e:
        logger.error(f"Error logging events for machine {self.machine.id}: {e}")
        db.rollback()
    finally:
        db.close()
```

**Location:** [polling.py:97-144](../backend/app/services/polling.py#L97-L144)

**Events Logged:**
1. **PollingEvent**: Every poll (success/failure, response time)
2. **MachineStatusEvent**: Status transitions (running → stopped, etc.)
3. **AlarmEvent**: New alarms detected (when status == "alarm")
4. **ProductionRun**: Program start/end tracking

**Database Design:** Uses separate database session (`SessionLocal()`) to avoid conflicts with the main request session. The session is closed after commit.

#### Status Transition Tracking

```python
async def _log_status_event(self, db: Session, status_data: Dict[str, Any], current_status: str):
    """Log machine status change event."""
    try:
        event = MachineStatusEvent(
            time=datetime.utcnow(),
            machine_id=self.machine.id,
            status=current_status,
            previous_status=self.last_status,
            program_name=status_data.get("program_name"),
            o_number=status_data.get("o_number"),
            metrics={
                "cycle_time_seconds": status_data.get("cycle_time_seconds"),
                "cutting_time_seconds": status_data.get("cutting_time_seconds"),
                "power_on_hours": status_data.get("power_on_hours"),
            }
        )
        db.add(event)
        logger.debug(f"Logged status event for machine {self.machine.id}: {self.last_status} → {current_status}")
    except Exception as e:
        logger.error(f"Failed to log status event: {e}")
        raise
```

**Location:** [polling.py:146-166](../backend/app/services/polling.py#L146-L166)

**Design Decision:** Uses in-memory tracking (`self.last_status`) to detect transitions efficiently. This avoids querying the database on every poll to determine if status changed.

**Tracked Metrics:**
- Status change (e.g., "stopped" → "running")
- Current program name and O-number
- Cycle time, cutting time, power-on hours (snapshot at transition)

#### Alarm Logging

```python
async def _log_alarms(self, db: Session, status_data: Dict[str, Any]):
    """
    Log alarm events.

    Fetches active alarms from machine and logs any new ones to database.
    """
    try:
        # Get alarms from machine
        http_client = CNCHttpClient(
            self.machine.ip_address,
            port=self.machine.http_port,
            timeout=5,
        )
        alarms = http_client.get_alarms()

        if not alarms:
            logger.debug(f"No alarms found for machine {self.machine.id}")
            return

        # Log each alarm that isn't already in the database
        for alarm in alarms:
            alarm_code = alarm.get("code", "UNKNOWN")

            # Check if this alarm is already logged and still active
            existing = db.query(AlarmEvent).filter(
                AlarmEvent.machine_id == self.machine.id,
                AlarmEvent.alarm_code == alarm_code,
                AlarmEvent.cleared_at.is_(None)
            ).first()

            if not existing:
                # New alarm - log it
                event = AlarmEvent(
                    time=datetime.utcnow(),
                    machine_id=self.machine.id,
                    alarm_code=alarm_code,
                    alarm_message=alarm.get("message", ""),
                    alarm_type=alarm.get("type"),
                    severity=alarm.get("severity"),
                )
                db.add(event)
                logger.info(f"Logged alarm for machine {self.machine.id}: {alarm_code} - {alarm.get('message', '')}")

    except Exception as e:
        logger.error(f"Failed to log alarms for machine {self.machine.id}: {e}")
        # Don't raise - alarm logging shouldn't block production run tracking
```

**Location:** [polling.py:168-213](../backend/app/services/polling.py#L168-L213)

**Alarm Deduplication:** Queries database to check if alarm is already logged and active (`cleared_at IS NULL`). Only new alarms are inserted.

**Error Handling:** Exceptions during alarm logging are logged but not raised. This prevents alarm fetch failures from blocking production run tracking.

#### Production Run Tracking

```python
async def _log_production_run(self, db: Session, status_data: Dict[str, Any]):
    """
    Track production run start/end.

    - Detects when program starts running (status == 'running')
    - Detects when program stops running (status in ['stopped', 'idle', 'alarm'])
    """
    try:
        current_status = status_data.get("status")
        program_name = status_data.get("program_name")

        # Check for active production run
        active_run = db.query(ProductionRun).filter(
            ProductionRun.machine_id == self.machine.id,
            ProductionRun.ended_at.is_(None)
        ).first()

        # Start new production run
        if current_status == "running" and program_name and program_name != "----":
            if not active_run:
                run = ProductionRun(
                    machine_id=self.machine.id,
                    program_name=program_name,
                    o_number=status_data.get("o_number"),
                    started_at=datetime.utcnow(),
                )
                db.add(run)
                logger.debug(f"Started production run for machine {self.machine.id}: {program_name}")

        # End active production run
        elif current_status in ["stopped", "idle", "alarm"] and active_run:
            active_run.ended_at = datetime.utcnow()
            active_run.duration_seconds = int(
                (active_run.ended_at - active_run.started_at).total_seconds()
            )
            active_run.completion_status = "completed" if current_status == "stopped" else current_status
            logger.debug(f"Ended production run for machine {self.machine.id}: {active_run.program_name}")

    except Exception as e:
        logger.error(f"Failed to log production run for machine {self.machine.id}: {e}")
        # Don't raise - production run logging shouldn't block other events
```

**Location:** [polling.py:215-255](../backend/app/services/polling.py#L215-L255)

**Run Detection:**
- **Start:** status == "running" AND program_name is not "----" AND no active run
- **End:** status in ["stopped", "idle", "alarm"] AND active run exists

**Completion Status:**
- "completed" if status == "stopped" (normal program end)
- Current status if stopped for other reasons ("idle", "alarm")

### ProgramService

The ProgramService handles NC program upload, versioning, and deployment to machines.

**Location:** [program_service.py:12-260](../backend/app/services/program_service.py#L12-L260)

#### Version Control

```python
def upload_program(
    self,
    gcode_content: str,
    original_filename: str,
    machine_id: Optional[int] = None,
    deployed_filename: Optional[str] = None,
    validate: bool = True,
    validation_results: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Upload a new NC program and optionally deploy to machine.

    Version Detection Logic:
    1. Parse G-code and extract metadata
    2. Compute SHA-256 hash of content
    3. Check if program with this hash already exists
       - If exists: Return existing program (no duplicate)
       - If new: Continue to step 4
    4. Get MAX(version_number) for this filename
    5. Insert new program with version_number = MAX + 1
    """
    # Step 1: Parse G-code
    try:
        parsed_metadata = parse_gcode(gcode_content)
    except Exception as e:
        raise ValueError(f"Failed to parse G-code: {str(e)}")

    # Step 2: Compute content hash
    content_hash = Program.compute_hash(gcode_content)

    # Step 3: Check if program already exists (by hash)
    existing_program = self.db.query(Program).filter(
        Program.content_hash == content_hash
    ).first()

    if existing_program:
        # Program already exists - return existing record (no duplicate)
        result = {
            "program": existing_program,
            "is_new_version": False,
            "deployment": None,
            "validation_results": None
        }

        # If deploying existing program, still create deployment record
        if machine_id and deployed_filename:
            deployment = self.deploy_program(
                program_id=existing_program.id,
                machine_id=machine_id,
                deployed_filename=deployed_filename,
                validate=validate,
                validation_results=validation_results
            )
            result["deployment"] = deployment

        return result

    # Step 4: Determine version number
    max_version = self.db.query(func.max(Program.version_number)).filter(
        Program.original_filename == original_filename
    ).scalar()

    version_number = (max_version or 0) + 1

    # Step 5: Create new Program record
    new_program = Program(
        original_filename=original_filename,
        content_hash=content_hash,
        posted_date=parsed_metadata.get("posted_date"),
        version_number=version_number,
        program_metadata={
            "tools": parsed_metadata.get("tools", []),
            "wcs_offset": parsed_metadata.get("wcs_offset"),
            "stock_size": parsed_metadata.get("stock_size"),
        },
        file_size_bytes=parsed_metadata.get("file_size", 0),
        line_count=parsed_metadata.get("line_count", 0),
        estimated_runtime_seconds=parsed_metadata.get("estimated_runtime_seconds"),
    )

    self.db.add(new_program)
    self.db.commit()
    self.db.refresh(new_program)

    # ... deployment logic ...
```

**Location:** [program_service.py:18-136](../backend/app/services/program_service.py#L18-L136)

**Content-Based Deduplication:**
- SHA-256 hash computed from G-code content
- Identical content → same hash → no duplicate record
- Different content → new version created

**Version Numbering:**
- Per-filename versioning (PART_123.nc v1, v2, v3...)
- Version number = MAX(existing versions) + 1
- First version of file = v1

**Parsed Metadata Storage:**
```json
{
  "tools": [
    {"tool_number": 1, "diameter": 0.5, "corner_radius": 0.0, "description": "1/2 ENDMILL"}
  ],
  "wcs_offset": {"x": 0.0, "y": 0.0, "z": -5.0, "work_offset": 54, "tolerance": 0.001},
  "stock_size": {"x": 146.05, "y": 25.4, "z": 12.7}
}
```

**Why Content Hash?** Prevents uploading the same program multiple times. If user uploads identical G-code with different filename, system recognizes it and links to existing record.

#### Deployment Management

```python
def deploy_program(
    self,
    program_id: int,
    machine_id: int,
    deployed_filename: str,
    validate: bool = True,
    validation_results: Optional[Dict[str, Any]] = None
) -> ProgramDeployment:
    """
    Deploy a program to a machine with O-number mapping.

    Deployment Flow:
    1. Validate program against machine (if requested)
    2. Mark any existing deployment with same O-number as replaced
    3. Create new deployment record
    4. Update program deployment stats
    """
    # Get program and machine
    program = self.db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise ValueError(f"Program {program_id} not found")

    machine = self.db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise ValueError(f"Machine {machine_id} not found")

    # Determine if validation passed
    if validation_results is not None:
        validation_passed = validation_results.get("valid", True)
    else:
        validation_results = {}
        validation_passed = None  # No validation performed

    # Construct deployment path
    deployed_path = f"{machine.path}/{deployed_filename}"

    # Mark existing deployment as replaced (if O-number already in use)
    existing_deployment = self.db.query(ProgramDeployment).filter(
        ProgramDeployment.machine_id == machine_id,
        ProgramDeployment.deployed_filename == deployed_filename,
        ProgramDeployment.is_current == True
    ).first()

    if existing_deployment:
        existing_deployment.is_current = False
        existing_deployment.replaced_at = datetime.utcnow()
        # Will set replaced_by after creating new deployment

    # Create deployment record
    deployment = ProgramDeployment(
        program_id=program_id,
        machine_id=machine_id,
        deployed_filename=deployed_filename,
        deployed_path=deployed_path,
        validation_results=validation_results,
        validation_passed=validation_passed,
        is_current=True
    )

    self.db.add(deployment)
    self.db.commit()
    self.db.refresh(deployment)

    # Update existing deployment with replaced_by reference
    if existing_deployment:
        existing_deployment.replaced_by = deployment.id
        self.db.commit()

    # Update program deployment stats
    program.last_deployed_at = datetime.utcnow()
    program.deployed_count = (program.deployed_count or 0) + 1
    self.db.commit()

    return deployment
```

**Location:** [program_service.py:138-223](../backend/app/services/program_service.py#L138-L223)

**O-Number Reuse Tracking:**
- Each deployment has `is_current` flag
- When O-number is reused, previous deployment marked as replaced:
  - `is_current = False`
  - `replaced_at = <timestamp>`
  - `replaced_by = <new deployment ID>`
- Full history of what was deployed to each O-number

**Deployment Path:** Combines machine.path + deployed_filename (e.g., "/PROGRAM/O2000.nc")

**Validation Storage:** Validation results stored in JSONB column for later review. See [PROGRAM_VALIDATION.md](PROGRAM_VALIDATION.md) for validation workflow details.

### ToolService

The ToolService aggregates tool usage data across programs and provides detailed speed/feed analysis for machining operations.

**Location:** [tool_service.py:12-220](../backend/app/services/tool_service.py#L12-L220)

#### Tool Summary Aggregation

```python
@staticmethod
def get_tool_summary(db: Session) -> ToolSummaryResponse:
    """
    Get aggregated summary of all tools across all programs.

    Aggregation Logic:
    1. Query program_metadata JSONB for all tools
    2. Group by tool_number and aggregate:
       - Count unique programs using each tool
       - Sum estimated runtime across programs
       - Collect unique operation names
       - Track machines where tool was used
    3. Enrich with tool descriptions from ATC data
    """
    query = text("""
        SELECT DISTINCT
            (tool_data->>'tool_number')::int as tool_number,
            (tool_data->>'diameter')::float as diameter,
            tool_data->>'description' as description
        FROM programs,
             jsonb_array_elements(program_metadata->'tools') as tool_data
        WHERE is_active = TRUE
        ORDER BY tool_number
    """)
```

**Location:** [tool_service.py:15-75](../backend/app/services/tool_service.py#L15-L75)

**Data Sources:**
- `program_metadata->tools`: JSONB array containing tool data per program
- `production_runs`: Count of actual machine runs using each tool
- `deployments`: Machine usage tracking

**Key Aggregations:**
- `programs_using`: Count of programs using tool
- `estimated_runtime_seconds`: Sum of runtime across all programs
- `operation_types`: Unique operation names (e.g., "ADAPTIVE1", "2D CONTOUR1")
- `machines_used`: Array of machine IDs where tool was deployed

#### Tool Detail with Per-Program Operations

```python
@staticmethod
def get_tool_detail(db: Session, tool_number: int) -> ToolDetail:
    """
    Get detailed analysis for a specific tool with per-program operations.

    Critical Design: Operations are NOT aggregated across programs.

    Data Structure:
    {
      "programs": [
        {
          "program_id": 5,
          "operations": [
            {
              "operation_name": "ADAPTIVE1",
              "spindle_speed": 5000.0,
              "feedrate_cutting": 39.4,
              "feedrate_plunge": 25.0,
              "feedrate_finish": 50.0,
              "feedrate_entry": 39.4,
              "feedrate_exit": 39.4,
              "feedrate_direct": 787.4,
              "feedrate_transition": 100.0
            }
          ]
        }
      ]
    }

    Rationale: Same operation name (e.g., "ADAPTIVE1") may have different
    speed/feed values in different programs. Aggregating would lose this
    critical per-program context.
    """
```

**Location:** [tool_service.py:78-150](../backend/app/services/tool_service.py#L78-L150)

**Per-Program Operation Extraction:**
```python
# Extract operations for this tool from each program's metadata
operations = []
if row.program_metadata and 'tools' in row.program_metadata:
    for tool in row.program_metadata['tools']:
        if tool.get('tool_number') == tool_number:
            tool_operations = tool.get('operations', [])
            for op in tool_operations:
                operations.append(OperationStats(
                    operation_name=op.get('operation_name'),
                    spindle_speed=op.get('spindle_speed'),
                    feedrate_cutting=op.get('feedrate_cutting'),
                    feedrate_plunge=op.get('feedrate_plunge'),
                    feedrate_finish=op.get('feedrate_finish'),
                    feedrate_entry=op.get('feedrate_entry'),
                    feedrate_exit=op.get('feedrate_exit'),
                    feedrate_direct=op.get('feedrate_direct'),
                    feedrate_transition=op.get('feedrate_transition')
                ))
```

**All 8 Feedrate Types Captured:**
1. `feedrate_cutting` - Primary cutting feedrate (IPM)
2. `feedrate_plunge` - Z-axis plunge rate (IPM)
3. `feedrate_finish` - Finish pass feedrate (IPM)
4. `feedrate_entry` - Entry move feedrate (IPM)
5. `feedrate_exit` - Exit move feedrate (IPM)
6. `feedrate_direct` - Direct/rapid traverse feedrate (IPM)
7. `feedrate_transition` - Transition feedrate between moves (IPM)
8. `spindle_speed` - Spindle RPM

**Null Handling:** Operations may have `null` values for unused feedrate types (e.g., finish pass not always used).

#### Tool-Related Alarms

```python
@staticmethod
def _get_tool_alarms(db: Session, tool_number: int) -> List[ToolAlarm]:
    """
    Get alarm history for a specific tool.

    Queries alarm_events table for alarms starting with 'T' code
    and correlates with program deployments to identify tool-related issues.
    """
```

**Location:** [tool_service.py:183-215](../backend/app/services/tool_service.py#L183-215)

**Alarm Correlation:**
- Filters for alarm codes matching `T*` pattern (tool alarms)
- Groups by program to show alarm frequency per program
- Provides last occurrence timestamp for each alarm type

#### Export Utilities

The service integrates with export utilities for CSV/JSON generation:

```python
# Backend generates flattened CSV structure
flattened = flatten_tool_data_for_csv(
    tool_number=tool.tool_number,
    diameter=tool.diameter,
    description=tool.description,
    total_runtime_seconds=tool.estimated_runtime_seconds,
    total_programs=tool.programs_using,
    total_runs=tool.total_runs,
    programs=programs  # Contains nested operations
)
```

**CSV Structure:**
- One row per program operation
- Tool summary repeated for each row
- Program context (ID, filename, version) included
- All 8 feedrate columns

**Location:** [export_utils.py:49-155](../backend/app/utils/export_utils.py#L49-L155)

#### Future: Physical Tool Tracking

The `tool_instances` table is prepared for future physical tool lifecycle tracking:

```sql
CREATE TABLE tool_instances (
    id SERIAL PRIMARY KEY,
    tool_number INTEGER NOT NULL,
    serial_number VARCHAR(100),
    purchase_date DATE,
    install_date TIMESTAMPTZ,
    total_runtime_hours FLOAT,
    total_parts_produced INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    retirement_date TIMESTAMPTZ,
    retirement_reason VARCHAR(500)
);
```

**Planned Features:**
- Track individual tool lifecycle (purchase → retirement)
- Monitor tool wear and replacement intervals
- Correlate tool quality with machining outcomes
- Predictive maintenance based on usage patterns

### WebSocketManager

The WebSocketManager handles real-time bidirectional communication with frontend clients.

**Location:** [websocket.py:13-124](../backend/app/services/websocket.py#L13-L124)

#### Connection Management

```python
class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_status: Dict[int, Dict[str, Any]] = {}  # machine_id -> status

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send initial status for all machines (from DB + cached polling data)
        try:
            db = SessionLocal()
            try:
                # Get all machines from database
                all_machines = db.query(Machine).all()

                # Clean up cache for deleted machines
                all_machine_ids = {m.id for m in all_machines}
                deleted_ids = [mid for mid in self.last_status.keys() if mid not in all_machine_ids]
                for mid in deleted_ids:
                    del self.last_status[mid]
                    logger.info(f"Cleaned up cache for deleted machine {mid}")

                machines_data = []

                for machine in all_machines:
                    # Start with database info
                    machine_info = {
                        "machine_id": machine.id,
                        "machine_name": machine.name,
                        "ip_address": machine.ip_address,
                        "enabled": machine.enabled,
                        "poll_timestamp": datetime.utcnow().isoformat(),
                    }

                    # Overlay cached polling data if available
                    if machine.id in self.last_status:
                        cached = self.last_status[machine.id]
                        machine_info.update(cached)
                    else:
                        # No polling data yet - assume offline until first poll
                        machine_info["is_online"] = False

                    machines_data.append(machine_info)

                # Send all machines to new client
                await websocket.send_json({
                    "type": "initial_status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "machines": machines_data,
                })
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error sending initial status: {e}")
```

**Location:** [websocket.py:20-71](../backend/app/services/websocket.py#L20-L71)

**Initial Status Message:**
When a client connects, they immediately receive status for ALL machines. This ensures the dashboard shows data without waiting for the next poll cycle.

**Data Sources:**
1. Database: Machine configuration (name, IP, enabled status)
2. Cache (`self.last_status`): Latest polling data (if available)

**Cache Cleanup:** Deleted machines are removed from cache on each new connection.

#### Broadcasting

```python
async def broadcast_status(self, status_data: Dict[str, Any]):
    """Broadcast machine status to all connected clients."""
    # Always cache the status, even if there are no active connections
    # This ensures the status is available for API queries
    machine_id = status_data.get("machine_id")
    if machine_id:
        self.last_status[machine_id] = status_data

    if not self.active_connections:
        return

    message = {
        "type": "status_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": status_data,
    }

    # Send to all connected clients
    disconnected = []
    for connection in self.active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            disconnected.append(connection)

    # Clean up disconnected clients
    for connection in disconnected:
        self.disconnect(connection)
```

**Location:** [websocket.py:79-107](../backend/app/services/websocket.py#L79-L107)

**Broadcast Flow:**
1. Cache status data in `self.last_status` (even if no connections)
2. Skip broadcast if no active connections
3. Create status_update message
4. Send to all connected clients
5. Track failed sends
6. Clean up disconnected clients

**Why Cache?**
- New WebSocket connections get latest data immediately
- API endpoints can query cached status (faster than polling)
- Status available even when no WebSocket clients connected

**Error Handling:** Failed sends are logged and tracked. Disconnected clients are removed from active list.

## Request Flow

### Typical HTTP Request Flow

```
1. Client Request
   └─> FastAPI Router
       └─> Endpoint Handler
           ├─> Dependency Injection (get_db)
           ├─> Request Validation (Pydantic)
           └─> Business Logic
               ├─> Service Layer (ProgramService)
               ├─> CNC Client (CNCHttpClient/CNCFtpClient)
               │   └─> Brother CNC Machine
               ├─> Database Query (SQLAlchemy)
               └─> WebSocket Broadcast
                   └─> Connected Clients

2. Response
   ├─> Pydantic Schema Serialization
   └─> JSON Response to Client
```

### Example: Upload Program Flow

**Endpoint:** `POST /api/programs/machines/{machine_id}/programs/upload`

**Location:** [programs.py:123-200](../backend/app/api/programs.py#L123-L200)

**Flow:**
1. Client uploads G-code file to API endpoint
2. FastAPI validates request (file content, machine_id)
3. Endpoint calls ProgramService.upload_program()
4. Service parses G-code, computes hash, checks for duplicates
5. Service creates Program record in database
6. If deploying: CNCFtpClient uploads file to machine via FTP
7. Service creates ProgramDeployment record
8. Response sent to client with program/deployment details

### Example: Polling Flow

**Triggered By:** Background PollingService loop (every 5 seconds)

**Flow:**
1. PollingService._poll_loop() triggers every 5 seconds
2. Service queries database for enabled machines
3. Service creates MachinePoller.poll() task for each machine
4. Tasks executed concurrently with asyncio.gather()
5. Each poller:
   - Creates CNCHttpClient
   - Sends HTTP request to CNC machine
   - Parses response HTML
   - Returns status dict
6. PollingService receives all results
7. For each result: WebSocketManager.broadcast_status()
8. WebSocket clients receive real-time updates

**No API Call Required:** Polling happens automatically in background. Frontend only needs to maintain WebSocket connection to receive updates.

## Design Patterns

### Service Layer Pattern

**Purpose:** Separate business logic from API routing logic

**Implementation:**
- **Routers** (`api/`) handle HTTP concerns (request validation, response formatting)
- **Services** (`services/`) contain business logic (version control, polling, broadcasting)
- **Clients** (`clients/`) handle external communication (HTTP, FTP)

**Example:**
```python
# Router (api/programs.py) - HTTP concerns
@router.post("/upload")
async def upload_program(file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()

    # Delegate to service
    service = ProgramService(db)
    result = service.upload_program(content, file.filename)

    return result

# Service (services/program_service.py) - Business logic
class ProgramService:
    def upload_program(self, content, filename):
        # Parse, validate, version, store
        pass
```

### Dependency Injection

**Purpose:** Manage database sessions and service instances

**Database Session:**
```python
from app.db.base import get_db

@router.get("/programs")
async def list_programs(db: Session = Depends(get_db)):
    programs = db.query(Program).all()
    return programs
```

**Service Injection:**
```python
# Global service instances
websocket_manager = WebSocketManager()
polling_service = PollingService(websocket_manager)

# Inject into routers
websocket.set_websocket_manager(websocket_manager)
```

**Benefits:**
- Automatic session lifecycle management
- Shared service instances across requests
- Testability (can inject mock dependencies)

### Repository Pattern (Implicit)

**Purpose:** Abstract database access

**Implementation:**
Services use SQLAlchemy ORM as an implicit repository:

```python
class ProgramService:
    def __init__(self, db: Session):
        self.db = db

    def get_program_by_hash(self, content_hash: str) -> Optional[Program]:
        """Get program by content hash."""
        return self.db.query(Program).filter(
            Program.content_hash == content_hash
        ).first()
```

**Why Implicit?** For this application's scale, SQLAlchemy queries are sufficient. Explicit repository classes would add unnecessary abstraction.

### Observer Pattern (WebSocket Broadcasting)

**Purpose:** Notify multiple clients of state changes

**Implementation:**
```python
# PollingService polls machines
for result in poll_results:
    # Notify all observers (WebSocket clients)
    await self.websocket_manager.broadcast_status(result)

# WebSocketManager maintains observer list
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []  # Observers

    async def broadcast_status(self, status_data):
        for connection in self.active_connections:
            await connection.send_json(status_data)
```

### Background Task Pattern

**Purpose:** Run long-lived tasks without blocking requests

**Implementation:**
```python
# Non-blocking event logging
asyncio.create_task(self._log_events_async(status_data, poll_timestamp, response_time_ms, success=True))
```

**Why?** Ensures slow database writes don't delay polling or HTTP responses.

## Error Handling

### Client-Level Errors

**CNCHttpClient:**
```python
try:
    response = self._send_request("/running_log")
    return self._parse_running_log(response)
except socket.timeout:
    raise TimeoutError(f"Connection to {self.ip_address} timed out")
except socket.error as e:
    raise ConnectionError(f"Failed to connect to {self.ip_address}: {e}")
```

**Location:** [http_client.py:89-94](../backend/app/clients/http_client.py#L89-L94)

**Strategy:** Convert low-level socket errors to domain-specific exceptions (TimeoutError, ConnectionError)

**CNCFtpClient:**
```python
except asyncio.TimeoutError:
    logger.error(f"Timeout listing files on {self.ip_address}")
    raise Exception(f"FTP connection timeout after {self.timeout} seconds")
except ConnectionResetError:
    logger.error(f"FTP connection reset by {self.ip_address}")
    raise Exception("FTP server connection reset - server may be busy or offline")
```

**Location:** [ftp_client.py:215-220](../backend/app/clients/ftp_client.py#L215-L220)

**Strategy:** Wrap asyncio/network exceptions with user-friendly messages

### Service-Level Errors

**PollingService:**
```python
try:
    # Poll machine
    status_data = http_client.get_status_overview()
except Exception as e:
    self.consecutive_failures += 1
    self.is_online = False

    logger.error(f"Error polling machine {self.machine.id}: {e}")

    return {
        "machine_id": self.machine.id,
        "is_online": False,
        "error": str(e),
        "consecutive_failures": self.consecutive_failures,
    }
```

**Location:** [polling.py:67-95](../backend/app/services/polling.py#L67-L95)

**Strategy:**
- Log errors
- Track failure count
- Return error status (don't crash polling loop)
- Continue polling other machines

**ProgramService:**
```python
# Step 1: Parse G-code
try:
    parsed_metadata = parse_gcode(gcode_content)
except Exception as e:
    raise ValueError(f"Failed to parse G-code: {str(e)}")
```

**Location:** [program_service.py:55-58](../backend/app/services/program_service.py#L55-L58)

**Strategy:** Re-raise as ValueError with context. API endpoint will catch and return 400 Bad Request.

### API-Level Errors

**Example from programs.py:**
```python
@router.post("/validate-file")
async def validate_file_on_machine(
    machine_id: int,
    file_path: str,
    db: Session = Depends(get_db)
):
    try:
        # ... validation logic ...
    except Exception as e:
        logger.error(f"Error validating file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate file: {str(e)}"
        )
```

**Strategy:**
- Catch service/client exceptions
- Log error details
- Return HTTPException with appropriate status code
- Include user-friendly error message

**HTTP Status Codes:**
- 400: Bad Request (invalid input, parsing errors)
- 404: Not Found (machine/program doesn't exist)
- 500: Internal Server Error (connection failures, database errors)
- 503: Service Unavailable (CNC unreachable)

### Database Error Handling

**Transaction Rollback:**
```python
try:
    db.add(polling_event)
    db.commit()
except Exception as e:
    logger.error(f"Error logging events: {e}")
    db.rollback()
finally:
    db.close()
```

**Location:** [polling.py:139-144](../backend/app/services/polling.py#L139-L144)

**Strategy:**
- Rollback on any exception
- Always close session in finally block
- Log error details

## Performance Considerations

### Concurrent Polling

**Design:** All machines polled concurrently using `asyncio.gather()`

```python
poll_tasks = [
    self.pollers[machine.id].poll()
    for machine in machines
]

results = await asyncio.gather(*poll_tasks, return_exceptions=True)
```

**Location:** [polling.py:356-361](../backend/app/services/polling.py#L356-L361)

**Performance Impact:**
- **Sequential:** 10 machines × 200ms = 2000ms per cycle
- **Concurrent:** max(200ms, 150ms, 180ms, ...) ≈ 200ms per cycle

**Scalability:** Can poll 100+ machines in ~200-500ms (depending on slowest machine)

### Non-Blocking Event Logging

**Design:** Database writes launched as background tasks

```python
# Don't await - returns immediately
asyncio.create_task(self._log_events_async(status_data, poll_timestamp, response_time_ms, success=True))
```

**Location:** [polling.py:63](../backend/app/services/polling.py#L63)

**Performance Impact:**
- **Blocking:** Poll time includes database write (50-200ms)
- **Non-Blocking:** Poll time only includes HTTP request (~50ms)

**Trade-off:** Database writes may fail silently. Mitigated by extensive logging and error tracking.

### WebSocket Caching

**Design:** Latest status cached in-memory

```python
# Always cache, even if no connections
machine_id = status_data.get("machine_id")
if machine_id:
    self.last_status[machine_id] = status_data
```

**Location:** [websocket.py:83-85](../backend/app/services/websocket.py#L83-L85)

**Performance Impact:**
- **Without Cache:** New connections wait up to 5 seconds for first poll
- **With Cache:** New connections get instant data from cache

**Memory:** ~1-5 KB per machine × 100 machines = ~100-500 KB total

### Connection Pooling

**Database:** SQLAlchemy connection pool

```python
# Default pool settings (can be configured)
engine = create_engine(
    settings.database_url,
    pool_size=5,          # Maintain 5 idle connections
    max_overflow=10,      # Allow 10 additional connections under load
    pool_pre_ping=True,   # Verify connection health before use
)
```

**Performance Impact:**
- Avoids connection overhead on each request
- Reuses existing connections
- Pre-ping prevents "connection closed" errors

### TimescaleDB Optimization

**Hypertables:** Automatically partition time-series data

```sql
-- Create hypertable for machine_status_events
SELECT create_hypertable('machine_status_events', 'time');

-- Set chunk interval (7 days)
SELECT set_chunk_time_interval('machine_status_events', INTERVAL '7 days');
```

**Performance Impact:**
- Old data automatically moved to compressed chunks
- Queries filtered by time range only scan relevant chunks
- Reduces query time for historical data (90 days)

**Retention Policies:**
- machine_status_events: 90 days
- alarm_events: 1 year
- production_runs: Indefinite
- polling_events: 30 days

See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for TimescaleDB configuration details.

### HTTP/1.0 for Brother CNC

**Design:** Uses HTTP/1.0 instead of HTTP/1.1

```python
# Send HTTP/1.0 request (CNC doesn't handle HTTP/1.1 properly)
request = f"GET {endpoint} HTTP/1.0\r\n\r\n".encode()
sock.send(request)
```

**Location:** [http_client.py:53](../backend/app/clients/http_client.py#L53)

**Why?** Brother CNC machines have non-standard HTTP implementation. HTTP/1.1 requests cause connection hangs.

**Performance Impact:** No keep-alive, but connections are fast enough (~50ms) that this doesn't matter.

## Configuration

All configuration is loaded from environment variables using Pydantic Settings.

**Location:** [config.py:6-66](../backend/app/core/config.py#L6-L66)

**Key Settings:**
- `APP_NAME`, `APP_VERSION`: Application metadata
- `BACKEND_HOST`, `BACKEND_PORT`: Server binding
- `POSTGRES_*`: Database connection
- `REDIS_*`: Cache connection (future)
- `DEFAULT_POLL_INTERVAL`: Polling frequency (default: 5 seconds)
- `CORS_ORIGINS`: Allowed origins for CORS

**Configuration Files:**
- `.env`: Local development
- `.env.production`: Production deployment
- Environment variables: Docker/K8s overrides

See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for complete configuration reference.

## Logging

**Configuration:**
```python
LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Logger Usage:**
```python
logger = logging.getLogger(__name__)

logger.debug(f"Polling machine {self.machine.id}")
logger.info(f"Added poller for machine {machine.id}")
logger.error(f"Error polling machine {self.machine.id}: {e}")
```

**Log Levels:**
- **DEBUG:** Verbose polling details (each poll, status transitions)
- **INFO:** Important state changes (service start/stop, machine add/remove)
- **ERROR:** Failures (connection errors, database errors)

**Production Recommendation:** Use INFO level to reduce log volume while capturing important events.

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

**Benefits:**
- Interactive request testing
- Schema definitions
- Example requests/responses

See [API_REFERENCE.md](API_REFERENCE.md) for detailed endpoint documentation.

## Related Documentation

- [API_REFERENCE.md](API_REFERENCE.md) - Complete REST API endpoint documentation
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database models and relationships
- [CNC_CLIENTS.md](CNC_CLIENTS.md) - HTTP/FTP client library details
- [PROGRAM_VALIDATION.md](PROGRAM_VALIDATION.md) - Program validation workflow
- [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) - WebSocket message format
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - Configuration reference
- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - Deployment guide
