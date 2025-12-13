#!/bin/bash
set -e

echo "Starting Shatter backend..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h ${POSTGRES_HOST} -U ${POSTGRES_USER} > /dev/null 2>&1; do
    sleep 1
done
echo "✓ PostgreSQL is ready"

# Run database migrations
echo "Running database migrations..."
python3 /app/scripts/run_migrations.py
if [ $? -ne 0 ]; then
    echo "✗ Migration failed! Exiting..."
    exit 1
fi

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
