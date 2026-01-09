# CNC Communication Clients

Shatter includes three client libraries for communicating with Brother CNC machines: HTTP, FTP, and Telnet.

## HTTP Client

**⚠️ DEPRECATED FOR POLLING**: The HTTP client is deprecated for data polling operations. The polling service has been migrated to use Telnet (Port 10000) for all data operations. HTTP endpoints may still be used for protocol detection and legacy fallback scenarios.

The `CNCHttpClient` handles HTTP endpoints on the CNC web server (primarily used for protocol detection now).

**📖 See [WEBSERVER_ENDPOINTS.md](WEBSERVER_ENDPOINTS.md) for complete documentation of all available HTTP endpoints on the Brother CNC machine webserver.**

### Features

- Raw socket connections (Brother CNC uses non-standard HTTP/1.1)
- HTML parsing for data extraction
- Multiple endpoint support

### Usage

```python
from app.clients.http_client import CNCHttpClient

# Initialize client
client = CNCHttpClient(
    ip_address="192.168.86.89",
    port=80,
    timeout=5
)

# Test connection
result = client.test_connection()
# {'success': True, 'latency_ms': 45.2, ...}

# Get running log data
data = client.get_running_log()
# {
#     'program_name': 'O2045',
#     'cycle_time': '0001:23:45.0',
#     'cutting_time': '0000:45:12.0',
#     'status': 'Running',
#     ...
# }

# Get comprehensive overview
overview = client.get_status_overview()
# Combines running_log, counters, and alarms
```

### Available Methods

- `test_connection()` - Test connectivity and measure latency
- `get_running_log()` - Fetch time display data (program, cycle time, etc.)
- `get_work_counter()` - Get workpiece counter values (4 counters)
- `get_alarm_log()` - Fetch current alarms
- `get_tool_data()` - Get ATC tool table (parsing incomplete)
- `get_status_overview()` - Comprehensive status from all endpoints

### Endpoints (Deprecated for Polling)

| Endpoint | Data Returned | Migration Status |
|----------|---------------|------------------|
| `/running_log` | Program name, cycle time, cutting time, power on hours, status | ✅ Replaced by MONTR via Telnet |
| `/work_counter` | Counter 1-4 values, targets, signals | ✅ Replaced by MONTR via Telnet |
| `/alarm_log` | Current alarms with codes and messages | ✅ Replaced by ALARM via Telnet |
| `/tool` | ATC tool table (needs HTML sample for parsing) | ✅ Replaced by ATCTL via Telnet |

**Note**: All data polling operations now use Telnet. HTTP endpoints are kept for legacy support and protocol detection only.

## FTP Client

The `CNCFtpClient` handles file operations via FTP.

### Features

- Async I/O (using aioftp)
- Program listing and filtering
- System file access
- Upload/download/delete operations

### Usage

```python
from app.clients.ftp_client import CNCFtpClient
import asyncio

# Initialize client
client = CNCFtpClient(
    ip_address="192.168.86.89",
    port=21,
    username="anonymous",
    password="anonymous",
    timeout=10
)

# Test connection
result = await client.test_connection()
# {'success': True, 'latency_ms': 120.5, ...}

# List all files
files = await client.list_files("/")
# [{'name': 'O2000.NC', 'size': 1234, ...}, ...]

# Get NC programs (O-numbers)
programs = await client.get_programs()
# [
#     {'name': 'O2000.NC', 'o_number': 2000, 'is_user_program': True, ...},
#     {'name': 'O2045.NC', 'o_number': 2045, 'is_user_program': True, ...},
# ]

# Download a program
content = await client.download_file("O2045.NC")
# b'G-code content here...'

# Upload a program
result = await client.upload_file(
    local_content=b"G0 X0 Y0\n...",
    remote_path="O2046.NC"
)
# {'success': True, 'size': 1234, ...}

# Get system file data
alarm_data = await client.get_alarm_data()
position_data = await client.get_position_data()
monitor_data = await client.get_monitor_data()
```

### Available Methods

- `test_connection()` - Test FTP connectivity
- `list_files(path)` - List files in directory
- `get_programs()` - List NC programs with O-number filtering
- `download_file(path)` - Download file as bytes
- `upload_file(content, path)` - Upload file from bytes
- `delete_file(path)` - Delete file from CNC
- `get_alarm_data()` - Download ALARM.NC system file
- `get_position_data()` - Download POSNI1.NC (position/coordinates)
- `get_monitor_data()` - Download MONTR.NC (monitor data)

### Key System Files

These files contain real-time machine data updated every scan:

| File | Contents |
|------|----------|
| `ALARM.NC` | Current alarm status (622 bytes) |
| `POSNI1.NC` | Position/coordinate system data (4489 bytes) |
| `MONTR.NC` | Real-time monitor data (440 bytes) |
| `IO.NC` | I/O status (32KB) |
| `WKCNTR.NC` | Workpiece counter data (240 bytes) |
| `MAINTC.NC` | Maintenance counter (2200 bytes) |

