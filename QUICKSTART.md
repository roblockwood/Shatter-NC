# Shatter - Quick Start Guide

## Prerequisites

- Docker Desktop installed and running
- Git (for cloning the repository)

## Step 1: Start Database Services

The PostgreSQL/TimescaleDB image is large (~225MB) and may take a few minutes to download on first run.

```bash
# Start just the database and Redis (faster initial setup)
docker compose -f docker-compose.simple.yml up -d

# Wait for services to be healthy
docker compose -f docker-compose.simple.yml ps
```

## Step 2: Run Backend Locally (Development)

While we build out the full containerized setup, you can run the backend locally:

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- http://localhost:8000 - API root
- http://localhost:8000/docs - Interactive API documentation (Swagger UI)
- http://localhost:8000/health - Health check

## Step 3: Test the API

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

## Step 4: Full Docker Setup (When Ready)

Once all images are downloaded:

```bash
# Start all services (backend, frontend, database, redis)
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

## Troubleshooting

### Docker image still downloading
Check progress:
```bash
docker images
```

You should see `timescale/timescaledb` and `redis` images.

### Backend won't start
Make sure PostgreSQL is running and healthy:
```bash
docker compose -f docker-compose.simple.yml ps
```

### Database connection errors
Check your `.env` file or use the defaults:
- POSTGRES_HOST=localhost
- POSTGRES_DB=shatter
- POSTGRES_USER=shatter_user
- POSTGRES_PASSWORD=changeme

## Next Steps

1. Add your CNC machine through the API
2. Build the frontend (React/Vue)
3. Implement CNC communication clients
4. Start polling your machines!

See [STATUS.md](STATUS.md) for current development progress.
