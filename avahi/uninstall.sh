#!/bin/bash
# Uninstall Avahi service file from the host system

set -e

TARGET_FILE="/etc/avahi/services/shatter.service"

echo "Uninstalling Avahi service for Shatter..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if service file exists
if [ ! -f "$TARGET_FILE" ]; then
    echo "Service file not found at $TARGET_FILE (may already be removed)"
    exit 0
fi

# Remove service file
echo "Removing service file..."
rm -f "$TARGET_FILE"

# Restart Avahi daemon to apply changes
if systemctl is-active --quiet avahi-daemon; then
    echo "Restarting Avahi daemon..."
    systemctl restart avahi-daemon
fi

echo "✓ Avahi service uninstalled successfully!"
