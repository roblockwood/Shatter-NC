# Shatter

**CNC Management Platform for Brother CNC Machines**

Shatter is an open-source web platform for monitoring and managing multiple Brother CNC machines. Built for isolated shop floor networks, Shatter provides real-time monitoring, intelligent G-code file transfer, version control, and production analytics.

## Features

- 🔴 **Real-time Monitoring** - Live status, cycle times, alarms, and counters for all machines
- 📁 **Smart File Transfer** - G-code validation, tool verification, and multi-machine deployment
- 📊 **Production Analytics** - Historical data, cycle time trends, and fleet-wide statistics
- 🔧 **Tool Management** - Track tool usage across programs with detailed speed/feed analysis
- 🔄 **Version Control** - Git-like versioning for NC programs with deployment tracking
- 🏭 **Multi-Machine** - Monitor and manage multiple CNCs from a single interface
- 🐳 **Easy Deployment** - Docker-based, runs on isolated networks
- 🌐 **Zero-Config Discovery** - Avahi/mDNS support for network discovery at `shatter.local`

## Quick Start

**Development (Recommended):**
```bash
git clone https://github.com/user/shatter
cd shatter
cp .env.example .env
docker compose up -d
```

Open http://localhost:3000 and add your CNC machines through the web UI.

**With Avahi enabled**, the service is also discoverable at http://shatter.local (or http://shatter.local:3000 in dev mode). See [Avahi Setup](avahi/README.md) for configuration.

**For detailed deployment options**, see [Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md).

## Architecture

- **Frontend**: React 19 + TypeScript + Vite (port 3000)
- **Backend**: Python 3.11 + FastAPI (port 8000)
- **Database**: PostgreSQL 14 + TimescaleDB (port 5432)
- **Cache**: Redis 7 (optional, port 6379)

**For complete architecture details**, see [Backend Architecture](docs/BACKEND_ARCHITECTURE.md) and [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md).

## Documentation

### Getting Started

- **[Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md)** - Production and development deployment
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
- 🚧 Automated testing (in progress)
- 📋 User authentication (planned)
- 📋 Alarm notifications (planned)
- 📋 Per-operation runtime tracking (planned)
- reduce steps for upload (parallel upload and validate, auto issue O####, allow rename perhaps?)

## License

TBD (Likely MIT or Apache 2.0)

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
