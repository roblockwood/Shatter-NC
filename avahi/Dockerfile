FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Avahi daemon and utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    avahi-daemon \
    avahi-utils \
    dbus \
    && rm -rf /var/lib/apt/lists/*

# Create directory for service files
RUN mkdir -p /etc/avahi/services

# Copy service file (will be mounted as volume, but this ensures directory exists)
# The actual service file will be mounted from the host

# Expose mDNS port (UDP 5353)
EXPOSE 5353/udp

# Start dbus and avahi-daemon
# Note: dbus is required for avahi-daemon
CMD dbus-daemon --system && \
    avahi-daemon --no-drop-root --no-chroot
