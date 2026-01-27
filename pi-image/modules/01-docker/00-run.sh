#!/bin/bash
# CustomPiOS Module: Install Docker Engine and Docker Compose
# This script installs Docker and pre-pulls required images

set -e

echo "=== Installing Docker Engine ==="

# Install Docker using official convenience script
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
rm /tmp/get-docker.sh

# Add pi user to docker group (if not already added)
usermod -aG docker pi || true

# Enable Docker service
systemctl enable docker

# Install Docker Compose V2 (as plugin)
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Verify installations
docker --version
docker compose version

echo "=== Docker installation complete ==="
