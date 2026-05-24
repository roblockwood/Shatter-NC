# Shatter

**CNC Management Platform for Brother CNC Machines**

Shatter is an open-source web platform for monitoring and managing multiple Brother CNC machines. Built for isolated shop floor networks, Shatter provides real-time monitoring, intelligent G-code file transfer, version control, and production analytics.

## Features

- 🔴 **Real-time Monitoring** - Live status, cycle times, alarms, and counters for all machines
- 📁 **Smart File Transfer** - G-code validation, tool verification, and multi-machine deployment
- 🔁 **Folder Sync (Upload/Download)** (beta) - Configure repeatable FTP sync jobs per machine from the Dashboard machine edit form
- 📊 **Production Analytics** - Historical data, cycle time trends, and fleet-wide statistics
- 🔧 **Tool Management** - Track tool usage across programs with detailed speed/feed analysis
- 🔔 **Notifications** (beta) - Email/SMS alerts for status changes, alarms, offline, and cycle complete
- 🔄 **Version Control** - Git-like versioning for NC programs with deployment tracking
- 🏭 **Multi-Machine** - Monitor and manage multiple CNCs from a single interface
- 🐳 **Easy Deployment** - Docker-based, runs on isolated networks

## Quick Start

**First-time or shop install:** See the **[Installation Guide](docs/INSTALLATION_GUIDE.md)** for step-by-step setup on Windows, macOS, or Linux using Docker Desktop (including private repo access and GitHub Desktop).

**Development (after cloning):**
```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
```

Open http://localhost:3000 and add your CNC machines through the web UI.

**For detailed deployment options**, see [Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md).

## Sync & Notifications

Shatter includes two operator-facing workflows (both require **beta mode** — rapid-click the logo to enable):

- **Sync (Dashboard → machine edit)**: Enable **FTP SYNC** on a Brother machine, then use the sync tabs to create per-machine FTP sync configs for **upload** (local folder → CNC) or **download** (CNC → local folder), browse local folders (restricted by `FTP_SYNC_LOCAL_BROWSE_ROOT`), and trigger runs with progress + run item details. Exclusion rules and filename validation are enforced during candidate selection. See `docs/FTP_SYNC_EXCLUSION_RULES.md`.
- **Notify (`/notifications`)**: Create notification **channels** (SMTP email or Twilio SMS) and **rules** that fire on status transitions (including error/offline) and cycle completion, with a delivery log and a “send test” action per channel.

### Configuration knobs (high-level)

- **FTP Sync**:
  - `FTP_SYNC_ENABLED` (default true)
  - `FTP_SYNC_LOCAL_WATCH_ENABLED` (watcher-triggered sync; default false)
  - `FTP_SYNC_LOCAL_BROWSE_ROOT` (limits what the UI can browse)
- **Notifications**:
  - SMTP defaults: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_START_TLS`, `SMTP_USE_TLS`
  - Twilio defaults: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`

Per-channel config stored in the database can override global defaults.

## Architecture

- **Frontend**: React 19 + TypeScript + Vite (port 3000)
- **Backend**: Python 3.11 + FastAPI (port 8000)
- **Database**: PostgreSQL 14 + TimescaleDB (port 5432)

**For complete architecture details**, see [Backend Architecture](docs/BACKEND_ARCHITECTURE.md) and [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md).

## Documentation

### Getting Started

- **[Installation Guide](docs/INSTALLATION_GUIDE.md)** - Step-by-step install for Windows, macOS, Linux (Docker Desktop; machinist-friendly)
- **[Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md)** - Production and development deployment
- **[Migration: Remove Redis](docs/MIGRATION_REMOVE_REDIS.md)** - Upgrading from a Redis-based deployment
- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Local development setup and workflows
- **[Environment Variables](docs/ENVIRONMENT_VARIABLES.md)** - Configuration reference
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to the project

### Architecture & Technical Reference

- **[Backend Architecture](docs/BACKEND_ARCHITECTURE.md)** - Services, polling system, WebSocket management
- **[Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md)** - React components, hooks, state management
- **[API Reference](docs/API_REFERENCE.md)** - Complete REST API documentation (50+ endpoints)
- **[Database Schema](docs/DATABASE_SCHEMA.md)** - PostgreSQL + TimescaleDB schema and relationships

### User Workflows

- **[Dashboard Workflows](docs/DASHBOARD_WORKFLOWS.md)** - Fleet monitoring and machine management
- **[File Browser Workflows](docs/FILE_BROWSER_WORKFLOWS.md)** - File management, validation, and deployment
- **[Tool Management Workflows](docs/TOOL_MANAGEMENT_WORKFLOWS.md)** - Tool usage analysis and speed/feed tracking
- **[Dashboard Summaries](docs/DASHBOARD_SUMMARIES.md)** - Summary feature guide

### Specialized Topics

- **[CNC Clients](docs/CNC_CLIENTS.md)** - HTTP/FTP client libraries for Brother CNCs
- **[Program Validation](docs/PROGRAM_VALIDATION.md)** - Validation algorithm and workflow
- **[UX Design Guide](docs/UX_DESIGN_GUIDE.md)** - Terminal aesthetic design system
- **[Branding](docs/BRANDING.md)** - Brand identity and logo usage

### Future Documentation

- **[Future Documentation Plan](docs/roadmap/FUTURE_DOCUMENTATION.md)** - Planned advanced topics (WebSocket protocol, testing, parsers)

## Development Status

🚧 **Active Development** - Core features implemented, testing infrastructure in progress

**Current Features:**
- ✅ Real-time machine monitoring with WebSocket updates
- ✅ G-code validation and intelligent deployment
- ✅ Multi-machine fleet management dashboard
- ✅ Historical data tracking with TimescaleDB
- ✅ Production analytics and summaries
- ✅ Tool management with speed/feed analysis
- ✅ File browser with FTP integration
- ✅ Folder sync (upload/download) with run history UI
- ✅ Email/SMS notifications with channels, rules, and delivery log
- 🚧 Automated testing (in progress)
- 📋 User authentication (planned)
- 📋 Per-operation runtime tracking (planned)
- reduce steps for upload (parallel upload and validate, auto issue O####, allow rename perhaps?)

## License

Shatter-NC is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE) for the full text. In short: you may use, modify, and distribute the software; if you run a modified version as a network service, you must offer the corresponding source to its users.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code of conduct
- Development process and branch naming
- Code style guidelines (Python PEP 8, TypeScript standards)
- **MANDATORY**: Documentation requirements ([.claude/rules.md](.claude/rules.md))
- **MANDATORY**: UX design compliance ([UX Design Guide](docs/UX_DESIGN_GUIDE.md))
- Review process and expectations

**Areas needing contribution**: Testing infrastructure, authentication, alarm notifications, advanced reporting

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.
