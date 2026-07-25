# Security Policy

## Supported Versions

Security fixes are applied to the latest **stable release** on `main` (semver tags and `:latest` on ghcr.io). Integration builds on the `beta` branch are not supported release channels. Older tagged releases may not receive backports unless noted in release notes.

## Reporting a Vulnerability

If you discover a security issue, please **do not** open a public GitHub issue with exploit details.

Instead:

1. Use [GitHub private vulnerability reporting](https://github.com/roblockwood/Shatter-NC/security/advisories/new) if enabled for this repository, **or**
2. Email the maintainers with a description of the issue, steps to reproduce, and impact assessment.

We aim to acknowledge reports within a few business days and will coordinate disclosure and a fix before public details are published when appropriate.

## Deployment Model

Shatter is designed for **trusted shop-floor LANs** where CNC machines, operators, and the Shatter server share an isolated network segment.

- Deploy behind a firewall; do not expose Shatter directly to the public internet without additional controls.
- Restrict access to the Shatter UI (port 80/3000) to shop staff and known devices.
- Use strong, unique values for `POSTGRES_PASSWORD` and `SECRET_KEY` in production (`SECRET_KEY` is required by compose but not yet used by application logic).

## Access Control

Shatter has **no user login, API tokens, or WebSocket authentication**. Anyone who can reach the API can configure machines, upload programs, and trigger CNC writes. That is intentional for trusted shop-floor LANs — treat network access as the primary security boundary.

Other security notes:

- No role-based access control (RBAC)
- CNC/compressor credentials are stored in PostgreSQL as plaintext (needed for equipment connections)

`ENABLE_AUTH` exists in configuration for historical compatibility but **has no effect**.

## Network Requirements

Production [`docker-compose.prod.yml`](docker-compose.prod.yml) is hardened to keep internal services off the host network:

| Service | Host exposure |
|---------|----------------|
| Frontend (nginx) | Port 80 — intended UI entry point |
| Backend API | Port 8000 — restrict via firewall if not proxied through nginx |
| PostgreSQL | **Not exposed** on host (internal Docker network only) |
| Mosquitto MQTT | **Not exposed** on host when using bundled broker |

Additional guidance:

- Set `CORS_ORIGINS` to explicit shop origins (avoid `"*"` unless you understand the tradeoff).
- OpenAPI is always available at `/docs` (Swagger UI), `/redoc` (ReDoc), and `/openapi.json`. Restrict port 8000 on untrusted networks like any other API surface.
- Do not publish PostgreSQL or MQTT ports to the internet.

## Credential Handling

Shatter stores CNC FTP passwords and Kaeser credentials in the database to connect to equipment. API responses **redact** secrets (FTP passwords and notification channel SMTP/Twilio tokens are not returned on GET).

Operational guidance:

- Never commit `.env` files or backups (for example `.env.bak`) to version control.
- Use [`.env.example`](.env.example) and [`.env.production.example`](.env.production.example) as templates only.
- Rotate credentials if a backup or database dump may have leaked.
- Restrict database backups to trusted storage.

## FTP Sync Local Browse

When `FTP_SYNC_LOCAL_BROWSE_ROOT` is mounted from the host filesystem (see production compose), the API can list directories under that path for sync configuration. This is powerful and should only be enabled on trusted hosts with appropriate OS-level permissions.

## Dependency Advisories

Run `pip-audit -r backend/requirements.txt` and `npm audit` in `frontend/` before production deployments. Some frontend dev-tooling packages may report advisories that do not affect the runtime container image.

## Sensitive Configuration

Shatter deployments require secrets such as database passwords, `SECRET_KEY`, and optional SMTP/Twilio credentials. Generate values locally:

```bash
openssl rand -hex 32
```
