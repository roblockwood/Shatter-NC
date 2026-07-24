# Shatter Installation Guide

Install and operate Shatter on **Windows**, **macOS**, or **Linux** using Docker Desktop.

- **Production / shop** — pull pre-built images from [GitHub Container Registry](https://github.com/roblockwood?tab=packages) (`ghcr.io`). Download two config files; **no git clone required**.
- **Development** — clone the repo and use `docker-compose.dev.yml` (see [Development Guide](DEVELOPMENT_GUIDE.md))

---

## What You'll Need

- A computer on the same network as your Brother CNC(s)
- **4 GB RAM minimum** (8 GB recommended)
- **~10 GB free disk** for Docker and data
- **~30 minutes** for first-time setup

---

## 1. Install Docker Desktop

Install [Docker Desktop](https://docs.docker.com/get-docker/) for your OS. On Windows, accept WSL 2 when prompted. Wait until Docker reports it is running before continuing.

Verify:

```bash
docker version
docker compose version
```

---

## 2. Compose Files

| File | Use case | Services | UI |
|------|----------|----------|-----|
| `docker-compose.prod.yml` | Shop production | postgres, backend, frontend (nginx) | Port **80** |
| `docker-compose.dev.yml` | Contributors (from source) | postgres, backend, frontend (Vite), mosquitto | Port **3000** |

**Production networking** (see [SECURITY.md](../SECURITY.md)):

| Service | Host exposure |
|---------|----------------|
| Frontend (nginx) | Port 80 — intended UI entry |
| Backend API | Port 8000 — restrict via firewall if not proxied |
| PostgreSQL | Internal Docker network only |
| Mosquitto (optional `--profile mqtt`) | Internal only |

---

## 3. Production Install (ghcr.io)

Shop installs run **published container images**. The backend image includes application code and SQL migrations; you do not build from source or clone the repository.

### Container images

| Image | Role |
|-------|------|
| `ghcr.io/roblockwood/shatter-nc/backend` | API, CNC polling, migrations |
| `ghcr.io/roblockwood/shatter-nc/frontend` | Web UI (nginx) |
| `timescale/timescaledb:latest-pg15` | PostgreSQL + TimescaleDB (pulled by compose) |

**Tags:** `latest`, `vX.Y.Z` (matches [GitHub Releases](https://github.com/roblockwood/Shatter-NC/releases)), or a commit SHA. Pin a version in `.env`:

```bash
IMAGE_TAG=v1.2.3   # optional; default is latest
```

**Registry:** Packages are public — `docker pull` works without login. Private forks need `docker login ghcr.io`.

### Step 1 — Create a deploy folder

```bash
mkdir -p ~/shatter
cd ~/shatter
```

Use any path; keep `docker-compose.prod.yml` and `.env` together.

### Step 2 — Download deploy files

Fetch the compose file and env template from GitHub (no clone):

```bash
BASE=https://raw.githubusercontent.com/roblockwood/Shatter-NC/main
curl -fsSL -O "$BASE/docker-compose.prod.yml" -O "$BASE/.env.production.example"
cp .env.production.example .env
```

To pin deploy files to a release, replace `main` with a tag (e.g. `v1.2.3`) in the URL.

### Step 3 — Configure `.env`

Edit `.env` before first start. Set at minimum:

- `POSTGRES_PASSWORD` — strong unique password
- `SECRET_KEY` — run `openssl rand -hex 32` (required by prod compose; reserved for future use — not consumed by app logic today)
- `CORS_ORIGINS` — JSON array of shop browser origins, e.g. `'["http://192.168.1.50","http://localhost"]'`. Include the UI origin on **port 80**; the SPA also calls the API on **port 8000** directly unless `VITE_API_URL` was set at build time.

Optional:

- `IMAGE_TAG` — pin backend/frontend to a release tag instead of `latest`
- `FTP_SYNC_LOCAL_BROWSE_HOST_PATH` — host folder exposed to the FTP sync folder picker (default `/Users` on macOS)

See [Environment Variables](ENVIRONMENT_VARIABLES.md) for the full list.

### Step 4 — Pull images and start

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

First start runs database migrations inside the backend container (may take a few minutes).

**Verify:**

```bash
curl http://localhost:8000/health
```

Open the UI at `http://<server-ip>` (port 80).

### Optional — bundled MQTT broker

Only if you use compressor MQTT publishing (`MQTT_PUBLISH_HOST=mosquitto` in `.env`):

```bash
docker compose -f docker-compose.prod.yml --profile mqtt up -d
```

### Alternative — clone the repo

Cloning is **optional** for production. Use it if you want the full docs tree locally or are also developing:

```bash
git clone https://github.com/roblockwood/Shatter-NC.git
cd Shatter-NC
cp .env.production.example .env
# edit .env, then same pull/up commands as above
```

---

## 4. Development Install

Requires a full clone — images are built from source in `docker-compose.dev.yml`.

```bash
git clone https://github.com/roblockwood/Shatter-NC.git
cd Shatter-NC
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
```

Open **http://localhost:3000**. API: **http://localhost:8000**. Interactive API docs: **http://localhost:8000/docs** when `LOG_LEVEL=DEBUG`.

Windows/macOS shortcut `start.command` starts the **dev** stack — fine for trials; production shops should use the ghcr.io flow in section 3.

---

## 5. First Use

1. Open the UI (prod: `http://<server-ip>`; dev: `http://localhost:3000`)
2. Add Brother CNC machines (name, IP, FTP credentials)
3. Optional: add Kaeser compressors (no beta required)
4. Optional (beta): enable beta mode (rapid-click logo), then configure notification channels (`/notifications`) or FTP sync (machine edit form)

Operator workflows: [USER_GUIDE.md](USER_GUIDE.md).

---

## 6. Stop and Start

Data persists in Docker volumes when you `down` without `-v`.

**Production** (from your deploy folder):

```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

**Development:** replace compose file with `docker-compose.dev.yml`.

Expect containers: **shatter-db-prod**, **shatter-backend-prod**, **shatter-frontend-prod** (names fixed in compose; volume names use `COMPOSE_PROJECT_NAME`).

---

## 7. Volumes and Backup

### Persistent data

| Volume | Purpose | Backup |
|--------|---------|--------|
| `<project>_postgres_data` | All Shatter data (machines, history, config) | **Critical** |
| `<project>_generated_data` | Generated runtime files | Low priority |

List volumes:

```bash
docker volume ls | grep -E 'shatter|postgres'
```

### Backup (recommended: pg_dump)

```bash
docker exec shatter-db-prod pg_dump -U shatter_user shatter | gzip > backup_$(date +%Y%m%d).sql.gz
```

Adjust container name (`docker ps`) and credentials if you changed defaults in `.env`.

### Restore

```bash
docker compose -f docker-compose.prod.yml stop backend
gunzip -c backup_20250101.sql.gz | docker exec -i shatter-db-prod psql -U shatter_user shatter
docker compose -f docker-compose.prod.yml start backend
```

**Warning:** `docker compose down -v` deletes **all** named volumes including the database. Never use `-v` unless you intend to wipe data.

---

## 8. Upgrading

Production upgrades are **image pulls** — no `git pull` required.

1. **Backup** the database (above)
2. **Optional:** set `IMAGE_TAG` in `.env` to a new release tag (e.g. `v1.3.0`)
3. Pull and recreate containers:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

4. Verify:

```bash
curl http://localhost:8000/health
docker compose -f docker-compose.prod.yml logs -f backend
```

Migrations run on backend startup ([DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md)).

Re-download `docker-compose.prod.yml` from GitHub only when [release notes](https://github.com/roblockwood/Shatter-NC/releases) mention compose or env changes.

**PostgreSQL major version upgrades** require dump/restore — backup first, then follow TimescaleDB upgrade docs for your target version.

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| Docker not running | Start Docker Desktop; wait until ready |
| Port in use (3000/8000/80) | Change port mappings in compose or stop conflicting app |
| Containers exit immediately | Check logs in Docker Desktop; verify `.env` values |
| UI unreachable | Confirm frontend container healthy; try `127.0.0.1` |
| Image pull fails | Check `ghcr.io` connectivity; verify tag exists on [Packages](https://github.com/roblockwood?tab=packages) |
| `401` / unauthorized pull | Packages are public for this project; private forks need `docker login ghcr.io` |
| Summary/history empty after upgrade | Confirm backend healthy; migrations completed (`docker logs shatter-backend-prod`) |

---

## Related

- [USER_GUIDE.md](USER_GUIDE.md) — dashboard, files, validation
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) — contributor setup
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) — configuration
- [SECURITY.md](../SECURITY.md) — deployment security model
