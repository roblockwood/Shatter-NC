# Raspberry Pi Deployment Guide

This guide covers deploying the Shatter CNC Platform on Raspberry Pi using either:
1. **Pre-built Raspberry Pi image** (recommended for new installations)
2. **Manual installation script** (for existing Raspberry Pi systems)

## Table of Contents

- [Overview](#overview)
- [Pre-built Image Deployment](#pre-built-image-deployment)
- [Manual Installation](#manual-installation)
- [First-Boot Setup Wizard](#first-boot-setup-wizard)
- [Service Management](#service-management)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)
- [Backup and Restore](#backup-and-restore)

---

## Overview

The Shatter CNC Platform can be deployed on Raspberry Pi in two ways:

| Method | Best For | Complexity |
|--------|----------|------------|
| **Pre-built Image** | New installations, minimal setup | Easy - flash and boot |
| **Manual Installation** | Existing Pi systems, custom configurations | Moderate - run script |

Both methods result in the same deployment:
- Docker Compose stack running all services
- Auto-start on boot via systemd
- Accessible via `http://shatter.local` (mDNS)
- Persistent data storage

**System Requirements:**
- Raspberry Pi 4 or newer (recommended)
- 4GB+ RAM (8GB recommended)
- 32GB+ SD card (64GB recommended)
- Network connection (WiFi or Ethernet)

---

## Pre-built Image Deployment

### Step 1: Download the Image

Download the latest Raspberry Pi image from [GitHub Releases](https://github.com/roblockwood/shatter-nc/releases):

- `shatter-nc-vX.X.X.img.xz` - Compressed image file
- `shatter-nc-checksums.txt` - SHA256 checksums

### Step 2: Verify Checksum (Optional but Recommended)

```bash
# Download checksums
wget https://github.com/roblockwood/shatter-nc/releases/download/vX.X.X/shatter-nc-checksums.txt

# Verify image integrity
sha256sum -c shatter-nc-checksums.txt
```

### Step 3: Extract Image

```bash
# Extract compressed image
xz -d shatter-nc-vX.X.X.img.xz
# or
unxz shatter-nc-vX.X.X.img.xz
```

### Step 4: Flash to SD Card

**Using Raspberry Pi Imager (Recommended):**

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Open Raspberry Pi Imager
3. Click "Choose OS" → "Use custom image"
4. Select the extracted `.img` file
5. Click "Choose Storage" → Select your SD card
6. Click "Write" and wait for completion

**Using Command Line:**

```bash
# Identify SD card device (be careful - this will erase the device!)
lsblk

# Flash image (replace /dev/sdX with your SD card device)
sudo dd if=shatter-nc-vX.X.X.img of=/dev/sdX bs=4M status=progress
sudo sync
```

### Step 5: Boot Raspberry Pi

1. Insert SD card into Raspberry Pi
2. Connect power supply
3. Connect to network (Ethernet or WiFi via first-boot wizard)
4. Wait for first boot (may take 2-3 minutes)

### Step 6: Complete First-Boot Setup

On first boot, the setup wizard will run automatically. See [First-Boot Setup Wizard](#first-boot-setup-wizard) for details.

### Step 7: Access the Web Interface

After setup completes, access Shatter at:
- `http://shatter.local` (mDNS - recommended)
- `http://<pi-ip-address>` (direct IP)

---

## Manual Installation

For users who already have a Raspberry Pi running Raspberry Pi OS, you can install Shatter using the automated installation script.

### Prerequisites

- Raspberry Pi running Raspberry Pi OS (32-bit or 64-bit)
- Internet connection
- User account with sudo privileges

### Installation Steps

**Option 1: One-Line Install**

```bash
curl -fsSL https://raw.githubusercontent.com/roblockwood/shatter-nc/main/scripts/install-shatter.sh | bash
```

**Option 2: Download and Run**

```bash
# Download script
wget https://raw.githubusercontent.com/roblockwood/shatter-nc/main/scripts/install-shatter.sh

# Make executable
chmod +x install-shatter.sh

# Run installation
./install-shatter.sh
```

### What the Script Does

1. **Checks prerequisites** - Verifies Docker and Docker Compose
2. **Installs Docker** - If not already installed
3. **Installs Docker Compose** - If not already installed
4. **Clones repository** - Downloads Shatter files to `/opt/shatter`
5. **Configures Avahi** - Sets up mDNS for `shatter.local` discovery
6. **Runs setup wizard** - Configures WiFi and generates credentials
7. **Installs systemd service** - Enables auto-start on boot
8. **Pulls Docker images** - Downloads required container images
9. **Starts services** - Launches the Docker Compose stack

### Post-Installation

After installation completes:

1. **Save your credentials** - The script displays generated passwords
2. **Access the web interface** - Navigate to `http://shatter.local`
3. **Configure machines** - Add your CNC machines via the web UI

---

## First-Boot Setup Wizard

The first-boot setup wizard runs automatically on first boot (pre-built image) or during manual installation.

### WiFi Configuration

The wizard will prompt you to configure WiFi:

1. **Scan for networks** - View available WiFi networks
2. **Enter SSID** - Type your WiFi network name
3. **Enter password** - Type your WiFi password (hidden input)
4. **Network restarts** - WiFi configuration is applied

**Note:** If you skip WiFi configuration, you can configure it later using:
```bash
sudo raspi-config
# Navigate to: System Options → Wireless LAN
```

### Credential Generation

The wizard automatically generates secure credentials:

- **POSTGRES_PASSWORD** - 32-character random password for PostgreSQL
- **REDIS_PASSWORD** - 32-character random password for Redis
- **SECRET_KEY** - 64-character hex string for application security

**IMPORTANT:** Save these credentials! They are displayed during setup and saved to `/opt/shatter/.env`.

### Configuration File

The wizard creates `/opt/shatter/.env` with all configuration:

```bash
# View configuration (requires sudo)
sudo cat /opt/shatter/.env
```

**Security:** The `.env` file has restricted permissions (600) and should not be shared.

---

## Service Management

### View Service Status

```bash
# Systemd service status
sudo systemctl status shatter.service

# Docker Compose status
cd /opt/shatter
docker compose -f docker-compose.prod.yml ps
```

### View Logs

```bash
# Systemd service logs
sudo journalctl -u shatter.service -f

# Individual container logs
cd /opt/shatter
docker compose -f docker-compose.prod.yml logs -f

# Specific service logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

### Start/Stop Services

```bash
# Start services
sudo systemctl start shatter.service

# Stop services
sudo systemctl stop shatter.service

# Restart services
sudo systemctl restart shatter.service

# Or use Docker Compose directly
cd /opt/shatter
docker compose -f docker-compose.prod.yml up -d    # Start
docker compose -f docker-compose.prod.yml down     # Stop
docker compose -f docker-compose.prod.yml restart  # Restart
```

### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot
sudo systemctl enable shatter.service

# Disable auto-start
sudo systemctl disable shatter.service
```

---

## Updating

### Update Docker Images

To update to the latest version of Shatter:

```bash
cd /opt/shatter

# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Restart services with new images
docker compose -f docker-compose.prod.yml up -d
```

### Update Pre-built Image

For pre-built image installations:

1. **Backup your data** - See [Backup and Restore](#backup-and-restore)
2. **Download new image** - Get latest from GitHub Releases
3. **Flash new image** - Follow [Pre-built Image Deployment](#pre-built-image-deployment) steps
4. **Restore data** - Restore your backup after first boot

### Update Manual Installation

For manual installations:

```bash
cd /opt/shatter

# Update repository
git pull

# Pull latest Docker images
docker compose -f docker-compose.prod.yml pull

# Restart services
docker compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting

### Services Won't Start

**Check Docker:**

```bash
# Verify Docker is running
sudo systemctl status docker

# Start Docker if stopped
sudo systemctl start docker
```

**Check logs:**

```bash
sudo journalctl -u shatter.service -n 50
cd /opt/shatter
docker compose -f docker-compose.prod.yml logs
```

### Can't Access Web Interface

**Check service status:**

```bash
sudo systemctl status shatter.service
cd /opt/shatter
docker compose -f docker-compose.prod.yml ps
```

**Check network:**

```bash
# Verify Pi is on network
ip addr show

# Test mDNS resolution
ping shatter.local

# Try direct IP
curl http://$(hostname -I | awk '{print $1}')
```

**Check firewall:**

```bash
# Raspberry Pi OS typically doesn't have firewall enabled
# But verify ports are open
sudo netstat -tlnp | grep -E ':(80|8000)'
```

### WiFi Not Connecting

**Check WiFi configuration:**

```bash
# View WiFi status
iwconfig

# Check wpa_supplicant config
sudo cat /etc/wpa_supplicant/wpa_supplicant.conf

# Restart networking
sudo systemctl restart networking
```

**Reconfigure WiFi:**

```bash
sudo raspi-config
# Navigate to: System Options → Wireless LAN
```

### Database Connection Errors

**Check PostgreSQL container:**

```bash
cd /opt/shatter
docker compose -f docker-compose.prod.yml ps postgres
docker compose -f docker-compose.prod.yml logs postgres
```

**Verify credentials:**

```bash
# Check .env file
sudo cat /opt/shatter/.env | grep POSTGRES
```

**Restart database:**

```bash
cd /opt/shatter
docker compose -f docker-compose.prod.yml restart postgres
```

### Out of Disk Space

**Check disk usage:**

```bash
df -h
docker system df
```

**Clean up Docker:**

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (WARNING: may delete data)
docker volume prune
```

**Clean up system:**

```bash
# Remove old logs
sudo journalctl --vacuum-time=7d

# Clean package cache
sudo apt-get clean
```

---

## Backup and Restore

### Backup Data

**Backup Docker volumes:**

```bash
cd /opt/shatter

# Stop services
docker compose -f docker-compose.prod.yml down

# Backup PostgreSQL data
docker run --rm \
  -v shatter_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz -C /data .

# Backup Redis data
docker run --rm \
  -v shatter_redis_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis_backup_$(date +%Y%m%d).tar.gz -C /data .

# Backup configuration
cp /opt/shatter/.env /opt/shatter/.env.backup

# Restart services
docker compose -f docker-compose.prod.yml up -d
```

**Backup entire SD card:**

```bash
# On another computer, create image backup
sudo dd if=/dev/sdX of=shatter-backup-$(date +%Y%m%d).img bs=4M status=progress
```

### Restore Data

**Restore Docker volumes:**

```bash
cd /opt/shatter

# Stop services
docker compose -f docker-compose.prod.yml down

# Restore PostgreSQL
docker run --rm \
  -v shatter_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup_YYYYMMDD.tar.gz -C /data

# Restore Redis
docker run --rm \
  -v shatter_redis_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/redis_backup_YYYYMMDD.tar.gz -C /data

# Restore configuration
cp /opt/shatter/.env.backup /opt/shatter/.env

# Restart services
docker compose -f docker-compose.prod.yml up -d
```

---

## Additional Resources

- [Docker Deployment Guide](DOCKER_DEPLOYMENT.md) - Detailed Docker configuration
- [Environment Variables](ENVIRONMENT_VARIABLES.md) - Configuration reference
- [API Reference](API_REFERENCE.md) - REST API documentation
- [GitHub Repository](https://github.com/roblockwood/shatter-nc) - Source code and issues

---

## Quick Reference

**Essential Commands:**

```bash
# Service management
sudo systemctl status shatter.service
sudo systemctl restart shatter.service
sudo journalctl -u shatter.service -f

# Docker Compose
cd /opt/shatter
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml restart

# Access web interface
http://shatter.local
http://$(hostname -I | awk '{print $1}')
```

**File Locations:**

- Configuration: `/opt/shatter/.env`
- Docker Compose: `/opt/shatter/docker-compose.prod.yml`
- Systemd Service: `/etc/systemd/system/shatter.service`
- Logs: `sudo journalctl -u shatter.service`
