# Network Access Guide

This guide explains how to access Shatter from devices on your local network.

## How It Works

Shatter's frontend is designed to automatically detect and connect to the backend API based on the hostname you use to access it. This means:

- **Access from the same machine**: `http://localhost` connects to `http://localhost:8000/api`
- **Access from another device**: `http://192.168.1.144` connects to `http://192.168.1.144:8000/api`

The frontend dynamically builds the API URL using `window.location.hostname`, so it works from any device without reconfiguration.

## Accessing from Other Devices

### 1. Find Your Server's IP Address

On the machine running Shatter (macOS):

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}'
```

Example output: `192.168.1.144`

On Linux:
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

On Windows:
```bash
ipconfig
```

### 2. Access from Your Phone/Tablet/Other Computer

Open a browser on the device and navigate to:

```
http://YOUR_SERVER_IP
```

For example:
```
http://192.168.1.144
```

The frontend will automatically connect to the backend at `http://192.168.1.144:8000/api` and establish a WebSocket connection to `ws://192.168.1.144:8000/api/ws`.

## Firewall Configuration

### macOS

Allow incoming connections on ports 80 and 8000:

```bash
# Check firewall status
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Allow Docker
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /Applications/Docker.app/Contents/MacOS/com.docker.backend --unblock
```

### Linux (UFW)

```bash
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp
```

### Windows Firewall

Add inbound rules for ports 80 and 8000 through Windows Defender Firewall.

## Network Requirements

### Same Network
- All devices must be on the same local network (e.g., same WiFi)
- Server and client devices must be able to communicate (no AP isolation)

### Port Requirements
- **Port 80**: Frontend (Nginx)
- **Port 8000**: Backend API + WebSocket
- **Port 5432**: PostgreSQL (internal only, not exposed)
- **Port 6379**: Redis (internal only, not exposed)

## Troubleshooting

### Can't Connect from Another Device

1. **Verify the server is accessible**:
   ```bash
   # From another device
   ping 192.168.1.144
   curl http://192.168.1.144:8000/health
   ```

2. **Check firewall**:
   - Ensure ports 80 and 8000 are not blocked
   - Temporarily disable firewall to test

3. **Check Docker is exposing ports**:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```
   Should show `0.0.0.0:80->80/tcp` and `0.0.0.0:8000->8000/tcp`

4. **Check network isolation**:
   - Some WiFi routers have "AP Isolation" enabled
   - Guest networks often block device-to-device communication
   - Try connecting from a device on the main network

### WebSocket Won't Connect

1. **Check browser console** for WebSocket errors
2. **Verify backend is running**:
   ```bash
   curl http://YOUR_IP:8000/health
   ```
3. **Check CORS** is allowing your origin (should allow `*` in production config)

### API Requests Failing

Check the browser's Network tab for CORS errors. The backend is configured to allow all origins (`*`) for internal network use.

## CORS Configuration

The backend's CORS policy (in [backend/app/core/config.py](backend/app/core/config.py)) is set to:

```python
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",      # Development - Vite/React
    "http://localhost:5173",      # Development - Vite alternative port
    "http://localhost",           # Production - Nginx on port 80
    "http://localhost:80",        # Production - Nginx explicit port
    "*",                          # Allow all origins
]
```

The wildcard (`*`) allows access from any IP address on your network. **Note**: This is suitable for internal networks but should be restricted for public deployments.

## Security Considerations

### Internal Network Only
The current configuration with CORS wildcard (`*`) is designed for:
- Shop floor networks isolated from the internet
- Home networks
- Development environments

### For Public Deployment
If exposing to the internet, you should:
1. Remove the CORS wildcard (`*`)
2. Add specific allowed origins
3. Enable HTTPS/TLS
4. Enable authentication (`ENABLE_AUTH=true`)
5. Use a reverse proxy (Nginx/Traefik) with SSL certificates

## Dynamic API Configuration

The frontend's API configuration ([frontend/src/config/api.ts](frontend/src/config/api.ts)) uses this logic:

```typescript
// Production fallback - use window.location to build URL dynamically
const protocol = window.location.protocol;  // http: or https:
const hostname = window.location.hostname;  // e.g., 192.168.1.144
const apiPort = '8000';

return `${protocol}//${hostname}:${apiPort}`;
```

This means:
- No hardcoded IP addresses
- Works from localhost, local IP, or domain name
- Automatically adapts to how you access the frontend
- WebSocket protocol (ws/wss) matches HTTP protocol automatically
