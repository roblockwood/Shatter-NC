#!/bin/bash
# CustomPiOS Module: Set up Shatter application files and directories
# This script creates the application directory structure and copies necessary files

set -e

echo "=== Setting up Shatter application ==="

# Create application directory
mkdir -p /opt/shatter
cd /opt/shatter

# Copy docker-compose.prod.yml from module files
# CustomPiOS provides MODULE_DIR variable pointing to module directory
MODULE_FILES_DIR="${MODULE_DIR}/../files"
if [ -f "${MODULE_FILES_DIR}/docker-compose.prod.yml" ]; then
    cp "${MODULE_FILES_DIR}/docker-compose.prod.yml" /opt/shatter/docker-compose.prod.yml
    chmod 644 /opt/shatter/docker-compose.prod.yml
fi

# Create .env.example template
cat > /opt/shatter/.env.example << 'EOF'
# Shatter CNC Platform - Environment Variables
# Copy this file to .env and configure with your values

# Database Configuration
POSTGRES_DB=shatter
POSTGRES_USER=shatter_user
POSTGRES_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD

# Redis Configuration
REDIS_HOST=redis
REDIS_PASSWORD=CHANGE_ME_TO_SECURE_REDIS_PASSWORD

# Application Configuration
LOG_LEVEL=WARNING
DEFAULT_POLL_INTERVAL=5
SECRET_KEY=CHANGE_ME_TO_SECURE_SECRET_KEY

# Backend Port
BACKEND_PORT=8000

# GitHub Container Registry (for pulling images)
GITHUB_OWNER=roblockwood
GITHUB_REPO=shatter-nc
IMAGE_TAG=latest
EOF

chmod 644 /opt/shatter/.env.example

# Create data directories for Docker volumes
mkdir -p /opt/shatter/data/postgres
mkdir -p /opt/shatter/data/redis

# Set proper permissions
chown -R pi:pi /opt/shatter
chmod 755 /opt/shatter

# Copy systemd service file
MODULE_FILES_DIR="${MODULE_DIR}/../files"
if [ -f "${MODULE_FILES_DIR}/shatter.service" ]; then
    cp "${MODULE_FILES_DIR}/shatter.service" /etc/systemd/system/shatter.service
    chmod 644 /etc/systemd/system/shatter.service
    systemctl daemon-reload
    # Enable service but don't start it yet (wait for first-boot wizard)
    systemctl enable shatter.service
fi

# Copy setup wizard script
if [ -f "${MODULE_FILES_DIR}/setup-wizard.sh" ]; then
    cp "${MODULE_FILES_DIR}/setup-wizard.sh" /opt/shatter/setup-wizard.sh
    chmod +x /opt/shatter/setup-wizard.sh
fi

echo "=== Shatter application setup complete ==="
