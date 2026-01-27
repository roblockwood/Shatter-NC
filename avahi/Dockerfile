FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Avahi daemon and utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    avahi-daemon \
    avahi-utils \
    dbus \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create directory for service files
RUN mkdir -p /etc/avahi/services

# Create dbus runtime directory (required for system bus socket)
RUN mkdir -p /run/dbus

# Create supervisor config directory
RUN mkdir -p /etc/supervisor/conf.d

# Create supervisor configuration to run both dbus and avahi-daemon
RUN echo '[supervisord]' > /etc/supervisor/conf.d/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'logfile=/var/log/supervisor/supervisord.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'pidfile=/var/run/supervisord.pid' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:dbus]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=/usr/bin/dbus-daemon --system --nofork --nopidfile --address=unix:path=/run/dbus/system_bus_socket' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startretries=3' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startsecs=1' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:avahi]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=/usr/sbin/avahi-daemon --no-drop-root --no-chroot' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startretries=5' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startsecs=2' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisor/conf.d/supervisord.conf

# Create log directory
RUN mkdir -p /var/log/supervisor

# Create startup script that ensures /run/dbus exists at runtime
RUN echo '#!/bin/bash' > /start.sh && \
    echo 'mkdir -p /run/dbus' >> /start.sh && \
    echo 'chmod 755 /run/dbus' >> /start.sh && \
    echo 'exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf' >> /start.sh && \
    chmod +x /start.sh

# Expose mDNS port (UDP 5353)
EXPOSE 5353/udp

# Start supervisor which will manage dbus and avahi-daemon
CMD ["/start.sh"]
