# API Reference

Complete REST API documentation for the Shatter CNC management platform.

## Base URL

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:8000` |
| Production | `http://<server-ip>` |

**API Version:** v1 (implicit, not versioned in URL)

## Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

Use these interfaces for interactive testing and schema exploration.

## Authentication

**Current:** No authentication required
**Future:** Optional authentication via `ENABLE_AUTH` environment variable

## Error Responses

All endpoints follow standard HTTP status codes and return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `204 No Content` - Resource deleted successfully
- `400 Bad Request` - Invalid input or malformed request
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error (CNC unreachable, database error, etc.)

---

## Machines API

Manage CNC machine configurations, test connectivity, and get fleet overview.

**Base Path:** `/api/machines`

### List All Machines

Get list of all configured machines.

**Endpoint:** `GET /api/machines`

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)
- `enabled_only` (bool, optional): Only return enabled machines (default: false)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Mill 1",
    "model": "Brother CNC",
    "ip_address": "192.168.86.89",
    "ftp_port": 21,
    "http_port": 80,
    "ftp_username": "anonymous",
    "ftp_password": "anonymous",
    "path": "/PROGRAM",
    "tags": ["production", "floor-a"],
    "poll_interval_seconds": 5,
    "enabled": true,
    "diameter_tolerance": 0.01,
    "length_tolerance_plus": 0.02,
    "length_tolerance_minus": 0.0,
    "tolerance_x": 0.0394,
    "tolerance_y": 0.0394,
    "tolerance_z": 0.0394,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-15T12:30:00Z",
    "last_seen_at": "2025-01-15T14:25:30Z"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/machines
curl http://localhost:8000/api/machines?enabled_only=true&limit=10
```

**Implementation:** [machines.py:17-29](../backend/app/api/machines.py#L17-L29)

---

### Get Machine by ID

Get detailed information for a specific machine.

**Endpoint:** `GET /api/machines/{machine_id}`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):** Same as individual machine object in list response

**Error Responses:**
- `404 Not Found` - Machine not found

**Example:**
```bash
curl http://localhost:8000/api/machines/1
```

**Implementation:** [machines.py:32-41](../backend/app/api/machines.py#L32-L41)

---

### Create Machine

Add a new machine configuration.

**Endpoint:** `POST /api/machines`

**Request Body:**
```json
{
  "name": "Mill 2",
  "model": "Brother CNC",
  "ip_address": "192.168.86.90",
  "ftp_port": 21,
  "http_port": 80,
  "ftp_username": "anonymous",
  "ftp_password": "anonymous",
  "path": "/PROGRAM",
  "tags": ["production"],
  "poll_interval_seconds": 5,
  "enabled": true,
  "diameter_tolerance": 0.01,
  "length_tolerance_plus": 0.02,
  "length_tolerance_minus": 0.0,
  "tolerance_x": 0.0394,
  "tolerance_y": 0.0394,
  "tolerance_z": 0.0394
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "name": "Mill 2",
  "ip_address": "192.168.86.90",
  ...
}
```

**Error Responses:**
- `400 Bad Request` - Machine with same name already exists

**Example:**
```bash
curl -X POST http://localhost:8000/api/machines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mill 2",
    "ip_address": "192.168.86.90",
    "enabled": true
  }'
```

**Implementation:** [machines.py:44-60](../backend/app/api/machines.py#L44-L60)

---

### Update Machine

Update an existing machine configuration.

**Endpoint:** `PUT /api/machines/{machine_id}`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Request Body:** (all fields optional, only send fields to update)
```json
{
  "name": "Mill 1 (Updated)",
  "ip_address": "192.168.86.91",
  "enabled": false
}
```

**Response (200 OK):** Updated machine object

**Error Responses:**
- `404 Not Found` - Machine not found

**Example:**
```bash
curl -X PUT http://localhost:8000/api/machines/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

