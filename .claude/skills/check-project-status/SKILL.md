---
name: check-project-status
description: Start full-stack development environment (all services containerized). Checks status first, starts containers if needed, reports service health.
allowed-tools: Bash, Read, Grep, Glob
---

# Project Status & Startup

## Purpose

Automatically prepare the development environment when the project loads:
- Start full-stack dev mode (all services containerized, frontend with hot reload)
- Check which services are already running
- Start missing containers
- Report service health and readiness

## Deployment Modes

Reference [docs/DEVELOPMENT_GUIDE.md](../../docs/DEVELOPMENT_GUIDE.md) for deployment options:
1. **Development** (`docker-compose.dev.yml`) - All services containerized, frontend with hot reload
2. **Production** (`docker-compose.prod.yml`) - Production-ready deployment with optimized builds

## What to Check

### 1. Docker Status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Check for these containers:
- `s700_nc-frontend-1` or `frontend`
- `s700_nc-backend-1` or `backend`
- `s700_nc-db-1` or `postgres`
- `s700_nc-redis-1` or `redis`

### 2. Active Compose File

```bash
# Check which compose file exists/is active
ls -l docker-compose*.yml
```

Look for:
- `docker-compose.dev.yml` - Development (default)
- `docker-compose.prod.yml` - Production deployment

### 3. Service Health

Check running processes and ports:

```bash
# Check if ports are listening
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
```

Or use netstat:
```bash
netstat -an | grep -E ':(3000|8000|5432|6379).*LISTEN'
```

### 4. Determine Status

Based on findings:
- **All Running**: All 4 containers running and healthy
- **Partial**: Some containers missing or unhealthy
- **Not Running**: No containers detected

## Output Format

### If Everything is Running (Concise Report)

```
✓ Development environment active - 4/4 containers running
✓ Frontend: http://localhost:3000
✓ Backend: http://localhost:8000
→ Ready to code!
```

### If Starting Containers (Detailed Report)

```
⚠ No containers running - starting development environment...
✓ Starting services: docker compose -f docker-compose.dev.yml up -d
✓ Waiting for health checks...
✓ All services started successfully
→ Frontend: http://localhost:3000
→ Backend: http://localhost:8000
```

## Instructions

When this skill is invoked:

1. **Check current state** - `docker ps` to see what's already running
2. **Start all containers if needed** - If not all running: `docker compose -f docker-compose.dev.yml up -d`
3. **Wait for health** - Check that postgres is healthy with `docker ps` (look for "healthy" status)
4. **Check ports** - Use `lsof` to verify all services are accessible (3000, 8000, 5432, 6379)
5. **Report status**:
   - Which containers were started (or already running)
   - Frontend URL (http://localhost:3000)
   - Backend URL (http://localhost:8000)
   - Ready to code message

## Examples

### Example 1: All Services Already Running

```
✓ Development environment active
✓ All 4 containers running: postgres (healthy), redis, backend, frontend
✓ Frontend: http://localhost:3000
✓ Backend: http://localhost:8000
→ Ready to code!
```

### Example 2: Starting All Containers

```
⚠ No containers running - starting development environment...
✓ Starting all services with docker-compose.dev.yml
✓ Waiting for postgres to become healthy...
✓ All services started successfully
→ Frontend: http://localhost:3000
→ Backend: http://localhost:8000
→ Ready to code!
```

### Example 3: Partial Startup (some running)

```
✓ Found 2/4 containers running
✓ Starting missing services...
✓ All services now running
→ Frontend: http://localhost:3000
→ Backend: http://localhost:8000
→ Ready to code!
```

## Important Notes

- **Full-stack dev is default** - Start all 4 containers (postgres, redis, backend, frontend)
- **Keep it concise** - Report should be 3-5 lines showing what was started
- **Be proactive** - Start containers automatically, don't ask permission
- **Use docker-compose.dev.yml** - This is the development configuration
- **Auto-run on load** - This skill runs automatically per rules.md Rule 0
- **Frontend has hot reload** - The containerized frontend supports live code changes
