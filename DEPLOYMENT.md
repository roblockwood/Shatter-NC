# Production Deployment Guide

## Table of Contents

- [Files Required for Deployment](#files-required-for-deployment)
- [Loading Images on Target Machine](#loading-images-on-target-machine)
- [Running with Docker Compose](#running-with-docker-compose)
- [Services](#services)
- [Health Checks](#health-checks)
- [Airgapped/Offline Deployment](#airgappedoffline-deployment)
- [Notes](#notes)

---

## Files Required for Deployment

For deployment to a macOS machine (or any machine with Docker Desktop), you need the following files:

1. **Production Docker Images:**
   - `shatter-backend-prod.tar` (209 MB) - Backend API service
   - `shatter-frontend-prod.tar` (22 MB) - Frontend web application

2. **Configuration Files:**
   - `docker-compose.prod.yml` - Docker Compose configuration for production
   - `.env.production.example` - Environment variable template (copy to `.env`)

3. **Documentation (optional but recommended):**
   - `DEPLOYMENT.md` - This deployment guide

**Note:** Base images (PostgreSQL/TimescaleDB, Redis, Nginx) will be automatically downloaded from Docker Hub when you run `docker-compose up`. You do not need to transfer these separately.

**For Airgapped/Offline Deployment:** If your target machine does not have internet access, you will also need to save and transfer the base images. See the [Airgapped Deployment](#airgapped-deployment) section below.

## Loading Images on Target Machine

1. Transfer all required files to your target machine:
   ```bash
   scp shatter-backend-prod.tar shatter-frontend-prod.tar docker-compose.prod.yml .env.production.example user@target-machine:/path/to/deployment/
   ```

2. Load the images into Docker:
   ```bash
   docker load -i shatter-backend-prod.tar
   docker load -i shatter-frontend-prod.tar
   ```

3. Verify images are loaded:
   ```bash
   docker images | grep s700_nc
   ```

## Running with Docker Compose

1. Copy `docker-compose.prod.yml` and `.env.production.example` to your target machine

2. Create a `.env` file from the production example:
   ```bash
   cp .env.production.example .env
   ```

3. Generate secure values for required secrets:
   ```bash
   # Generate PostgreSQL password
   openssl rand -base64 32
   
   # Generate SECRET_KEY
   openssl rand -hex 32
   
   # (Optional) Generate Redis password
   openssl rand -base64 32
   ```

4. Edit the `.env` file with your production values:
   ```bash
   nano .env  # or use your preferred editor
   ```
   
   **Required changes (must be updated):**
   - `POSTGRES_PASSWORD`: Set a strong password for the PostgreSQL database (use the generated value from step 3)
   - `SECRET_KEY`: Set a strong secret key (use the generated value from step 3)
   - `VITE_API_URL`: Set to your backend API URL:
     - Same machine: `http://localhost:8000`
     - Remote backend: `http://your-backend-ip-or-hostname:8000`
   
   **Optional changes (defaults are usually fine):**
   - `POSTGRES_DB`: Change database name if needed (default: `shatter`)
   - `POSTGRES_USER`: Change database user if needed (default: `shatter_user`)
   - `BACKEND_PORT`: Change backend port if needed (default: `8000`)
   - `LOG_LEVEL`: Adjust logging level (default: `WARNING`)
   - `DEFAULT_POLL_INTERVAL`: Change polling interval in seconds (default: `5`)
   - `REDIS_PASSWORD`: Set Redis password if needed (leave empty to disable authentication)

5. Verify your `.env` file:
   ```bash
   # Check that required values are set (not the placeholder values)
   grep -E "CHANGE_ME|^#.*CHANGE" .env
   ```
   If you see any output, those values still need to be updated.

6. Start the services:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

7. Check service status:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   docker-compose -f docker-compose.prod.yml logs -f
   ```

## Services

- **Frontend**: Available on port 80 (http://your-server-ip)
- **Backend API**: Available on port 8000 (http://your-server-ip:8000)
- **PostgreSQL**: Port 5432 (internal only, not exposed by default)
- **Redis**: Port 6379 (internal only, not exposed by default)

## Health Checks

- Backend health: `curl http://localhost:8000/health`
- Frontend health: `curl http://localhost/`

## Airgapped/Offline Deployment

If your target machine does **not** have internet access, you need to save and transfer the base images as well.

### On a Machine with Internet Access:

1. Pull the required base images:
   ```bash
   docker pull timescale/timescaledb:latest-pg15
   docker pull redis:7-alpine
   docker pull nginx:alpine
   ```

2. Save the base images:
   ```bash
   docker save timescale/timescaledb:latest-pg15 -o timescaledb-prod.tar
   docker save redis:7-alpine -o redis-prod.tar
   docker save nginx:alpine -o nginx-prod.tar
   ```

3. Transfer all images to the airgapped machine:
   ```bash
   scp shatter-backend-prod.tar shatter-frontend-prod.tar timescaledb-prod.tar redis-prod.tar nginx-prod.tar docker-compose.prod.yml .env.production.example user@target-machine:/path/to/deployment/
   ```

### On the Airgapped Machine:

1. Load all images:
   ```bash
   docker load -i shatter-backend-prod.tar
   docker load -i shatter-frontend-prod.tar
   docker load -i timescaledb-prod.tar
   docker load -i redis-prod.tar
   docker load -i nginx-prod.tar
   ```

2. Verify all images are loaded:
   ```bash
   docker images | grep -E "s700_nc|timescale|redis|nginx"
   ```

3. Follow the normal deployment steps starting from "Running with Docker Compose" above.

## Notes

- The production images use optimized builds (no hot-reload, production mode)
- Database migrations run automatically on backend startup
- Ensure your target machine has Docker and Docker Compose installed
- **Base images (PostgreSQL/TimescaleDB, Redis, Nginx) will be automatically pulled from Docker Hub** when you run `docker-compose up` - you do not need to transfer these separately **unless deploying to an airgapped machine**
- Docker Desktop on macOS includes Docker Compose, so no additional installation is needed

