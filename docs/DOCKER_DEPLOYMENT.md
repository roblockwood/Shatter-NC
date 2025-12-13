# Docker Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Docker Compose Configurations](#docker-compose-configurations)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Development (Full Stack)](#development-full-stack)
  - [Development (DB Only)](#development-db-only)
  - [Production](#production)
- [Service Details](#service-details)
  - [PostgreSQL + TimescaleDB](#postgresql--timescaledb)
  - [Redis](#redis)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Volume Management](#volume-management)
- [Health Checks](#health-checks)
- [Networking](#networking)
- [Upgrading](#upgrading)
- [Backup and Restore](#backup-and-restore)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Overview

The Shatter CNC platform is deployed using Docker Compose with multiple configuration files for different use cases. All services run in isolated Docker containers with persistent data volumes.

**Why Docker?**
- ✅ Consistent environment across development and production
- ✅ Easy setup (no manual dependency installation)
- ✅ Isolated services (no conflicts with system packages)
- ✅ Portable deployment (works on any Docker-capable host)
- ✅ Built-in health monitoring and auto-restart

**System Requirements:**
- **Docker:** 20.10+ (with Docker Compose V2)
- **RAM:** 4GB minimum, 8GB recommended
- **Disk:** 10GB minimum for images and data
- **OS:** Linux, macOS, Windows with WSL2

---

## Docker Compose Configurations

Four Docker Compose files are provided for different scenarios:

| File | Use Case | Services | Frontend | Description |
|------|----------|----------|----------|-------------|
| **docker-compose.yml** | Development (full stack) | postgres, redis, backend, frontend | Vite dev server | Full stack with hot reload |
| **docker-compose.dev.yml** | Development (lightweight) | postgres, redis | N/A | Smaller PostgreSQL image, run backend/frontend locally |
| **docker-compose.simple.yml** | Development (hybrid) | postgres, redis | N/A | Database services only, run app locally |
| **docker-compose.prod.yml** | Production | postgres, redis, backend, frontend | Nginx static | Optimized for production with health checks |

**Choosing a Configuration:**

- **New developers:** Start with `docker-compose.yml` (full stack)
- **Backend development:** Use `docker-compose.simple.yml` + local backend
- **Frontend development:** Use `docker-compose.yml` (full stack)
- **Production deployment:** Use `docker-compose.prod.yml`

---

## Architecture

### Development Architecture (docker-compose.yml)

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Network (shatter-network)                           │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │  PostgreSQL  │   │    Redis     │   │   Backend    │   │
│  │  (TimescaleDB)│←─┤  (Cache)     │←─┤  (FastAPI)   │   │
│  │  Port: 5432  │   │  Port: 6379  │   │  Port: 8000  │   │
│  └──────────────┘   └──────────────┘   └──────┬───────┘   │
│         ↓                                      ↑            │
│  ┌──────────────┐                    ┌─────────┴───────┐   │
│  │ postgres_data│                    │   Frontend      │   │
│  │  (Volume)    │                    │   (Vite dev)    │   │
│  └──────────────┘                    │   Port: 3000    │   │
│                                       └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
        ↓                                       ↓
 Host: localhost:5432                  Host: localhost:3000
```

### Production Architecture (docker-compose.prod.yml)

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Network (shatter-network)                           │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │  PostgreSQL  │   │    Redis     │   │   Backend    │   │
│  │ (TimescaleDB)│←─┤  (+ password) │←─┤  (4 workers) │   │
│  │  Port: 5432  │   │  Port: 6379  │   │  Port: 8000  │   │
│  └──────────────┘   └──────────────┘   └──────┬───────┘   │
│         ↓                  ↓                   ↑            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────┴──────┐    │
│  │ postgres_data│   │  redis_data  │   │  Frontend   │    │
│  │  (Volume)    │   │  (Volume)    │   │  (Nginx)    │    │
│  └──────────────┘   └──────────────┘   │  Port: 80   │    │
│                                         └─────────────┘    │
└─────────────────────────────────────────────────────────────┘
                                                  ↓
                                         Host: localhost:80
```

**Key Differences:**
- **Development:** Vite dev server (hot reload), single backend worker
- **Production:** Nginx static server (built assets), 4 backend workers, health checks

---

## Quick Start

### Development (Full Stack)

**Step 1: Clone repository**

```bash
git clone https://github.com/your-org/shatter.git
cd shatter
```

**Step 2: Create .env file**

```bash
cp .env.example .env
# Edit .env if needed (defaults are fine for development)
```

**Step 3: Start services**

```bash
docker-compose up -d
```

**Step 4: Verify services**

```bash
# Check all services are running
docker-compose ps

# Should see 4 services with "Up" status:
# - shatter-db (postgres)
# - shatter-redis
# - shatter-backend
# - shatter-frontend
```

**Step 5: Access application**

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Swagger UI)

**Step 6: View logs**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

**Step 7: Stop services**

```bash
# Stop (preserves data)
docker-compose down

# Stop and remove volumes (deletes data)
docker-compose down -v
```

---

### Development (DB Only)

For running backend/frontend locally while using Docker for database services.

**Step 1: Start database services**

```bash
docker-compose -f docker-compose.simple.yml up -d
```

**Step 2: Run backend locally**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Step 3: Run frontend locally**

```bash
cd frontend
npm install
npm run dev
```

**Advantages:**
- Faster backend restart (no container rebuild)
- Native debugger support
- IDE integration works better

---

### Production

**⚠️ IMPORTANT:** Never use development configurations in production!

**Step 1: Create production .env**

```bash
cp .env.production.example .env.production
```

**Step 2: Edit .env.production with secure values**

```bash
# Generate secure passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 32  # For REDIS_PASSWORD
openssl rand -hex 32     # For SECRET_KEY

# Edit .env.production
nano .env.production
```

**Required changes:**
- `POSTGRES_PASSWORD` - Strong password
- `REDIS_PASSWORD` - Strong password
- `SECRET_KEY` - Random 64-char hex
- `LOG_LEVEL=WARNING` - Less verbose logging
- `ENABLE_AUTH=true` - Enable authentication (when implemented)

**Step 3: Start production stack**

```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

**Step 4: Verify health**

```bash
# Check services
docker-compose -f docker-compose.prod.yml ps

# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost/
```

**Step 5: Monitor logs**

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Only errors
docker-compose -f docker-compose.prod.yml logs -f | grep -i error
```

**Step 6: Set up log rotation**

```bash
# Configure Docker daemon for log rotation
sudo nano /etc/docker/daemon.json
```

Add:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

```bash
sudo systemctl restart docker
```

---

## Service Details

### PostgreSQL + TimescaleDB

**Image:** `timescale/timescaledb:latest-pg15`

**Purpose:** Primary database with time-series extension

**Configuration:**

```yaml
postgres:
  image: timescale/timescaledb:latest-pg15
  environment:
    POSTGRES_DB: shatter
    POSTGRES_USER: shatter_user
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./database/init:/docker-entrypoint-initdb.d
  ports:
    - "5432:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U shatter_user"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Features:**
- **TimescaleDB extension** - Automatic hypertable partitioning for time-series data
- **Initialization scripts** - SQL files in `/database/init/` run on first startup
- **Health check** - `pg_isready` checks database is accepting connections
- **Persistent volume** - Data survives container restarts

**Initialization:**

SQL files in `database/init/` are executed alphabetically on first startup:

```
database/init/
├── 01_create_tables.sql      # Create base tables
├── 02_create_hypertables.sql # Convert to TimescaleDB hypertables
└── 03_create_indexes.sql     # Create indexes
```

**Accessing PostgreSQL:**

```bash
# From host
psql -h localhost -U shatter_user -d shatter

# From Docker
docker exec -it shatter-db psql -U shatter_user -d shatter
```

**Location:** [docker-compose.yml:4-22](../docker-compose.yml#L4-L22)

---

### Redis

**Image:** `redis:7-alpine`

**Purpose:** Caching and task queue (optional)

**Configuration:**

```yaml
redis:
  image: redis:7-alpine
  volumes:
    - redis_data:/data
  ports:
    - "6379:6379"
  command: redis-server --appendonly yes
```

**Production Differences:**

```yaml
# Production adds authentication
command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
```

**Features:**
- **AOF persistence** - `--appendonly yes` ensures data durability
- **Authentication** - Password required in production
- **Health check** - Ping command verifies Redis is responsive

**Accessing Redis:**

```bash
# From host
redis-cli -h localhost

# Production (with password)
redis-cli -h localhost -a $REDIS_PASSWORD

# From Docker
docker exec -it shatter-redis redis-cli
```

**Current Usage:**
- Not actively used yet
- Future: Caching machine status, task queue for background jobs

**Location:** [docker-compose.yml:70-78](../docker-compose.yml#L70-L78)

---

### Backend

**Image:** Custom (built from `backend/Dockerfile`)

**Base:** `python:3.11-slim`

**Purpose:** FastAPI application with polling service

**Multi-Stage Build:**

```dockerfile
FROM python:3.11-slim AS base
# Install dependencies, copy code

FROM base AS development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Configuration:**

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
    target: production  # or development
  environment:
    POSTGRES_HOST: postgres
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    REDIS_HOST: redis
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
    DEFAULT_POLL_INTERVAL: 5
  ports:
    - "8000:8000"
  depends_on:
    postgres:
      condition: service_healthy
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Development vs Production:**

| Feature | Development | Production |
|---------|-------------|------------|
| **Uvicorn workers** | 1 (--reload) | 4 (multi-worker) |
| **Target stage** | `development` | `production` |
| **Hot reload** | ✅ Yes | ❌ No |
| **Health check** | ❌ No | ✅ Yes (curl /health) |
| **Restart policy** | `unless-stopped` | `always` |

**Dependencies:**

The backend waits for postgres to be healthy before starting:

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

**Logs:**

```bash
# View backend logs
docker-compose logs -f backend

# Filter for errors
docker-compose logs backend | grep ERROR
```

**Location:** [docker-compose.yml:25-48](../docker-compose.yml#L25-L48)

---

### Frontend

**Image:** Custom (built from `frontend/Dockerfile`)

**Purpose:** React + Vite application

**Multi-Stage Build:**

```dockerfile
FROM node:20-alpine AS development
CMD ["npm", "run", "dev", "--", "--host"]

FROM node:20-alpine AS build
RUN npm run build

FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
```

**Configuration:**

**Development:**
```yaml
frontend:
  build:
    context: ./frontend
    target: development
  ports:
    - "3000:3000"
  volumes:
    - ./frontend:/app          # Hot reload
    - /app/node_modules        # Preserve node_modules
  command: npm run dev
```

**Production:**
```yaml
frontend:
  build:
    context: ./frontend
    target: production
    args:
      VITE_API_URL: ${VITE_API_URL:-http://localhost:8000}
  ports:
    - "80:80"  # Nginx on port 80
```

**Development vs Production:**

| Feature | Development | Production |
|---------|-------------|------------|
| **Server** | Vite dev server | Nginx |
| **Port** | 3000 | 80 |
| **Assets** | Source files | Built/minified |
| **Hot reload** | ✅ Yes | ❌ No |
| **Volume mount** | ✅ Yes (for hot reload) | ❌ No |
| **Health check** | ❌ No | ✅ Yes (wget /) |

**VITE_API_URL:**

Build-time argument passed to frontend:

```yaml
args:
  VITE_API_URL: ${VITE_API_URL:-http://localhost:8000}
```

If not set, frontend auto-detects based on browser hostname.

**Location:** [docker-compose.yml:51-67](../docker-compose.yml#L51-L67)

---

## Volume Management

### Persistent Volumes

Docker volumes store data that persists across container restarts.

| Volume | Purpose | Size (typical) | Backup Priority |
|--------|---------|----------------|-----------------|
| `postgres_data` | Database files | 1-10GB | ⚠️ CRITICAL |
| `redis_data` | Redis AOF logs | 10-100MB | 🔵 Optional |

**List volumes:**

```bash
docker volume ls | grep shatter
```

**Inspect volume:**

```bash
docker volume inspect shatter_postgres_data
```

**Volume location on host:**

```bash
# Linux
/var/lib/docker/volumes/shatter_postgres_data/_data

# Docker Desktop (Mac/Windows)
# Access via Docker Desktop GUI or docker exec
```

**Clean up unused volumes:**

```bash
# Warning: Only run if you don't need old data
docker volume prune
```

---

### Backup

#### PostgreSQL Backup

**Method 1: pg_dump (recommended)**

```bash
# Backup to SQL file
docker exec shatter-db pg_dump -U shatter_user shatter > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
docker exec shatter-db pg_dump -U shatter_user shatter | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Method 2: Volume backup**

```bash
# Stop services first
docker-compose down

# Backup volume
docker run --rm \
  -v shatter_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz -C /data .

# Restart services
docker-compose up -d
```

**Automated Backup Script:**

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
docker exec shatter-db pg_dump -U shatter_user shatter | gzip > $BACKUP_DIR/shatter_$DATE.sql.gz

# Keep last 7 days
find $BACKUP_DIR -name "shatter_*.sql.gz" -mtime +7 -delete

echo "Backup completed: shatter_$DATE.sql.gz"
```

**Schedule with cron:**

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/shatter_backup.log 2>&1
```

---

### Restore

**From pg_dump backup:**

```bash
# Stop backend to prevent conflicts
docker-compose stop backend

# Restore
docker exec -i shatter-db psql -U shatter_user shatter < backup.sql

# Or from gzip
gunzip -c backup.sql.gz | docker exec -i shatter-db psql -U shatter_user shatter

# Restart backend
docker-compose start backend
```

**From volume backup:**

```bash
# Stop all services
docker-compose down

# Remove old volume
docker volume rm shatter_postgres_data

# Restore volume
docker run --rm \
  -v shatter_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /data

# Start services
docker-compose up -d
```

---

## Health Checks

Health checks monitor service availability and automatically restart unhealthy containers.

### PostgreSQL Health Check

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U shatter_user -d shatter"]
  interval: 10s    # Check every 10 seconds
  timeout: 5s      # Command must complete in 5 seconds
  retries: 5       # Retry 5 times before marking unhealthy
```

**Check status:**

```bash
docker inspect shatter-db | grep -A 10 Health
```

---

### Backend Health Check (Production)

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s  # Allow 40s for startup before checking
```

**Manual health check:**

```bash
curl http://localhost:8000/health
```

---

### Redis Health Check (Production)

```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

## Networking

### Default Network

Development (`docker-compose.yml`) creates a default network:

```yaml
networks:
  default:
    name: shatter-network
```

**Features:**
- Services can communicate by service name (e.g., `http://backend:8000`)
- Isolated from other Docker networks
- DNS resolution built-in

---

### Custom Network (Production)

Production uses an explicit bridge network:

```yaml
networks:
  shatter-network:
    driver: bridge
```

All services must explicitly join:

```yaml
services:
  postgres:
    networks:
      - shatter-network
```

**Advantages:**
- More control over network configuration
- Can attach external containers
- Better isolation

---

### Service Communication

**Within Docker network:**

```python
# Backend connecting to PostgreSQL
database_url = "postgresql://shatter_user:password@postgres:5432/shatter"
#                                                    ^^^^^^
#                                              Service name (not localhost)
```

**From host:**

```bash
# PostgreSQL
psql -h localhost -p 5432 -U shatter_user shatter

# Backend
curl http://localhost:8000/api/machines

# Frontend
http://localhost:3000
```

---

## Upgrading

### Upgrade Application Code

**Step 1: Pull latest code**

```bash
git pull origin main
```

**Step 2: Rebuild containers**

```bash
# Development
docker-compose build
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

**Step 3: Verify**

```bash
# Check logs for errors
docker-compose logs -f backend

# Check health
curl http://localhost:8000/health
```

---

### Upgrade Dependencies

**Backend (Python):**

```bash
# Update requirements.txt
cd backend
pip-compile requirements.in  # If using pip-tools

# Rebuild
docker-compose build backend
docker-compose up -d backend
```

**Frontend (Node):**

```bash
# Update package.json
cd frontend
npm update

# Rebuild
docker-compose build frontend
docker-compose up -d frontend
```

---

### Upgrade PostgreSQL

**⚠️ WARNING:** PostgreSQL major version upgrades require data migration.

**Minor version upgrade (safe):**

```bash
# Update docker-compose.yml
image: timescale/timescaledb:latest-pg15

# Pull new image
docker-compose pull postgres

# Restart
docker-compose up -d postgres
```

**Major version upgrade (PostgreSQL 14 → 15):**

1. **Backup database** (critical!)
   ```bash
   docker exec shatter-db pg_dump -U shatter_user shatter > backup_pre_upgrade.sql
   ```

2. **Stop services**
   ```bash
   docker-compose down
   ```

3. **Remove old volume** (after verifying backup!)
   ```bash
   docker volume rm shatter_postgres_data
   ```

4. **Update image version**
   ```yaml
   image: timescale/timescaledb:latest-pg16
   ```

5. **Start new version**
   ```bash
   docker-compose up -d postgres
   ```

6. **Restore data**
   ```bash
   docker exec -i shatter-db psql -U shatter_user shatter < backup_pre_upgrade.sql
   ```

---

## Troubleshooting

### Services Won't Start

**Error: "port is already allocated"**

```bash
# Find process using port
lsof -i :5432  # PostgreSQL
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Kill process or change port in .env
BACKEND_PORT=8001
```

---

**Error: "ERROR: Couldn't connect to Docker daemon"**

```bash
# Start Docker daemon
sudo systemctl start docker  # Linux
# or open Docker Desktop (Mac/Windows)

# Verify Docker is running
docker ps
```

---

### Container Keeps Restarting

**Check logs:**

```bash
docker-compose logs backend
```

**Common causes:**

1. **Database not ready**
   - Solution: Wait for postgres health check to pass

2. **Missing environment variable**
   ```
   Error: POSTGRES_PASSWORD not set
   ```
   - Solution: Create .env file from .env.example

3. **Port conflict**
   - Solution: Change port in .env or stop conflicting service

---

### Database Connection Refused

**Error in backend logs:**

```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**Solutions:**

1. **Check postgres is running**
   ```bash
   docker-compose ps postgres
   # Should show "Up (healthy)"
   ```

2. **Check POSTGRES_HOST**
   ```bash
   # Should be "postgres" (service name), not "localhost"
   echo $POSTGRES_HOST
   ```

3. **Check credentials**
   ```bash
   # Verify password matches
   docker-compose exec postgres psql -U shatter_user -d shatter
   ```

---

### Frontend Can't Reach Backend

**Error in browser console:**

```
GET http://localhost:8000/api/machines net::ERR_CONNECTION_REFUSED
```

**Solutions:**

1. **Check backend is running**
   ```bash
   docker-compose ps backend
   curl http://localhost:8000/health
   ```

2. **Check VITE_API_URL**
   ```bash
   # Should match backend port
   VITE_API_URL=http://localhost:8000
   ```

3. **Rebuild frontend** (if changed VITE_API_URL)
   ```bash
   docker-compose build frontend
   docker-compose up -d frontend
   ```

---

### Out of Disk Space

**Check disk usage:**

```bash
# Docker disk usage
docker system df

# Detailed breakdown
docker system df -v
```

**Clean up:**

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes (WARNING: deletes data)
docker volume prune

# Clean everything (WARNING: deletes all unused resources)
docker system prune -a --volumes
```

---

## Advanced Topics

### Custom Networks

Create external network for service isolation:

```bash
# Create network
docker network create shatter-external

# Update docker-compose.yml
networks:
  default:
    external: true
    name: shatter-external
```

---

### Resource Limits

Limit CPU and memory per service:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

### SSL/TLS with Nginx Reverse Proxy

**docker-compose.nginx.yml:**

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
```

**nginx.conf:**

```nginx
server {
    listen 443 ssl;
    server_name shatter.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://frontend;
    }

    location /api/ {
        proxy_pass http://backend:8000;
    }
}
```

---

### Docker Swarm Deployment

For multi-node deployments:

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml shatter

# Check services
docker service ls
```

---

## Related Documentation

- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) - Environment variable reference
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - Local development setup
- [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md) - Backend service details
- [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) - Frontend build process
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - Database structure

---

## Quick Reference

**Essential Commands:**

```bash
# Development
docker-compose up -d              # Start all services
docker-compose down               # Stop all services
docker-compose logs -f            # View all logs
docker-compose ps                 # Service status
docker-compose restart backend    # Restart service

# Production
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
docker-compose -f docker-compose.prod.yml logs -f
docker-compose -f docker-compose.prod.yml down

# Maintenance
docker-compose exec postgres psql -U shatter_user shatter  # Database CLI
docker-compose exec backend bash                            # Backend shell
docker volume ls                                            # List volumes
docker system df                                            # Disk usage
```

**Port Reference:**

| Service | Development | Production |
|---------|-------------|------------|
| Frontend | 3000 | 80 |
| Backend | 8000 | 8000 |
| PostgreSQL | 5432 | 5432 |
| Redis | 6379 | 6379 |
