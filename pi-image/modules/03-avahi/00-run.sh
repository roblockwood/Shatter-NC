#!/bin/bash
# CustomPiOS Module: Configure Avahi for mDNS service discovery
# This script installs and configures Avahi daemon

set -e

echo "=== Configuring Avahi ==="

# Avahi should already be installed via packages in config.yaml
# But ensure it's installed
apt-get update
apt-get install -y avahi-daemon avahi-utils || true

# Copy Avahi service file
# Try module-specific files first, then shared files directory
if [ -f "${MODULE_DIR}/files/shatter.service" ]; then
    mkdir -p /etc/avahi/services
    cp "${MODULE_DIR}/files/shatter.service" /etc/avahi/services/shatter.service
    chmod 644 /etc/avahi/services/shatter.service
elif [ -f "${MODULE_DIR}/../files/avahi/shatter.service" ]; then
    mkdir -p /etc/avahi/services
    cp "${MODULE_DIR}/../files/avahi/shatter.service" /etc/avahi/services/shatter.service
    chmod 644 /etc/avahi/services/shatter.service
fi

# Configure Avahi daemon
cat > /etc/avahi/avahi-daemon.conf << 'EOF'
[server]
host-name=shatter
domain-name=local
enable-dbus=no

[wide-area]
enable-wide-area=yes

[publish]
disable-publishing=no
EOF

# Enable Avahi service
systemctl enable avahi-daemon

echo "=== Avahi configuration complete ==="
