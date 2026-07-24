# Documentation Audit Log

> **Temporary audit artifact** — line-by-line review of Shatter-NC documentation against the codebase (March 2026).  
> Ground truth reference: [CODEBASE_GROUND_TRUTH.md](./CODEBASE_GROUND_TRUTH.md).

**Status:** Inaccuracies below were **corrected in source docs** on 2026-03-20. Keep this log for traceability until the audit artifacts are archived.

**Scope:** Active operator/contributor docs under `docs/`, plus root `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `frontend/README.md`.  
**Excluded:** `docs/archive/`, `docs/scrape/` (vendor manuals), `brother_cnc_export/`, `.cursor/`.  

**Legend**

| Severity | Meaning |
|----------|---------|
| **Critical** | Wrong path/behavior; likely breaks integration or misleads operators |
| **High** | Factually wrong feature behavior or deployment step |
| **Medium** | Outdated details, missing context, or incomplete coverage |
| **Low** | Cosmetic, aspirational, or minor wording drift |
| **Info** | Accurate; noted for audit completeness |

---

## Executive summary

| Doc | Issues found | Critical | High | Medium | Low |
|-----|--------------|----------|------|--------|-----|
| [WEBSOCKET_PROTOCOL.md](../WEBSOCKET_PROTOCOL.md) | 3 | 1 | 1 | 1 | 0 |
| [USER_GUIDE.md](../USER_GUIDE.md) | 8 | 0 | 2 | 5 | 1 |
| [BACKEND_ARCHITECTURE.md](../BACKEND_ARCHITECTURE.md) | 6 | 0 | 0 | 4 | 2 |
| [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) | 4 | 0 | 1 | 2 | 1 |
| [COMPRESSOR_INTEGRATION.md](../COMPRESSOR_INTEGRATION.md) | 4 | 0 | 0 | 3 | 1 |
| [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) | 12+ | 0 | 1 | 9 | 2+ |
| [DATABASE_MIGRATIONS.md](../DATABASE_MIGRATIONS.md) | 2 | 0 | 0 | 2 | 0 |
| [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) | 3 | 0 | 0 | 2 | 1 |
| [INSTALLATION_GUIDE.md](../INSTALLATION_GUIDE.md) | 4 | 0 | 0 | 3 | 1 |
| [TELNET_REFERENCE.md](../TELNET_REFERENCE.md) | 1 | 0 | 0 | 1 | 0 |
| [FTP_SYNC_EXCLUSION_RULES.md](../FTP_SYNC_EXCLUSION_RULES.md) | 2 | 0 | 0 | 1 | 1 |
| [NC_PARSER_GUIDE.md](../NC_PARSER_GUIDE.md) | 1 | 0 | 0 | 1 | 0 |
| [UX_DESIGN_GUIDE.md](../UX_DESIGN_GUIDE.md) | 3 | 0 | 0 | 0 | 3 |
| [README.md](../README.md) (docs index) | 2 | 0 | 0 | 1 | 1 |
| [README.md](../../README.md) (root) | 2 | 0 | 0 | 2 | 0 |
| [SECURITY.md](../../SECURITY.md) | 1 | 0 | 0 | 1 | 0 |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | 1 | 0 | 0 | 1 | 0 |
| [frontend/README.md](../../frontend/README.md) | 0 | — | — | — | — |

**Cross-cutting themes**

1. WebSocket endpoint documented as `/ws`; code and frontend use **`/api/ws`**.
2. Production nginx proxies **`/api/`**, not a standalone `/ws` path; SPA calls API on **port 8000** directly.
3. Dashboard does **not** REST-poll machine status when WebSocket drops (stale cache or loading screen only).
4. PostgreSQL version documented as **14**; compose uses **`timescale/timescaledb:latest-pg15`**.
5. **`DATABASE_SCHEMA.md`** is substantially stale (missing tables, wrong retention, wrong column defaults).
6. Prod **`docker-compose.prod.yml`** does not pass **`SMTP_*`** or **`LOCAL_TIMEZONE`** to the backend container.
7. Several beta-gated features documented without mentioning beta mode.

---

## WEBSOCKET_PROTOCOL.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 8–9 | Endpoint `ws://<host>:8000/ws` | Router prefix `/api` + `@router.websocket("/ws")` → **`/api/ws`**. Frontend: `frontend/src/config/api.ts` `WS_URL`. | **Critical** |
| 11 | “Production nginx proxies this path” | `frontend/nginx.conf` proxies **`/api/`** only. No `/ws` location. WS goes to `host:8000/api/ws` unless `VITE_API_URL` overrides. | **High** |
| 3, 67–68 | No auth; passwords not in payloads | Accurate (`WebSocketManager`, compressor credential flags). | Info |
| 19–23 | Envelope fields `type`, `timestamp`, `data`, `machines`, `compressors` | Matches `backend/app/services/websocket.py`. | Info |
| 27–37 | `initial_status` on connect | Accurate. | Info |
| 40–59 | `status_update` + server merge | Accurate (`_STATUS_SNAPSHOT_KEYS_FROM_CACHE`, program name preservation). | Info |
| 61–63 | `compressor_status_update` | Accurate (`broadcast_compressor_status`). | Info |
| 74 | “REST fallback: machine list and status APIs when WebSocket is disconnected” | Backend cache updated regardless of WS clients. Frontend dashboard **does not** poll REST for fleet status; shows `AsciiLoadingScreen` or stale WS data. Deprecated `GET /api/machines/{id}/status` exists but is not used as dashboard fallback. | **Medium** |

