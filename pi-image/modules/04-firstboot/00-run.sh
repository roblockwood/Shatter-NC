#!/bin/bash
# CustomPiOS Module: Set up first-boot wizard
# This script creates a systemd service that runs the setup wizard on first boot

set -e

echo "=== Setting up first-boot wizard ==="

# Create systemd service for first-boot setup
cat > /etc/systemd/system/shatter-setup.service << 'EOF'
[Unit]
Description=Shatter CNC Platform First-Boot Setup Wizard
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/shatter/setup-wizard.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

chmod 644 /etc/systemd/system/shatter-setup.service

# Enable the setup service (will run on first boot)
systemctl enable shatter-setup.service

echo "=== First-boot wizard setup complete ==="
