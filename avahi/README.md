# Avahi mDNS Service Discovery

This directory contains configuration for Avahi, which enables zero-configuration network service discovery for Shatter. When Avahi is running, the service will be discoverable on your local network as `shatter.local`.

## What is Avahi?

Avahi is a system for service discovery on local networks using mDNS (multicast DNS) and DNS-SD (DNS Service Discovery). It's the Linux implementation of Apple's Bonjour protocol.

## Benefits

- **Zero Configuration**: No need to know the IP address - just visit `http://shatter.local`
- **Network Discovery**: Automatically discoverable by other devices on the local network
- **Cross-Platform**: Works with macOS (Bonjour), Windows (mDNS), and Linux

## Setup Options

### Option 1: Host-Based Setup (Recommended for Docker)

If you're running Shatter in Docker, run Avahi on the host machine:

1. **Install Avahi** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install -y avahi-daemon avahi-utils
   
   # macOS (via Homebrew)
   brew install avahi
   
   # Arch Linux
   sudo pacman -S avahi
   ```

2. **Copy the service file**:
   ```bash
   sudo cp avahi/shatter.service /etc/avahi/services/shatter.service
   ```

3. **Restart Avahi**:
   ```bash
   # Linux (systemd)
   sudo systemctl restart avahi-daemon
   sudo systemctl enable avahi-daemon
   
   # macOS
   brew services restart avahi
   ```

4. **Verify it's running**:
   ```bash
   avahi-browse -a  # Should show _http._tcp services
   ```

### Option 2: Docker Container Setup

For containerized deployments, the Avahi service is already included in your `docker-compose.yml` files. It uses a custom Dockerfile that builds an Avahi image:

```yaml
avahi:
  build:
    context: ./avahi
    dockerfile: Dockerfile
  container_name: shatter-avahi
  network_mode: host  # Required for mDNS to work
  volumes:
    - ./avahi/shatter.service:/etc/avahi/services/shatter.service:ro
  restart: unless-stopped
```

**Note**: `network_mode: host` is required because mDNS uses multicast, which doesn't work through Docker's bridge network.

**macOS Docker Desktop Limitation**: Docker Desktop on macOS runs containers in a Linux VM, and mDNS multicast may not bridge properly to the host network. If you're on macOS and Avahi doesn't work in Docker, consider:
1. Running Avahi directly on macOS (Option 1)
2. Using Docker Desktop's host networking (may require Docker Desktop settings)
3. Testing on a Linux host where host networking works natively

### Option 3: Custom Hostname

To use a custom hostname (e.g., `shatter-cnc.local`), you can:

1. Edit `/etc/avahi/avahi-daemon.conf`:
   ```
   [server]
   host-name=shatter-cnc
   ```

2. Or set it via environment variable in Docker:
   ```yaml
   avahi:
     environment:
       - AVAHI_HOSTNAME=shatter-cnc
   ```

## Testing

### Check Service Discovery

```bash
# Browse all services
avahi-browse -a

# Browse HTTP services specifically
avahi-browse _http._tcp

# Resolve the hostname
avahi-resolve -n shatter.local
```

### Access the Service

Once Avahi is running, you can access Shatter at:
- `http://shatter.local` (from any device on the network)
- `http://shatter.local:80` (explicit port)

### Troubleshooting

**Service not discoverable:**
- Ensure Avahi daemon is running: `systemctl status avahi-daemon`
- Check firewall allows mDNS (UDP port 5353)
- Verify service file is in `/etc/avahi/services/`
- Check logs: `journalctl -u avahi-daemon -f`

**Can't resolve hostname:**
- Try `ping shatter.local` to verify mDNS resolution
- On some systems, you may need `.local` domain resolution enabled
- macOS: Should work out of the box
- Linux: May need `nss-mdns` package
- Windows: Requires Bonjour Print Services or mDNS support

**Port conflicts:**
- If port 80 is already in use, edit `shatter.service` and change the `<port>` value
- Update nginx/frontend configuration to match

## Service File Format

The `shatter.service` file uses the DNS-SD service definition format:

- `<name>`: Display name for the service
- `<type>`: Service type (`_http._tcp` for HTTP)
- `<port>`: Port number (80 for HTTP)
- `<txt-record>`: Additional metadata (optional)

## Security Considerations

- Avahi only works on local networks (multicast doesn't route)
- The service is only discoverable on the same subnet
- No authentication is provided by Avahi itself
- Ensure your application has proper authentication if needed

## References

- [Avahi Documentation](https://avahi.org/)
- [DNS-SD Specification](https://www.dns-sd.org/)
- [mDNS Specification (RFC 6762)](https://tools.ietf.org/html/rfc6762)
