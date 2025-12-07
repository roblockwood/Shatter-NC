# Shatter - Quick Start Guide

## Prerequisites

- Docker Desktop installed and running
- Git (for cloning the repository)

## Quick Start (Recommended)

Start all services with Docker Compose:

```bash
# Clone the repository
git clone https://github.com/user/shatter
cd shatter

# Copy environment file
cp .env.example .env

# Start all services (database, backend, frontend, Redis)
docker compose up -d

# View logs
docker compose logs -f

# Check service status
docker compose ps
```

The application will be available at:
- http://localhost:3000 - Frontend web application
- http://localhost:8000 - Backend API
- http://localhost:8000/docs - Interactive API documentation (Swagger UI)
- http://localhost:8000/health - Health check

## Alternative: Local Backend Development

If you prefer to run the backend locally for development:

```bash
# Start just the database and Redis
docker compose -f docker-compose.simple.yml up -d

# In a new terminal, run the backend locally
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test the API

### Using the Browser

Visit http://localhost:8000/docs for interactive API documentation.

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# List machines (will be empty initially)
curl http://localhost:8000/api/machines

# Add a machine
curl -X POST http://localhost:8000/api/machines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mill 1",
    "ip_address": "192.168.86.89",
    "location": "Production Floor",
    "tags": ["production"]
  }'

# Get machine details
curl http://localhost:8000/api/machines/1
```

## Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (deletes all data)
docker compose down -v
```

## Troubleshooting

### Services won't start
Check if Docker Desktop is running and healthy:
```bash
docker compose ps
docker compose logs
```

### Database connection errors
If running the backend locally, ensure the database is accessible:
- Check `.env` file has `POSTGRES_HOST=localhost`
- Verify database is running: `docker compose -f docker-compose.simple.yml ps`

Default database credentials:
- POSTGRES_DB=shatter
- POSTGRES_USER=shatter_user
- POSTGRES_PASSWORD=changeme

### Port conflicts
If ports 3000, 8000, or 5432 are already in use, modify the ports in `docker-compose.yml` or stop the conflicting services

## Next Steps

1. Add your CNC machine through the API
2. Build the frontend (React/Vue)
3. Implement CNC communication clients
4. Start polling your machines!

See [STATUS.md](STATUS.md) for current development progress.
