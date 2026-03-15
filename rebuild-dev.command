#!/bin/bash
# Pull latest from GitHub, stop Shatter dev stack, rebuild images, then start again.
# Double-click in Finder to run in Terminal (macOS).
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.dev.yml"

cd "$SCRIPT_DIR"

echo "Pulling latest from GitHub..."
git pull

echo "Stopping Shatter (docker-compose.dev.yml)..."
docker compose -f "$COMPOSE_FILE" down

echo "Building images..."
docker compose -f "$COMPOSE_FILE" build

echo "Starting Shatter..."
docker compose -f "$COMPOSE_FILE" up -d

echo "Done. Backend: ${BACKEND_PORT:-8000}, Frontend: 3000, Postgres: 5432"
echo ""
read -n 1 -s -r -p "Press any key to close..."