---

## USER_GUIDE.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 12 | Header shows `WS CONNECTED` | Accurate; label toggles to `WS DISCONNECTED` (`Dashboard.tsx`). | Info |
| 22 | “If disconnected, the UI falls back to REST polling” | **False** for dashboard fleet status. WS-only via `WebSocketContext`. Summary modals poll REST every 2s, but machine cards do not. | **High** |
| 28 | Run states include “idle, alarm, etc.” | PRD3 maps to `off`, `standby`, `operating`, `stopped`, `error`. UI displays `standby` as **IDLE** label; there is no separate `idle` status from backend. “Alarm” is separate from run state (alarm pane). | **Medium** |
| 40 | FTP sync in add/edit without beta note | FTP sync checkbox and `MachineSyncPanel` are **beta-gated** (`isBetaMode` in `MachineCard.tsx`). | **Medium** |
| 64 | “Open File Browser from a machine card” | Also available via nav **`/files`** route and deep links (`?machine=&file=&path=`). Doc incomplete, not wrong. | **Low** |
| 78 | Work offsets via POSNI | Validation uses **telnet** `get_position_data()` → POSNI (`programs.py`); not FTP. Accurate. | Info |
| 97 | Tool statuses: `found`, `missing`, `mismatch`, `not_in_nc` | API returns `ToolValidationResult` with `available`, `diameter_match`, `length_sufficient`. UI shows **PASS/FAIL**, not those string statuses. | **Medium** |
| 108 | WCS status `xyz_not_parsed` | UI shows **“XYZ NOT PARSED”** (display string); API uses `WCSValidationResult` with `valid`/`within_tolerance`/`warnings`. Concept accurate, field names wrong. | **Medium** |
| 123–131 | Tools page described without beta | Route `/tools` wrapped in **`BetaRoute`**; requires beta mode activation. | **High** |
| 143 | “Configure … in **Settings**” | Notifications live at **`/notifications`** (beta). No Settings page. | **Medium** |
| 137 | Compressors on dashboard | Accurate; not beta-gated. | Info |

---

