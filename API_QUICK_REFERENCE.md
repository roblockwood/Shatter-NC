# Shatter API - Quick Reference

**Base URL:** `http://localhost:8000`

## Machine Management

```bash
# List all machines
GET /api/machines/

# Add a machine
POST /api/machines/
{
  "name": "Mill 1",
  "ip_address": "192.168.86.89",
  "location": "Production Floor",
  "tags": ["production"]
}

# Get machine details
GET /api/machines/{id}

# Update machine
PUT /api/machines/{id}
{
  "poll_interval_seconds": 10
}

# Delete machine
DELETE /api/machines/{id}

# Test connection (HTTP + FTP)
POST /api/machines/{id}/test

# Fleet overview
GET /api/machines/overview
```

## Machine Status (Real-Time)

```bash
# Comprehensive status (recommended)
GET /api/machines/{id}/status
# Returns: program, cycle time, counters, alarms, etc.

# Individual endpoints
GET /api/machines/{id}/running-log    # Time display
GET /api/machines/{id}/counters       # Workpiece counters
GET /api/machines/{id}/alarms         # Current alarms
GET /api/machines/{id}/tools          # Tool table
GET /api/machines/{id}/position       # X/Y/Z position
GET /api/machines/{id}/programs       # List NC programs (FTP)
```

## Examples

### Add Your CNC
```bash
curl -X POST http://localhost:8000/api/machines/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Speedio",
    "ip_address": "192.168.86.89",
    "location": "Garage",
    "tags": ["prototyping"]
  }'
```

### Test Connection
```bash
curl -X POST http://localhost:8000/api/machines/1/test
```

### Get Live Status
```bash
curl http://localhost:8000/api/machines/1/status
```

### List Programs on CNC
```bash
curl http://localhost:8000/api/machines/1/programs
```

## Interactive Docs

**Swagger UI:** http://localhost:8000/docs
- Try all endpoints
- See request/response schemas
- Execute API calls directly

## Response Formats

### Machine Object
```json
{
  "id": 1,
  "name": "Mill 1",
  "ip_address": "192.168.86.89",
  "ftp_port": 21,
  "http_port": 80,
  "location": "Production Floor",
  "tags": ["production"],
  "enabled": true,
  "connection_status": "online",
  "created_at": "2025-11-30T04:00:00Z"
}
```

### Status Response
```json
{
  "machine_id": 1,
  "program_name": "O2045",
  "cycle_time": "0001:23:45.0",
  "cutting_time": "0000:45:12.0",
  "status": "Running",
  "power_on_hours": "01068:06:26",
  "counters": [
    {"counter_number": 1, "count": 245},
    {"counter_number": 2, "count": 0}
  ],
  "alarms": [],
  "timestamp": "2025-11-30T04:00:00Z"
}
```

### Connection Test Response
```json
{
  "machine_id": 1,
  "http": {
    "success": true,
    "latency_ms": 45.2
  },
  "ftp": {
    "success": true,
    "latency_ms": 120.5
  },
  "overall_status": "online"
}
```

## Error Codes

- `200` - Success
- `201` - Created
- `204` - No Content (delete success)
- `404` - Machine not found
- `422` - Validation error
- `500` - CNC communication error

## Python Client Usage

```python
import httpx

# Add machine
response = httpx.post(
    "http://localhost:8000/api/machines/",
    json={
        "name": "Mill 1",
        "ip_address": "192.168.86.89"
    }
)
machine = response.json()

# Get status
response = httpx.get(
    f"http://localhost:8000/api/machines/{machine['id']}/status"
)
status = response.json()
print(f"Running: {status['program_name']}")
```

## JavaScript/Node Usage

```javascript
// Add machine
const response = await fetch('http://localhost:8000/api/machines/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: 'Mill 1',
    ip_address: '192.168.86.89'
  })
});
const machine = await response.json();

// Get status
const statusResponse = await fetch(
  `http://localhost:8000/api/machines/${machine.id}/status`
);
const status = await statusResponse.json();
console.log(`Running: ${status.program_name}`);
```