## API Endpoints

Shatter exposes these clients via REST API:

### Machine Testing

```http
POST /api/machines/{machine_id}/test
```

Tests both HTTP and FTP connectivity.

**Response:**
```json
{
  "machine_id": 1,
  "machine_name": "Mill 1",
  "ip_address": "192.168.86.89",
  "http": {
    "success": true,
    "latency_ms": 45.2,
    "response_size": 2585,
    "timestamp": "2025-11-30T04:00:00Z"
  },
  "ftp": {
    "success": true,
    "latency_ms": 120.5,
    "timestamp": "2025-11-30T04:00:00Z"
  },
  "overall_status": "online"
}
```

### Status Endpoints

```http
GET /api/machines/{machine_id}/status          # Comprehensive overview
GET /api/machines/{machine_id}/running-log     # Time display
GET /api/machines/{machine_id}/counters        # Workpiece counters
GET /api/machines/{machine_id}/alarms          # Alarm log
GET /api/machines/{machine_id}/tools           # Tool table
GET /api/machines/{machine_id}/programs        # List NC programs (FTP)
GET /api/machines/{machine_id}/position        # Position data (FTP)
```

**Example - Get Status:**
```bash
curl http://localhost:8000/api/machines/1/status
```

**Response:**
```json
{
  "machine_id": 1,
  "machine_name": "Mill 1",
  "ip_address": "192.168.86.89",
  "program_name": "O2045",
  "cycle_time": "0001:23:45.0",
  "cutting_time": "0000:45:12.0",
  "status": "Running",
  "power_on_hours": "01068:06:26",
  "counters": [
    {"counter_number": 1, "count": 245},
    {"counter_number": 2, "count": 0},
    ...
  ],
  "alarms": [],
  "timestamp": "2025-11-30T04:00:00Z"
}
```

## Error Handling

Both clients include comprehensive error handling:

### Connection Errors

```python
try:
    data = client.get_running_log()
except ConnectionError as e:
    # Handle connection failure
    print(f"Cannot connect to CNC: {e}")
except TimeoutError as e:
    # Handle timeout
    print(f"Connection timed out: {e}")
```

### API Errors

API endpoints return appropriate HTTP status codes:
- `404` - Machine not found
- `500` - Communication error with CNC
- `503` - CNC not responding

## HTML Parsing Notes

The HTTP client parses HTML responses to extract data. Current parsing uses regex patterns based on observed HTML structure. Some endpoints may need refinement when tested with actual machine data:

- ✅ Running log - Tested and working
- ✅ Work counters - Basic parsing implemented
- ⚠️  Tool data - Needs actual HTML sample for accurate parsing
- ⚠️  Alarm log - May need refinement based on alarm format

## Testing Without Machine Access

While away from the network, you can still:

1. **Review the code** - All client methods are documented
2. **Check API docs** - Visit http://localhost:8000/docs
3. **Test API structure** - Endpoints will return errors but show expected format
4. **Plan integration** - Design polling services and data storage

When back on the network:

1. Test connection endpoint with your machine
2. Verify data parsing accuracy
3. Refine regex patterns if needed
4. Add any missing endpoints

## Telnet Client

The `CNCTelnetClient` handles direct data file reading and write operations via Protocol Type 2 (Port 10000).

**📖 See [archive/BACKEND_TELNET_MIGRATION_PLAN.md](archive/BACKEND_TELNET_MIGRATION_PLAN.md) for complete documentation of the Telnet migration plan and protocol details (archived - migration largely complete).**

### Features

- **Connection Pooling**: Persistent connections are reused across operations for improved stability
- **Semaphore Serialization**: Per-machine locks ensure only one operation at a time
- **Auto-Reconnect**: Connections automatically recover if lost
- **Direct data access**: Same data format as FTP files, but more reliable
- **Write operations**: Supports tool color changes, ATC assignments, and more (Phase 6)

### Connection Pooling

**⚠️ IMPORTANT**: Always use `get_or_create_connection()` instead of creating `CNCTelnetClient` directly.

The telnet client uses a connection pool to maintain persistent connections per machine. This dramatically improves stability:

- **Reduced connection churn**: Connections are reused instead of created/destroyed each operation
- **Faster operations**: No connect/disconnect overhead
- **Better reliability**: Fewer connection attempts = fewer failure points
- **Automatic recovery**: Lost connections are automatically reconnected

**Usage Pattern**:
```python
from app.clients.telnet_client import get_or_create_connection

# Get pooled connection (reused across operations)
telnet_client = await get_or_create_connection(
    ip_address="192.168.86.89",
    port=10000,
    timeout=10
)

# Use connection for operations
tool_data = await telnet_client.get_tool_table_data(units='in')
atc_data = await telnet_client.get_atc_magazine_data()

# Connection stays in pool - DO NOT call disconnect()
```