## BACKEND_ARCHITECTURE.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 13 | PostgreSQL **14** + TimescaleDB | Compose: **`latest-pg15`**. | **Medium** |
| 29 | Diagram: “WebSocket /ws” | Actual path **`/api/ws`**. | **Medium** |
| 53–56 | Startup: migrations → settings → PollingService + CompressorPollingService | Also starts **`NotificationService`**, **`FtpSyncService`**, **`MqttPublisher`** (`main.py` startup_event). | **Medium** |
| 70 | `WebSocketManager.broadcast_status_update` | Method is **`broadcast_status`** (`websocket.py`). | **Low** |
| 74 | “Failed polls mark machine offline” | **Debounced**: `display_online()` requires prior success and `< 3` consecutive failures (`_machine_poller.py`). | **Medium** |
| 99 | Offsets “telnet/FTP POSNI” | Validation uses **telnet POSNI** in `programs.py`; FTP not used for validate-time offsets. | **Low** |
| 118 | Optional MQTT publish for compressors | Accurate; also publishes **`shatter/machines/{id}/poll`** from CNC polling. Doc omits CNC MQTT topics. | **Low** |
| 132–135 | No auth, rate limit 100/min, OpenAPI when DEBUG | Accurate. | Info |
| 143 | Key routers list | Omits **`compressors`**, **`history`**, **`settings`**. Incomplete. | **Low** |

---

## ENVIRONMENT_VARIABLES.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 19–65 | Backend variable table | Matches `config.py` for listed vars. | Info |
| 62–63 | `SECRET_KEY` required in prod; `ENABLE_AUTH` no effect | `SECRET_KEY` loaded but **not used** by app logic. `ENABLE_AUTH` accurate. | **Medium** |
| 67–71 | Frontend: only `VITE_API_URL` | Also used: **`VITE_APP_VERSION`**, **`VITE_TABLET_MACHINE_ID`**, **`VITE_TABLET_COMPRESSOR_ID`**, **`VITE_PWA_START_URL`** (build/Docker). | **Medium** |
| — (missing) | — | **`MIGRATIONS_DIR`**, **`SHATTER_TELNET_PROXY_HOST`**, **`SHATTER_TELNET_PROXY_PORT`** used in dev compose / migration runner; not documented. | **Medium** |
| 53–58, 75–83 | SMTP vars configurable via `.env` for prod | **`docker-compose.prod.yml`** does **not** list `SMTP_*` or `LOCAL_TIMEZONE` under backend `environment:`. Values in `.env` alone won't reach container. Twilio vars **are** listed. | **High** |
| 28 | `LOG_LEVEL=DEBUG` enables OpenAPI | Accurate (`main.py` checks `LOG_LEVEL`, not `DEBUG` flag). | Info |

---

## COMPRESSOR_INTEGRATION.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 3 | Direct SC2 polling, no sidecar | Accurate. | Info |
| 7 | Tablet routes without beta | Accurate. | Info |
| 11–14 | Data model fields | Matches `backend/app/models/compressor.py`. | Info |
| 18 | MQTT topic with literal `\n` in markdown | Formatting artifact; topic is `shatter/compressors/{id}/poll`. Accurate content. | **Low** |
| 22 | Literal `\n+-` in bullet | Markdown formatting broken; content otherwise accurate. | **Low** |
| 40 | status-samples: “**MQTT-throttled ~1 Hz** … **30-day** retention” | Throttle is **`COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS`** (backend poll). Retention **14 days raw** (migration 19 overrides migration 18’s 30 days). 1-min aggregate retained 400 days. | **Medium** |
| 38–41 | REST paths under `/api/compressors` | CRUD/status under compressors router. **`status-history`** and **`status-samples`** are under **`/api/compressors/{id}/...`** via `history.py` — paths correct. | Info |
| 52 | HTTPS self-signed | Client uses httpx; verify cert behavior in `KaeserSc2Client` if documenting TLS skip (not verified in this audit). | **Medium** (unverified) |

---

## DATABASE_SCHEMA.md

