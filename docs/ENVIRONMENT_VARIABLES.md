# Environment Variables

Shatter uses [12-factor](https://12factor.net/config) configuration via `.env` files (never committed). **Source of truth:** [`backend/app/core/config.py`](../backend/app/core/config.py), [`.env.example`](../.env.example), [`.env.production.example`](../.env.production.example).

> **Security:** Shatter has no API authentication. Deploy on a trusted shop LAN. See [SECURITY.md](../SECURITY.md).

---

## Quick Setup

**Development:** `cp .env.example .env` then `docker compose -f docker-compose.dev.yml up -d`

**Production:** download `docker-compose.prod.yml` and `.env.production.example` (see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)), copy to `.env`, set `POSTGRES_PASSWORD`, `SECRET_KEY`, and `CORS_ORIGINS` before first start.

---

## Variable Reference

| Variable | Default | Required in prod | Purpose |
|----------|---------|------------------|---------|
| `COMPOSE_PROJECT_NAME` | — | No | Docker project prefix (`.env.example`: `shatter`) |
| `GITHUB_OWNER` | `roblockwood` | No | ghcr.io image owner (`docker-compose.prod.yml`) |
| `GITHUB_REPO` | `shatter-nc` | No | ghcr.io image repo name (lowercase) |
| `IMAGE_TAG` | `latest` | No | Backend/frontend image tag (`v1.2.3`, commit SHA, or `latest`) |
| `APP_NAME` | `Shatter` | No | Display name in logs |
| `APP_VERSION` | from code | No | API metadata (semantic-release updates) |
| `DEBUG` | `false` | No | Verbose debug mode |
| `LOG_LEVEL` | `INFO` | No | `DEBUG` enables OpenAPI at `/docs` |
| `BACKEND_HOST` | `0.0.0.0` | No | API bind address |
| `BACKEND_PORT` | `8000` | No | API port |
| `POSTGRES_HOST` | `localhost` | Yes | DB host (`postgres` in compose) |
| `POSTGRES_PORT` | `5432` | Yes | DB port |
| `POSTGRES_DB` | `shatter` | Yes | Database name |
| `POSTGRES_USER` | `shatter_user` | Yes | DB user |
| `POSTGRES_PASSWORD` | `changeme` | **Yes** | DB password — change in prod |
| `DEFAULT_POLL_INTERVAL` | `5` | No | CNC status poll seconds |
| `DEFAULT_TOOL_POLL_INTERVAL` | `30` | No | Tool table poll seconds |
| `HEARTBEAT_INTERVAL_MINUTES` | `2` | No | Status log interval when unchanged |
| `FTP_SYNC_ENABLED` | `true` | No | Enable FTP sync feature |
| `FTP_SYNC_LOCAL_WATCH_ENABLED` | `false` | No | Watch local folders for changes |
| `FTP_SYNC_SCAN_INTERVAL_SECONDS` | `5` | No | Local watch scan interval |
| `FTP_SYNC_REMOTE_DIR_CREATE_RETRIES` | `2` | No | Remote mkdir retries |
| `FTP_SYNC_REMOTE_DIR_CREATE_DELAY_SECONDS` | `0.25` | No | Delay between mkdir retries |
| `FTP_SYNC_LOCAL_BROWSE_ROOT` | `/` | No | Container path for sync folder picker |
| `FTP_SYNC_LOCAL_BROWSE_HOST_PATH` | — | No | Host path mounted into container (compose) |
| `MQTT_PUBLISH_HOST` | unset | No | Mosquitto host; empty = disabled |
| `MQTT_PUBLISH_PORT` | `1883` | No | MQTT port |
| `MQTT_PUBLISH_USERNAME` | unset | No | MQTT auth |
| `MQTT_PUBLISH_PASSWORD` | unset | No | MQTT auth |
| `MQTT_PUBLISH_TOPIC_PREFIX` | `shatter` | No | Topic prefix for compressor publish |
| `COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS` | `1.0` | No | Min interval between compressor samples |
| `COMPRESSOR_STATUS_SAMPLES_RAW_DAYS` | `14` | No | Raw hypertable retention days |
| `SMTP_HOST` | unset | No | Global SMTP default (channels override) |
| `SMTP_PORT` | `587` | No | SMTP port |
| `SMTP_USERNAME` | unset | No | SMTP user |
| `SMTP_PASSWORD` | unset | No | SMTP password |
| `SMTP_START_TLS` | `true` | No | STARTTLS (port 587) |
| `SMTP_USE_TLS` | `false` | No | Implicit TLS (port 465) |
| `TWILIO_ACCOUNT_SID` | unset | No | SMS channel default |
| `TWILIO_AUTH_TOKEN` | unset | No | SMS channel default |
| `TWILIO_FROM_NUMBER` | unset | No | SMS sender E.164 |
| `SECRET_KEY` | unset | **Yes** | Required in prod compose; loaded by config but **not used** by app logic today |
| `ENABLE_AUTH` | `false` | No | **Legacy — no effect** |
| `CORS_ORIGINS` | localhost list | **Yes** | JSON array of allowed browser origins |
| `LOCAL_TIMEZONE` | `America/Los_Angeles` | No | CNC timestamp interpretation |
| `MIGRATIONS_DIR` | auto-detect | No | SQL migration directory (`run_migrations.py`; set in compose) |
| `SHATTER_TELNET_PROXY_HOST` | unset | No | Dev-only telnet proxy host (Docker Desktop → CNC) |
| `SHATTER_TELNET_PROXY_PORT` | `10000` | No | Dev-only telnet proxy port |

### Frontend (Vite)

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | auto-detect | Override API base URL (rare; see `.env.example`) |
| `VITE_APP_VERSION` | from build | Display version in UI header (CI/Docker build arg) |
| `VITE_TABLET_MACHINE_ID` | unset | Default CNC id for `/tablet` kiosk entry |
| `VITE_TABLET_COMPRESSOR_ID` | unset | Default compressor id for tablet entry |
| `VITE_PWA_START_URL` | unset | Optional PWA manifest override (Docker build arg) |

---

## Production Checklist

```bash
POSTGRES_PASSWORD=<openssl rand -hex 32>
SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS='["http://your-shop-ip","http://localhost"]'
LOG_LEVEL=WARNING
ENABLE_AUTH=false
```

Restrict `FTP_SYNC_LOCAL_BROWSE_HOST_PATH` to directories operators should see. See [SECURITY.md](../SECURITY.md#ftp-sync-local-browse).

### Production compose passthrough

`docker-compose.prod.yml` lists explicit `environment:` keys for the backend. Variables in `.env` used only for `${...}` substitution are **not** automatically visible inside the container unless listed under `environment:` or passed via `env_file`.

**Currently passed in prod compose:** database, `LOG_LEVEL`, poll/compressor settings, `SECRET_KEY`, `CORS_ORIGINS`, MQTT, Twilio, SMTP, `LOCAL_TIMEZONE`, `FTP_SYNC_ENABLED`, `MIGRATIONS_DIR`, FTP browse root.

**Dev compose** uses `env_file: .env`, so any variable in `.env` reaches the backend without listing each key explicitly.

---

## Related

- [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) — deploy with these values
- [COMPRESSOR_INTEGRATION.md](COMPRESSOR_INTEGRATION.md) — compressor + MQTT details
