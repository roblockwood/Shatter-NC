# Shatter-NC Documentation

This directory contains all documentation for the Shatter-NC project. Documentation is organized by category for easy navigation.

## Quick Navigation

### Getting Started
- **[Development Guide](DEVELOPMENT_GUIDE.md)** - Local development setup and workflows
- **[Docker Deployment](DOCKER_DEPLOYMENT.md)** - Production and development deployment
- **[Environment Variables](ENVIRONMENT_VARIABLES.md)** - Configuration reference

### Architecture & Technical Reference
- **[Backend Architecture](BACKEND_ARCHITECTURE.md)** - Services, polling system, WebSocket management
- **[Frontend Architecture](FRONTEND_ARCHITECTURE.md)** - React components, hooks, state management
- **[Database Schema](DATABASE_SCHEMA.md)** - PostgreSQL + TimescaleDB schema and relationships
- **[Database Migrations](DATABASE_MIGRATIONS.md)** - Database migration history

### API Documentation
- **[API Reference](API_REFERENCE.md)** - Complete REST API documentation (50+ endpoints)
- **[CNC Webserver Endpoints](WEBSERVER_ENDPOINTS.md)** - Brother CNC webserver API endpoints

### CNC Communication & Protocols
- **[CNC Clients](CNC_CLIENTS.md)** - HTTP/FTP/Telnet client libraries for Brother CNCs
- **[Telnet Command Coverage](TELNET_COMMAND_COVERAGE.md)** - Telnet protocol command reference
- **[Telnet ATC Write Operations](TELNET_ATC_WRITE_OPERATIONS.md)** - ATC operations via Telnet

### Parsing & Validation
- **[NC Parser Guide](NC_PARSER_GUIDE.md)** - G-code parsing guide
- **[Program Validation](PROGRAM_VALIDATION.md)** - Validation algorithm and workflow

### User Workflows
- **[Dashboard Workflows](DASHBOARD_WORKFLOWS.md)** - Fleet monitoring and machine management
- **[File Browser Workflows](FILE_BROWSER_WORKFLOWS.md)** - File management, validation, and deployment
- **[Tool Management Workflows](TOOL_MANAGEMENT_WORKFLOWS.md)** - Tool usage analysis and speed/feed tracking
- **[Dashboard Summaries](DASHBOARD_SUMMARIES.md)** - Summary feature guide
- **[Tools Pane Data Coverage](TOOLS_PANE_DATA_COVERAGE.md)** - Tools pane documentation

### Design & Branding
- **[UX Design Guide](UX_DESIGN_GUIDE.md)** - Terminal aesthetic design system
- **[Branding](BRANDING.md)** - Brand identity and logo usage

## Document Organization

### Active Documentation
All documentation files in the root `docs/` directory are **active** and should be kept up-to-date with the codebase.

### Archived Documentation
Documents in `archive/` are historical records of completed migrations or implementations:
- **[BACKEND_TELNET_MIGRATION_PLAN.md](archive/BACKEND_TELNET_MIGRATION_PLAN.md)** - Telnet migration plan (archived - migration complete)
- **[PHASE3_UNITS_IMPLEMENTATION_PLAN.md](archive/PHASE3_UNITS_IMPLEMENTATION_PLAN.md)** - Units implementation plan (archived - implementation complete)
- **[DRQALL_CONTROL_VERIFICATION.md](archive/DRQALL_CONTROL_VERIFICATION.md)** - DRQALL format verification notes

### Templates
Templates and reusable documentation structures:
- **[Schema Definition Template](templates/SCHEMA_DEFINITION_TEMPLATE.md)** - Template for defining CNC data file schemas

### Bugs & issues
- **[GitHub Issues](https://github.com/roblockwood/Shatter-NC/issues)** - Report bugs and track improvements. Use the `bug` label for defects.

### Roadmap
Future planning and roadmap documents:
- **[Future Documentation Plan](roadmap/FUTURE_DOCUMENTATION.md)** - Planned advanced topics (WebSocket protocol, testing, parsers)

## Documentation Status

### Current (Up-to-Date)
All active documentation files are maintained and validated against the codebase:
- ✅ API Reference - All endpoints documented
- ✅ Architecture docs - Reflect current implementation
- ✅ Workflow docs - Match UI implementation
- ✅ Client libraries - Telnet migration documented

### Needs Review
The following areas may need periodic review as the codebase evolves:
- API endpoints (new endpoints may need documentation)
- Workflow steps (UI changes may require doc updates)
- Protocol details (as new features are added)

## Contributing to Documentation

When updating documentation:

1. **Keep it current**: Documentation should match the actual implementation
2. **Use code references**: Reference specific files and line numbers when possible
3. **Update cross-references**: When moving or renaming files, update all links
4. **Archive completed plans**: Move completed migration/implementation plans to `archive/`
5. **Follow structure**: Use consistent formatting and organization

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full contribution guidelines.

## Finding Documentation

### By Topic
- **Setting up development?** → [Development Guide](DEVELOPMENT_GUIDE.md)
- **Deploying to production?** → [Docker Deployment](DOCKER_DEPLOYMENT.md)
- **Understanding the architecture?** → [Backend Architecture](BACKEND_ARCHITECTURE.md), [Frontend Architecture](FRONTEND_ARCHITECTURE.md)
- **Working with the API?** → [API Reference](API_REFERENCE.md)
- **Understanding CNC protocols?** → [CNC Clients](CNC_CLIENTS.md), [Telnet Command Coverage](TELNET_COMMAND_COVERAGE.md)
- **Learning user workflows?** → [Dashboard Workflows](DASHBOARD_WORKFLOWS.md), [File Browser Workflows](FILE_BROWSER_WORKFLOWS.md)

### By File Type
- **Architecture**: `*_ARCHITECTURE.md`, `DATABASE_SCHEMA.md`
- **API/Protocols**: `API_REFERENCE.md`, `*_ENDPOINTS.md`, `*_CLIENTS.md`
- **Workflows**: `*_WORKFLOWS.md`, `*_SUMMARIES.md`
- **Guides**: `*_GUIDE.md`, `*_VALIDATION.md`

---

*Last updated: 2025-01-15*
