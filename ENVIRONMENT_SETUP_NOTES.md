# Environment Setup Notes

## Current Issue: Dev/Production Configuration Separation

### Problem Encountered (2025-12-06)

During implementation of the summary feature, encountered database authentication failures:

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
connection to server at "postgres" (172.19.0.3), port 5432 failed:
FATAL: password authentication failed for user "shatter_user"
```

### Root Cause

1. **Database Container** was initialized with production credentials from `.env.production`:
   - `POSTGRES_PASSWORD=XVane3E68casFxAz/ElUdJiUdkM2kplMZ8pSdEn1Y=`

2. **Backend Container** was using default hardcoded credentials:
   - `POSTGRES_PASSWORD=changeme` (from `backend/app/core/config.py` defaults)

3. **Docker Compose** only reads `.env` file by default, not `.env.production`

4. **Missing Database Tables**: The event tracking tables (`production_runs`, `alarm_events`, `machine_status_events`) were missing because:
   - Database volume persisted from previous initialization
   - Init scripts in `/database/init/` only run on first container creation
   - When database was recreated with new credentials, init scripts weren't re-run

### Temporary Solution Applied

1. **Created `.env` file** by copying `.env.production`:
   ```bash
   cp .env.production .env
   ```
   - Note: `.env` is in `.gitignore` (intentional, correct security practice)
   - This is a **temporary workaround**, not a permanent solution

2. **Manually ran database init scripts**:
   ```bash
   docker exec -i shatter-db psql -U shatter_user -d shatter < database/init/02-add-program-tracking.sql
   ```

3. **Recreated backend container** to pick up new environment:
   ```bash
   docker-compose up -d backend
   ```

### Proper Solutions to Implement

#### Option 1: Docker Compose Override (Recommended for Development)

Create `docker-compose.override.yml` (automatically loaded by docker-compose):

```yaml
# docker-compose.override.yml (for local development)
version: '3.8'

services:
  postgres:
    environment:
      POSTGRES_PASSWORD: changeme  # Simple dev password

  backend:
    environment:
      POSTGRES_PASSWORD: changeme
      LOG_LEVEL: DEBUG

  # Add other dev-specific overrides
```

**Workflow:**
- `docker-compose.yml` - Base configuration
- `docker-compose.override.yml` - Dev settings (gitignored)
- `docker-compose.prod.yml` - Production settings (explicit)
- Production: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

#### Option 2: Environment-Specific Compose Files

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### Option 3: ENV File Selection

Update docker-compose.yml to support ENV file selection:

```yaml
services:
  postgres:
    env_file:
      - ${ENV_FILE:-.env}  # Defaults to .env, override with ENV_FILE=.env.production
```

Usage:
```bash
# Development
docker-compose up -d

# Production
ENV_FILE=.env.production docker-compose up -d
```

### Database Volume Management

To properly reset database when changing credentials:

```bash
# Stop containers
docker-compose down

# Remove postgres volume (WARNING: destroys all data)
docker volume rm s700_nc_postgres_data

# Recreate with correct .env file
docker-compose up -d
```

### Current Status

✅ **Working**: Backend can connect to database with production credentials via `.env`
✅ **Working**: All tables created (programs, deployments, events, runs)
⚠️ **Temporary**: Using `.env` file copied from production (not in git)
⚠️ **Issue**: `production_runs` table exists but isn't a hypertable (primary key issue)

### Next Steps

1. **Implement proper dev/prod separation** (Option 1 recommended)
2. **Fix production_runs hypertable** - Need to adjust primary key to include `started_at`
3. **Document environment setup** in main README.md
4. **Create `.env.example`** with all required variables (safe defaults)
5. **Update deployment docs** with proper production deployment steps

### Files to Review

- `docker-compose.yml` - Base configuration
- `.env.production` - Production credentials (**keep secure**)
- `.env.production.example` - Template for production
- `.env.example` - Template for development
- `database/init/02-add-program-tracking.sql` - Table creation (line 175-206 for production_runs)

---

**Last Updated**: 2025-12-06
**Status**: Development environment functional with temporary workaround