**Implementation:** [machines.py:63-82](../backend/app/api/machines.py#L63-L82)

---

### Delete Machine

Delete a machine configuration.

**Endpoint:** `DELETE /api/machines/{machine_id}`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (204 No Content):** No response body

**Error Responses:**
- `404 Not Found` - Machine not found

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/machines/1
```

**Implementation:** [machines.py:85-97](../backend/app/api/machines.py#L85-L97)

**Note:** Cascade deletes all related data (deployments, events, etc.)

---

### Test Machine Connection

Test HTTP and FTP connectivity to a machine.

**Endpoint:** `POST /api/machines/{machine_id}/test`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "machine_name": "Mill 1",
  "ip_address": "192.168.86.89",
  "http": {
    "success": true,
    "latency_ms": 45.2,
    "response_size": 2585,
    "timestamp": "2025-01-15T14:30:00Z"
  },
  "ftp": {
    "success": true,
    "latency_ms": 120.5,
    "current_directory": "/",
    "timestamp": "2025-01-15T14:30:00Z"
  },
  "overall_status": "online"
}
```

**Overall Status Values:**
- `online` - Both HTTP and FTP working
- `partial` - Either HTTP or FTP working
- `offline` - Both failed

**Error Responses:**
- `404 Not Found` - Machine not found

**Example:**
```bash
curl -X POST http://localhost:8000/api/machines/1/test
```

**Implementation:** [machines.py:100-153](../backend/app/api/machines.py#L100-L153)

---

### Disconnect Machine

Close FTP connection to a machine.

**Endpoint:** `POST /api/machines/{machine_id}/disconnect`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Disconnected from Mill 1 (192.168.86.89)"
}
```

**Error Responses:**
- `404 Not Found` - Machine not found

**Example:**
```bash
curl -X POST http://localhost:8000/api/machines/1/disconnect
```

**Implementation:** [machines.py:156-183](../backend/app/api/machines.py#L156-L183)

---

### Get Machines Overview

Get basic overview of all enabled machines.

**Endpoint:** `GET /api/machines/overview`

**Response (200 OK):**
```json
{
  "total_machines": 3,
  "machines": [
    {
      "id": 1,
      "name": "Mill 1",
      "last_seen_at": "2025-01-15T14:25:30Z"
    },
    {
      "id": 2,
      "name": "Mill 2",
      "last_seen_at": "2025-01-15T14:25:28Z"
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/machines/overview
```

**Implementation:** [machines.py:186-205](../backend/app/api/machines.py#L186-L205)

**Note:** This endpoint is lightweight. For detailed real-time status, use `/api/summary/machines`.

---

## Status API

Real-time machine status, file operations, and CNC data retrieval.

**Base Path:** `/api/machines/{machine_id}`

### Get Comprehensive Status

Get real-time comprehensive status including running log, counters, alarms, and tools.

**Endpoint:** `GET /api/machines/{machine_id}/status`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "machine_name": "Mill 1",
  "ip_address": "192.168.86.89",
  "timestamp": "2025-01-15T14:30:00Z",
  "program_name": "O2045",
  "cycle_time": "0001:23:45.0",
  "cutting_time": "0000:45:12.0",
  "non_cutting_time": "0000:38:33.0",
  "power_on_hours": "01068:06:26",
  "operation_time": "00245:12:18",
  "status": "running",
  "counters": [
    {"counter_number": 1, "count": 245},
    {"counter_number": 2, "count": 0},
    {"counter_number": 3, "count": 12},
    {"counter_number": 4, "count": 0}
  ],
  "alarms": [],
  "tools": [
    {
      "tool_number": 1,
      "tool_name": ".250 3FL",
      "diameter": 0.25,
      "length": 3.4494
    }
  ]
}
```

**Error Responses:**
- `404 Not Found` - Machine not found
- `500 Internal Server Error` - Failed to connect to machine

**Example:**
```bash
curl http://localhost:8000/api/machines/1/status
```

**Implementation:** [status.py:19-55](../backend/app/api/status.py#L19-L55)

---

### Get Running Log

Get running log data (time display) from machine.

**Endpoint:** `GET /api/machines/{machine_id}/running-log`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "program_name": "O2045",
  "cycle_time": "0001:23:45.0",
  "cutting_time": "0000:45:12.0",
  "non_cutting_time": "0000:38:33.0",
  "power_on_hours": "01068:06:26",
  "operation_time": "00245:12:18",
  "status": "running",
  "timestamp": "2025-01-15T14:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/running-log
```

**Implementation:** [status.py:58-79](../backend/app/api/status.py#L58-L79)

---

### Get Work Counters

Get workpiece counter data (4 counters).

**Endpoint:** `GET /api/machines/{machine_id}/counters`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "counters": [
    {"counter_number": 1, "count": 245},
    {"counter_number": 2, "count": 0},
    {"counter_number": 3, "count": 12},
    {"counter_number": 4, "count": 0}
  ],
  "timestamp": "2025-01-15T14:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/counters
```

**Implementation:** [status.py:82-103](../backend/app/api/status.py#L82-L103)

---

### Get Alarms

Get current alarms from machine.

**Endpoint:** `GET /api/machines/{machine_id}/alarms`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "alarms": [
    {
      "code": "P504",
      "message": "PROGRAM NOT FOUND",
      "program": "O2045",
      "block_no": "N100",
      "severity": "error",
      "level_class": "alarm_level_3"
    }
  ],
  "timestamp": "2025-01-15T14:30:00Z"
}
```

**Alarm Severity Levels:**
- `info` - Informational (level 1)
- `warning` - Warning (level 2)
- `error` - Error (level 3)
- `critical` - Critical (level 4)

**Example:**
```bash
curl http://localhost:8000/api/machines/1/alarms
```

**Implementation:** [status.py:106-127](../backend/app/api/status.py#L106-L127)

---

### Get Tool Data

Get ATC (Automatic Tool Changer) tool table.

**Endpoint:** `GET /api/machines/{machine_id}/tools`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "tools": [
    {
      "tool_number": 1,
      "tool_name": ".250 3FL",
      "diameter": 0.25,
      "length": 3.4494
    },
    {
      "tool_number": 2,
      "tool_name": "1/2 ENDMILL",
      "diameter": 0.5,
      "length": 4.0
    }
  ],
  "timestamp": "2025-01-15T14:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/tools
```

**Implementation:** [status.py:130-151](../backend/app/api/status.py#L130-L151)

---

### List Programs (FTP)

List files and directories on machine via FTP.

**Endpoint:** `GET /api/machines/{machine_id}/programs`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `path` (str, optional): Directory path to list (default: "/")

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "machine_name": "Mill 1",
  "current_path": "/",
  "total_count": 5,
  "programs": [
    {
      "name": "O2000.NC",
      "path": "/O2000.NC",
      "is_directory": false,
      "size": 12450,
      "modified": "2025-01-10T08:30:00"
    },
    {
      "name": "SUBDIR",
      "path": "/SUBDIR",
      "is_directory": true,
      "size": 0,
      "modified": ""
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/programs
curl "http://localhost:8000/api/machines/1/programs?path=/SUBDIR"
```

**Implementation:** [status.py:154-195](../backend/app/api/status.py#L154-L195)

---

### Get Position Data

Get work offsets (G54-G59) and extended offsets from POSNI1.NC file.

**Endpoint:** `GET /api/machines/{machine_id}/position`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Response (200 OK):**
```json
{
  "machine_id": 1,
  "machine_name": "Mill 1",
  "work_offsets": {
    "54": {"x": 0.0, "y": 0.0, "z": -5.0},
    "55": {"x": 10.0, "y": 0.0, "z": -5.0},
    "56": {"x": 20.0, "y": 0.0, "z": -5.0},
    "57": {"x": 0.0, "y": 0.0, "z": 0.0},
    "58": {"x": 0.0, "y": 0.0, "z": 0.0},
    "59": {"x": 0.0, "y": 0.0, "z": 0.0}
  },
  "extended_offsets": {
    "X01": {"x": 0.0, "y": 0.0, "z": 0.0},
    ...
  },
  "fixture_offsets": {},
  "rotary_offsets": {}
}
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/position
```

**Implementation:** [status.py:198-241](../backend/app/api/status.py#L198-L241)

---

### Download File

Download a file from machine via FTP.

**Endpoint:** `GET /api/machines/{machine_id}/download`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `file_path` (str, required): Path to file on machine (e.g., "/O2000.NC")

**Response (200 OK):** File download (octet-stream)

**Headers:**
```
Content-Disposition: attachment; filename=O2000.NC
Content-Type: application/octet-stream
```

**Error Responses:**
- `404 Not Found` - Machine or file not found

**Example:**
```bash
curl "http://localhost:8000/api/machines/1/download?file_path=/O2000.NC" -o O2000.NC
```

**Implementation:** [status.py:244-294](../backend/app/api/status.py#L244-L294)

---

### Get File Metadata

Get parsed metadata (tools, runtime) for a file on the machine.

**Endpoint:** `GET /api/machines/{machine_id}/metadata`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `file_path` (str, required): Path to file on machine

**Response (200 OK):**
```json
{
  "file_path": "/O2000.NC",
  "tools": [1, 2, 3, 5],
  "runtime_seconds": 3845,
  "has_errors": false
}
```

**Example:**
```bash
curl "http://localhost:8000/api/machines/1/metadata?file_path=/O2000.NC"
```

**Implementation:** [status.py:297-357](../backend/app/api/status.py#L297-L357)

---

### View File Content

View file content as text (up to 8MB by default).

**Endpoint:** `GET /api/machines/{machine_id}/view`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `file_path` (str, required): Path to file on machine
- `max_size` (int, optional): Maximum file size in bytes (default: 8388608 = 8MB)

**Response (200 OK):**
```json
{
  "file_path": "/O2000.NC",
  "content": "O2000\nG0 X0 Y0 Z0\n...",
  "size": 12450,
  "lines": 523
}
```

**Error Responses:**
- `404 Not Found` - File not found
- `413 Request Entity Too Large` - File exceeds max_size

**Example:**
```bash
curl "http://localhost:8000/api/machines/1/view?file_path=/O2000.NC"
```

**Implementation:** [status.py:360-423](../backend/app/api/status.py#L360-L423)

---

### Upload File

Upload a file to machine via FTP.

**Endpoint:** `POST /api/machines/{machine_id}/upload`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `file_path` (str, required): Destination path on machine (e.g., "/O2000.NC")

**Request Body:** Multipart form-data with file upload

**Response (200 OK):**
```json
{
  "success": true,
  "file_path": "/O2000.NC",
  "size": 12450,
  "message": "File uploaded successfully to /O2000.NC"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/machines/1/upload?file_path=/O2000.NC" \
  -F "file=@local_file.nc"
```

**Implementation:** [status.py:426-478](../backend/app/api/status.py#L426-L478)

---

## Programs API

Program validation, upload, versioning, and deployment management.

**Base Path:** `/api/programs`

### Validate Program

Validate a G-code program against machine configuration (tools, WCS offsets).

**Endpoint:** `POST /api/programs/machines/{machine_id}/programs/validate`

**Path Parameters:**
- `machine_id` (int): Target machine ID

**Request Body:**
```json
{
  "gcode_content": "O2000\nG54\nT01 M06\nG0 X0 Y0 Z0\n..."
}
```

**Response (200 OK):**
```json
{
  "valid": true,
  "tools": {
    "1": {
      "tool_number": 1,
      "required_diameter": 0.25,
      "required_length": 3.5,
      "available": true,
      "diameter_match": true,
      "length_sufficient": true,
      "machine_tool_data": {
        "tool_name": ".250 3FL",
        "diameter": 0.25,
        "length": 3.5
      },
      "warnings": []
    }
  },
  "wcs_offset": {
    "valid": true,
    "work_offset": 54,
    "expected": {"x": 0.0, "y": 0.0, "z": -5.0},
    "actual": {"x": 0.0, "y": 0.0, "z": -5.0},
    "difference": {"x": 0.0, "y": 0.0, "z": 0.0},
    "tolerance": 0.0394,
    "within_tolerance": true,
    "warnings": []
  },
  "warnings": [],
  "errors": [],
  "metadata": {
    "posted_date": "2025-01-10T00:00:00Z",
    "estimated_runtime_seconds": 3845,
    "tool_count": 3,
    "line_count": 523,
    "file_size": 12450
  }
}
```

**Validation Checks:**
- **Tool Availability:** Each tool (T01, T02, etc.) must exist in machine ATC
- **Tool Diameter:** Must match within `diameter_tolerance` (default: ±0.010")
- **Tool Length:** Machine tool length must be within tolerance range
- **WCS Offset:** Work coordinate system (G54-G59) must match within tolerance (default: ±1mm = ±0.0394")

**Error Responses:**
- `404 Not Found` - Machine not found
- `400 Bad Request` - Invalid G-code

**Example:**
```bash
curl -X POST http://localhost:8000/api/programs/machines/1/programs/validate \
  -H "Content-Type: application/json" \
  -d '{"gcode_content": "O2000\nT01 M06\n..."}'
```

**Implementation:** [programs.py:80-210](../backend/app/api/programs.py#L80-L210)

See [PROGRAM_VALIDATION.md](PROGRAM_VALIDATION.md) for detailed validation workflow.

---

### Validate File on Machine

Download and validate a file already on the machine.

**Endpoint:** `POST /api/programs/machines/{machine_id}/programs/validate-file`

**Path Parameters:**
- `machine_id` (int): Target machine ID

**Query Parameters:**
- `file_path` (str, required): Path to file on machine (e.g., "/O2000.NC")

**Response (200 OK):**
```json
{
  "validation": {
    "valid": true,
    "tools": {...},
    "wcs_offset": {...},
    "warnings": [],
    "errors": [],
    "metadata": {...}
  },
  "gcode_content": "O2000\nG54\nT01 M06\n..."
}
```

**Note:** Returns both validation results AND file content. The content can be used for subsequent deployment without re-downloading.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/programs/machines/1/programs/validate-file?file_path=/O2000.NC"
```

**Implementation:** [programs.py:213-271](../backend/app/api/programs.py#L213-L271)

---

### List Programs

List all programs in the library.

**Endpoint:** `GET /api/programs`

**Query Parameters:**
- `skip` (int, optional): Records to skip (default: 0)
- `limit` (int, optional): Max records (default: 100)
- `filename_filter` (str, optional): Filter by filename (partial match)
- `active_only` (bool, optional): Only active versions (default: true)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "original_filename": "PART_123_OP1.NC",
    "content_hash": "abc123...",
    "version_number": 2,
    "posted_date": "2025-01-10T00:00:00Z",
    "file_size_bytes": 12450,
    "line_count": 523,
    "estimated_runtime_seconds": 3845,
    "first_seen_at": "2025-01-01T10:00:00Z",
    "last_deployed_at": "2025-01-15T14:00:00Z",
    "deployed_count": 5,
    "is_active": true
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/programs
curl "http://localhost:8000/api/programs?filename_filter=PART_123"
```

**Implementation:** [programs.py:455-481](../backend/app/api/programs.py#L455-L481)

---

### Get Program by ID

Get detailed program information.

**Endpoint:** `GET /api/programs/{program_id}`

**Path Parameters:**
- `program_id` (int): Program ID

**Response (200 OK):** Same as individual program object in list response

**Error Responses:**
- `404 Not Found` - Program not found

**Example:**
```bash
curl http://localhost:8000/api/programs/1
```

**Implementation:** [programs.py:484-490](../backend/app/api/programs.py#L484-L490)

---

### Get Program Versions by Filename

Get all versions of a program by filename.

**Endpoint:** `GET /api/programs/by-filename/{filename}`

**Path Parameters:**
- `filename` (str): Original filename

**Response (200 OK):** Array of program objects ordered by version (newest first)

**Error Responses:**
- `404 Not Found` - No programs found

**Example:**
```bash
curl http://localhost:8000/api/programs/by-filename/PART_123_OP1.NC
```

**Implementation:** [programs.py:493-503](../backend/app/api/programs.py#L493-L503)

---

### Upload Program

Upload a new NC program with optional validation and deployment.

**Endpoint:** `POST /api/programs/upload`

**Request Body:**
```json
{
  "gcode_content": "O2000\nG54\nT01 M06\n...",
  "original_filename": "PART_123_OP1.NC",
  "machine_id": 1,
  "deployed_filename": "O2000.nc",
  "validate_before_upload": true,
  "validation_results": null
}
```

**Fields:**
- `gcode_content` (str, required): G-code content
- `original_filename` (str, required): Original filename
- `machine_id` (int, optional): Machine ID for deployment
- `deployed_filename` (str, optional): O-number for deployment (e.g., "O2000.nc")
- `validate_before_upload` (bool, optional): Validate before upload (default: false)
- `validation_results` (object, optional): Pre-computed validation results

**Response (200 OK):**
```json
{
  "program": {
    "id": 1,
    "original_filename": "PART_123_OP1.NC",
    "version_number": 1,
    "content_hash": "abc123..."
  },
  "is_new_version": true,
  "deployment": {
    "id": 1,
    "program_id": 1,
    "machine_id": 1,
    "deployed_filename": "O2000.nc",
    "deployed_path": "/PROGRAM/O2000.nc",
    "deployed_at": "2025-01-15T14:30:00Z",
    "validation_passed": true,
    "validation_results": {...},
    "is_current": true,
    "replaced_at": null,
    "replaced_by": null
  },
  "validation_results": {...}
}
```

**Version Control:**
- SHA-256 content hash prevents duplicates
- Same content → returns existing program
- Different content → creates new version

**Example:**
```bash
curl -X POST http://localhost:8000/api/programs/upload \
  -H "Content-Type: application/json" \
  -d '{
    "gcode_content": "O2000\n...",
    "original_filename": "PART_123.NC",
    "machine_id": 1,
    "deployed_filename": "O2000.nc",
    "validate_before_upload": true
  }'
```

**Implementation:** [programs.py:508-562](../backend/app/api/programs.py#L508-L562)

See [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md#programservice) for version control details.

---

### Deploy Validated Program

Create deployment record for file already on machine (re-validation workflow).

**Endpoint:** `POST /api/programs/machines/{machine_id}/programs/deploy-validated`

**Path Parameters:**
- `machine_id` (int): Target machine ID

**Request Body:**
```json
{
  "deployed_filename": "O2000.nc",
  "gcode_content": "O2000\n...",
  "validation_results": {
    "valid": true,
    "tools": {...},
    "wcs_offset": {...}
  }
}
```

**Response (200 OK):** Deployment object (same as in upload response)

**Note:** This does NOT upload the file to the machine. It creates a database record for a file that's already deployed.

**Example:**
```bash
curl -X POST http://localhost:8000/api/programs/machines/1/programs/deploy-validated \
  -H "Content-Type: application/json" \
  -d '{
    "deployed_filename": "O2000.nc",
    "gcode_content": "...",
    "validation_results": {...}
  }'
```

**Implementation:** [programs.py:565-603](../backend/app/api/programs.py#L565-L603)

See [PROGRAM_VALIDATION.md](PROGRAM_VALIDATION.md#auto-save-behavior) for re-validation workflow.

---

### Deploy Program

Deploy an existing program to a machine.

**Endpoint:** `POST /api/programs/{program_id}/deploy`

**Path Parameters:**
- `program_id` (int): Program ID

**Request Body:**
```json
{
  "machine_id": 1,
  "deployed_filename": "O2000.nc",
  "validate_before_upload": true
}
```

**Response (200 OK):** Deployment object

**Example:**
```bash
curl -X POST http://localhost:8000/api/programs/1/deploy \
  -H "Content-Type: application/json" \
  -d '{"machine_id": 1, "deployed_filename": "O2000.nc"}'
```

**Implementation:** [programs.py:608-631](../backend/app/api/programs.py#L608-L631)

---

### List Machine Deployments

List all deployments for a specific machine.

**Endpoint:** `GET /api/programs/machines/{machine_id}/deployments`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `current_only` (bool, optional): Only current deployments (default: false)
- `skip` (int, optional): Records to skip (default: 0)
- `limit` (int, optional): Max records (default: 100)

**Response (200 OK):** Array of deployment objects

**Example:**
```bash
curl http://localhost:8000/api/programs/machines/1/deployments
curl http://localhost:8000/api/programs/machines/1/deployments?current_only=true
```

**Implementation:** [programs.py:634-658](../backend/app/api/programs.py#L634-L658)

---

### List Program Deployments

List all deployments of a specific program (across all machines).

**Endpoint:** `GET /api/programs/{program_id}/deployments`

**Path Parameters:**
- `program_id` (int): Program ID

**Query Parameters:**
- `skip` (int, optional): Records to skip (default: 0)
- `limit` (int, optional): Max records (default: 100)

**Response (200 OK):** Array of deployment objects

**Example:**
```bash
curl http://localhost:8000/api/programs/1/deployments
```

**Implementation:** [programs.py:661-678](../backend/app/api/programs.py#L661-L678)

---

### Get Deployment by O-Number

Get current deployment info for an O-number with full program details.

**Endpoint:** `GET /api/programs/machines/{machine_id}/deployments/by-onumber/{onumber}`

**Path Parameters:**
- `machine_id` (int): Machine ID
- `onumber` (str): O-number (flexible format: "2000", "O2000", "O2000.nc")

**Query Parameters:**
- `include_program` (bool, optional): Include full program details (default: true)
- `include_history` (bool, optional): Include deployment history (default: false)

**Response (200 OK):**
```json
{
  "deployment": {
    "id": 1,
    "deployed_filename": "O2000.nc",
    "deployed_path": "/PROGRAM/O2000.nc",
    "deployed_at": "2025-01-15T14:00:00Z",
    "validation_passed": true,
    "validation_results": {...}
  },
  "program": {
    "id": 1,
    "original_filename": "PART_123_OP1.NC",
    "version_number": 2,
    "posted_date": "2025-01-10T00:00:00Z",
    "estimated_runtime_seconds": 3845,
    "program_metadata": {...},
    "file_size_bytes": 12450,
    "line_count": 523
  },
  "history": [
    {
      "id": 1,
      "deployed_at": "2025-01-15T14:00:00Z",
      "validation_passed": true,
      "replaced_at": null,
      "is_current": true,
      "program_version": 2,
      "original_filename": "PART_123_OP1.NC"
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/programs/machines/1/deployments/by-onumber/2000
curl http://localhost:8000/api/programs/machines/1/deployments/by-onumber/O2000?include_history=true
```

**Implementation:** [programs.py:681-770](../backend/app/api/programs.py#L681-L770)

---

### Get Deployment by ID

Get full deployment details by deployment ID.

**Endpoint:** `GET /api/programs/deployments/{deployment_id}`

**Path Parameters:**
- `deployment_id` (int): Deployment ID

**Response (200 OK):** Same structure as deployment by O-number response

**Error Responses:**
- `404 Not Found` - Deployment not found

**Example:**
```bash
curl http://localhost:8000/api/programs/deployments/1
```

**Implementation:** [programs.py:773-816](../backend/app/api/programs.py#L773-L816)

---

### Get Next O-Number (FIFO)

Get next available O-number using FIFO allocation (O2000-O3999).

**Endpoint:** `GET /api/programs/machines/{machine_id}/next-onumber`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `filename` (str, optional): Original filename to check for existing deployment

**Response (200 OK):**
```json
{
  "next_onumber": "O2000.nc",
  "onumber_int": 2000,
  "is_replacing": false,
  "replacement_info": null,
  "is_redeployment": false
}
```

**OR (if pool full):**
```json
{
  "next_onumber": "O2005.nc",
  "onumber_int": 2005,
  "is_replacing": true,
  "replacement_info": {
    "onumber": "2005",
    "deployed_at": "2025-01-01T10:00:00Z",
    "original_filename": "OLD_PROGRAM.NC"
  },
  "is_redeployment": false
}
```

**FIFO Allocation:**
- Range: O2000-O3999 (2000 slots)
- Allocates first available O-number
- When full: replaces oldest deployment (FIFO)
- If filename already deployed: returns existing O-number

**Example:**
```bash
curl http://localhost:8000/api/programs/machines/1/next-onumber
curl "http://localhost:8000/api/programs/machines/1/next-onumber?filename=PART_123.NC"
```

**Implementation:** [programs.py:819-921](../backend/app/api/programs.py#L819-L921)

---

## History API

Event history and analytics for status changes, alarms, and production runs.

**Base Path:** `/api`

### Get Status History

Get machine status change history.

**Endpoint:** `GET /api/machines/{machine_id}/status-history`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `start_time` (datetime, optional): Filter from this datetime (ISO format)
- `end_time` (datetime, optional): Filter until this datetime (ISO format)
- `limit` (int, optional): Max events to return (max: 1000, default: 100)

**Response (200 OK):**
```json
[
  {
    "time": "2025-01-15T14:00:00Z",
    "machine_id": 1,
    "status": "running",
    "previous_status": "stopped",
    "program_name": "O2045",
    "o_number": "2045",
    "metrics": {
      "cycle_time_seconds": 3845,
      "cutting_time_seconds": 2712,
      "power_on_hours": 1068.1
    }
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/status-history
curl "http://localhost:8000/api/machines/1/status-history?start_time=2025-01-15T00:00:00Z&limit=50"
```

**Implementation:** [history.py:21-49](../backend/app/api/history.py#L21-L49)

---

### Get Alarm History

Get alarm history for a machine.

**Endpoint:** `GET /api/machines/{machine_id}/alarms`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `start_time` (datetime, optional): Filter from datetime
- `end_time` (datetime, optional): Filter until datetime
- `active_only` (bool, optional): Only uncleared alarms (default: false)
- `limit` (int, optional): Max events (max: 1000, default: 100)

**Response (200 OK):**
```json
[
  {
    "time": "2025-01-15T14:00:00Z",
    "machine_id": 1,
    "alarm_code": "P504",
    "alarm_message": "PROGRAM NOT FOUND",
    "alarm_type": "program",
    "severity": "error",
    "program_id": null,
    "deployment_id": null,
    "cleared_at": "2025-01-15T14:05:00Z",
    "duration_seconds": 300,
    "cleared_by": null,
    "resolution_notes": null
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/alarms
curl http://localhost:8000/api/machines/1/alarms?active_only=true
```

**Implementation:** [history.py:54-86](../backend/app/api/history.py#L54-L86)

---

### Get Active Alarms

Get all currently active alarms across all machines (or specific machine).

**Endpoint:** `GET /api/alarms/active`

**Query Parameters:**
- `machine_id` (int, optional): Filter to specific machine

**Response (200 OK):** Array of alarm objects

**Example:**
```bash
curl http://localhost:8000/api/alarms/active
curl http://localhost:8000/api/alarms/active?machine_id=1
```

**Implementation:** [history.py:89-108](../backend/app/api/history.py#L89-L108)

---

### Get Production Runs

Get production run history for a machine.

**Endpoint:** `GET /api/machines/{machine_id}/production-runs`

**Path Parameters:**
- `machine_id` (int): Machine ID

**Query Parameters:**
- `start_time` (datetime, optional): Filter from datetime
- `end_time` (datetime, optional): Filter until datetime
- `program_id` (int, optional): Filter by program
- `active_only` (bool, optional): Only active runs (default: false)
- `limit` (int, optional): Max runs (max: 1000, default: 100)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "started_at": "2025-01-15T10:00:00Z",
    "ended_at": "2025-01-15T11:04:05Z",
    "machine_id": 1,
    "program_id": 1,
    "deployment_id": 1,
    "program_name": "O2045",
    "o_number": "2045",
    "cycle_count": 0,
    "parts_produced": 0,
    "duration_seconds": 3845,
    "actual_cycle_time_seconds": null,
    "estimated_cycle_time_seconds": null,
    "efficiency_percent": null,
    "completion_status": "completed",
    "abort_reason": null,
    "alarm_count": 0,
    "total_downtime_seconds": 0
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/machines/1/production-runs
curl "http://localhost:8000/api/machines/1/production-runs?program_id=1&limit=20"
```

**Implementation:** [history.py:113-149](../backend/app/api/history.py#L113-L149)

---

### Get Program Production History

Get production history for a specific program across all machines.

**Endpoint:** `GET /api/programs/{program_id}/production-runs`

**Path Parameters:**
- `program_id` (int): Program ID

**Query Parameters:**
- `limit` (int, optional): Max runs (max: 1000, default: 100)

**Response (200 OK):** Array of production run objects

**Example:**
```bash
curl http://localhost:8000/api/programs/1/production-runs
```

**Implementation:** [history.py:152-171](../backend/app/api/history.py#L152-L171)

---

## Summary API

Fleet-wide summaries and statistics.

**Base Path:** `/api`

### Get Running Summary

Get machines sorted by total run time within a time range.

**Endpoint:** `GET /api/summary/running`

**Query Parameters:**
- `time_range` (str, optional): One of: "1h", "4h", "24h", "7d", "30d" (default: "24h")

**Response (200 OK):**
```json
{
  "time_range": "24h",
  "total_machines": 3,
  "machines": [
    {
      "machine_id": 1,
      "machine_name": "Mill 1",
      "current_status": "running",
      "total_run_time_seconds": 64800.0,
      "total_run_time_formatted": "18h 0m",
      "run_percentage": 75.0,
      "active_runs_count": 5,
      "last_run_start": "2025-01-15T14:00:00Z",
      "current_program": "O2045"
    }
  ]
}
```

**Sorted By:** Total run time (descending)

**Example:**
```bash
curl http://localhost:8000/api/summary/running
curl "http://localhost:8000/api/summary/running?time_range=7d"
```

**Implementation:** [summary.py:222-298](../backend/app/api/summary.py#L222-L298)

---

### Get Online Summary

*DEPRECATED: Use `/api/summary/machines` instead*

Get all currently online machines with connection health.

**Endpoint:** `GET /api/summary/online`

**Response (200 OK):**
```json
{
  "total_online": 2,
  "machines": [
    {
      "machine_id": 1,
      "machine_name": "Mill 1",
      "is_online": true,
      "online_since": "2025-01-15T08:00:00Z",
      "online_duration_seconds": 23400,
      "online_duration_formatted": "6h 30m",
      "last_seen_at": "2025-01-15T14:29:55Z",
      "connection_health": "healthy",
      "polling_history_8h": [
        {"time": "2025-01-15T06:00:00Z", "success": true, "response_time_ms": 45},
        {"time": "2025-01-15T06:00:05Z", "success": true, "response_time_ms": 48}
      ]
    }
  ]
}
```

**Connection Health:**
- `healthy` - Last seen < 30 seconds ago
- `degraded` - Last seen 30s-5min ago
- `stale` - Last seen > 5min ago

**Example:**
```bash
curl http://localhost:8000/api/summary/online
```

**Implementation:** [summary.py:300-367](../backend/app/api/summary.py#L300-L367)

---

### Get Offline Summary

*DEPRECATED: Use `/api/summary/machines` instead*

Get all currently offline machines.

**Endpoint:** `GET /api/summary/offline`

**Response (200 OK):**
```json
{
  "total_offline": 1,
  "machines": [
    {
      "machine_id": 3,
      "machine_name": "Mill 3",
      "is_online": false,
      "offline_since": "2025-01-15T12:00:00Z",
      "offline_duration_seconds": 8700,
      "offline_duration_formatted": "2h 25m",
      "last_seen_at": "2025-01-15T12:00:00Z",
      "last_known_status": "stopped",
      "enabled": true,
      "polling_history_8h": [
        {"time": "2025-01-15T06:00:00Z", "success": true, "response_time_ms": 45},
        {"time": "2025-01-15T06:00:05Z", "success": false, "response_time_ms": null}
      ]
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/summary/offline
```

**Implementation:** [summary.py:369-437](../backend/app/api/summary.py#L369-L437)

---

### Get Machines Summary (Unified)

Get unified machine status summary with polling data (replaces online/offline).

**Endpoint:** `GET /api/summary/machines`

**Response (200 OK):**
```json
{
  "total_machines": 3,
  "online_count": 2,
  "offline_count": 1,
  "machines": [
    {
      "machine_id": 1,
      "machine_name": "Mill 1",
      "is_online": true,
      "uptime_8h_percent": 98.5,
      "current_status": "running",
      "connection_health": "healthy",
      "online_duration_formatted": "6h 30m",
      "offline_duration_formatted": "",
      "status_changed_at": "2025-01-15T08:00:00Z",
      "polling_history_8h": [
        {"time": "2025-01-15T13:00:00Z", "success": true, "response_time_ms": 45},
        {"time": "2025-01-15T13:00:05Z", "success": true, "response_time_ms": 48}
      ],
      "polling_summary": {
        "total_polls": 720,
        "successful_polls": 709,
        "failed_polls": 11,
        "success_rate": 98.5,
        "avg_response_time_ms": 47,
        "current_streak": 150
      }
    }
  ]
}
```

**Polling Summary Fields:**
- `total_polls` - Total polls in 8-hour window
- `successful_polls` - Successful polls
- `failed_polls` - Failed polls
- `success_rate` - Percentage (0-100%)
- `avg_response_time_ms` - Average response time (successful polls only)
- `current_streak` - Consecutive successes (positive) or failures (negative)

**Sorted By:** Online first, then by uptime percentage

**Example:**
```bash
curl http://localhost:8000/api/summary/machines
```

**Implementation:** [summary.py:439-561](../backend/app/api/summary.py#L439-L561)

---

## WebSocket API

Real-time bidirectional communication for machine status updates.

**Base Path:** `/api`

### WebSocket Connection

Connect to receive real-time machine status updates.

**Endpoint:** `WebSocket /api/ws`

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws');

ws.onopen = () => {
  console.log('Connected to WebSocket');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Message:', message);
};

ws.onclose = () => {
  console.log('Disconnected from WebSocket');
};
```

**Message Types:**

**1. Initial Status (sent immediately on connect):**
```json
{
  "type": "initial_status",
  "timestamp": "2025-01-15T14:30:00Z",
  "machines": [
    {
      "machine_id": 1,
      "machine_name": "Mill 1",
      "ip_address": "192.168.86.89",
      "enabled": true,
      "is_online": true,
      "program_name": "O2045",
      "status": "running",
      "poll_timestamp": "2025-01-15T14:29:55Z"
    }
  ]
}
```

**2. Status Update (sent every 5 seconds for each machine):**
```json
{
  "type": "status_update",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    "machine_id": 1,
    "machine_name": "Mill 1",
    "is_online": true,
    "poll_timestamp": "2025-01-15T14:30:00Z",
    "response_time_ms": 45,
    "program_name": "O2045",
    "status": "running",
    "cycle_time": "0001:23:45.0",
    "cutting_time": "0000:45:12.0",
    "counters": [...],
    "alarms": [],
    "tools": [...]
  }
}
```

**Client Messages:**
Currently, the WebSocket is unidirectional (server → client). Client messages are received but not processed.

Future: Support for subscription filters, machine-specific subscriptions, etc.

**Auto-Reconnect:**
The WebSocket connection may be closed by the server during shutdown or errors. Clients should implement auto-reconnect logic.

**Example (React Hook):**
```typescript
import { useWebSocket } from './hooks/useWebSocket';

function Dashboard() {
  const { messages, status } = useWebSocket('ws://localhost:8000/api/ws');

  return (
    <div>
      <p>Status: {status}</p>
      {messages.map((msg, i) => (
        <div key={i}>{JSON.stringify(msg)}</div>
      ))}
    </div>
  );
}
```

**Implementation:** [websocket.py:19-56](../backend/app/api/websocket.py#L19-L56)

See [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) for detailed protocol documentation.

---

## Health Check

Check API health and polling service status.

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "polling_service": {
    "running": true,
    "active_machines": 3,
    "websocket_connections": 2
  }
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

**Implementation:** [main.py:42-52](../backend/app/main.py#L42-L52)

---

## Root Endpoint

API information and version.

**Endpoint:** `GET /`

**Response (200 OK):**
```json
{
  "name": "Shatter",
  "version": "0.1.0",
  "status": "running"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

**Implementation:** [main.py:32-39](../backend/app/main.py#L32-L39)

---

## Rate Limiting

**Current:** No rate limiting
**Future:** Redis-based rate limiting for API endpoints

---

## Pagination

Endpoints that return lists support pagination via `skip` and `limit` parameters:

```bash
# Get first 50 programs
curl http://localhost:8000/api/programs?skip=0&limit=50

# Get next 50 programs
curl http://localhost:8000/api/programs?skip=50&limit=50
```

**Default Limits:**
- Most endpoints: 100 records
- History endpoints: 100 records (max: 1000)

---

## Filtering

Many endpoints support filtering via query parameters:

**Machines:**
- `enabled_only` - Only enabled machines

**Programs:**
- `filename_filter` - Partial filename match
- `active_only` - Only active versions

**History:**
- `start_time`, `end_time` - Time range filters (ISO 8601 format)
- `active_only` - Only active records
- `program_id`, `machine_id` - Resource filters

**Example:**
```bash
# Get status history for last 24 hours
curl "http://localhost:8000/api/machines/1/status-history?start_time=2025-01-14T14:00:00Z&end_time=2025-01-15T14:00:00Z"
```

---

## CORS

Configured CORS origins (default):
- `http://localhost:3000` - Development (React)
- `http://localhost:5173` - Development (Vite)
- `http://localhost` - Production (Nginx)
- `*` - Allow all (for isolated networks)

Configure via `CORS_ORIGINS` environment variable. See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md).

---

## Related Documentation

- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) - Backend services and architecture
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database models and relationships
- [CNC_CLIENTS.md](CNC_CLIENTS.md) - HTTP/FTP client library details
- [PROGRAM_VALIDATION.md](PROGRAM_VALIDATION.md) - Validation workflow and logic
- [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) - WebSocket message format and protocol
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - Configuration reference
