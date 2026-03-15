# Development Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup Options](#development-setup-options)
  - [Option 1: Full Docker (Recommended for Beginners)](#option-1-full-docker-recommended-for-beginners)
  - [Option 2: Hybrid - Local Backend](#option-2-hybrid---local-backend)
  - [Option 3: Hybrid - Local Frontend](#option-3-hybrid---local-frontend)
  - [Option 4: Fully Local](#option-4-fully-local)
- [Project Structure](#project-structure)
- [Backend Development](#backend-development)
  - [Adding API Endpoints](#adding-api-endpoints)
  - [Database Migrations](#database-migrations)
  - [Testing](#testing)
  - [Debugging](#debugging)
- [Frontend Development](#frontend-development)
  - [Creating Components](#creating-components)
  - [Adding New Pages](#adding-new-pages)
  - [State Management](#state-management)
  - [Testing](#testing-1)
  - [Debugging](#debugging-1)
- [Code Quality](#code-quality)
- [Development Workflow](#development-workflow)
- [Debugging Common Issues](#debugging-common-issues)
- [Hot Reload Behavior](#hot-reload-behavior)
- [API Documentation](#api-documentation)

---

## Prerequisites

Before starting development, ensure you have these tools installed:

### Required

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **Git** | 2.30+ | Version control | https://git-scm.com/downloads |
| **Docker** | 20.10+ | Containerization | https://docs.docker.com/get-docker/ |
| **Docker Compose** | V2 | Orchestration | Included with Docker Desktop |

### Optional (for local development)

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **Python** | 3.11+ | Backend development | https://www.python.org/downloads/ |
| **Node.js** | 20+ | Frontend development | https://nodejs.org/ |
| **PostgreSQL** | 15+ | Local database | https://www.postgresql.org/download/ |

**Verify installations:**

```bash
# Required
git --version          # git version 2.39.0
docker --version       # Docker version 24.0.0
docker-compose version # Docker Compose version v2.20.0

# Optional
python --version       # Python 3.11.5
node --version         # v20.9.0
npm --version          # 10.1.0
psql --version         # psql (PostgreSQL) 15.4
```

---

## Development Setup Options

Choose the option that best fits your workflow and experience level.

### Option 1: Full Docker (Recommended for Beginners)

**Pros:**
- ✅ Easiest setup (no local installations needed)
- ✅ Consistent environment (works same on all platforms)
- ✅ Isolated from system (no conflicts)
- ✅ Hot reload for both backend and frontend

**Cons:**
- ❌ Slower startup (Docker overhead)
- ❌ Debugging requires Docker knowledge
- ❌ IDE integration can be tricky

**Setup Steps:**

```bash
# 1. Clone repository
git clone https://github.com/your-org/shatter.git
cd shatter

# 2. Create environment file
cp .env.example .env

# 3. Start all services
docker compose -f docker-compose.dev.yml up -d

# 4. Verify services
docker compose -f docker-compose.dev.yml ps
# Should see 3 services running:
# - shatter-db (postgres)
# - shatter-backend
# - shatter-frontend

# 5. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Making Changes:**

**Backend:**
1. Edit Python files in `backend/`
2. Uvicorn auto-reloads on file change (~2 seconds)
3. Check logs: `docker-compose logs -f backend`

**Frontend:**
1. Edit TypeScript/React files in `frontend/`
2. Vite HMR reloads instantly
3. Check browser console for errors

**Viewing Logs:**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

**Stopping:**

```bash
# Stop (keeps data)
docker-compose down

# Stop and remove data
docker-compose down -v
```

---

### Option 2: Hybrid - Local Backend

Run backend locally for better debugging while using Docker for database services.

**Pros:**
- ✅ Faster backend restart
- ✅ Native debugger support (VS Code, PyCharm)
- ✅ IDE integration works perfectly
- ✅ No Docker rebuild needed

**Cons:**
- ❌ Requires Python 3.11+ installed
- ❌ Need to manage virtual environment
- ❌ Frontend still in Docker

**Setup Steps:**

```bash
# 1. Clone repository
git clone https://github.com/your-org/shatter.git
cd shatter

# 2. Start only database services
# Note: Use full dev environment with docker-compose.dev.yml instead
docker-compose -f docker-compose.dev.yml up -d

# 3. Set up Python virtual environment
cd backend
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Create local .env (optional overrides)
cp .env.example .env
# Edit if needed

# 6. Run backend locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. In another terminal, run frontend
cd ../frontend
npm install
npm run dev
```

**Environment Variables:**

Backend reads from `backend/.env` (if exists) or falls back to `.env` in project root.

```bash
# backend/.env
POSTGRES_HOST=localhost  # Note: localhost, not "postgres"
POSTGRES_PORT=5432
POSTGRES_DB=shatter
POSTGRES_USER=shatter_user
POSTGRES_PASSWORD=changeme
```

**Debugging Backend:**

**VS Code:**

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

Set breakpoints and press F5 to start debugging.

---

### Option 3: Hybrid - Local Frontend

Run frontend locally for better debugging while using Docker for backend.

**Pros:**
- ✅ Faster frontend rebuild
- ✅ Native browser dev tools
- ✅ React Dev Tools work better
- ✅ No Docker rebuild needed

**Cons:**
- ❌ Requires Node.js 20+ installed
- ❌ Need to manage node_modules
- ❌ Backend still in Docker

**Setup Steps:**

```bash
# 1. Clone repository
git clone https://github.com/your-org/shatter.git
cd shatter

# 2. Start backend services
docker-compose -f docker-compose.dev.yml up -d postgres backend

# 3. Set up frontend locally
cd frontend
npm install

# 4. Run frontend dev server
npm run dev

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

**Frontend connects to Dockerized backend automatically** (auto-detection based on hostname).

---

### Option 4: Fully Local

Run everything locally without Docker (advanced).

**Pros:**
- ✅ Fastest development cycle
- ✅ Full native debugging
- ✅ No Docker overhead
- ✅ All IDE features work

**Cons:**
- ❌ Most complex setup
- ❌ Requires all tools installed locally
- ❌ Potential version conflicts
- ❌ Platform-specific issues

**Setup Steps:**

```bash
# 1. Install PostgreSQL 15 + TimescaleDB extension
# See: https://docs.timescale.com/install/latest/

# 2. Create database
createdb shatter
psql shatter -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
psql shatter -c "CREATE USER shatter_user WITH PASSWORD 'changeme';"
psql shatter -c "GRANT ALL PRIVILEGES ON DATABASE shatter TO shatter_user;"

# 3. Set up backend
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env
cat > .env << EOF
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=shatter
POSTGRES_USER=shatter_user
POSTGRES_PASSWORD=changeme
EOF

# Run backend
uvicorn app.main:app --reload

# 4. Set up frontend (in new terminal)
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
shatter/
├── backend/                      # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/                  # API endpoints (routers)
│   │   │   ├── machines.py       # Machine management
│   │   │   ├── status.py         # Machine status queries
│   │   │   ├── programs.py       # Program validation/deployment
│   │   │   ├── history.py        # Historical data queries
│   │   │   ├── summary.py        # Summary/analytics
│   │   │   └── websocket.py      # WebSocket real-time updates
│   │   ├── core/                 # Core application components
│   │   │   ├── config.py         # Pydantic settings
│   │   │   └── database.py       # SQLAlchemy setup
│   │   ├── models/               # Database models (SQLAlchemy)
│   │   │   ├── machine.py        # Machine model
│   │   │   ├── program.py        # Program & deployment models
│   │   │   └── event.py          # Event models (time-series)
│   │   ├── services/             # Business logic services
│   │   │   ├── polling.py        # PollingService (background)
│   │   │   ├── program_service.py# ProgramService (validation)
│   │   │   └── websocket.py      # WebSocketManager
│   │   ├── clients/              # External service clients
│   │   │   ├── http_client.py    # CNC HTTP client
│   │   │   └── ftp_client.py     # CNC FTP client
│   │   ├── parsers/              # G-code and data parsers
│   │   │   ├── gcode_parser.py   # G-code parser
│   │   │   └── posni_parser.py   # POSNI format parser
│   │   └── utils/                # Utility functions
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Multi-stage Docker build
│   └── .env                      # Local environment variables
│
├── frontend/                     # React + TypeScript frontend
│   ├── src/
│   │   ├── main.tsx              # Application entry point
│   │   ├── App.tsx               # Root component with routing
│   │   ├── pages/                # Top-level page components
│   │   │   ├── Dashboard.tsx     # Machine fleet dashboard
│   │   │   └── FileBrowser.tsx   # FTP file browser
│   │   ├── components/           # React components
│   │   │   ├── ui/               # Reusable UI primitives
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── StatusIndicator.tsx
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   └── TerminalBox.tsx
│   │   │   ├── MachineCard.tsx   # Machine status card
│   │   │   ├── AddMachineCard.tsx
│   │   │   ├── ValidationResultModal.tsx
│   │   │   ├── ToolListModal.tsx
│   │   │   └── ...
│   │   ├── hooks/                # Custom React hooks
│   │   │   └── useWebSocket.ts   # WebSocket connection hook
│   │   ├── config/               # Configuration
│   │   │   └── api.ts            # API base URL
│   │   ├── styles/               # Global styles
│   │   │   └── terminal.css      # Terminal aesthetic
│   │   └── index.css             # Global CSS reset
│   ├── package.json              # Node.js dependencies
│   ├── vite.config.ts            # Vite build configuration
│   ├── tsconfig.json             # TypeScript configuration
│   └── Dockerfile                # Multi-stage Docker build
│
├── database/                     # Database initialization
│   └── init/                     # SQL scripts (run on first startup)
│       ├── 01_create_tables.sql
│       ├── 02_create_hypertables.sql
│       └── 03_create_indexes.sql
│
├── docs/                         # Documentation
│   ├── BACKEND_ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── DATABASE_SCHEMA.md
│   ├── FRONTEND_ARCHITECTURE.md
│   ├── DASHBOARD_WORKFLOWS.md
│   ├── FILE_BROWSER_WORKFLOWS.md
│   ├── ENVIRONMENT_VARIABLES.md
│   ├── DOCKER_DEPLOYMENT.md
│   ├── DEVELOPMENT_GUIDE.md      # This file
│   ├── CONTRIBUTING.md
│   ├── roadmap/FUTURE_DOCUMENTATION.md
│   ├── CNC_CLIENTS.md
│   ├── PROGRAM_VALIDATION.md
│   ├── UX_DESIGN_GUIDE.md
│   ├── BRANDING.md
│   └── DASHBOARD_SUMMARIES.md
│
├── docker-compose.dev.yml        # Full stack development
├── docker-compose.prod.yml       # Production deployment
├── .env.example                  # Development env template
├── .env.production.example       # Production env template
├── .gitignore                    # Git ignore rules
├── README.md                     # Project overview
└── rules.md                      # Development standards
```

**Key Directories:**

- **`backend/app/api/`** - API endpoints (one file per router)
- **`backend/app/services/`** - Business logic (decoupled from API layer)
- **`backend/app/models/`** - Database models (SQLAlchemy ORM)
- **`frontend/src/pages/`** - Top-level route components
- **`frontend/src/components/`** - Reusable React components
- **`docs/`** - Comprehensive documentation

---

## Backend Development

### Adding API Endpoints

**Step 1: Create router file** (if new category)

```python
# backend/app/api/analytics.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter(
    prefix="/api/analytics",
    tags=["analytics"]
)

@router.get("/machine-utilization")
async def get_machine_utilization(
    machine_id: int,
    db: Session = Depends(get_db)
):
    """Get machine utilization statistics."""
    # Implementation
    return {"machine_id": machine_id, "utilization": 0.85}
```

**Step 2: Register router in main.py**

```python
# backend/app/main.py
from app.api import machines, status, programs, history, summary, websocket, analytics  # Add analytics

app.include_router(machines.router)
app.include_router(status.router)
app.include_router(programs.router)
app.include_router(history.router)
app.include_router(summary.router)
app.include_router(websocket.router)
app.include_router(analytics.router)  # Add this line
```

**Step 3: Test endpoint**

```bash
# Restart backend (if not using --reload)
docker-compose restart backend

# Test endpoint
curl http://localhost:8000/api/analytics/machine-utilization?machine_id=1

# Check API docs
open http://localhost:8000/docs
```

**Design Patterns:**

- **Router → Service → Model** - Keep business logic in services
- **Dependency Injection** - Use `Depends()` for database, services
- **Type hints** - Always annotate parameters and return types
- **Async/await** - Use for I/O-bound operations (database, HTTP)

**Example with Service Layer:**

```python
# backend/app/services/analytics_service.py
from sqlalchemy.orm import Session
from app.models.event import MachineStatusEvent

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_utilization(self, machine_id: int) -> float:
        # Complex business logic here
        events = self.db.query(MachineStatusEvent).filter(
            MachineStatusEvent.machine_id == machine_id
        ).all()
        # Calculate utilization
        return 0.85

# backend/app/api/analytics.py
from app.services.analytics_service import AnalyticsService

@router.get("/machine-utilization")
async def get_machine_utilization(
    machine_id: int,
    db: Session = Depends(get_db)
):
    service = AnalyticsService(db)
    utilization = service.calculate_utilization(machine_id)
    return {"machine_id": machine_id, "utilization": utilization}
```

---

### Database Migrations

**⚠️ Currently:** Manual SQL migrations in `database/init/`

**Future:** Alembic migrations (planned)

**Adding a New Table:**

```sql
-- database/init/04_add_analytics_table.sql
CREATE TABLE IF NOT EXISTS machine_analytics (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    utilization FLOAT NOT NULL,
    uptime_seconds INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_machine_date ON machine_analytics(machine_id, date);
```

**Applying Migration:**

```bash
# Recreate database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d

# Or apply manually
docker exec -i shatter-db psql -U shatter_user shatter < database/init/04_add_analytics_table.sql
```

---

### Testing

**⚠️ Currently:** No automated tests (future implementation)

**Manual Testing:**

**API Endpoints:**
```bash
# Use curl or Postman
curl -X POST http://localhost:8000/api/machines \
  -H "Content-Type: application/json" \
  -d '{"name":"TEST-001","ip_address":"192.168.1.100",...}'
```

**Unit Tests (Future):**
```python
# tests/test_analytics.py
import pytest
from app.services.analytics_service import AnalyticsService

def test_calculate_utilization():
    service = AnalyticsService(db)
    utilization = service.calculate_utilization(machine_id=1)
    assert 0.0 <= utilization <= 1.0
```

**Run tests:**
```bash
pytest
```

---

### Debugging

**Print Debugging:**

```python
# backend/app/api/machines.py
@router.get("/")
async def list_machines(db: Session = Depends(get_db)):
    print("DEBUG: Listing machines")  # Simple debug
    machines = db.query(Machine).all()
    print(f"DEBUG: Found {len(machines)} machines")
    return machines
```

View output:
```bash
docker-compose logs -f backend | grep DEBUG
```

**Logging:**

```python
import logging
logger = logging.getLogger(__name__)

@router.get("/")
async def list_machines(db: Session = Depends(get_db)):
    logger.info("Listing machines")
    machines = db.query(Machine).all()
    logger.info(f"Found {len(machines)} machines")
    return machines
```

**VS Code Debugger** (local backend only):

Set breakpoint → Press F5 → Breakpoint hits → Inspect variables

---

### Units Handling

Shatter supports both imperial (inches) and metric (millimeters) units. Units are configured per-machine and used throughout the system for dimensional data.

**Backend Units Handling:**

1. **Machine Configuration**: Each machine has a `units` field (`'in'` or `'mm'`) stored in the database
   - Location: `backend/app/models/machine.py`
   - Default: `'in'` (inches)

2. **Unit Converter Utility**: Conversion functions for display/validation
   - Location: `backend/app/utils/unit_converter.py`
   - Functions:
     - `convert_inches_to_mm(value: float) -> float`
     - `convert_mm_to_inches(value: float) -> float`
     - `convert_dimension(value: float, from_units: str, to_units: str) -> float`
     - `format_dimension(value: float, units: str, decimals: int = 4) -> str`

3. **Parser Integration**: Parsers accept `units` parameter and include units in output
   - Example: `parse_tolni(content: bytes, units: str = 'in') -> Dict[str, Any]`
   - Parsers store raw values (no conversion) and include `units` metadata
   - Location: `backend/app/parsers/tolni_parser.py`, `posni_parser.py`

4. **API Endpoints**: All dimensional data endpoints pass `machine.units` to parsers
   - Location: `backend/app/api/status.py`
   - Response includes `units` field for client display
   - Example: `GET /api/machines/{id}/tools` returns `{"tools": [...], "units": "in"}`

5. **Validation**: Tool and WCS validation converts tolerances to machine's native units
   - Location: `backend/app/api/programs.py`
   - Tolerances stored in inches, converted to mm if machine uses mm

**Frontend Units Handling:**

1. **Formatting Utility**: Consistent dimension display
   - Location: `frontend/src/utils/formatDimension.ts`
   - Function: `formatDimension(value: number | null | undefined, units: 'in' | 'mm', decimals: number = 4) -> string`
   - Returns: `"0.2500\""` for inches, `"6.3500 mm"` for millimeters, `"────"` for null/undefined

2. **Component Usage**: All dimensional displays use `formatDimension`
   - Import: `import { formatDimension } from '../utils/formatDimension'`
   - Usage: `formatDimension(tool.diameter, units, 4)`
   - Components: `ToolListModal`, `ToolsPane`, `ToolDetailModal`, `UploadConfirmationModal`

3. **Machine Data**: Components receive `units` prop from machine configuration
   - Passed from `MachineCard` to child components
   - Available in API responses: `machine.units` or `status.units`

**Best Practices:**

- ✅ Always pass `units` parameter to parsers (from `machine.units`)
- ✅ Include `units` field in API responses with dimensional data
- ✅ Use `formatDimension` utility for all frontend displays
- ✅ Store raw values (no conversion) - convert only at display/validation time
- ✅ Default to `'in'` for backward compatibility
- ❌ Don't hardcode unit suffixes (`"` or ` mm`) - use `formatDimension`
- ❌ Don't convert values in parsers - store raw and convert when needed

**Example: Adding Units to New Endpoint**

```python
# backend/app/api/status.py
@router.get("/{machine_id}/tools")
async def get_tools(machine_id: int, db: Session = Depends(get_db)):
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    # ... fetch tool data ...
    data = http_client.get_tool_data(units=db_machine.units)  # Pass units
    data["units"] = db_machine.units  # Include in response
    return data
```

```typescript
// frontend/src/components/ToolDisplay.tsx
import { formatDimension } from '../utils/formatDimension';

export const ToolDisplay: React.FC<{tool: Tool, units: string}> = ({ tool, units }) => {
  return (
    <div>
      Diameter: {formatDimension(tool.diameter, units, 4)}
      Length: {formatDimension(tool.length, units, 4)}
    </div>
  );
};
```

See [archive/PHASE3_UNITS_IMPLEMENTATION_PLAN.md](archive/PHASE3_UNITS_IMPLEMENTATION_PLAN.md) for complete implementation details (archived - implementation complete).

---

## Frontend Development

### Creating Components

**UI Component (Reusable):**

```typescript
// frontend/src/components/ui/Button.tsx
import React from 'react';
import './Button.css';

interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  label,
  onClick,
  variant = 'primary',
  disabled = false
}) => {
  return (
    <button
      className={`terminal-button ${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      [ {label} ]
    </button>
  );
};
```

**Feature Component:**

```typescript
// frontend/src/components/MachineStatusChart.tsx
import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

interface MachineStatusChartProps {
  machineId: number;
}

export const MachineStatusChart: React.FC<MachineStatusChartProps> = ({ machineId }) => {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/analytics/machine-utilization?machine_id=${machineId}`)
      .then(res => res.json())
      .then(setData);
  }, [machineId]);

  return (
    <div className="machine-chart">
      {/* Render chart */}
    </div>
  );
};
```

---

### Adding New Pages

**Step 1: Create page component**

```typescript
// frontend/src/pages/Analytics.tsx
import React from 'react';
import { MachineStatusChart } from '../components/MachineStatusChart';

export const Analytics: React.FC = () => {
  return (
    <div className="analytics-page">
      <h1>ANALYTICS</h1>
      <MachineStatusChart machineId={1} />
    </div>
  );
};
```

**Step 2: Add route in App.tsx**

```typescript
// frontend/src/App.tsx
import { Analytics } from './pages/Analytics';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/files" element={<FileBrowser />} />
        <Route path="/analytics" element={<Analytics />} />  {/* Add this */}
      </Routes>
    </Router>
  );
}
```

**Step 3: Add navigation link**

```typescript
// frontend/src/App.tsx (Navigation component)
<Link to="/analytics" className="nav-link">
  [ ANALYTICS ]
</Link>
```

---

### State Management

**Use `useState` for component-level state:**

```typescript
const [machines, setMachines] = useState<Machine[]>([]);
const [loading, setLoading] = useState(false);
```

**Use custom hooks for shared logic:**

```typescript
// frontend/src/hooks/useMachines.ts
export const useMachines = () => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/machines`)
      .then(res => res.json())
      .then(setMachines)
      .finally(() => setLoading(false));
  }, []);

  return { machines, loading };
};

// Usage in component
const { machines, loading } = useMachines();
```

**For complex state, consider Zustand** (already installed):

```typescript
// frontend/src/store/machineStore.ts
import create from 'zustand';

interface MachineStore {
  machines: Machine[];
  setMachines: (machines: Machine[]) => void;
}

export const useMachineStore = create<MachineStore>((set) => ({
  machines: [],
  setMachines: (machines) => set({ machines }),
}));
```

---

### Testing

**⚠️ Currently:** No automated tests (future implementation)

**Manual Testing:**
- Open http://localhost:3000
- Test user flows manually
- Check browser console for errors

**Component Tests (Future):**

```typescript
// frontend/src/components/__tests__/Button.test.tsx
import { render, fireEvent } from '@testing-library/react';
import { Button } from '../ui/Button';

test('button calls onClick when clicked', () => {
  const handleClick = jest.fn();
  const { getByText } = render(<Button label="Test" onClick={handleClick} />);

  fireEvent.click(getByText('[ Test ]'));
  expect(handleClick).toHaveBeenCalledTimes(1);
});
```

---

### Debugging

**Browser DevTools:**
- Open DevTools (F12)
- **Console:** View `console.log()` output and errors
- **Network:** Inspect API requests/responses
- **React DevTools:** Inspect component hierarchy and props

**React DevTools:**

Install browser extension:
- Chrome: https://chrome.google.com/webstore → "React Developer Tools"
- Firefox: https://addons.mozilla.org/firefox → "React Developer Tools"

---

## Code Quality

### Python (Backend)

**Linting:**

```bash
# Install
pip install flake8

# Run
cd backend
flake8 app/
```

**Formatting:**

```bash
# Install
pip install black

# Format
black app/

# Check without modifying
black --check app/
```

**Type Checking:**

```bash
# Install
pip install mypy

# Check
mypy app/
```

---

### TypeScript (Frontend)

**Linting:**

```bash
# Run ESLint
cd frontend
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

**Type Checking:**

```bash
# Check types without building
npm run type-check

# TypeScript compiler
tsc --noEmit
```

**Formatting:**

```bash
# Install Prettier
npm install --save-dev prettier

# Format
npx prettier --write src/

# Check
npx prettier --check src/
```

---

## Development Workflow

### Git Workflow

**Branch Naming:**

```bash
# Feature
git checkout -b feature/add-analytics-page

# Bug fix
git checkout -b fix/machine-card-crash

# Documentation
git checkout -b docs/update-api-reference
```

**Commit Messages:**

```bash
# Good
git commit -m "Add machine utilization endpoint

- Implement AnalyticsService.calculate_utilization()
- Add GET /api/analytics/machine-utilization endpoint
- Include tests and documentation"

# Bad
git commit -m "fix stuff"
git commit -m "wip"
```

**Push and Pull Request:**

```bash
# Push feature branch
git push -u origin feature/add-analytics-page

# Create PR on GitHub
# Fill out PR template with:
# - What changed
# - Why it changed
# - How to test
# - Screenshots (if UI changes)
```

---

## Debugging Common Issues

### Backend Won't Start

**Error: "ModuleNotFoundError: No module named 'app'"**

**Solution:**
```bash
# Ensure you're in backend/ directory
cd backend

# Check PYTHONPATH
export PYTHONPATH=.
uvicorn app.main:app --reload
```

---

**Error: "psycopg2.OperationalError: could not connect to server"**

**Solution:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check POSTGRES_HOST
echo $POSTGRES_HOST
# Should be "postgres" (Docker) or "localhost" (local)

# Test connection
psql -h localhost -U shatter_user -d shatter
```

---

### Frontend Won't Start

**Error: "Error: Cannot find module"**

**Solution:**
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

---

**Error: "EADDRINUSE: address already in use :::3000"**

**Solution:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
npm run dev -- --port 3001
```

---

## Hot Reload Behavior

### Backend (Uvicorn --reload)

**Triggers:** Changes to `.py` files in `backend/app/`

**Reload Time:** ~2 seconds

**Behavior:**
- Automatic restart on file save
- Preserves database connections
- WebSocket connections drop (clients auto-reconnect)

**Excludes:** Changes to `requirements.txt` (requires Docker rebuild)

---

### Frontend (Vite HMR)

**Triggers:** Changes to `.tsx`, `.ts`, `.css` files in `frontend/src/`

**Reload Time:** <100ms (instant)

**Behavior:**
- Hot Module Replacement (no full page reload)
- Preserves component state (usually)
- WebSocket connections maintained

**Full Reload Triggers:**
- Changes to `vite.config.ts`
- Changes to `index.html`
- Changes to environment variables

**Rebuild Required:**
- Changes to `package.json` dependencies
- Changes to build configuration

---

## API Documentation

### Swagger UI

**Access:** http://localhost:8000/docs

**Features:**
- Interactive API documentation
- Try endpoints directly in browser
- See request/response schemas
- Download OpenAPI spec

**Example:**

1. Open http://localhost:8000/docs
2. Expand `GET /api/machines`
3. Click "Try it out"
4. Click "Execute"
5. See response

---

### ReDoc

**Access:** http://localhost:8000/redoc

**Features:**
- Clean, professional documentation
- Three-panel layout
- Code examples
- Searchable

**Use Case:** Share with team or stakeholders

---

### OpenAPI Spec

**Download:**

```bash
curl http://localhost:8000/openapi.json > api_spec.json
```

**Use:**
- Import into Postman
- Generate client SDKs
- API testing tools

---

## Related Documentation

- [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) - Docker setup and deployment
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) - Configuration reference
- [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md) - Backend code organization
- [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) - Frontend code organization
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [API_REFERENCE.md](./API_REFERENCE.md) - Complete API documentation

---

## Quick Reference

**Daily Development Commands:**

```bash
# Start development
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml logs -f

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart service
docker compose restart backend

# Stop everything
docker compose down

# Access database
docker exec -it shatter-db psql -U shatter_user shatter

# Access backend shell
docker exec -it shatter-backend bash

# Run backend tests
pytest

# Run frontend tests
npm test
```

**Useful Endpoints:**

| Endpoint | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |
