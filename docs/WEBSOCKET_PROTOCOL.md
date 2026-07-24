# WebSocket Protocol

Real-time dashboard updates use a single WebSocket endpoint. There is **no authentication** on the socket today — treat network access as the security boundary (see [SECURITY.md](../SECURITY.md)).

## Endpoint

```
ws://<host>:8000/api/ws
```

The FastAPI router is mounted at `/api` with route `/ws` ([`websocket.py`](../backend/app/api/websocket.py)). The frontend connects via [`useWebSocket.ts`](../frontend/src/hooks/useWebSocket.ts) and [`api.ts`](../frontend/src/config/api.ts) (`WS_URL`).

**Production networking:** The SPA auto-detects the API at `{browser-hostname}:8000` unless `VITE_API_URL` was set at build time. Production nginx proxies **`/api/`** (including WebSocket upgrade) to the backend, but the current client connects directly to port **8000** for both REST and WebSocket. Ensure `CORS_ORIGINS` includes your shop UI origin (e.g. `http://<server-ip>` on port 80).

## Message envelope

All messages are JSON objects with a `type` field:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Message kind (see below) |
| `timestamp` | string | ISO-8601 UTC time from server |
| `data` | object | Single machine or compressor payload (updates only) |
| `machines` | array | All CNC machines (initial snapshot only) |
| `compressors` | array | All compressors (initial snapshot only) |

## Message types

### `initial_status`

Sent once when a client connects. Contains full fleet snapshot from the database overlaid with cached polling data.

```json
{
  "type": "initial_status",
  "timestamp": "2025-01-15T14:30:00.000000",
  "machines": [ { "machine_id": 1, "machine_name": "Mill 1", "is_online": true, "...": "..." } ],
  "compressors": [ { "asset_kind": "compressor", "compressor_id": 1, "...": "..." } ]
}
```

### `status_update`

Broadcast when a CNC machine is polled or partial data changes. `data` follows the machine status shape (see [useWebSocket.ts](../frontend/src/hooks/useWebSocket.ts) `MachineStatus`).

```json
{
  "type": "status_update",
  "timestamp": "2025-01-15T14:30:05.000000",
  "data": {
    "machine_id": 1,
    "machine_name": "Mill 1",
    "is_online": true,
    "status": "operating",
    "program_name": "O2045",
    "poll_timestamp": "2025-01-15T14:30:05.000000"
  }
}
```

The server merges partial updates with cached fields (program name, tools, cycle times, etc.) so clients do not lose data on fast polls.

### `compressor_status_update`

Broadcast when a Kaeser compressor is polled. `data` includes `asset_kind: "compressor"` and `compressor_id`.

## Security notes

- **FTP passwords and Kaeser passwords are not included** in WebSocket payloads under normal operation.
- Clients should not log full message bodies in production browser consoles on shared machines.

## Implementation

- Server: [websocket.py](../backend/app/services/websocket.py) (`WebSocketManager`)
- Client hook: [useWebSocket.ts](../frontend/src/hooks/useWebSocket.ts)
- **Dashboard behavior when disconnected:** Fleet cards use WebSocket only. If disconnected with no cached data, the UI shows a loading screen; otherwise stale WS data remains visible. Summary modals poll REST (`/api/summary/*`) on their own interval — that is not a fleet-status fallback. The backend still updates its in-memory poll cache when no clients are connected.

## Related documentation

- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) — polling and broadcast flow
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) — `useWebSocket.ts` integration
- OpenAPI at `/docs` when `LOG_LEVEL=DEBUG`
