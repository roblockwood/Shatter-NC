# GitHub Actions Workflows

Shatter publishes two Docker image channels on [GitHub Container Registry](https://github.com/roblockwood?tab=packages) (ghcr.io):

| Channel | Git branch | When images build | Tags pushed | Audience |
|---------|------------|-------------------|-------------|----------|
| **Beta** | `beta` | Push to `beta` (docker-related paths) | `:beta`, `:{sha}`, `:{date}-{sha}` | Maintainers / early adopters |
| **Stable** | `main` | Push to `main` after semantic-release | `:latest`, `:vX.Y.Z`, `:{sha}`, `:{date}-{sha}` | Production shops |

**`:latest` always tracks the latest stable release from `main`**, never beta integration builds.

See [docs/RELEASE_PROCESS.md](../docs/RELEASE_PROCESS.md) for branch workflow and promotion steps.

---

## Workflows

### `test.yml`

- **Triggers:** Push and PR to `main` or `beta`
- **Purpose:** Backend pytest with coverage floor

### `docker-build-push.yml`

- **Triggers:** PR to `main` or `beta` (docker-related paths)
- **Purpose:** Validate production Dockerfiles build; **does not push** images

### `docker-build-beta.yml`

- **Triggers:** Push to `beta` (docker-related paths)
- **Purpose:** Build and push **beta** channel images
- **Tags:** `beta`, commit SHA, date-SHA — **never** `latest` or `vX.Y.Z`

### `release.yml`

- **Triggers:** Push to `main`
- **Purpose:**
  1. Run **semantic-release** (version bump, CHANGELOG, GitHub Release, git tag)
  2. Build and push **stable** images when docker-related files changed

---

## Image names

```
ghcr.io/{owner}/{repo}/backend:{tag}
ghcr.io/{owner}/{repo}/frontend:{tag}
```

Example (`roblockwood/shatter-nc`):

| Tag | Meaning |
|-----|---------|
| `beta` | Latest integration build from `beta` branch |
| `latest` | Latest stable release from `main` |
| `v1.2.3` | Pinned stable release (matches GitHub Releases) |
| `abc1234` | Specific commit (either channel) |

---

## Pulling images

**Maintainer server (beta):**

```bash
# In .env
IMAGE_TAG=beta

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

**Production shop (stable — recommended pin):**

```bash
# In .env
IMAGE_TAG=v1.2.3

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Or pull directly:

```bash
docker pull ghcr.io/roblockwood/shatter-nc/backend:beta
docker pull ghcr.io/roblockwood/shatter-nc/backend:v1.2.3
```

Packages are public for this project. Private forks may need `docker login ghcr.io`.

---

## Related docs

- [INSTALLATION_GUIDE.md](../docs/INSTALLATION_GUIDE.md) — operator install
- [RELEASE_PROCESS.md](../docs/RELEASE_PROCESS.md) — beta vs stable workflow
- [ENVIRONMENT_VARIABLES.md](../docs/ENVIRONMENT_VARIABLES.md) — `IMAGE_TAG`
