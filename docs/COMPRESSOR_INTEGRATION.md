# Compressor integration (Kaeser SIGMA CONTROL 2, backend-direct)

Shatter polls Kaeser compressors **directly** via the SC2 / Kaeser Connect web interface using a backend-native client (`backend/app/integrations/kaeser_sc2/client.py`). There is **no sidecar** and no compressor MQTT subscriber path.

## UI beta gate (dashboard)

Compressor **cards and add flow** on the dashboard are hidden until **beta mode** is enabled (same as the **[ TOOLS ]** page: rapid clicks on the **SHATTER** logo). The backend still exposes `/api/compressors`, polling, and WebSocket updates whenever compressor rows exist.

## Data model

- Table **`compressors`**: name, `ip_address` (SC2 host for display/ops), optional **`kaeser_connect_base_url`** / **`kaeser_username`** / **`kaeser_password`** (Kaeser Connect; password stored like machine FTP secrets and **never returned** from JSON APIs), `poll_interval_seconds`, `enabled`, optional `tags` / `layout_config`, timestamps, `last_seen_at`.
- Hypertable **`compressor_status_events`** (Timescale): status transitions for timeline/history APIs.

Compressors use **separate integer primary keys** from `machines.id`. Live payloads include `asset_kind: "compressor"` and `compressor_id`.

## MQTT (optional publish)

Shatter can optionally **publish** full compressor poll snapshots to Mosquitto (retained, QoS 1) under:\n\n- `shatter/compressors/{compressor_id}/poll`\n\nThis is separate from polling; Shatter still functions without MQTT.

## Shatter backend

- **`KaeserSc2Client`**: logs into SC2/Connect and fetches the same bundle shape Shatter expects.\n+- **`CompressorPollingService`**: polls each enabled compressor, writes samples/events, broadcasts **`compressor_status_update`**.

### Backend environment

| Variable | Purpose |
|----------|---------|
| `MQTT_PUBLISH_HOST` | Broker hostname; unset/empty to disable publishing. |
| `MQTT_PUBLISH_PORT` | Default `1883`. |
| `MQTT_PUBLISH_USERNAME` / `MQTT_PUBLISH_PASSWORD` | Optional broker credentials. |

## WebSocket

`initial_status` includes **`compressors`** (DB fields + cache). **`compressor_status_update`** carries the latest payload (operational telemetry + messages-derived alarms).

## REST API

- **`/api/compressors`**: CRUD, **`GET /{id}/status`** (cached).
- **`GET /api/compressors/{id}/status-history`**: poll-based **transition** log (unchanged).
- **`GET /api/compressors/{id}/status-samples`**: MQTT-throttled **~1 Hz** samples (Timescale **`compressor_status_samples`**, 30-day retention) for the compressor status oscilloscope in the UI.
- **`GET/PUT /api/compressors/{id}/layout`**.

## Testing

- `backend/tests/test_sidecar_mapper.py` — JSON → status payload mapping.

## Migrating existing databases

Init scripts:\n\n- `database/init/16-migrate-compressors-sidecar.sql`: legacy safe no-op (drops old Modbus columns if present)\n- `database/init/20-drop-compressor-sidecar-columns.sql`: drops legacy sidecar columns if present

## On-machine checks
\nShatter reaches the SC2 web UI (often **HTTPS** with a self-signed certificate). Ensure the backend can reach the compressor’s SC2/Connect address over the network.
