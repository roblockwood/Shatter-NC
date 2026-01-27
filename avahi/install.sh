#!/bin/bash
# Install Avahi service file on the host system
# This script copies the service file to the system Avahi directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/shatter.service"
TARGET_DIR="/etc/avahi/services"
TARGET_FILE="$TARGET_DIR/shatter.service"

echo "Installing Avahi service for Shatter..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Create target directory if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    echo "Creating $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
fi

# Copy service file
echo "Copying service file to $TARGET_FILE..."
cp "$SERVICE_FILE" "$TARGET_FILE"
chmod 644 "$TARGET_FILE"

# Check if Avahi daemon is running
if systemctl is-active --quiet avahi-daemon; then
    echo "Restarting Avahi daemon..."
    systemctl restart avahi-daemon
else
    echo "Starting Avahi daemon..."
    systemctl start avahi-daemon
    systemctl enable avahi-daemon
fi

echo "✓ Avahi service installed successfully!"
echo ""
echo "Shatter should now be discoverable at: http://shatter.local"
echo ""
echo "To verify, run:"
echo "  avahi-browse _http._tcp"
echo "  avahi-resolve -n shatter.local"
