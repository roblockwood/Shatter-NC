#!/bin/bash
# CustomPiOS Module: Pre-pull Docker images
# This script pulls all required Docker images during image build
# Note: Requires GitHub Container Registry authentication token

set -e

echo "=== Pre-pulling Docker images ==="

# Note: During image build, we'll need to authenticate with GitHub Container Registry
# This will be handled by the build process passing GITHUB_TOKEN

# Start Docker service (required for pulling images)
systemctl start docker || service docker start

# Wait for Docker to be ready
sleep 5

# Pull base images (public, no auth required)
echo "Pulling TimescaleDB image..."
docker pull timescale/timescaledb:latest-pg15 || echo "Warning: Failed to pull TimescaleDB image"

echo "Pulling Redis image..."
docker pull redis:7-alpine || echo "Warning: Failed to pull Redis image"

# Pull Shatter images from GitHub Container Registry
# These require authentication, which will be provided during build
GITHUB_OWNER="${GITHUB_OWNER:-roblockwood}"
GITHUB_REPO="${GITHUB_REPO:-shatter-nc}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "Pulling Shatter backend image..."
docker pull ghcr.io/${GITHUB_OWNER}/${GITHUB_REPO}/backend:${IMAGE_TAG} || echo "Warning: Failed to pull backend image (may require authentication)"

echo "Pulling Shatter frontend image..."
docker pull ghcr.io/${GITHUB_OWNER}/${GITHUB_REPO}/frontend:${IMAGE_TAG} || echo "Warning: Failed to pull frontend image (may require authentication)"

echo "Pulling Avahi image..."
docker pull ghcr.io/${GITHUB_OWNER}/${GITHUB_REPO}/avahi:${IMAGE_TAG} || echo "Warning: Failed to pull Avahi image (may require authentication)"

# Build Avahi image locally if pull fails (fallback)
if ! docker images | grep -q "ghcr.io/${GITHUB_OWNER}/${GITHUB_REPO}/avahi"; then
    echo "Building Avahi image locally..."
    if [ -d "/tmp/avahi-build" ]; then
        cd /tmp/avahi-build
        docker build -t ghcr.io/${GITHUB_OWNER}/${GITHUB_REPO}/avahi:${IMAGE_TAG} . || echo "Warning: Failed to build Avahi image"
    fi
fi

# List pulled images
echo "=== Pulled Docker images ==="
docker images

echo "=== Image pre-pull complete ==="
