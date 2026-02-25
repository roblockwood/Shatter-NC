# Environment Variables Reference

## Table of Contents

- [Overview](#overview)
- [Configuration Files](#configuration-files)
- [Variable Categories](#variable-categories)
  - [Application Configuration](#application-configuration)
  - [Server Configuration](#server-configuration)
  - [Database Configuration](#database-configuration)
  - [CNC Polling Configuration](#cnc-polling-configuration)
  - [Security Configuration](#security-configuration)
  - [CORS Configuration](#cors-configuration)
  - [Frontend Configuration](#frontend-configuration)
  - [Docker Compose Configuration](#docker-compose-configuration)
- [Development vs Production](#development-vs-production)
- [Security Best Practices](#security-best-practices)
- [Validation](#validation)
- [Accessing Settings in Code](#accessing-settings-in-code)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Shatter CNC platform uses environment variables for configuration, following the [12-Factor App methodology](https://12factor.net/config). This allows the same codebase to run in different environments (development, staging, production) with different configurations.

**Configuration System:**
- **Backend:** Pydantic Settings for type-safe configuration
- **Frontend:** Vite environment variables (prefixed with `VITE_`)
- **Storage:** `.env` files (not committed to git)
- **Examples:** `.env.example` and `.env.production.example` (committed to git)

**Location:** [config.py](../backend/app/core/config.py)

---

## Configuration Files

| File | Purpose | Committed to Git | Used By |
|------|---------|------------------|---------|
| `.env.example` | Development configuration template | ✅ Yes | Developers (copy to `.env`) |
| `.env.production.example` | Production configuration template | ✅ Yes | Operators (copy to `.env.production`) |
| `.env` | Active development configuration | ❌ No (.gitignore) | Docker Compose, Local dev |
| `.env.production` | Active production configuration | ❌ No (.gitignore) | Docker Compose production |
| `backend/.env` | Backend-specific overrides | ❌ No (.gitignore) | Local backend development |

**Setup Instructions:**

**Development:**
```bash
cp .env.example .env
# Edit .env with your local settings
docker-compose up
```

**Production:**
```bash
cp .env.production.example .env.production
# Edit .env.production with secure values
docker-compose -f docker-compose.prod.yml up -d
```

---

## Variable Categories

### Application Configuration

Variables controlling application behavior and metadata.

#### APP_NAME

**Purpose:** Application name displayed in logs and UI

**Type:** String

**Default:** `"Shatter"`

**Example:**
```bash
APP_NAME=Shatter
```

**Used In:**
- Application logs
- Frontend header (hardcoded in UI currently)
- Error messages

---

#### APP_VERSION

**Purpose:** Application version number (semantic versioning)

**Type:** String

**Default:** `"0.1.0"`

**Example:**
```bash
APP_VERSION=0.1.0
```

**Used In:**
- Startup logs
- API `/health` endpoint (future)
- About page (future)

---

#### DEBUG

**Purpose:** Enable debug mode with verbose logging and error details

**Type:** Boolean (`true` or `false`)

**Default:** `false`

**Example:**
```bash
DEBUG=true  # Development only
```

**Effects:**
- More verbose logging
- Stack traces in API responses
- Disables some optimizations

**⚠️ SECURITY WARNING:** Never enable in production (exposes sensitive information)

---

#### LOG_LEVEL

**Purpose:** Minimum log level for application logs

**Type:** String (case-insensitive)

**Valid Values:**
- `DEBUG` - All messages (very verbose)
- `INFO` - Informational messages and above (default development)
- `WARNING` - Warnings and errors only (default production)
- `ERROR` - Errors only
- `CRITICAL` - Critical errors only

**Default:** `"INFO"`

**Example:**
```bash
# Development
LOG_LEVEL=INFO

# Production
LOG_LEVEL=WARNING
```

**Used By:**
- Python logging system
- FastAPI log output
- Background services (PollingService, etc.)

---

### Server Configuration

Variables controlling the backend HTTP server.

#### BACKEND_HOST

**Purpose:** Host address for backend to bind to

**Type:** String (IP address or hostname)

**Default:** `"0.0.0.0"`

**Example:**
```bash
# Bind to all interfaces (Docker, production)
BACKEND_HOST=0.0.0.0

# Bind to localhost only (local development)
BACKEND_HOST=127.0.0.1
```

**Common Values:**
- `0.0.0.0` - All network interfaces (Docker, allows external access)
- `127.0.0.1` - Localhost only (prevents external access)

**⚠️ SECURITY NOTE:** Use `0.0.0.0` in Docker, consider `127.0.0.1` for local dev if you don't need network access

---

#### BACKEND_PORT

**Purpose:** Port number for backend HTTP server

**Type:** Integer (1-65535)

**Default:** `8000`

**Example:**
```bash
BACKEND_PORT=8000
```

**Used By:**
- Uvicorn server binding
- Frontend API_BASE_URL construction
- Docker port mapping

**Common Ports:**
- `8000` - Default (development and production)
- `8080` - Alternative if 8000 is in use

---

### Database Configuration

PostgreSQL database connection settings.

#### POSTGRES_HOST

**Purpose:** PostgreSQL server hostname or IP address

**Type:** String

**Default:** `"localhost"`

**Example:**
```bash
# Docker Compose (service name)
POSTGRES_HOST=postgres

# Local development
POSTGRES_HOST=localhost

# Remote server
POSTGRES_HOST=192.168.1.50
```

---

#### POSTGRES_PORT

**Purpose:** PostgreSQL server port

**Type:** Integer

**Default:** `5432`

**Example:**
```bash
POSTGRES_PORT=5432
```

**Note:** Rarely needs to be changed unless PostgreSQL is running on a custom port

---

#### POSTGRES_DB

**Purpose:** Database name to connect to

**Type:** String

**Default:** `"shatter"`

**Example:**
```bash
POSTGRES_DB=shatter
```

**Naming Convention:** Use lowercase, underscores (not hyphens)

---

#### POSTGRES_USER

**Purpose:** PostgreSQL username for authentication

**Type:** String

**Default:** `"shatter_user"`

**Example:**
```bash
POSTGRES_USER=shatter_user
```

**Security:** Use a dedicated database user (not `postgres` superuser)

---

#### POSTGRES_PASSWORD

**Purpose:** PostgreSQL password for authentication

**Type:** String

**Default:** `"changeme"`

**Example:**
```bash
# Development (simple password)
POSTGRES_PASSWORD=changeme_secure_password

# Production (strong password)
POSTGRES_PASSWORD=xK9mP2nQ7vB4wE8tR6yU5iO3pL1sD0fG
```

**⚠️ SECURITY CRITICAL:**
- **Development:** Use a simple but unique password
- **Production:** Use a strong, randomly generated password (32+ characters)
- **Generate secure password:**
  ```bash
  openssl rand -base64 32
  ```

**Constructed Property:**

The database URL is automatically constructed from these variables:

```python
database_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
# Example: postgresql://shatter_user:changeme@localhost:5432/shatter
```

---

### CNC Polling Configuration

Settings for the background polling service.

#### DEFAULT_POLL_INTERVAL

**Purpose:** Default interval (in seconds) for polling CNC machines

**Type:** Integer (1-300)

**Default:** `5`

**Example:**
```bash
# Default: Poll every 5 seconds
DEFAULT_POLL_INTERVAL=5

# More frequent: Poll every 2 seconds (higher load)
DEFAULT_POLL_INTERVAL=2

# Less frequent: Poll every 10 seconds (lower load)
DEFAULT_POLL_INTERVAL=10
```

**Used By:**
- PollingService default interval
- New machine creation (unless overridden per-machine)

**Considerations:**
- **Lower values (1-3s):** Near-real-time updates, higher network/CPU load
- **Recommended (5-10s):** Good balance of freshness and performance
- **Higher values (30-60s):** Lower load, acceptable for monitoring applications

**Per-Machine Override:**

Each machine can have a custom poll interval set in the database. This setting is just the default for new machines.

**Location:** [config.py:31](../backend/app/core/config.py#L31)

---

### Security Configuration

Security-related settings (optional, future use).

#### SECRET_KEY

**Purpose:** Secret key for cryptographic operations (signing, encryption)

**Type:** String (optional)

**Default:** None

**Example:**
```bash
# Production (generate with: openssl rand -hex 32)
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

**⚠️ SECURITY CRITICAL:**
- **Must be kept secret** (never commit to git)
- **Must be random and unique** per deployment
- **Generate with:**
  ```bash
  openssl rand -hex 32
  # Output: a1b2c3d4e5f6...
  ```

**Future Use:**
- JWT token signing
- Session cookies
- Password reset tokens
- API key generation

**Current Status:** Not yet implemented (authentication disabled)

---

#### ENABLE_AUTH

**Purpose:** Enable authentication and authorization

**Type:** Boolean (`true` or `false`)

**Default:** `false`

**Example:**
```bash
# Development (auth disabled)
ENABLE_AUTH=false

# Production (auth enabled)
ENABLE_AUTH=true
```

**Current Status:** Not yet implemented (authentication is disabled regardless of this setting)

**Future Implementation:**
- User login/logout
- API token authentication
- Role-based access control (RBAC)
- Machine access permissions

---

### CORS Configuration

Cross-Origin Resource Sharing settings.

#### CORS_ORIGINS

**Purpose:** List of allowed origins for CORS requests

**Type:** List of strings (comma-separated in .env, list in Python)

**Default:**
```python
[
    "http://localhost:3000",      # Vite dev server
    "http://localhost:5173",      # Vite alternative port
    "http://localhost",           # Production Nginx
    "http://localhost:80",        # Production Nginx explicit
    "*",                          # Allow all (development/internal only)
]
```

**Example (.env file):**
```bash
# NOT DIRECTLY CONFIGURABLE VIA .ENV
# Modify in config.py if needed
```

**Note:** CORS_ORIGINS is hardcoded in [config.py:38-44](../backend/app/core/config.py#L38-L44) and cannot be overridden via environment variables.

**To Customize:**

Edit `backend/app/core/config.py`:

```python
CORS_ORIGINS: list[str] = [
    "http://your-domain.com",
    "https://your-domain.com",
]
```

**Security Considerations:**
- `"*"` - Allows all origins (convenient for development, **dangerous in production**)
- Specific origins - More secure, only allows listed domains
- Include both `http://` and `https://` variants if using SSL

**Used By:**
- FastAPI CORS middleware
- Determines which frontend origins can access the API

---

### Frontend Configuration

Vite-specific environment variables (prefixed with `VITE_`).

#### VITE_API_URL

**Purpose:** Backend API base URL for frontend to connect to

**Type:** String (URL)

**Default:** Auto-detected based on browser hostname

**Example:**
```bash
# Development (explicit localhost)
VITE_API_URL=http://localhost:8000

# Production (specific IP)
VITE_API_URL=http://192.168.1.100:8000

# Production (domain)
VITE_API_URL=https://shatter.example.com/api
```

**Auto-Detection Behavior:**

If `VITE_API_URL` is **not set**, the frontend automatically constructs the API URL:

```typescript
// frontend/src/config/api.ts
export const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;
```

**Example Auto-Detection:**
- Browser at `http://localhost:3000` → API at `http://localhost:8000`
- Browser at `http://192.168.1.50:3000` → API at `http://192.168.1.50:8000`
- Browser at `http://factory-pc:3000` → API at `http://factory-pc:8000`

**When to Set Explicitly:**
- Backend on different host than frontend
- Backend on different port than 8000
- Using a reverse proxy or load balancer
- SSL/TLS with custom domain

**⚠️ IMPORTANT:** Vite environment variables are **embedded at build time**. If you change `VITE_API_URL`, you must rebuild the frontend.

```bash
cd frontend
npm run build
```

---

### Docker Compose Configuration

Variables specific to Docker Compose orchestration.

#### COMPOSE_PROJECT_NAME

**Purpose:** Docker Compose project name (prefixes container names)

**Type:** String

**Default:** `"shatter"`

**Example:**
```bash
COMPOSE_PROJECT_NAME=shatter
```

**Effect:**

Container names will be prefixed:
- `shatter-postgres-1`
- `shatter-backend-1`
- `shatter-frontend-1`

**Customization:**

Use a different name if running multiple instances on the same host:

```bash
# Production instance
COMPOSE_PROJECT_NAME=shatter_prod

# Development instance
COMPOSE_PROJECT_NAME=shatter_dev
```

---

## Development vs Production

### Development Configuration (.env.example)

**Focus:** Convenience, debugging, fast iteration

```bash
# Application
APP_NAME=Shatter
LOG_LEVEL=INFO         # Verbose logging
DEBUG=false            # Can enable for troubleshooting

# Database
POSTGRES_PASSWORD=changeme_secure_password  # Simple password

# Security
# SECRET_KEY not required (auth disabled)
# ENABLE_AUTH=false

# Frontend
# VITE_API_URL not set (auto-detection)
```

**Characteristics:**
- Simple passwords (still not "password", but not highly secure)
- INFO level logging (see what's happening)
- Auto-detected API URLs (works from any device on network)
- Debug mode available if needed

---

### Production Configuration (.env.production.example)

**Focus:** Security, performance, stability

```bash
# Application
APP_NAME=Shatter
LOG_LEVEL=WARNING      # Less verbose (warnings and errors only)
DEBUG=false            # Never enable in production

# Database
POSTGRES_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD  # Strong 32+ char password

# Security
SECRET_KEY=CHANGE_ME_TO_SECURE_SECRET_KEY  # openssl rand -hex 32
ENABLE_AUTH=true       # Enable when implemented

# Frontend
# VITE_API_URL only if needed (e.g., reverse proxy)
```

**Characteristics:**
- Strong randomly generated passwords
- WARNING level logging (reduce log volume)
- Secret key for future auth features
- Explicit API URLs if using reverse proxy

---

## Security Best Practices

### 1. Never Commit .env Files

**❌ Never commit:**
- `.env`
- `.env.production`
- `backend/.env`
- Any file containing real passwords/secrets

**✅ Always commit:**
- `.env.example`
- `.env.production.example`

**Verify .gitignore:**

```bash
# Check that .env is ignored
cat .gitignore | grep "\.env"
# Should see: .env
```

---

### 2. Generate Strong Passwords

**PostgreSQL Password:**

```bash
# Generate 32-character base64 password
openssl rand -base64 32
# Example output: xK9mP2nQ7vB4wE8tR6yU5iO3pL1sD0fG
```

**Secret Key:**

```bash
# Generate 64-character hex string
openssl rand -hex 32
# Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6...
```

---

### 3. Use Different Passwords Per Environment

**Don't reuse passwords between:**
- Development and production
- Different production deployments
- Database and other services
- Application secret keys

---

### 4. Rotate Passwords Regularly

**Recommended schedule:**
- **Development:** Rotate yearly or when team members leave
- **Production:** Rotate quarterly or after security incidents

**Rotation Process:**

1. Generate new password
2. Update `.env.production`
3. Restart affected services
4. Verify application still works
5. Update documentation/password manager

---

### 5. Restrict File Permissions

**Linux/Mac:**

```bash
# Restrict .env to owner read/write only
chmod 600 .env
chmod 600 .env.production

# Verify permissions
ls -la .env
# Should show: -rw------- (600)
```

**Docker:**

`.env` files are read by Docker Compose and passed to containers. Ensure host file permissions are restrictive.

---

### 6. Use Environment-Specific Domains

**Development:**
- `http://localhost:3000`
- `http://192.168.1.x:3000`

**Production:**
- `https://shatter.example.com` (SSL/TLS)
- `https://factory.company.com/shatter`

---

## Validation

### Pydantic Settings Validation

The backend uses Pydantic Settings for automatic validation:

**Type Validation:**

```python
BACKEND_PORT: int = 8000  # Must be integer
DEBUG: bool = False        # Must be boolean (true/false)
```

**Invalid values cause startup errors:**

```bash
# Invalid type
BACKEND_PORT=abc
# Error: value is not a valid integer

# Invalid boolean
DEBUG=yes
# Error: value is not a valid boolean (use true/false)
```

**Default Values:**

Missing environment variables use defaults from [config.py](../backend/app/core/config.py):

```python
class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"  # Default if not set
```

---

### Accessing Settings in Code

**Backend:**

```python
from app.core.config import settings

# Access individual settings
app_name = settings.APP_NAME
log_level = settings.LOG_LEVEL

# Use constructed properties
db_url = settings.database_url
```

**Frontend:**

```typescript
// Access Vite environment variables
const apiUrl = import.meta.env.VITE_API_URL;

// Type-safe access
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
}
```

---

## Troubleshooting

### Backend Won't Start - Database Connection Error

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**Possible Causes:**

1. **PostgreSQL not running**
   ```bash
   # Check if PostgreSQL container is running
   docker-compose ps

   # Should see postgres container with "Up" status
   ```

2. **Wrong POSTGRES_HOST**
   ```bash
   # Docker Compose: should be "postgres" (service name)
   POSTGRES_HOST=postgres

   # Local dev: should be "localhost"
   POSTGRES_HOST=localhost
   ```

3. **Wrong POSTGRES_PASSWORD**
   ```bash
   # Check password matches what was used to create database
   # If changed, may need to recreate database
   docker-compose down -v  # Warning: deletes data
   docker-compose up -d
   ```

---

### Frontend Can't Connect to Backend

**Error in browser console:**
```
Failed to fetch
GET http://localhost:8000/api/machines net::ERR_CONNECTION_REFUSED
```

**Possible Causes:**

1. **Backend not running**
   ```bash
   docker-compose ps
   # Check backend container is "Up"
   ```

2. **Wrong VITE_API_URL**
   ```bash
   # Check frontend config
   echo $VITE_API_URL

   # If accessing from another device, use device's hostname/IP
   VITE_API_URL=http://192.168.1.50:8000

   # Rebuild frontend after changing
   cd frontend && npm run build
   ```

3. **CORS not allowing origin**
   ```bash
   # Check browser console for CORS error
   # Add your origin to CORS_ORIGINS in config.py
   ```

---

### Environment Variable Not Taking Effect

**Symptom:** Changed variable but application still uses old value

**Causes:**

1. **Didn't restart application**
   ```bash
   docker-compose restart backend
   # or
   docker-compose down && docker-compose up -d
   ```

2. **Frontend variables embedded at build time**
   ```bash
   cd frontend
   npm run build  # Must rebuild after changing VITE_* variables
   ```

3. **Wrong .env file**
   ```bash
   # Make sure editing the right file
   ls -la .env*

   # Check which file Docker Compose uses
   docker-compose config  # Shows resolved config
   ```

4. **Extra spaces in .env**
   ```bash
   # Wrong (space after =)
   BACKEND_PORT= 8000

   # Correct (no spaces)
   BACKEND_PORT=8000
   ```

---

### Docker Compose Can't Find .env

**Error:**
```
WARNING: The POSTGRES_PASSWORD variable is not set. Defaulting to a blank string.
```

**Solutions:**

1. **Create .env file**
   ```bash
   cp .env.example .env
   ```

2. **Specify .env file explicitly**
   ```bash
   docker-compose --env-file .env.production up -d
   ```

3. **Check file location**
   ```bash
   # .env must be in same directory as docker-compose.yml
   ls -la .env
   ```

---

## Related Documentation

- [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) - Using environment variables in Docker
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - Development setup with environment variables
- [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md) - How settings are used in backend
- [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) - Frontend configuration

---

## Quick Reference

**Essential Variables:**

| Variable | Development | Production |
|----------|-------------|------------|
| `POSTGRES_PASSWORD` | `changeme_secure_password` | Strong 32+ char password |
| `LOG_LEVEL` | `INFO` | `WARNING` |
| `DEBUG` | `false` | `false` (never true) |
| `VITE_API_URL` | Auto-detect | Set if using reverse proxy |
| `SECRET_KEY` | Not required (no auth) | Random 64-char hex |

**Configuration Files:**

| File | Use Case |
|------|----------|
| `.env.example` | Copy to `.env` for development |
| `.env.production.example` | Copy to `.env.production` for production |
| `.env` | Active development config (not committed) |
| `.env.production` | Active production config (not committed) |
