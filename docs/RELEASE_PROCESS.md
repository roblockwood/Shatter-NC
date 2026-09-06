# Release Process

Shatter uses two long-lived branches and two Docker image channels so maintainers can integrate and deploy daily work without shipping every change to production users.

Stable versioning uses **[release-please](https://github.com/googleapis/release-please)** with **conventional commits**. Version bumps land via a **Release PR** (fits branch protection — no direct pushes to `main`).

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
2. Commit on the feature branch (**never commit directly on `main` or `beta`** — Cursor agents enforce this; see `.cursor/rules/branch-commit-policy.mdc`)
3. Open a PR **into `beta`** with a **conventional commit title** (CI enforces this)
4. CI runs tests + Docker build validation
5. Merge to `beta`
6. CI builds and pushes **`ghcr.io/.../backend:beta`** (and frontend)
7. On your server:

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

1. Open a PR **`beta` → `main`** (promote PR). **Cursor maintainers:** follow [`.cursor/promote-release-skill.md`](../.cursor/promote-release-skill.md).
2. Review and merge the promote PR to `main`
3. **`release.yml`** runs **release-please** on push to `main`:
   - Opens or updates a **Release Please PR** that bumps `VERSION`, `CHANGELOG.md`, `frontend/package.json`, and `APP_VERSION` in `backend/app/core/config.py`
4. Review and merge the **Release Please PR** into `main`
5. On that merge, release-please:
   - Creates the git tag (`vX.Y.Z`) and GitHub Release
   - Triggers the stable Docker build: `:latest`, `:vX.Y.Z`, SHA tags
6. Announce the release; users upgrade with a pinned tag:

```bash
IMAGE_TAG=v1.3.0   # from GitHub Releases
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

After a release lands on `main`, sync `beta` with `main` (merge `main` back into `beta` so VERSION/CHANGELOG stay aligned).

Do **not** manually edit `VERSION` or CHANGELOG for releases — use the Release Please PR.

---

## Image tag reference

| Tag | Moves when | Safe for production? |
|-----|------------|----------------------|
| `beta` | Every qualifying push to `beta` | No — integration only |
| `latest` | Stable release on `main` (after Release Please PR merges) | Convenience only; pin `vX.Y.Z` for shops |
| `vX.Y.Z` | Stable release on `main` | **Yes** — recommended for operators |
| `{sha}` | Build from that commit | Yes — immutable pin |

---

## Versioning

- **release-please** runs on pushes to **`main`** only
- Commit / PR types (`feat:`, `fix:`, etc.) determine semver bumps — see [CONTRIBUTING.md](../CONTRIBUTING.md)
- Config: [`release-please-config.json`](../release-please-config.json), manifest: [`.release-please-manifest.json`](../.release-please-manifest.json)
- Beta builds embed `VITE_RELEASE_CHANNEL=beta` in the frontend image — the header shows **`SHATTER v1.1.1 [BETA]`** (semver unchanged; `[BETA]` is the integration channel marker). Stable builds omit the suffix.

---

## Conventional commits (enforced)

- **PR titles** into `beta` and `main` must match conventional commit format (`feat:`, `fix:`, …). See workflow `conventional-commits.yml`.
- Prefer **squash merge** for feature → `beta` so the squash title is the releasable conventional subject.
- Promote **`beta` → `main`** may use a merge commit; release-please still sees the underlying conventional commits on `main`.
- Do **not** enable a branch ruleset `commit_message_pattern` that rejects `Merge pull request #…` — that conflicts with merge commits.

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

Recommended GitHub settings:

- Ruleset on `main` (require PR + CI) — already used; release-please does **not** need a bypass actor
- Ruleset or protection on `beta` (require PR) recommended
- Optional: after `conventional-commits.yml` has run once, add required status check **PR title** on the ruleset (in addition to **pytest**)
- Do **not** add a ruleset `commit_message_pattern` that rejects `Merge pull request #…` — that conflicts with merge commits on promote PRs

---

## CI workflows

| Workflow | Trigger | Pushes images? |
|----------|---------|----------------|
| `test.yml` | Push/PR to `main`, `beta` | No |
| `conventional-commits.yml` | PR to `main`, `beta` | No (PR title lint) |
| `docker-build-push.yml` | PR to `main`, `beta` | No (validate only) |
| `docker-build-beta.yml` | Push to `beta` | Yes (`:beta`, SHA) |
| `release.yml` | Push to `main` | Yes (`:latest`, `:vX.Y.Z`, SHA) **only when a release is created** |

Details: [.github/workflows/README.md](../.github/workflows/README.md)

---

## External contributors

- Open PRs against **`beta`** unless a maintainer directs otherwise
- Use a conventional commit **PR title**
- Stable releases happen when maintainers promote **`beta` → `main`**, then merge the **Release Please** PR
- Fork sync: merge `upstream/beta` for ongoing work; merge `upstream/main` for stable-only fixes if applicable
