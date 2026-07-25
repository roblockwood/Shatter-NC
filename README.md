# Shatter

**CNC Management Platform for Brother CNC Machines**

Shatter is an open-source web platform for monitoring and managing multiple Brother CNC machines. Built for isolated shop floor networks, Shatter provides real-time monitoring, intelligent G-code file transfer, version control, and production analytics.

## Features

- 🔴 **Real-time Monitoring** - Live status, cycle times, alarms, and counters for all machines
- 📁 **Smart File Transfer** - G-code validation, tool verification, and multi-machine deployment
- 🔁 **Folder Sync (Upload/Download)** (beta) - Configure repeatable FTP sync jobs per machine from the Dashboard machine edit form
- 📊 **Production Analytics** - Historical data, cycle time trends, and fleet-wide statistics
- 🔧 **Tool Management** (beta) - Track tool usage across programs with detailed speed/feed analysis
- 🔔 **Notifications** (beta) - Email/SMS alerts for status changes, alarms, offline, and cycle complete
- 🔄 **Version Control** - Git-like versioning for NC programs with deployment tracking
- 🏭 **Multi-Machine** - Monitor and manage multiple CNCs from a single interface
- 🐳 **Easy Deployment** - Docker-based, runs on isolated networks



## Quick Start

**First-time or shop install:** See the **[Installation Guide](docs/INSTALLATION_GUIDE.md)** for production deployment with pre-built Docker images, or development setup from source.

**Development (after cloning):**

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
```

Open [http://localhost:3000](http://localhost:3000) and add your CNC machines through the web UI.

**For install, backup, and upgrade**, see [Installation Guide](docs/INSTALLATION_GUIDE.md).

## Sync & Notifications

Shatter includes two operator-facing workflows (both require **beta mode** — rapid-click the logo to enable):

- **Sync (Dashboard → machine edit)**: Enable **FTP SYNC** on a Brother machine, then use the sync tabs to create per-machine FTP sync configs for **upload** (local folder → CNC) or **download** (CNC → local folder), browse local folders (restricted by `FTP_SYNC_LOCAL_BROWSE_ROOT`), and trigger runs with progress + run item details. Exclusion rules and filename validation are enforced during candidate selection. See `docs/FTP_SYNC_EXCLUSION_RULES.md`.
- **Notify (**`/notifications`**)**: Create notification **channels** (SMTP email or Twilio SMS) and **rules** that fire on status transitions (including error/offline) and cycle completion, with a delivery log and a “send test” action per channel.



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
- **Database**: PostgreSQL 15 + TimescaleDB (port 5432 in dev; internal in prod)

**For architecture details**, see [Backend Architecture](docs/BACKEND_ARCHITECTURE.md) and [Development Guide](docs/DEVELOPMENT_GUIDE.md).

## Documentation



### Getting Started

- **[Installation Guide](docs/INSTALLATION_GUIDE.md)** — Shop install, backup, upgrade
- **[User Guide](docs/USER_GUIDE.md)** — Dashboard, files, validation, tools
- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)** — Contributor setup and tests
- **[Environment Variables](docs/ENVIRONMENT_VARIABLES.md)** — Configuration table
- **[Contributing](CONTRIBUTING.md)** — PR process and versioning
- **[Release Process](docs/RELEASE_PROCESS.md)** — Beta vs stable Docker channels



### Technical Reference

- **[Backend Architecture](docs/BACKEND_ARCHITECTURE.md)** — Services and data flow
- **[WebSocket Protocol](docs/WEBSOCKET_PROTOCOL.md)** — Real-time messages
- **[Telnet Reference](docs/TELNET_REFERENCE.md)** — Brother port 10000
- **[Database Schema](docs/DATABASE_SCHEMA.md)** — PostgreSQL + TimescaleDB
- **[NC Parser Guide](docs/NC_PARSER_GUIDE.md)** — Fusion post-processor (CAM)
- **[Compressor Integration](docs/COMPRESSOR_INTEGRATION.md)** — Kaeser SIGMA CONTROL 2
- **[UX Design Guide](docs/UX_DESIGN_GUIDE.md)** — UI standards (+ branding)
- **[Security](SECURITY.md)** — Deployment model

REST API: OpenAPI at `/docs` (Swagger), `/redoc`, and `/openapi.json` on the backend (see Development Guide).

Full index: **[docs/README.md](docs/README.md)**

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



## Acknowledgments

Thanks to the early testers who ran Shatter on real shop floors and helped shape it through feedback, bug reports, and patience with rough edges:

- **Matt Blackwell - Matt was the first external contributor, validated and repaired D00 schema, and added features like the ATC Optimizer, push notifications and file sync.**
- **Dennis Rathi - Dennis was the first person to install Shatter, validating that it's deployable by humans. He would really appreciate Fanuc, Siemens, and Heidenhain support.** 
- **Justin Gray - Justin gave some advise on architecture early on, which reinforced the path. He also plays the role of Ivan Drago, knowing he'll always be auditing.**



## License

Shatter-NC is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE) for the full text. In short: you may use, modify, and distribute the software; if you run a modified version as a network service, you must offer the corresponding source to its users.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code of conduct
- Development process and branch naming
- Code style guidelines (Python PEP 8, TypeScript standards)
- **MANDATORY**: Documentation requirements ([CONTRIBUTING.md](CONTRIBUTING.md#documentation-requirements))
- **MANDATORY**: UX design compliance ([UX Design Guide](docs/UX_DESIGN_GUIDE.md))
- Review process and expectations

**Areas needing contribution**: Testing infrastructure, alarm notifications, advanced reporting

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.