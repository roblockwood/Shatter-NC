FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Avahi daemon and utilities (no dbus needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    avahi-daemon \
    avahi-utils \
    && rm -rf /var/lib/apt/lists/*

# Create directory for service files
RUN mkdir -p /etc/avahi/services

# Configure avahi-daemon to run without dbus
# This avoids the dbus socket issues in containers
RUN echo '[server]' > /etc/avahi/avahi-daemon.conf && \
    echo 'enable-dbus=no' >> /etc/avahi/avahi-daemon.conf && \
    echo 'host-name=shatter' >> /etc/avahi/avahi-daemon.conf && \
    echo 'domain-name=local' >> /etc/avahi/avahi-daemon.conf && \
    echo '' >> /etc/avahi/avahi-daemon.conf && \
    echo '[wide-area]' >> /etc/avahi/avahi-daemon.conf && \
    echo 'enable-wide-area=yes' >> /etc/avahi/avahi-daemon.conf && \
    echo '' >> /etc/avahi/avahi-daemon.conf && \
    echo '[publish]' >> /etc/avahi/avahi-daemon.conf && \
    echo 'disable-publishing=no' >> /etc/avahi/avahi-daemon.conf

# Expose mDNS port (UDP 5353)
EXPOSE 5353/udp

# Run avahi-daemon directly (no dbus needed with enable-dbus=no)
CMD ["/usr/sbin/avahi-daemon", "--no-drop-root", "--no-chroot", "--no-rlimits"]
