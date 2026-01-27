# Raspberry Pi Image Build

This directory contains the CustomPiOS configuration for building a pre-configured Raspberry Pi image with Shatter CNC Platform.

## Overview

The CustomPiOS build process creates a Raspberry Pi OS Lite image that includes:
- Docker Engine and Docker Compose pre-installed
- Pre-pulled Docker images (if authenticated)
- Shatter application files and configuration
- Avahi mDNS service discovery
- First-boot setup wizard

## Prerequisites

- CustomPiOS tool installed
- Docker (for building CustomPiOS images)
- GitHub Container Registry access token (for pulling private images)
- Sufficient disk space (8GB+ for image build)

## Building the Image

### Install CustomPiOS

```bash
# Using pip
pip3 install custompios

# Or from source
git clone https://github.com/guysoft/CustomPiOS.git
cd CustomPiOS
pip3 install .
```

### Build Configuration

The build process uses `config.yaml` which defines:
- Base image: Raspberry Pi OS Lite (64-bit)
- Modules to run during build
- Packages to install
- User configuration

### Build Process

**Basic build (public images only):**

```bash
cd pi-image
custompios --config config.yaml --output ../shatter-nc.img
```

**Build with GitHub Container Registry authentication:**

```bash
# Authenticate with GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Set environment variables for image pulling
export GITHUB_OWNER=roblockwood
export GITHUB_REPO=shatter-nc
export IMAGE_TAG=latest

# Build image
cd pi-image
custompios --config config.yaml --output ../shatter-nc.img
```

**Note:** CustomPiOS may require running in a specific environment. Check the [CustomPiOS documentation](https://github.com/guysoft/CustomPiOS) for detailed build instructions.

### Post-Build

After building the image:

1. **Compress the image:**
   ```bash
   xz -9 shatter-nc.img
   ```

2. **Generate checksums:**
   ```bash
   sha256sum shatter-nc.img.xz > shatter-nc-checksums.txt
   ```

3. **Test the image:**
   - Flash to SD card
   - Boot Raspberry Pi
   - Verify first-boot wizard runs
   - Test service startup

## Directory Structure

```
pi-image/
├── config.yaml              # Main CustomPiOS configuration
├── modules/                  # CustomPiOS modules
│   ├── 01-docker/           # Docker installation
│   │   ├── 00-run.sh        # Install Docker Engine and Compose
│   │   └── 01-pull-images.sh # Pre-pull Docker images
│   ├── 02-shatter/          # Application setup
│   │   └── 00-run.sh        # Create directories and copy files
│   ├── 03-avahi/            # Avahi configuration
│   │   ├── 00-run.sh        # Install and configure Avahi
│   │   └── files/
│   │       └── shatter.service # Avahi service file
│   └── 04-firstboot/        # First-boot wizard setup
│       └── 00-run.sh         # Create first-boot service
└── files/                    # Files copied to image
    ├── docker-compose.prod.yml # Production Docker Compose config
    ├── shatter.service       # Systemd service file
    └── setup-wizard.sh       # First-boot setup wizard
```

## Module Execution Order

Modules run in numerical order:
1. `01-docker` - Installs Docker and pre-pulls images
2. `02-shatter` - Sets up application files and directories
3. `03-avahi` - Configures Avahi for mDNS
4. `04-firstboot` - Sets up first-boot wizard

## Customization

### Changing Base Image

Edit `config.yaml`:
```yaml
base_image: "raspios_lite_arm64"  # Change to desired base image
```

### Adding Packages

Edit `config.yaml`:
```yaml
packages:
  - "package-name"
```

### Modifying Modules

Each module directory contains scripts that run during image build. Modify scripts as needed, but be aware that changes may affect the build process.

## Troubleshooting

### Build Fails

- Check CustomPiOS version compatibility
- Verify base image is available
- Check disk space
- Review module script syntax

### Images Not Pre-pulled

- Verify GitHub Container Registry authentication
- Check network connectivity during build
- Images will be pulled on first boot if not pre-pulled

### First-Boot Wizard Doesn't Run

- Check systemd service: `systemctl status shatter-setup.service`
- Verify setup wizard script exists: `/opt/shatter/setup-wizard.sh`
- Check logs: `journalctl -u shatter-setup.service`

## Automated Builds

GitHub Actions workflow (`.github/workflows/build-pi-image.yml`) automatically builds images on version tags. See the workflow file for details.

## Related Documentation

- [PI_DEPLOYMENT.md](../docs/PI_DEPLOYMENT.md) - Deployment guide for end users
- [DOCKER_DEPLOYMENT.md](../docs/DOCKER_DEPLOYMENT.md) - Docker configuration details
- [CustomPiOS Documentation](https://github.com/guysoft/CustomPiOS) - CustomPiOS tool documentation
