# Shatter-NC install (public packages + Komodo)

This guide assumes you are installing Shatter-NC **from public container images** (GHCR), without cloning the main Shatter-NC source repo.

## Install a container engine

You need a working container runtime and CLI.

- **Docker Engine (recommended)**: follow the official docs for your OS at `https://docs.docker.com/engine/install/`.
  - Verify: `docker version` and `docker run --rm hello-world`

> macOS/Windows note: Docker Engine runs inside a VM (commonly via Docker Desktop or an alternative). As long as `docker` works in your terminal, you’re good.

### Podman (optional)

Podman can run Compose stacks (with `podman compose` or `docker compose` compatibility), but Komodo Periphery typically expects access to a Docker-compatible socket. If you want to officially support Podman, standardize on one documented approach and test it (rootful socket vs rootless socket).

## Install Komodo

Komodo is a UI + agent (Core + Periphery) that can deploy Docker Compose stacks.

Follow Komodo’s official setup docs:

- Setup: `https://komo.do/docs/setup`
- MongoDB quick start: `https://komo.do/docs/setup/mongo`

The official quick start downloads Komodo’s compose files and runs:

```bash
docker compose -p komodo -f komodo/mongo.compose.yaml --env-file komodo/compose.env up -d
```

Then open Komodo at `http://<host>:9120`.
## Deploy Shatter-NC (using the generator)

1. Open the Shatter-NC Install Kit generator page (GitHub Pages).
2. Fill in:
   - `POSTGRES_PASSWORD`
   - `SECRET_KEY` (use Generate)
   - (Optional) `MQTT_PUBLISH_HOST` / `MQTT_PUBLISH_PORT` / credentials (to publish telemetry to Mosquitto)
   - GHCR owner/repo + image tag
3. Download:
   - `.env`
   - `docker-compose.yml`
4. In Komodo:
   - Create a new **Stack**
   - Paste the `docker-compose.yml` into the compose editor
   - Paste the `.env` values into the stack environment / env-file area
   - Deploy

When the stack is up:

- Frontend: `http://<host>:<FRONTEND_PORT>` (defaults to 80)
- Backend health: `http://<host>:<BACKEND_PORT>/health` (defaults to 8000)
## Notes

- The backend image contains SQL migrations and applies them on startup; the generated compose intentionally avoids bind-mounts that require a source checkout.
- If your GHCR packages are private, you must configure registry credentials on the host (or in Komodo) before deploy.
