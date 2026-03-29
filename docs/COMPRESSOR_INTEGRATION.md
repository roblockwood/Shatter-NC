# Compressor integration (Kaeser SIGMA CONTROL 2 via sidecar)

Shatter does **not** talk Modbus or Kaeser Connect on the controller directly. It integrates with **[Brown-Industries/kaeser-sc2-api](https://github.com/Brown-Industries/kaeser-sc2-api)** (GPL-3.0), vendored under `vendor/kaeser-sc2-api`, as a **sidecar** that logs into the SC2 **Kaeser Connect** web UI and exposes **REST** + **MQTT**.

## UI beta gate (dashboard)

Compressor **cards and add flow** on the dashboard are hidden until **beta mode** is enabled (same as the **[ TOOLS ]** page: rapid clicks on the **SHATTER** logo). The backend still exposes `/api/compressors`, polling, and WebSocket updates whenever compressor rows exist.

## Data model

- Table **`compressors`**: name, `ip_address` (SC2 host for display/ops), **`sidecar_rest_base_url`** (e.g. `http://kaeser-sc2-api:3004`), **`mqtt_topic_root`** (must match the sidecar’s `MQTT_TOPIC_ROOT`), optional **`kaeser_connect_base_url`** / **`kaeser_username`** / **`kaeser_password`** (Kaeser Connect; password stored like machine FTP secrets and **never returned** from JSON APIs), `poll_interval_seconds`, `enabled`, optional `tags` / `layout_config`, timestamps, `last_seen_at`.
- Hypertable **`compressor_status_events`** (Timescale): status transitions for timeline/history APIs.

Compressors use **separate integer primary keys** from `machines.id`. Live payloads include `asset_kind: "compressor"` and `compressor_id`.

### Kaeser credentials from the Shatter UI (sidecar env file)

The stock sidecar only reads **`KAESER_*` / `MQTT_*` at process start**. Shatter can still let operators enter **URL + username + password** in the add/edit compressor dialog:

1. Set backend **`KAESER_SIDECAR_ENV_DIR`** (Compose dev: `/docker/generated` with host bind `./docker/generated`).
2. On create/update, if all three Kaeser fields are set, the backend writes **`{KAESER_SIDECAR_ENV_DIR}/compressor-{id}.env`** (MQTT lines come from `MQTT_BROKER_*` / `MQTT_USER` / `MQTT_PASSWORD` and the compressor’s `mqtt_topic_root`).
3. Point **`docker-compose`** **`env_file`** at that file (see `docker/generated/compressor-1.env.example` — replace **`1`** with the compressor row id).
4. **Restart** the sidecar (`docker compose ... up -d --force-recreate` for that service) so Nest picks up the new file.

If `KAESER_SIDECAR_ENV_DIR` is unset, credentials are only stored in the DB (for future use); nothing is written for the sidecar.

## Sidecar and MQTT

- Run **one kaeser-sc2-api container per compressor** (same Kaeser user must not be shared concurrently across sessions).
- Sidecar environment: normally supplied via the generated **`compressor-{id}.env`** above, or manually: `KAESER_ADDRESS`, `KAESER_USERNAME`, `KAESER_PASSWORD`, `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASS`, `MQTT_TOPIC_ROOT` (see `docker/kaeser-sc2-api.env.example`).
- **Eclipse Mosquitto** is included in Compose (`docker/mosquitto/mosquitto.conf`, anonymous listener for dev).
- **Dev:** `docker compose -f docker-compose.dev.yml --profile kaeser up -d` starts the sidecar **in addition** to `mqtt` (already in the default profile).
- **SC2 `json.json` register IDs** (pressure, temps, status text) are **firmware/HMI-specific**. This repo patches the vendored sidecar in **`vendor/kaeser-sc2-api/src/modules/maintenance/dto/operational.dto.ts`** (`SC2_OPERATIONAL_IDS`) and the **`getOperational()`** id list in **`maintenance.service.ts`**. Rebuild the sidecar image after changes.

## Shatter backend

- **`aiomqtt`**: subscribes to broker topics under each compressor’s `mqtt_topic_root` (e.g. `…/operational-data`, `…/status`). Fast UI updates when the sidecar publishes.
- **`httpx`**: on a slower interval (`COMPRESSOR_REST_REFRESH_SECONDS`, default 60), calls `GET {sidecar}/api/v1/maintenance?data=…` for messages, maintenance timers, I/O, operating hours.
- **`CompressorPollingService`**: merges bridge state, updates `last_seen_at` / status events, broadcasts **`compressor_status_update`**.

### Backend environment

| Variable | Purpose |
|----------|---------|
| `MQTT_BROKER_HOST` | Broker hostname (Compose default `mqtt`); unset to disable MQTT (REST-only). |
| `MQTT_BROKER_PORT` | Default `1883`. |
| `MQTT_USER` / `MQTT_PASSWORD` | Optional credentials (must match sidecar if the broker requires them). |
| `COMPRESSOR_REST_REFRESH_SECONDS` | REST full refresh interval (default `60`). |

## WebSocket

`initial_status` includes **`compressors`** (DB fields + cache). **`compressor_status_update`** carries the merged payload (operational telemetry, alarms from messages, sidecar errors in `metrics`).

## REST API

- **`/api/compressors`**: CRUD, **`GET /{id}/status`** (cached).
- **`GET /api/compressors/{id}/status-history`**: poll-based **transition** log (unchanged).
- **`GET /api/compressors/{id}/status-samples`**: MQTT-throttled **~1 Hz** samples (Timescale **`compressor_status_samples`**, 30-day retention) for the compressor status oscilloscope in the UI.
- **`GET/PUT /api/compressors/{id}/layout`**.

## Testing

- `backend/tests/test_sidecar_mapper.py` — JSON → status payload mapping.

## Migrating existing databases

Init script **`database/init/16-migrate-compressors-sidecar.sql`** drops `modbus_port` / `modbus_unit_id` and adds sidecar columns when an old schema is detected. Fresh installs use **`15-add-compressors.sql`** only. Existing Docker volumes that already ran the old `15` need the DB to apply `16` (re-init volume or run the SQL manually).

## On-machine checks

The **sidecar** reaches the SC2 web UI (often **HTTPS** with a self-signed certificate). Shatter only needs network access to **MQTT** and the **sidecar REST** port (**3004** in upstream `main.ts`).
