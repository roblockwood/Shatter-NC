# Development Guide

Contributor quickstart for the Shatter-NC monorepo. For shop install, see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md). For contribution workflow, see [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Git | 2.30+ | Clone and PR workflow |
| Docker | 20.10+ | Default dev environment |
| Node.js | 20+ | Local frontend (optional) |
| Python | 3.11+ (Docker image); 3.12 (CI) | Local backend (optional) |

---

## Setup Options

| Option | Docker | Local processes | Best for |
|--------|--------|-----------------|----------|
| **1. Full Docker** | postgres + backend + frontend + mosquitto | — | Beginners, CI-like env |
| **2. Hybrid backend** | postgres (+ frontend optional) | backend in venv | Python debugging |
| **3. Hybrid frontend** | postgres + backend | `npm run dev` | React HMR without frontend container |
| **4. Fully local** | postgres only or external DB | backend + frontend | Advanced |

### Option 1: Full Docker (recommended)

```bash
git clone https://github.com/roblockwood/Shatter-NC.git
cd Shatter-NC
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Logs: `docker compose -f docker-compose.dev.yml logs -f backend`

Backend hot-reloads on Python changes; frontend uses Vite HMR.

### Option 2: Local backend

```bash
docker compose -f docker-compose.dev.yml up -d postgres
cd backend && python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export POSTGRES_HOST=localhost  # if postgres port published
./scripts/start-dev.sh
```

### Option 3: Local frontend

```bash
docker compose -f docker-compose.dev.yml up -d postgres backend
cd frontend && npm install && npm run dev
```

### Option 4: Fully local

Run PostgreSQL locally or point `POSTGRES_*` at a remote instance. Start backend with `start-dev.sh` and frontend with `npm run dev`.

---

## Project Map

```
backend/app/
  api/           REST routers
  services/      polling, websocket, programs, ftp sync, notifications
  clients/       telnet, ftp, http
  parsers/       gcode + telnet v2 parsers (*_v2.py)
  models/        SQLAlchemy models
  core/config.py settings

frontend/src/
  pages/         route-level views
  components/    UI (MachineCard, modals, panes)
  hooks/         useWebSocket, etc.
  api/           REST client helpers
```

---

## Where to Change Things

| Task | Location |
|------|----------|
| New REST endpoint | `backend/app/api/*.py` → register in `main.py` |
| Polling / machine status | `backend/app/services/_machine_poller.py`, `polling.py` |
| WebSocket broadcast | `backend/app/services/websocket.py` |
| G-code validation | `backend/app/api/programs.py`, `parsers/gcode_parser.py` |
| Telnet protocol | `backend/app/clients/telnet_client.py`, `_telnet_*.py` |
| New page | `frontend/src/pages/` + route in `App.tsx` |
| Dashboard UI | `frontend/src/components/MachineCard.tsx`, `Dashboard.tsx` |
| Styling | Follow [UX_DESIGN_GUIDE.md](UX_DESIGN_GUIDE.md) |

---

## Testing

```bash
# Backend (from repo root; CI enforces coverage floor via --cov-fail-under)
PYTHONPATH=backend pytest backend/tests/ --cov=app --cov-report=term-missing

# Frontend
cd frontend && npm test

# Build check
cd frontend && npm run build
```

CI coverage floor is currently **60%** (`--cov-fail-under=60` in [`.github/workflows/test.yml`](../.github/workflows/test.yml)). Document test commands in PR descriptions.

---

## API Documentation

REST endpoints are documented via **FastAPI OpenAPI** when enabled:

- Set `LOG_LEVEL=DEBUG` in `.env`
- Open http://localhost:8000/docs

Production disables `/docs` and `/openapi.json` ([`main.py`](../backend/app/main.py)). For new endpoints: add route docstrings and describe behavior in the PR — do not maintain a separate REST encyclopedia.

WebSocket messages: [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md).

---

## Database Migrations

SQL migrations in `database/init/` run automatically on backend startup. See [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md).

After adding a migration file, restart the backend container — init scripts alone do **not** run on existing volumes.

---

## Code Quality

- Python: PEP 8, type hints where existing code uses them
- TypeScript: strict mode, match surrounding component patterns
- UI: **mandatory** [UX_DESIGN_GUIDE.md](UX_DESIGN_GUIDE.md) compliance
- Commits: conventional format — see [CONTRIBUTING.md](../CONTRIBUTING.md#versioning)

---

## Debugging Tips

| Issue | Check |
|-------|-------|
| Backend 500 on summaries | `polling_events` table exists; run migrations |
| WebSocket disconnected | Backend up; client uses `ws://<host>:8000/api/ws` (prod nginx also proxies `/api/` if using same-origin URLs) |
| Telnet timeouts | Single connection per machine; stop duplicate backends polling same IP |
| CORS errors | `CORS_ORIGINS` includes your browser origin |

Machine testing with telnet: stop the backend container first to free the CNC connection (see [`.cursorrules`](../.cursorrules)).

---

## Related Documentation

| Doc | Contents |
|-----|----------|
| [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) | Services and data flow |
| [USER_GUIDE.md](USER_GUIDE.md) | Operator-facing features |
| [TELNET_REFERENCE.md](TELNET_REFERENCE.md) | Brother port 10000 protocol |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Tables and hypertables |
| [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | Configuration reference |
