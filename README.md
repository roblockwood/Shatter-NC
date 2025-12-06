# Shatter

**CNC Management Platform for Brother CNC Machines**

Shatter is an open-source web platform for monitoring and managing multiple Brother CNC machines. Built for isolated shop floor networks, Shatter provides real-time monitoring, intelligent G-code file transfer, version control, and production analytics.

## Features

- 🔴 **Real-time Monitoring** - Live status, cycle times, alarms, and counters for all machines
- 📁 **Smart File Transfer** - G-code validation, tool verification, and multi-machine deployment
- 📊 **Production Analytics** - Historical data, cycle time trends, and fleet-wide statistics
- 🔄 **Version Control** - Git-like versioning for NC programs with deployment tracking
- 🏭 **Multi-Machine** - Monitor and manage multiple CNCs from a single interface
- 🐳 **Easy Deployment** - Docker-based, runs on isolated networks

## Quick Start

```bash
git clone https://github.com/user/shatter
cd shatter
cp .env.example .env
docker-compose up -d
```

Open http://localhost:3000 and add your CNC machines through the web UI.

## Architecture

- **Frontend**: React/Vue SPA (port 3000)
- **Backend**: Python FastAPI (port 8000)
- **Database**: PostgreSQL + TimescaleDB (port 5432)

## Documentation

- [Project Plan](STATUS.md - Comprehensive development roadmap
- [API Endpoints](API_QUICK_REFERENCE.md) - REST API documentation
- [CNC Communication](webserver_endpoints.md) - Brother CNC protocol details

## Development Status

🚧 **In Active Development** - Phase 1: MVP Foundation

See [STATUS.md](STATUS.md) for detailed development phases and progress.

## License

TBD (Likely MIT or Apache 2.0)

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.
