# Shatter-NC Documentation

Curated docs for installing, operating, and contributing to Shatter.

## Operators

| Document | Contents |
|----------|----------|
| [Installation Guide](INSTALLATION_GUIDE.md) | Docker install, backup, upgrade |
| [User Guide](USER_GUIDE.md) | Dashboard, files, validation, tools |
| [NC Parser Guide](NC_PARSER_GUIDE.md) | Fusion post-processor requirements (CAM) |
| [FTP Sync Exclusion Rules](FTP_SYNC_EXCLUSION_RULES.md) | Sync filename policy |
| [Compressor Integration](COMPRESSOR_INTEGRATION.md) | Kaeser SIGMA CONTROL 2 |

## Contributors

| Document | Contents |
|----------|----------|
| [Development Guide](DEVELOPMENT_GUIDE.md) | Setup, tests, where to change code |
| [Contributing](../CONTRIBUTING.md) | PR process, versioning, doc standards |
| [UX Design Guide](UX_DESIGN_GUIDE.md) | Terminal UI system (+ branding) |
| [Backend Architecture](BACKEND_ARCHITECTURE.md) | Services and data flow (~300 lines) |
| [WebSocket Protocol](WEBSOCKET_PROTOCOL.md) | Real-time message format |
| [Telnet Reference](TELNET_REFERENCE.md) | Brother port 10000 commands |
| [Database Schema](DATABASE_SCHEMA.md) | PostgreSQL + TimescaleDB |
| [Database Migrations](DATABASE_MIGRATIONS.md) | Startup migration runner |
| [Environment Variables](ENVIRONMENT_VARIABLES.md) | Configuration table |

## External

- [SECURITY.md](../SECURITY.md) — deployment model and vulnerability reporting
- [README.md](../README.md) — project overview
- [GitHub Issues](https://github.com/roblockwood/Shatter-NC/issues)

## Maintaining docs

Update the smallest relevant doc in the same PR as code changes. REST API details live in OpenAPI (`/docs` when `LOG_LEVEL=DEBUG`), not a hand-maintained reference. Prefer deleting obsolete sections over duplicating — git history retains removed content.

Parser schema template for agents: [`.cursor/templates/SCHEMA_DEFINITION_TEMPLATE.md`](../.cursor/templates/SCHEMA_DEFINITION_TEMPLATE.md)
