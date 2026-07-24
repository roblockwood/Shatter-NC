# Compressor integration (Kaeser SIGMA CONTROL 2, backend-direct)

Shatter polls Kaeser compressors **directly** via the SC2 / Kaeser Connect web interface using a backend-native client (`backend/app/integrations/kaeser_sc2/client.py`). There is **no sidecar** and no compressor MQTT subscriber path.

## Dashboard UI

Compressor **cards and add flow** appear on the dashboard alongside CNC machines. Use **[ ADD COMPRESSOR ]** on the add card to register a Kaeser unit. Tablet kiosk routes (`/tablet/compressor/...`) work without beta mode.

## Data model

- Table **`compressors`**: name, `ip_address` (SC2 host for display/ops), optional **`kaeser_connect_base_url`** / **`kaeser_username`** / **`kaeser_password`** (Kaeser Connect; password stored like machine FTP secrets and **never returned** from JSON APIs), `poll_interval_seconds`, `enabled`, optional `tags` / `layout_config`, timestamps, `last_seen_at`.
- Hypertable **`compressor_status_events`** (Timescale): status transitions for timeline/history APIs.
- Hypertable **`compressor_status_samples`**: high-frequency telemetry for chart/oscilloscope UI.
- Continuous aggregate **`compressor_status_samples_1min`**: downsampled history beyond raw retention window.

Compressors use **separate integer primary keys** from `machines.id`. Live payloads include `asset_kind: "compressor"` and `compressor_id`.

## MQTT (optional publish)

Shatter can optionally **publish** full compressor poll snapshots to Mosquitto (retained, QoS 1) under:

- `shatter/compressors/{compressor_id}/poll`

This is separate from polling; Shatter still functions without MQTT.

## Shatter backend

- **`KaeserSc2Client`**: logs into SC2/Connect and fetches the bundle Shatter expects.
- **`CompressorPollingService`**: polls each enabled compressor, writes samples/events, broadcasts **`compressor_status_update`**.

Sample writes are throttled by **`COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS`** (default 1.0s) during backend polling — not by MQTT.

### Backend environment

| Variable | Purpose |
|----------|---------|
| `MQTT_PUBLISH_HOST` | Broker hostname; unset/empty to disable publishing. |
| `MQTT_PUBLISH_PORT` | Default `1883`. |
| `MQTT_PUBLISH_USERNAME` / `MQTT_PUBLISH_PASSWORD` | Optional broker credentials. |
| `COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS` | Min seconds between raw sample rows (default `1.0`). |
| `COMPRESSOR_STATUS_SAMPLES_RAW_DAYS` | App setting aligned with raw hypertable retention (default `14`). |

## WebSocket

`initial_status` includes **`compressors`** (DB fields + cache). **`compressor_status_update`** carries the latest payload (operational telemetry + messages-derived alarms).

## REST API

- **`/api/compressors`**: CRUD, **`GET /{id}/status`** (cached).
- **`GET /api/compressors/{id}/status-history`**: poll-based transition log.
- **`GET /api/compressors/{id}/status-samples`**: chart samples (~1 Hz during polling; raw hypertable **14-day** retention, 1-minute aggregate for longer ranges).
- **`GET/PUT /api/compressors/{id}/layout`**.

## Testing

- `backend/tests/test_sidecar_mapper.py` — JSON → status payload mapping.

## Migrating existing databases

Init scripts:

- `database/init/16-migrate-compressors-sidecar.sql`: legacy safe no-op (drops old Modbus columns if present)
- `database/init/20-drop-compressor-sidecar-columns.sql`: drops legacy sidecar columns if present

## On-machine checks

Shatter reaches the SC2 web UI (often **HTTPS** with a self-signed certificate). Ensure the backend can reach the compressor's SC2/Connect address over the network.
