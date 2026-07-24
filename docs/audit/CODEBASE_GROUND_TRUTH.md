# Codebase Ground Truth (Documentation Audit Reference)

> **Temporary audit artifact.** This document describes how Shatter-NC **actually works in code** as of the current repository state. Use it to verify operator and contributor docs — not as end-user documentation.

**Generated from:** independent codebase review (backend, frontend, database, Docker, CI).  
**App version in code:** `0.23.0` (`VERSION`, `backend/app/core/config.py`, `frontend/package.json` via build).

---

## How to use this document

1. Pick a doc from [docs/README.md](../README.md).
2. Compare each factual claim against the matching section below.
3. Record discrepancies in the [Documentation audit matrix](#documentation-audit-matrix) (or a separate audit spreadsheet).
4. Delete or archive this file after the doc audit is complete.

---

## 1. System summary

Shatter-NC is a **single-process asyncio FastAPI backend** plus a **React 19 / Vite SPA**. It monitors Brother CNC machines over **Telnet port 10000** and **FTP port 21**, and optionally Kaeser SIGMA CONTROL 2 compressors over **HTTP(S) to the SC2 web UI**. PostgreSQL with **TimescaleDB** stores configuration and time-series events.

| Layer | Technology | Port (typical) |
|-------|------------|----------------|
| Frontend (dev) | React 19 + TypeScript + Vite | 3000 |
| Frontend (prod) | nginx serving static SPA | 80 |
| Backend | Python 3.11 + FastAPI + uvicorn | 8000 |
| Database | TimescaleDB on PostgreSQL **15** (`timescale/timescaledb:latest-pg15`) | 5432 (dev only exposed) |
| Optional MQTT | Mosquitto 2 | 1883 (dev exposed; prod internal + `--profile mqtt`) |

**Security model:** No REST or WebSocket authentication. Network isolation is the trust boundary. Rate limit: **100 req/min/IP** (`RateLimitMiddleware`).

**Versioning:** semantic-release on merge to `main`; Docker images pushed to `ghcr.io/roblockwood/shatter-nc/{backend,frontend}`.

---

## 2. Repository layout

```
backend/app/
  main.py              FastAPI app, lifecycle, router registration
  core/config.py       Pydantic settings (source of truth for env vars)
  api/                 REST + WebSocket routers
  services/            polling, websocket, programs, ftp sync, notifications, …
  clients/             telnet_client, ftp_client
  parsers/             gcode + telnet v2 parsers (*_parser_v2.py)
  models/              SQLAlchemy models
  integrations/kaeser_sc2/   Kaeser HTTP client + status mapping

frontend/src/
  App.tsx              Routes + navigation
  config/api.ts        API_BASE_URL, WS_URL
  contexts/            WebSocketContext, ExpandedMachineContext, BetaModeContext
  hooks/useWebSocket.ts
  pages/               Dashboard, FileBrowser, ToolManagement, tablet/*
  api/                 layout, summary, ftpSync, notifications helpers

database/init/         Numbered SQL migrations (01–29, applied at startup)
docker-compose.dev.yml / docker-compose.prod.yml
```

---

## 3. Backend lifecycle

### Startup sequence

1. **`backend/scripts/start.sh`** (prod) or inline CMD in dev Dockerfile:
   - Wait for Postgres
   - Run **`backend/scripts/run_migrations.py`** (idempotent; tracks `schema_migrations`)
   - Start **`uvicorn app.main:app --host 0.0.0.0 --port 8000`**
2. FastAPI **`startup`** event starts (in order):
   - `MqttPublisher.start()` (no-op if `MQTT_PUBLISH_HOST` unset)
   - `NotificationService.start()`
   - `PollingService.start()` — CNC fast + tool poll loops
   - `CompressorPollingService.start()`
   - `FtpSyncService.start()` (optional local folder watcher)
3. **`shutdown`:** stops all services, `close_all_connections()` for telnet

### Global singletons (injected into routers)

`websocket_manager`, `mqtt_publisher`, `notification_service`, `polling_service`, `compressor_polling_service`, `ftp_sync_service`

### Root endpoints (not under `/api`)

| Method | Path | Response |
|--------|------|----------|
| GET | `/` | `{ name, version, status: "running" }` |
| GET | `/health` | `{ status: "healthy" }`; extra stats when `LOG_LEVEL=DEBUG` |

OpenAPI `/docs` and `/openapi.json` are enabled **only when `LOG_LEVEL=DEBUG`**.

---

## 4. REST API surface (actual routes)

All routers registered in `backend/app/main.py`.

### Compressors — `/api/compressors`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | List |
| GET | `/{id}` | Get one |
| GET | `/{id}/status` | Cached/live from polling |
| POST | `/` | Create |
| PUT | `/{id}` | Update |
| GET/PUT | `/{id}/layout` | UI grid layout JSON |
| DELETE | `/{id}` | Delete |

### Machines — `/api/machines`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | List (`enabled_only` query param) |
| GET | `/{id}` | Get one |
| POST | `/` | Create |
| PUT | `/{id}` | Update |
| DELETE | `/{id}` | Delete |
| POST | `/{id}/test` | Test HTTP/FTP/telnet |
| POST | `/{id}/detect-protocols` | **Deprecated** |
| POST | `/{id}/disconnect` | Close telnet connections |
| GET | `/overview` | **Deprecated** |
| GET/PUT | `/{id}/layout` | Per-machine UI layout |
| POST | `/{id}/refresh-program-name` | **Deprecated** |

### Status (same prefix `/api/machines`)

**Reads** (`_status_reads.py`):

| Method | Path |
|--------|------|
| GET | `/{id}/status` | **Deprecated** on-demand telnet poll |
| GET | `/{id}/running-log` | MONTR |
| GET | `/{id}/counters` | Workpiece counters |
| GET | `/{id}/alarms/live` | Live ALARM |
| GET | `/{id}/tools` | Tool table/ATC (cache or telnet) |

**Tool writes** (`_status_tools.py`): refresh, ATC color/type/tool assignment, spindle tool, tool life, tool offset — all gated by `MachineStateValidator` (blocks when operating/editing).

**Files** (`_status_files.py`):

| Method | Path |
|--------|------|
| GET | `/{id}/programs` | FTP listing |
| GET | `/{id}/position` | POSNI offsets |
| GET | `/{id}/download` | FTP download |
| GET | `/{id}/metadata` | File metadata |
| GET | `/{id}/view` | File content |
| POST | `/{id}/upload` | FTP upload |

### Programs — `/api/programs`

Upload, validate, deploy-validated, analyze-atc, deployment history, next-onumber, etc. Several **`/{id}/deploy`** routes marked deprecated.

### History — `/api`

| Path pattern | Purpose |
|--------------|---------|
| `/machines/{id}/status-history` | Status transitions |
| `/compressors/{id}/status-history` | Compressor transitions |
| `/compressors/{id}/status-samples` | High-frequency chart samples |
| `/machines/{id}/alarms` | Stored alarms |
| `/alarms/active` | Fleet active alarms |
| `/machines/{id}/cycle-history` | Cycle intervals from PRD3 |
| `/machines/{id}/prd3-status-history` | Raw PRD3 rows |
| `/machines/{id}/production-runs-timeline` | Production timeline |
| `/machines/{id}/production-runs` | **Deprecated** |

### Summary — `/api`

| Method | Path |
|--------|------|
| GET | `/summary/running?time_range=` |
| GET | `/summary/machines?time_range=` |

### Tools — `/api/tools`

| Method | Path |
|--------|------|
| GET | `/summary` |
| GET | `/{tool_number}` |
| GET | `/{tool_number}/history` |
| POST | `/export` |
| GET | `/instances/{machine_id}` |

### Settings — `/api/settings`

| Method | Path |
|--------|------|
| GET/PUT | `/layout` | Global default layout (**in-memory dict**, not persisted to DB) |

### FTP sync — `/api`

Under `/machines/{id}/ftp-sync/…`: configs CRUD, trigger, runs, conflicts, local-folders browse.

### Notifications — `/api/notifications`

Channels CRUD, rules CRUD, test send, delivery log.

---

## 5. WebSocket protocol (actual)

| Item | Code truth |
|------|------------|
| **Route** | `@router.websocket("/ws")` with router prefix `/api` → **`/api/ws`** |
| **Full URL** | `ws://<host>:8000/api/ws` (frontend: `frontend/src/config/api.ts` → `WS_URL`) |
| **Auth** | None |
| **Client → server** | Text received and logged only; no subscription protocol |

### Message types (only three)

| `type` | When | Payload |
|--------|------|---------|
| `initial_status` | On connect | `machines[]`, `compressors[]` (DB + poll cache overlay) |
| `status_update` | CNC poll / partial update | `data` = single machine status |
| `compressor_status_update` | Compressor poll | `data` with `asset_kind: "compressor"` |

All messages include `timestamp` (ISO-8601 UTC).

### Server-side cache behavior

- `WebSocketManager.last_status` updated on every poll **even with zero connected clients** (REST/cache fallback).
- Partial `status_update` merges with cache: preserves program name (won't replace good name with `"----"`), tools, panel, alarms, cycle times, `last_successful_poll_at`.
- FTP sync progress can piggyback on status broadcasts.

### Production nginx

`frontend/nginx.conf` proxies **`/api/`** (includes WebSocket upgrade) and **`/health`** to backend. It does **not** define a separate `/ws` location. The SPA connects directly to **port 8000** for WebSocket unless `VITE_API_URL` overrides at build time.

---

## 6. CNC polling and telnet

### Architecture

- **`PollingService`** (`services/polling.py`): one **`MachinePoller`** per enabled machine.
- **No persistent telnet pool** — each operation uses **`create_fresh_connection()`**, disconnects in `finally`.
- **Per-machine asyncio lock** on `(ip, port)` serializes all telnet reads/writes.
- Default telnet port: **10000**. Optional dev proxy: `SHATTER_TELNET_PROXY_HOST`, `SHATTER_TELNET_PROXY_PORT`.

### Poll loops

| Loop | Interval | Skips when |
|------|----------|------------|
| Fast (status) | min(`poll_interval_seconds`) across machines; default **5s** | — |
| Tool table | min(`tool_poll_interval_seconds`); default **30s** | `last_known_prd3_status == "operating"` |

### LOD data fetched (v2 schema-driven parsers)

| LOD | Parser | Used for |
|-----|--------|----------|
| MONTR | `montr_parser_v2` | Program, times, counters |
| PRD3/PRDD3 | `prd3_parser_v2` | Status codes 1–5 → off/standby/operating/stopped/error |
| MEM | `mem_parser_v2` | Mode, operation_status, program_name |
| ALARM | `alarm_parser_v2` | Active alarms (+ JSON code lookup) |
| PANEL | `panel_parser_v2` | Panel switches |
| TOLNI1/TOLNM1 | `tolni_parser_v2` | Tool table (slow poll) |
| ATCTL/ATDTL | `atctl_parser_v2` | ATC magazine (slow poll) |
| Macro #500+ | RED | Macro variables |

Control version **C00 vs D00** stored on `machines.control_version`; affects parser schemas and FTP sync rules.

### Online / offline semantics

`MachinePoller.display_online()`:

- `True` only after **≥1 successful fast poll** AND `consecutive_failures < 3`
- Threshold **`offline_threshold = 3`** consecutive failures before logged offline transition

This is **debounced** — transient failures (1–2) keep UI online.

### Background tasks

All **asyncio tasks** — **Celery is in `requirements.txt` but unused**.

Other async work: event logging, PRD3 history ingest, FTP sync runs, control-version pre-population on startup.

---

## 7. Compressor integration (actual)

- **Direct HTTP polling** via `KaeserSc2Client` — **no sidecar**, no MQTT subscriber required for live UI.
- Auth: SHA-256 login to `{kaeser_connect_base_url}/login.html`, data via `POST …/json.json`.
- **`CompressorPollingService`** polls enabled compressors, writes `compressor_status_events` + throttled **`compressor_status_samples`**.
- Sample throttle: `COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS` (default **1.0s**).
- **Raw sample retention: 14 days** (`database/init/19-compressor-samples-rollup.sql`); 1-minute continuous aggregate retained **400 days**.
- Optional **MQTT publish** (retained) to `shatter/compressors/{id}/poll` when `MQTT_PUBLISH_HOST` set — publish only, not consumed by Shatter for polling.

Status inference: LED load/idle take precedence; maps to Shatter statuses (`load`, `idle`, `stopped`, `online`, etc.) in `sidecar_mapper.py`.

---

## 8. FTP sync (actual)

- Service: `FtpSyncService`; client: `CNCFtpClient` (stdlib `ftplib`, not `aioftp`).
- Requires `machines.ftp_sync_enabled = True` (per-machine flag).
- Directions: **`upload`** (local → CNC), **`download`** (CNC → local).
- Run states: `queued` → `in_progress` → `completed` / `failed` / `interrupted`.
- Per-file: `queued`, `success`, `failed`, `conflict`, `skipped`.
- Rules engine: `app/utils/ftp_sync_rules.py` (Brother C00/D00 naming — see `FTP_SYNC_EXCLUSION_RULES.md`).
- Local folder watcher: **`FTP_SYNC_LOCAL_WATCH_ENABLED`** default **false** (manual trigger only).
- Progress broadcast over WebSocket via status merge.

---

## 9. Programs and validation

1. **`gcode_parser.py`** extracts tools, WCS, runtime, posted date from NC comments.
2. Live machine tools (telnet TOLN/ATCTL) and offsets (POSNI) compared at validate time.
3. Tolerance source per machine: `use_machine_tool_tolerances`, `use_machine_wcs_tolerances`.
4. Programs stored by **SHA-256 content hash**; deployments track validation snapshots.
5. **`ATCOptimizer`** (`atc_optimizer.py`) for `/api/programs/analyze-atc`.

---

## 10. Notifications

- **`NotificationService`**: evaluates rules on status/cycle events.
- Channels: **SMTP** (`aiosmtplib`) or **Twilio SMS**.
- Global SMTP/Twilio defaults from env; per-channel overrides in DB.
- Secrets redacted on API read (`secret_redaction.py`).

---

## 11. Database

### Migration strategy

1. **Dev first boot:** `./database/init` mounted to Postgres `/docker-entrypoint-initdb.d`.
2. **Every backend start:** `run_migrations.py` applies pending `*.sql` in sorted order; records in **`schema_migrations`**.

Prod Postgres has **no init mount** — schema comes entirely from backend migration runner using SQL baked into image at `/app/migrations`.

### Core tables (non-exhaustive)

| Domain | Tables |
|--------|--------|
| CNC config | `machines` (+ control_version, ftp_sync_enabled, tolerances, layout_config, …) |
| Programs | `programs`, `program_deployments` |
| Tools | `tool_instances` |
| Compressors | `compressors`, `compressor_status_events`, `compressor_status_samples`, view `compressor_status_samples_1min` |
| FTP sync | `ftp_sync_configs`, `ftp_sync_runs`, `ftp_sync_run_items`, `ftp_sync_file_states` |
| Notifications | `notification_channels`, `notification_rules`, `notification_log` |
| Hypertables | `machine_status_events`, `alarm_events`, `production_runs`, `polling_events`, `prd3_status_history`, `macro_history`, `tool_table_history`, `panel_history`, `counter_history`, … |

Full column-level reference: `docs/DATABASE_SCHEMA.md` (verify against `database/init/*.sql` and `app/models/`).

---

## 12. Environment variables (code truth)

**Source:** `backend/app/core/config.py`, compose files, `frontend/src/config/api.ts`.

### Backend settings loaded and used

All vars in `docs/ENVIRONMENT_VARIABLES.md` table match `config.py` **except** these are **used in code but missing from that doc**:

| Variable | Where used |
|----------|------------|
| `MIGRATIONS_DIR` | `run_migrations.py` |
| `SHATTER_TELNET_PROXY_HOST` | `telnet_client.py` (dev Docker) |
| `SHATTER_TELNET_PROXY_PORT` | `telnet_client.py` (default 10000) |

### Loaded but not wired to runtime logic

| Variable | Notes |
|----------|-------|
| `SECRET_KEY` | In config + prod compose; **no middleware consumes it** |
| `ENABLE_AUTH` | Documented as no effect — **accurate** |
| `SSL_CERT_PATH`, `SSL_KEY_PATH` | In `.env.production.example` only |

### Frontend (Vite)

| Variable | Default behavior |
|----------|------------------|
| `VITE_API_URL` | If unset: `{protocol}//{hostname}:8000` |
| `VITE_APP_VERSION` | Injected at Docker/CI build |
| `VITE_TABLET_MACHINE_ID` | Tablet entry default CNC id |
| `VITE_TABLET_COMPRESSOR_ID` | Tablet entry default compressor id |
| `VITE_PWA_START_URL` | Dockerfile build arg only |

**Not documented in ENVIRONMENT_VARIABLES.md:** `VITE_APP_VERSION`, `VITE_TABLET_*`, `VITE_PWA_START_URL`.

### Prod compose env passthrough

`docker-compose.prod.yml` passes database, poll/compressor, CORS, MQTT, Twilio, **SMTP**, `LOCAL_TIMEZONE`, `FTP_SYNC_ENABLED`, and related keys to the backend. Dev compose uses `env_file: .env` for broader passthrough.

---

## 13. Frontend (actual)

### Routes (`App.tsx`)

| Path | Component | Gated |
|------|-----------|-------|
| `/` | Dashboard | — |
| `/files` | FileBrowser | — |
| `/sync` | Redirect → `/` | — |
| `/notifications` | NotificationSettings | **BetaRoute** |
| `/tools` | ToolManagement | **BetaRoute** |
| `/tablet`, `/tablet/setup`, `/tablet/:machineId/:paneSlug` | Tablet kiosk | — |
| `/tablet/compressor/:compressorId/:paneSlug` | Compressor kiosk | — |

Navigation hidden on `/tablet/*`.

### Beta mode

- **Activation:** 10 rapid clicks on `SHATTER v{version}` header title.
- **Storage:** `localStorage` key `shatter_beta_mode`.
- **Gates:** `/tools`, `/notifications`, FTP sync UI in machine edit, AUTO DETECT control version, some ToolsPane features.

Compressors and tablet routes work **without** beta.

### WebSocket usage

- Single connection via `WebSocketProvider` → `useWebSocket(WS_URL)`.
- Dashboard fleet data comes **only from WebSocket** (`initial_status` + updates).
- On disconnect with **empty** fleet: `AsciiLoadingScreen`. With cached data: stale data remains visible; header shows **WS DISCONNECTED**.
- **No automatic REST polling fallback** for dashboard machine status (contrasts with some doc wording).
- Summary modals/popups **do** poll REST every 2s (`/api/summary/running`, `/api/summary/machines`).

### State management

No Redux, React Query, or Zustand in use — manual `fetch` + `useEffect`. Contexts: WebSocket, ExpandedMachine, BetaMode.

### Machine detail panes (dashboard expanded card)

`statusTimeline`, `alarms`, `currentProgram`, `tools`, `productionRuns`, `statusHistory`, `panel`, `fileManager` — layout persisted per machine via `/api/machines/{id}/layout`.

### API URL in production

Browser calls **`hostname:8000`** directly for API and WebSocket. nginx `/api/` proxy exists but SPA does not use relative `/api` URLs by default.

---

## 14. Deployment flows (actual)

### Production (shop)

1. Download `docker-compose.prod.yml` + `.env.production.example` → `.env`
2. Set `POSTGRES_PASSWORD`, `SECRET_KEY`, `CORS_ORIGINS`
3. `docker compose -f docker-compose.prod.yml pull && up -d`
4. UI: **port 80**; API health: **port 8000** `/health`
5. Optional MQTT: `--profile mqtt`, set `MQTT_PUBLISH_HOST=mosquitto`

Images: `ghcr.io/roblockwood/shatter-nc/{backend,frontend}:${IMAGE_TAG:-latest}`

### Development

1. `cp .env.example .env`
2. `docker compose -f docker-compose.dev.yml up -d`
3. UI: **3000**; API: **8000**; Postgres: **5432** exposed

macOS helpers: `start.command`, `rebuild-dev.command`.

### CI

- **`test.yml`:** Python **3.12**, pytest, 25% cov floor
- **`release.yml`:** semantic-release → Docker build/push on relevant path changes
- Backend Docker base: **`python:3.11-slim`**

---

## 15. Dependencies worth noting

| Package | Status |
|---------|--------|
| `celery` | In requirements; **unused** |
| `python-jose`, `passlib` | Auth deps; **unused** (`ENABLE_AUTH=False`) |
| `aioftp` | Listed; FTP uses **`ftplib`** |
| `aiomqtt` | Optional MQTT publisher |
| `@tanstack/react-query`, `zustand` | In frontend package.json; **not imported** |

---

## Documentation audit matrix

Preliminary discrepancies found by comparing existing docs to this ground truth. Expand during full audit.

| Doc | Topic | Doc says | Code says | Severity |
|-----|-------|----------|-----------|----------|
| [WEBSOCKET_PROTOCOL.md](../WEBSOCKET_PROTOCOL.md) | Endpoint | `ws://<host>:8000/ws` | **`ws://<host>:8000/api/ws`** | **High** — wrong path |
| [WEBSOCKET_PROTOCOL.md](../WEBSOCKET_PROTOCOL.md) | nginx | "Production nginx proxies this path" | nginx proxies **`/api/`** only; frontend connects to `:8000/api/ws` | Medium |
| [BACKEND_ARCHITECTURE.md](../BACKEND_ARCHITECTURE.md) | WebSocket path | Diagram shows `/ws` | **`/api/ws`** | Medium |
| [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) | WebSocket | "nginx proxies `/ws` in prod" | Same as above | Medium |
| [USER_GUIDE.md](../USER_GUIDE.md) | WS fallback | "UI falls back to REST polling" if disconnected | Dashboard uses WS only; loading screen or stale cache; summaries poll REST | **High** — misleading |
| [USER_GUIDE.md](../USER_GUIDE.md) | Notifications | "Configure … in **Settings**" | Route is **`/notifications`** (beta); no Settings page | Medium |
| [USER_GUIDE.md](../USER_GUIDE.md) | Tools page | Described without beta note | **`/tools` requires beta mode** | Medium |
| [USER_GUIDE.md](../USER_GUIDE.md) | File browser | "Open from machine card" | Also standalone **`/files`** route + deep links | Low |
| [COMPRESSOR_INTEGRATION.md](../COMPRESSOR_INTEGRATION.md) | Sample retention | "30-day retention" for status-samples | **14 days raw** (+ 400d 1-min aggregate) | Medium |
| [COMPRESSOR_INTEGRATION.md](../COMPRESSOR_INTEGRATION.md) | Sample source | "MQTT-throttled ~1 Hz samples" | **Backend poll throttle** (`COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS`); MQTT is optional publish | Medium |
| [COMPRESSOR_INTEGRATION.md](../COMPRESSOR_INTEGRATION.md) | Formatting | Stray `\n` in markdown | Cosmetic only | Low |
| [BACKEND_ARCHITECTURE.md](../BACKEND_ARCHITECTURE.md) | Broadcast method | `broadcast_status_update` | Code uses **`broadcast_status`** | Low |
| [BACKEND_ARCHITECTURE.md](../BACKEND_ARCHITECTURE.md) | Online detection | "Failed polls mark machine offline" | **Debounced**: 3 consecutive failures; needs prior success | Medium |
| [BACKEND_ARCHITECTURE.md](../BACKEND_ARCHITECTURE.md) | MQTT | Listed under compressors as optional | Accurate for **publish**; clarify not used for polling | Low |
| [BACKEND_ARCHITECTURE.md](../BACKEND_ARCHITECTURE.md) | PostgreSQL | "PostgreSQL 14" | Compose uses **`latest-pg15`** | Low |
| [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) | PostgreSQL | "14+" | Runtime is **15** in compose | Low |
| [README.md](../../README.md) | PostgreSQL | "PostgreSQL 14" | **15** in compose | Low |
| [README.md](../../README.md) / [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) | Python CI | "Python 3.11+" | CI runs **3.12**; Docker **3.11** | Low |
| [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) | Frontend vars | Only `VITE_API_URL` | Also **`VITE_APP_VERSION`**, **`VITE_TABLET_*`** | Medium |
| [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) | Telnet proxy | Not listed | **`SHATTER_TELNET_PROXY_*`** used in dev | Medium |
| [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) | Migrations | Not listed | **`MIGRATIONS_DIR`** | Low |
| [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) | Prod SMTP | Documented | **Fixed** — SMTP vars now in prod compose | Resolved |
| [INSTALLATION_GUIDE.md](../INSTALLATION_GUIDE.md) | Overall flow | Generally accurate | Verify prod API/CORS when UI on :80 and API on :8000 | Medium |
| [TELNET_REFERENCE.md](../TELNET_REFERENCE.md) | Commands | Implemented read/write tables | Appears aligned with `telnet_client.py` mixins | Verify during audit |
| [FTP_SYNC_EXCLUSION_RULES.md](../FTP_SYNC_EXCLUSION_RULES.md) | Rules | Policy description | Implemented in `ftp_sync_rules.py` | Verify during audit |
| [NC_PARSER_GUIDE.md](../NC_PARSER_GUIDE.md) | CAM requirements | Post-processor formats | Cross-check with `gcode_parser.py` | Not verified here |
| [UX_DESIGN_GUIDE.md](../UX_DESIGN_GUIDE.md) | UI patterns | Design standards | Cross-check with components | Not verified here |
| [SECURITY.md](../../SECURITY.md) | No auth | Accurate | Matches code | OK |
| [DATABASE_MIGRATIONS.md](../DATABASE_MIGRATIONS.md) | Runner behavior | Documented | Matches `run_migrations.py` | Likely OK |

### Undocumented in operator docs

| Feature | Code location | Notes |
|---------|---------------|-------|
| Beta mode | `BetaModeContext`, `BetaRoute` | README mentions for sync/notify; USER_GUIDE omits beta for tools |
| Tablet kiosk | `/tablet/*` | Only COMPRESSOR_INTEGRATION mentions tablet |
| Global layout API | `/api/settings/layout` | In-memory only |
| Deprecated API routes | Various `@deprecated` in routers | No deprecation list in docs |
| `display_online` debounce | `_machine_poller.py` | Affects UX timing |
| Prod dual-port API access | `api.ts` + nginx | Operators may need firewall rules for :8000 |

---

## 16. Key file index (for deep dives)

| Topic | Path |
|-------|------|
| App entry | `backend/app/main.py` |
| Settings | `backend/app/core/config.py` |
| WebSocket server | `backend/app/services/websocket.py`, `backend/app/api/websocket.py` |
| WebSocket client | `frontend/src/hooks/useWebSocket.ts`, `frontend/src/config/api.ts` |
| Polling | `backend/app/services/polling.py`, `backend/app/services/_machine_poller.py` |
| Telnet | `backend/app/clients/telnet_client.py`, `_telnet_state.py`, `_telnet_data_reads.py`, `_telnet_write_ops.py` |
| Kaeser | `backend/app/integrations/kaeser_sc2/client.py` |
| FTP sync | `backend/app/services/ftp_sync_service.py`, `backend/app/utils/ftp_sync_rules.py` |
| Migrations | `backend/scripts/run_migrations.py`, `database/init/*.sql` |
| Compose | `docker-compose.dev.yml`, `docker-compose.prod.yml` |
| Frontend routes | `frontend/src/App.tsx` |
| nginx | `frontend/nginx.conf` |

---

## 17. Suggested audit order

1. **WEBSOCKET_PROTOCOL.md** — fix path (`/api/ws`); clarify prod networking
2. **USER_GUIDE.md** — WS behavior, beta gates, notification route
3. **ENVIRONMENT_VARIABLES.md** — prod compose passthrough, missing vars
4. **COMPRESSOR_INTEGRATION.md** — retention and sampling source
5. **BACKEND_ARCHITECTURE.md** — online debounce, WS path, PG version
6. **INSTALLATION_GUIDE.md** — ports, CORS, API URL expectations
7. **DATABASE_SCHEMA.md** — column drift vs models/migrations
8. **TELNET_REFERENCE.md**, **FTP_SYNC_EXCLUSION_RULES.md**, **NC_PARSER_GUIDE.md** — line-by-line vs implementation
