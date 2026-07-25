# Release Process

Shatter uses two long-lived branches and two Docker image channels so maintainers can integrate and deploy daily work without shipping every change to production users.

---

## Branches

| Branch | Role | Who merges here | Docker channel |
|--------|------|-----------------|----------------|
| **`beta`** | Integration / dogfood | Day-to-day feature and fix PRs | `:beta`, commit SHA |
| **`main`** | Stable / public releases | Promote PRs from `beta` when ready | `:latest`, `:vX.Y.Z` |

**Default GitHub branch stays `main`** (stable). Contributors and docs reference stable URLs on `main`.

---

## Day-to-day development (maintainers)

1. Create a feature branch from `beta`
2. Open a PR **into `beta`**
3. CI runs tests + Docker build validation
4. Merge to `beta`
5. CI builds and pushes **`ghcr.io/.../backend:beta`** (and frontend)
6. On your server:

```bash
# .env
IMAGE_TAG=beta

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Use conventional commits on PRs to `beta`. Version numbers and CHANGELOG are **not** bumped on `beta` merges.

---

## Cutting a stable release

When `beta` is ready for public users:

1. Open a PR **`beta` → `main`** (promote / release PR)
2. Review and merge to `main`
3. **`release.yml`** runs on push to `main`:
   - **semantic-release** analyzes commits since the last release tag
   - Bumps `VERSION`, updates CHANGELOG, creates GitHub Release + git tag
   - Builds stable Docker images: `:latest`, `:vX.Y.Z`, SHA tags
4. Announce the release; users upgrade with a pinned tag:

```bash
IMAGE_TAG=v1.3.0   # from GitHub Releases
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

After merging to `main`, sync `beta` with `main` if needed (merge `main` back into `beta` so both branches stay aligned).

---

## Image tag reference

| Tag | Moves when | Safe for production? |
|-----|------------|----------------------|
| `beta` | Every qualifying push to `beta` | No — integration only |
| `latest` | Stable release on `main` | Convenience only; pin `vX.Y.Z` for shops |
| `vX.Y.Z` | Stable release on `main` | **Yes** — recommended for operators |
| `{sha}` | Build from that commit | Yes — immutable pin |

---

## Versioning

- **semantic-release** runs **only on `main`**
- Commit types (`feat:`, `fix:`, etc.) determine semver bumps — see [CONTRIBUTING.md](../CONTRIBUTING.md)
- Do not manually edit `VERSION` or CHANGELOG for releases
- Beta builds embed the current `VERSION` file in the UI build arg but do not create release tags

---

## First-time setup (after enabling this model)

On GitHub, create the `beta` branch from current `main`:

```bash
git checkout main
git pull origin main
git checkout -b beta
git push -u origin beta
```

Set your server `.env` to `IMAGE_TAG=beta`.

Optional GitHub settings:

- Branch protection on `main` (require PR + passing CI)
- Allow direct pushes to `beta` for maintainer speed (optional)

---

## CI workflows

| Workflow | Trigger | Pushes images? |
|----------|---------|----------------|
| `test.yml` | Push/PR to `main`, `beta` | No |
| `docker-build-push.yml` | PR to `main`, `beta` | No (validate only) |
| `docker-build-beta.yml` | Push to `beta` | Yes (`:beta`, SHA) |
| `release.yml` | Push to `main` | Yes (`:latest`, `:vX.Y.Z`, SHA) |

Details: [.github/workflows/README.md](../.github/workflows/README.md)

---

## External contributors

- Open PRs against **`beta`** unless a maintainer directs otherwise
- Stable releases happen when maintainers promote **`beta` → `main`**
- Fork sync: merge `upstream/beta` for ongoing work; merge `upstream/main` for stable-only fixes if applicable