> Large doc (~970 lines). Audit focused on schema diagram, `machines` table, retention section, and missing domains.

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 7, 17 | PostgreSQL **14+** | Runtime **PG 15** in compose. | **Medium** |
| 36–55 (diagram) | `machines` columns | **Missing** from diagram: `tool_poll_interval_seconds`, `control_version`, `part_display_mode`, `ftp_sync_enabled`, `validate_tool_diameter`, `validate_tool_length`. | **High** |
| 169 | Location `machine.py:8-42` | Model now extends to line 63; line ref stale. | **Low** |
| 181 | `path` default **`/PROGRAM`** | SQL init: **`/program`** (`01-init.sql`). Model default: **`/`**. Three conflicting values. | **Medium** |
| 185, 194 | `units` listed twice in table | Duplicate row in doc table. | **Low** |
| 151–160 (diagram) | Hypertables listed | **Missing entire domains**: compressors, FTP sync, notifications, PRD3 history, extended history tables, compressor samples. | **High** |
| 500–501, 740 | `machine_status_events` retention **90 days** | SQL: **`1 year`** (`02-add-program-tracking.sql`). | **Medium** |
| 688, 747–748 | `polling_events` retention **30 days** | SQL: **`1 year`** (`05-add-polling-events.sql`). | **Medium** |
| 743 | `alarm_events` retention **1 year** | SQL: **`2 years`**. | **Medium** |
| 794 | “Continuous Aggregates (Future)” | **`compressor_status_samples_1min`** exists (migration 19). Section outdated. | **Medium** |
| 819–827 | “Current Approach” + future Alembic | Alembic in requirements; project uses **SQL file runner**. Alembic listed as future — partially accurate but Alembic already a dependency. | **Low** |
| 642–688 | `polling_events` section | Table exists and matches init SQL; retention wrong (see above). | **Medium** |

**Recommendation:** Treat `DATABASE_SCHEMA.md` as needing a full rewrite against `database/init/*.sql` and `backend/app/models/`.

---

## DATABASE_MIGRATIONS.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 22–24 | Dev uses `start-dev.sh` | Dev Docker **`Dockerfile` development target** uses **inline bash CMD**, not `start-dev.sh` (comment: Windows CRLF). `start-dev.sh` valid for **local hybrid** dev only. | **Medium** |
| 139 | “Dockerfile updated to use startup scripts (start-dev.sh for development)” | Dev container uses inline CMD; prod uses `start.sh`. Partially outdated. | **Medium** |
| 31–35, 52–88 | Migration runner behavior | Accurate (`run_migrations.py`, `schema_migrations`). | Info |
| 7–14 | Root cause narrative (polling_events) | Historical context; still accurate as cautionary tale. | Info |

---

## DEVELOPMENT_GUIDE.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 14 | Python **3.11+** | Docker/CI split: image **3.11**, CI **3.12** (`.github/workflows/test.yml`). | **Medium** |
| 22–25 | Full Docker: postgres + backend + frontend | Dev compose also starts **mosquitto** (always, not profile-gated). | **Low** |
| 104 | `PYTHONPATH=backend pytest backend/tests/` | Accurate; CI also enforces **25% coverage floor** (not mentioned). | **Low** |
| 121–124 | OpenAPI when `LOG_LEVEL=DEBUG` | Accurate. | Info |
| 152 | “nginx proxies `/ws` in prod” | **Wrong** — nginx proxies `/api/`; WS path is `/api/ws` on port 8000. | **Medium** |
| 153 | Telnet single connection | Accurate (per-machine lock, fresh connections). | Info |

---

