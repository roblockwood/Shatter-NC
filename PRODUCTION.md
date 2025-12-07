# Production Deployment Guide

This guide covers deploying Shatter with production-ready Docker images.

## Prerequisites

- Docker and Docker Compose installed
- At least 2GB RAM available
- Production server or machine with network access to CNC machines

## Quick Production Deployment

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/user/shatter
cd shatter

# Copy production environment template
cp .env.production.example .env.production

# Edit the production environment file
nano .env.production  # or use your preferred editor
```

### 2. Configure Security Settings

**IMPORTANT:** Update these values in `.env.production`:

```bash
# Generate a secure PostgreSQL password
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Set a secure Redis password
REDIS_PASSWORD=$(openssl rand -base64 32)
```

Update `VITE_API_URL` to match your server's IP or domain:
```bash
# For local network deployment
VITE_API_URL=http://192.168.1.100:8000

# For domain-based deployment
VITE_API_URL=https://shatter.yourdomain.com
```

### 3. Deploy Production Stack

```bash
# Build and start all services in production mode
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# Monitor the startup
docker compose -f docker-compose.prod.yml logs -f
```

### 4. Verify Deployment

```bash
# Check all services are running
docker compose -f docker-compose.prod.yml ps

# Test the backend health
curl http://localhost:8000/health

# Access the application
# Frontend: http://your-server-ip
# Backend API: http://your-server-ip:8000
# API Docs: http://your-server-ip:8000/docs
```

## Production Architecture

The production setup includes:

- **Frontend (Nginx)**: Optimized static build on port 80
- **Backend (Uvicorn)**: Multi-worker FastAPI on port 8000
- **Database (PostgreSQL + TimescaleDB)**: Persistent storage on port 5432
- **Redis**: Caching and task queue on port 6379

## Differences from Development

| Feature | Development | Production |
|---------|-------------|------------|
| Frontend | Vite dev server | Nginx static hosting |
| Backend | Single worker with reload | 4 workers, no reload |
| Volumes | Code mounted for hot reload | Code baked into images |
| Logging | INFO level | WARNING level |
| Security | Minimal | Passwords required |

## Management Commands

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
```

### Stop Services

```bash
# Stop all services (keeps data)
docker compose -f docker-compose.prod.yml down

# Stop and remove all data
docker compose -f docker-compose.prod.yml down -v
```

### Update to Latest Version

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Remove old images
docker image prune -f
```

### Backup Database

```bash
# Create backup directory
mkdir -p backups

# Backup database
docker exec shatter-db-prod pg_dump -U shatter_user shatter > backups/shatter_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database

```bash
# Restore from backup
cat backups/shatter_backup_YYYYMMDD_HHMMSS.sql | docker exec -i shatter-db-prod psql -U shatter_user shatter
```

## Performance Tuning

### Backend Workers

Adjust the number of Uvicorn workers based on your CPU cores:

Edit [backend/Dockerfile](backend/Dockerfile:34):
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Recommended: `(2 x CPU cores) + 1`

### Database Connections

For high-load scenarios, adjust PostgreSQL max connections in `docker-compose.prod.yml`:

```yaml
postgres:
  command: postgres -c max_connections=200
```

### Resource Limits

Add resource constraints in `docker-compose.prod.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

## Security Hardening

### 1. Use HTTPS

For production, use a reverse proxy (Nginx/Traefik) with SSL certificates:

```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d shatter.yourdomain.com
```

### 2. Firewall Rules

Only expose necessary ports:

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct database access from external networks
sudo ufw deny 5432/tcp
```

### 3. Network Isolation

The production compose file uses an isolated bridge network. CNC machines should be on the same network or have routing configured.

## Monitoring

### Health Checks

All services have built-in health checks. Check status:

```bash
docker compose -f docker-compose.prod.yml ps
```

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

## Troubleshooting

### Services fail to start

Check logs for errors:
```bash
docker compose -f docker-compose.prod.yml logs
```

### Database connection errors

Ensure PostgreSQL is healthy:
```bash
docker compose -f docker-compose.prod.yml ps postgres
docker exec shatter-db-prod pg_isready -U shatter_user
```

### Frontend can't reach backend

Verify backend is accessible:
```bash
curl http://localhost:8000/health
```

Check `VITE_API_URL` in `.env.production` matches your setup.

### Out of disk space

Clean up old images and containers:
```bash
docker system prune -a
```

## Next Steps

- Configure your CNC machines in the web UI
- Set up regular database backups (cron job)
- Configure monitoring/alerting
- Review logs regularly for issues
- Plan capacity based on number of machines
