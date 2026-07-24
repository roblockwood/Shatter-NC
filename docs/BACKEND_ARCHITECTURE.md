# Backend Architecture

Sketch of the Shatter backend: how polling, API, WebSocket, and storage fit together. For contributor setup see [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md).

---

## Stack

| Component | Technology | Role |
|-----------|------------|------|
| API | FastAPI | REST + WebSocket |
| ORM | SQLAlchemy 2.0 | PostgreSQL access |
| Database | PostgreSQL 15 + TimescaleDB (`latest-pg15` in compose) | Config + time-series |
| CNC primary | Telnet :10000 | Status, tools, offsets |
| CNC files | FTP :21 | Upload/download/list |
| Cache / locks | In-process (`asyncio`) | Per-machine telnet serialization, rate limit, WS cache |
| Compressors | Kaeser SC2 HTTP client | Direct polling (no sidecar) |
| Optional MQTT | Mosquitto publish | CNC + compressor snapshot topics |

---

## Architecture Diagram

```
┌──────────────┐     REST / WS      ┌─────────────────────────────────┐
│   Frontend   │◄──────────────────►│  FastAPI (main.py)              │
│   (React)    │                    │  ├── api routers                │
└──────────────┘                    │  ├── RateLimitMiddleware        │
                                    │  └── WebSocket /api/ws          │
                                    └───────────┬─────────────────────┘
                                                │
          ┌─────────────────────────────────────┼─────────────────────────┐
          ▼                     ▼                 ▼                         ▼
   PollingService        ProgramService    FtpSyncService          CompressorPollingService
   (_machine_poller)     (upload/validate)  (folder sync jobs)      (KaeserSc2Client)
          │                     │                 │                         │
          ▼                     ▼                 ▼                         ▼
   CNCTelnetClient         CNCFtpClient      CNCFtpClient              DB + optional MQTT
   (fresh conn/poll)      (programs)        (batch sync)              publish
          │                     │                 │
          └──────────┬──────────┴─────────────────┘
                     ▼
              PostgreSQL + TimescaleDB
                     │
                     ▼
              WebSocketManager.broadcast_status
```

---

## Startup

1. [`start.sh`](../backend/scripts/start.sh) (prod) or inline CMD in dev [`Dockerfile`](../backend/Dockerfile) runs [`run_migrations.py`](../backend/scripts/run_migrations.py). Hybrid local dev may use [`start-dev.sh`](../backend/scripts/start-dev.sh).
2. FastAPI app loads settings from [`config.py`](../backend/app/core/config.py)
3. **`startup` event** starts: `MqttPublisher`, `NotificationService`, `PollingService`, `CompressorPollingService`, `FtpSyncService`
4. Routers receive injected service singletons (`summary`, `websocket`, etc.)

See [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) for migration behavior.

---

## Polling Loop (CNC)

[`PollingService`](../backend/app/services/polling.py) schedules per-machine pollers ([`_machine_poller.py`](../backend/app/services/_machine_poller.py)):

1. Open **fresh telnet connection** per operation (`create_fresh_connection`)
2. Fetch status, tools, program name, alarms (LOD/RED commands — see [TELNET_REFERENCE.md](TELNET_REFERENCE.md))
3. Write time-series events (`machine_status_events`, `polling_events`, production data)
4. Update in-memory cache used by WebSocket
5. `WebSocketManager.broadcast_status(payload)`

**Locks:** [`_get_machine_lock`](../backend/app/clients/_telnet_state.py) serializes telnet reads/writes per `(ip, port)`.

**Online detection:** Debounced via `display_online()` — requires at least one successful fast poll and fewer than **3** consecutive failures before the UI shows offline.

---

## WebSocket

[`WebSocketManager`](../backend/app/services/websocket.py):

| Message | When |
|---------|------|
| `initial_status` | Client connects — full fleet snapshot |
| `status_update` | After CNC poll or partial update |
| `compressor_status_update` | After compressor poll |

Protocol details: [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md).

Partial updates merge with cached fields so fast status polls do not wipe tool tables.

---

## Programs and Validation

[`ProgramService`](../backend/app/services/program_service.py) + [`programs.py`](../backend/app/api/programs.py):

1. Parse G-code ([`gcode_parser.py`](../backend/app/parsers/gcode_parser.py)) for tool/WCS metadata
2. Fetch live machine tools (telnet) and offsets (telnet POSNI)
3. Compare with tolerances from machine settings or G-code defaults
4. Store programs by content hash; deployments track validation snapshots

User-facing flow: [USER_GUIDE.md](USER_GUIDE.md#validation-algorithm).

---

## FTP Sync

[`FtpSyncService`](../backend/app/services/ftp_sync_service.py) runs upload/download jobs with:

- Per-machine `asyncio.Lock` (one sync at a time per machine)
- Filename policy from [`ftp_sync_rules.py`](../backend/app/utils/ftp_sync_rules.py) — [FTP_SYNC_EXCLUSION_RULES.md](FTP_SYNC_EXCLUSION_RULES.md)

---

## Compressors

[`CompressorPollingService`](../backend/app/services/compressor_polling.py) uses [`KaeserSc2Client`](../backend/app/integrations/kaeser_sc2/client.py). Optional MQTT publish via [`mqtt_publisher.py`](../backend/app/services/mqtt_publisher.py) to topics such as `shatter/compressors/{id}/poll` and `shatter/machines/{id}/poll`.

See [COMPRESSOR_INTEGRATION.md](COMPRESSOR_INTEGRATION.md).

---

## Notifications

Rule engine evaluates machine/compressor events; channels send email (SMTP) or SMS (Twilio). Secrets stored in DB; API redacts on read ([`secret_redaction.py`](../backend/app/utils/secret_redaction.py)).

---

## Security Notes

- No REST or WebSocket authentication — LAN trust boundary ([SECURITY.md](../SECURITY.md))
- API errors sanitized via [`api_errors.py`](../backend/app/utils/api_errors.py)
- Rate limit: 100 req/min/IP in [`rate_limit.py`](../backend/app/middleware/rate_limit.py)
- OpenAPI `/docs` only when `LOG_LEVEL=DEBUG`

---

## API Surface

REST routers under `/api/*` — use OpenAPI in dev (`LOG_LEVEL=DEBUG` → `/docs`). Do not maintain parallel manual REST docs.

Key router modules: `machines`, `status`, `programs`, `history`, `summary`, `tools`, `compressors`, `notifications`, `ftp_sync`, `settings`.

---

## Database

Relational config + Timescale hypertables for events, production runs, compressor samples. Schema reference: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

---

## Related

| Doc | Topic |
|-----|-------|
| [TELNET_REFERENCE.md](TELNET_REFERENCE.md) | Port 10000 commands |
| [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) | Message formats |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Tables |
| [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | Config |