## INSTALLATION_GUIDE.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 36–37 | Prod services: postgres, backend, frontend | Accurate; mosquitto optional via **`--profile mqtt`**. | Info |
| 60 | `timescale/timescaledb:latest-pg15` | Accurate. | Info |
| 44 | Backend port 8000 exposed | Accurate; frontend SPA calls **8000 directly** for API/WS (CORS must include UI origin on port 80). | **Medium** |
| 96–97 | `SECRET_KEY` required minimum | Loaded but unused by runtime; still good practice. | **Low** |
| 155 | API docs at `:8000/docs` when `LOG_LEVEL=DEBUG` | Accurate. | Info |
| 157 | `start.command` for dev | Accurate (`start.command` uses dev compose). | Info |
| 165 | “notification channels, FTP sync configs” in first use | Both are **beta-gated** in UI (FTP sync checkbox + `/notifications`). | **Medium** |
| 184 | Container names `shatter-*-prod` | Accurate per prod compose. | Info |
| 205–216 | Backup/restore commands | Accurate pattern. | Info |

---

## TELNET_REFERENCE.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 3 | HTTP port 80 legacy, not used for polling | Polling uses telnet; `http_client.py` exists but not primary poll path. Accurate enough. | Info |
| 20 | `get_atc_magazine_data()` → **ATCTL / ATCTLD** | Code uses **ATCTL (C00)** and **ATDTL (D00)**, not ATCTLD (`_telnet_data_reads.py`). | **Medium** |
| 15–21, 31–42 | LOD/RED read methods | Match `_telnet_data_reads.py` mixins. | Info |
| 56–66 | CHGMAG* write commands | Match `_telnet_write_ops.py`. | Info |
| 84–96 | ATC status codes | Match `COMPLETION_CODES` in `_telnet_state.py`. | Info |
| 102–104 | Not implemented list | Accurate (FTP used for files). | Info |

---

## FTP_SYNC_EXCLUSION_RULES.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 11 | “only `.NC` files … sync **upload**” | Extension rule applies in `validate_brother_filename` for both directions when rules run; upload-focused wording slightly narrow. | **Low** |
| 14 | Reserved files list | Code also excludes **`TLOAD*`**, **`ATCTLD*`** (`SYSTEM_FILE_PATTERNS` in `ftp_sync_rules.py`); doc list incomplete. | **Medium** |
| 20–22 | Nested directory limits C00/D00 | Implemented in `ftp_sync_service._max_nested_folder_depth` (C00: 0, D00: 2) — matches “root only” / “two folder levels”. | Info |
| 37–50 | Exclusion reason codes | Match `validate_brother_filename` and `ftp_sync_service` skip reasons. | Info |
| 28 | `include_pattern` config field | Exists on model (`ftp_sync.py` default `*.NC`); rules doc lists it but exclusion section doesn’t explain its use — incomplete. | **Low** |

---

## NC_PARSER_GUIDE.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 24–29 | Tool comment format `(T01 D=…)` | Matches `gcode_parser.py` extraction patterns. | Info |
| 45–66 | WCS verification block macros | Matches `extract_wcs_offset()` approach. | Info |
| 99 | `parse()` returns tools, wcs, posted_date, runtime | Returns **`wcs_offset`** key (not `wcs_location` used in internal docstring comment). | **Medium** |
| 72 | Operation metadata for Tools page | Accurate when post emits operation comments. | Info |

---

## UX_DESIGN_GUIDE.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 11 | **NO EMOJI** | Root **README.md** uses emoji in feature list; product marketing differs from UI guide. Guide is prescriptive for UI code. | **Low** (internal consistency) |
| 40–44 | “Users could switch between phosphor colors” | No theme switcher found in frontend; single green terminal theme (+ component-level amber/red). **Aspirational**. | **Low** |
| 92 | Example header “SHATTER v0.1.0” | Version now dynamic (`VITE_APP_VERSION` / 0.23.0). | **Low** |
| Colors, fonts, ASCII patterns | Generally match `terminal.css`, `TerminalBox`, IBM Plex Mono usage. | Info |

---

