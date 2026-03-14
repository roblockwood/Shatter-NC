FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Copy database migration files into the image
# These will be available at /app/migrations in the container
COPY database/init /app/migrations

# Make startup scripts executable
RUN chmod +x /app/scripts/*.sh

# Create non-root user
RUN useradd -m -u 1000 shatter && chown -R shatter:shatter /app

# Development stage: inline startup so we don't depend on host-mounted start-dev.sh
# (on Windows, the mount can have CRLF line endings, which breaks exec of the script)
FROM base AS development
USER shatter
EXPOSE 8000
CMD ["/bin/bash", "-c", "echo 'Waiting for PostgreSQL...' && while ! pg_isready -h ${POSTGRES_HOST} -U ${POSTGRES_USER}; do sleep 1; done && echo 'Running migrations...' && python3 /app/scripts/run_migrations.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

# Production stage
FROM base AS production
USER shatter
EXPOSE 8000

# Use startup script that runs migrations first
CMD ["/app/scripts/start.sh"]
