# CNC Communication Clients

Shatter includes two client libraries for communicating with Brother CNC machines.

## HTTP Client

The `CNCHttpClient` handles polling HTTP endpoints on the CNC web server.

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

### Endpoints Polled

| Endpoint | Data Returned |
|----------|---------------|
| `/running_log` | Program name, cycle time, cutting time, power on hours, status |
| `/work_counter` | Counter 1-4 values, targets, signals |
| `/alarm_log` | Current alarms with codes and messages |
| `/tool` | ATC tool table (needs HTML sample for parsing) |

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

## Next Steps

1. **Implement polling service** - Background task to continuously fetch data
2. **Store time-series data** - Save status snapshots to database
3. **Add WebSocket** - Push real-time updates to frontend
4. **Refine parsers** - Test with real machine data and adjust
5. **Add caching** - Use Redis for frequently accessed data