**Key Points**:
- **Never create `CNCTelnetClient` directly**: Always use `get_or_create_connection()`
- **Don't disconnect**: Connections stay open in the pool for reuse
- **Automatic health checks**: Connections are checked and auto-reconnected if lost
- **Per-machine pools**: Each machine has its own persistent connection

### Available Methods

- `get_or_create_connection(ip_address, port, timeout)` - Get pooled connection
- `load_data(data_name)` - Load arbitrary data file (e.g., "MEM", "TOLNI1", "ATCTL")
- `get_tool_table_data(units)` - Get tool table (TOLNI1 or TOLNM1 based on units)
- `get_atc_magazine_data(control_version)` - Get ATC magazine configuration
- `get_memory_data()` - Get memory/program information
- `get_position_data()` - Get position/work offsets
- `change_atc_tool_color(pot_number, tool_number, color)` - Change tool color (Phase 6)
- `test_connection()` - Test connectivity and measure latency

### Data Files Available via LOD

| File | Contents |
|------|----------|
| `MEM` | Memory/program information (same as MEM.NC via FTP) |
| `TOLNI1` / `TOLNM1` | Tool table (inches/metric, same as TOLNI1.NC/TOLNM1.NC via FTP) |
| `ATCTL` / `ATCTLD` | ATC magazine configuration (C00/D00 control versions) |
| `POSNI1` / `POSNM1` | Position/work offsets (same as POSNI1.NC/POSNM1.NC via FTP) |
| `SYSC89`, `SYSC94-99` | System data files |
| `PRD1`, `PRD2`, `PRD3` | Production data |

### Semaphore Serialization

All telnet operations use per-machine semaphore locks to ensure:
- Only one operation per machine at a time
- Writes wait for active reads to complete
- Reads wait for active writes to complete
- No conflicts between polling (reads) and API operations (writes)

This is handled automatically - you don't need to manage locks manually.

### Write Operations (Phase 6)

Write operations use extended timeouts (5 seconds) and are fully serialized:

```python
# Change tool color
telnet_client = await get_or_create_connection(ip_address, port=10000)
success, status = await telnet_client.change_atc_tool_color(
    pot_number=2,
    tool_number=2,
    color=4  # Green
)
```

**Status Codes**:
- `00` - Success
- `02` - Illegal slave command header
- `30` - Invalid tool/pot number
- `32` - Cannot change during operation
- See `COMPLETION_CODES` in `telnet_client.py` for full list

### Error Handling

```python
try:
    telnet_client = await get_or_create_connection(ip_address, port=10000)
    data = await telnet_client.get_tool_table_data(units='in')
except ConnectionError as e:
    # Connection failed
    logger.error(f"Cannot connect to CNC: {e}")
except TimeoutError as e:
    # Operation timed out
    logger.error(f"Operation timed out: {e}")
```

### Benefits Over HTTP/FTP

- **More reliable**: Direct TCP connection, no HTML parsing
- **Faster**: Lower latency, persistent connections
- **Write support**: Can modify machine data (tool colors, ATC assignments, etc.)
- **Better error handling**: Structured status codes
- **Same data format**: Files match FTP format, so parsers work unchanged

## Protocol Detection

Shatter includes a protocol detection utility to identify available communication protocols beyond HTTP/FTP.

### Detect Protocols via API

```http
POST /api/machines/{machine_id}/detect-protocols
```

Scans for:
- **FOCAS** (Fanuc Open CNC API) - Ports 8192-8195
- **Other protocols** - Modbus TCP, OPC UA, Telnet, etc.

**Response:**
```json
{
  "machine_id": 1,
  "machine_name": "Mill 1",
  "ip_address": "192.168.86.89",
  "summary": {
    "focas_available": true,
    "other_protocols": []
  },
  "focas": {
    "ports_checked": [8193, 8192, 8194, 8195],
    "results": [...]
  },
  ...
}
```

### Detect Protocols via Script

```bash
# From backend directory
python scripts/detect_protocols.py 192.168.86.89
python scripts/detect_protocols.py 192.168.86.89 80 21
```

The script will:
- Scan all common protocol ports
- Check system files for protocol hints
- Test HTTP endpoints for protocol information
- Generate a detailed report with recommendations

### If FOCAS is Available

If FOCAS is detected, you can enable advanced functionality:
- **Real-time position** - Current XYZ coordinates
- **Machine control** - Start/stop programs, feed hold, etc.
- **Advanced status** - Spindle speed, feedrate, axis positions
- **Program management** - Upload/download programs via FOCAS

To use FOCAS, you'll need:
- FOCAS library (Fwlib32.dll on Windows, libfwlib32.so on Linux)
- Machine must have FOCAS option enabled
- Network configuration for FOCAS port (typically 8193)

## Next Steps

1. **Detect protocols** - Use protocol detection to identify available options
2. **Implement polling service** - Background task to continuously fetch data
3. **Store time-series data** - Save status snapshots to database
4. **Add WebSocket** - Push real-time updates to frontend
5. **Refine parsers** - Test with real machine data and adjust
6. **Add caching** - Use Redis for frequently accessed data
