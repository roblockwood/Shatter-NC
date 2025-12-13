# Check Project Status Skill

Check the current development environment status for the Shatter CNC Management Platform.

## Task

Analyze the current project status and report back with:

1. **Docker Status**: Check if Docker is running
2. **Active Services**: Identify which Docker services are currently running
3. **Deployment Configuration**: Determine which development setup option is being used (see @docs/DEVELOPMENT_GUIDE.md for the 4 options)
4. **Service Health**: Check the health status of running services
5. **Port Accessibility**: Verify which ports are accessible (frontend: 3000, backend: 8000, database: 5432)

## Steps

### 1. Check Docker Status

Run `docker ps` to see if Docker is running and what containers are active.

### 2. Identify Deployment Configuration

Based on the running containers, determine which of the 4 development options from @docs/DEVELOPMENT_GUIDE.md is being used:

- **Option 1: Full Docker** - All services running in containers (postgres, redis, backend, frontend)
- **Option 2: Hybrid - Local Backend** - Only postgres and redis in Docker, backend running locally
- **Option 3: Hybrid - Local Frontend** - Backend, postgres, redis in Docker, frontend running locally
- **Option 4: Fully Local** - No Docker containers running, all services local

### 3. Check Service Health

For each running service:
- Check container health status (if Docker)
- Check if services are responsive on their ports
- Identify any unhealthy or stopped containers

### 4. Check Configuration Files

Identify which docker-compose file is being used (if any):
- `docker-compose.yml` - Full stack development
- `docker-compose.dev.yml` - Lightweight development (no TimescaleDB)
- `docker-compose.simple.yml` - Database services only (hybrid setup)
- `docker-compose.prod.yml` - Production deployment

### 5. Report Findings

Provide a concise summary in this format:

```
## Project Status Report

**Docker Status:** [Running/Not Running]

**Deployment Configuration:** [Option 1/2/3/4]

**Active Services:**
- Frontend: [Running on port 3000 / Not Running / Running locally]
- Backend: [Running on port 8000 / Not Running / Running locally]
- Database: [Running on port 5432 / Not Running / Running locally]
- Redis: [Running on port 6379 / Not Running / Not configured]

**Service Health:**
- [Service]: [Healthy/Unhealthy/Not Running]

**Docker Compose File:** [filename or "None"]

**Recommendations:**
- [Any suggestions for improving the setup]
```

## Notes

- If Docker is not running, report that and suggest starting it or running in fully local mode
- If services are unhealthy, suggest troubleshooting steps from @docs/DEVELOPMENT_GUIDE.md
- If no services are running, provide quick start instructions from @docs/DOCKER_DEPLOYMENT.md
- Be concise and actionable - focus on what the developer needs to know right now