## docs/README.md (index)

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 22 | BACKEND_ARCHITECTURE “~300 lines” | File is **~161 lines**. | **Low** |
| 39 | Parser template at `.cursor/templates/SCHEMA_DEFINITION_TEMPLATE.md` | Link target exists under `.cursor/templates/`. Separate `docs/templates/` path referenced in glob index may not exist on disk. | **Low** |
| 5–27 | Doc index listing | All linked active docs exist except verify roadmap/templates paths. | Info |

---

## README.md (root)

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 56 | PostgreSQL **14** | Compose uses **PG 15**. | **Medium** |
| 11, 14 | Sync and Notifications “(beta)” | Accurate for UI gating. | Info |
| 81 | OpenAPI when `LOG_LEVEL=DEBUG` | Accurate. | Info |
| 54–56 | React 19, Python 3.11, ports | Accurate. | Info |

---

## SECURITY.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 28–35 | No auth; ENABLE_AUTH no effect | Accurate. | Info |
| 39–46 | Prod port exposure table | Matches `docker-compose.prod.yml`. | Info |
| 24 | `SECRET_KEY` in production | Required in compose but **unused** by application code — doc implies security value that code doesn't enforce. | **Medium** |
| 56 | API redacts secrets on GET | Accurate (`secret_redaction.py`). | Info |

---

## CONTRIBUTING.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| 32 | Python 3.11+ | CI runs **3.12**; Docker **3.11**. | **Medium** |
| 571 | Test WebSocket reconnection | Valid manual test; no automated test cited. | Info |

---

## frontend/README.md

| Line(s) | Doc claim | Code truth | Sev |
|---------|-----------|------------|-----|
| All | Points to dev guide, UX guide, user guide; docker/npm commands | Accurate. | Info |

---

## Verified accurate (no issues logged)

These docs were reviewed and found **substantially accurate** for their scope:

- **SECURITY.md** — deployment model, port exposure, no-auth stance (except SECRET_KEY nuance above).
- **FTP_SYNC_EXCLUSION_RULES.md** — core rule codes and C00/D00 nesting (minor list gaps only).
- **NC_PARSER_GUIDE.md** — CAM author guidance aligns with `gcode_parser.py`.
- **frontend/README.md** — minimal pointer doc; correct.

---

## Broken or missing doc paths

| Reference | Issue |
|-----------|-------|
| `docs/roadmap/FUTURE_DOCUMENTATION.md` | Appears in repo index/glob but **not readable** on disk in this workspace |
| `docs/templates/SCHEMA_DEFINITION_TEMPLATE.md` | Same; live template is **`.cursor/templates/SCHEMA_DEFINITION_TEMPLATE.md`** |

---

## Suggested fix priority

1. **WEBSOCKET_PROTOCOL.md** — fix endpoint to `/api/ws`; clarify prod networking (port 8000 vs nginx `/api/`).
2. **USER_GUIDE.md** — remove REST polling fallback claim; document beta gates; fix Notifications route.
3. **ENVIRONMENT_VARIABLES.md** — document prod compose passthrough gap for SMTP; add missing vars.
4. **DATABASE_SCHEMA.md** — full refresh from migrations/models (largest drift).
5. **COMPRESSOR_INTEGRATION.md** — sample retention/throttle source.
6. **BACKEND_ARCHITECTURE.md**, **DEVELOPMENT_GUIDE.md** — WS path, PG version, startup services, online debounce.
7. **TELNET_REFERENCE.md** — ATDTL vs ATCTLD.
8. **INSTALLATION_GUIDE.md** — beta features, CORS note for port 80 UI + 8000 API.

---

## Audit metadata

| Field | Value |
|-------|-------|
| App version in code | 0.23.0 |
| Audit date | 2026-03-20 |
| Method | Line-by-line doc review cross-checked against `backend/`, `frontend/`, `database/init/`, compose files |
| Follow-up | Doc fixes applied 2026-03-20; archive this log when no longer needed |
