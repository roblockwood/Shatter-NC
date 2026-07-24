# GitHub Actions Workflows

## Docker Build and Push

The `docker-build-push.yml` workflow automatically builds and pushes Docker images to GitHub Packages (ghcr.io) when code is merged into the `main` branch.

### Trigger

- **When**: Push to `main` branch (after PR merge)
- **What changes trigger it**: 
  - Changes to `backend/` directory
  - Changes to `frontend/` directory
  - Changes to `docker-compose.prod.yml`
  - Changes to the workflow file itself

### Image Tags

Images are tagged with multiple tags for flexibility:

1. **`latest`** - Always points to the most recent build from main
2. **`main-<short-sha>`** - Specific commit (e.g., `main-abc1234`)
3. **`YYYY-MM-DD-<short-sha>`** - Date and commit (e.g., `2025-12-15-abc1234`)

### GitHub Packages Setup

**No setup required!** GitHub Packages is automatically enabled for all repositories. You don't need to:
- Enable it in settings
- Create a separate account
- Configure anything special

The workflow uses the built-in `GITHUB_TOKEN` for authentication. No additional secrets are required! The workflow automatically has permissions to:
- Read repository contents
- Write to GitHub Packages

**Note:** Packages will only appear after the first successful build. Until then, you won't see a "Packages" section in your repository.

### Image Names

Images will be pushed to GitHub Container Registry (ghcr.io) as:
- `ghcr.io/{OWNER}/{REPO}/backend:{tag}`
- `ghcr.io/{OWNER}/{REPO}/frontend:{tag}`

For example, for repository `roblockwood/Shatter-NC` (note: repository name is converted to lowercase):
- `ghcr.io/roblockwood/shatter-nc/backend:latest`
- `ghcr.io/roblockwood/shatter-nc/backend:abc1234` (commit SHA)
- `ghcr.io/roblockwood/shatter-nc/backend:2025-12-15-abc1234` (date + commit)
- `ghcr.io/roblockwood/shatter-nc/frontend:latest`
- `ghcr.io/roblockwood/shatter-nc/frontend:abc1234`
- `ghcr.io/roblockwood/shatter-nc/frontend:2025-12-15-abc1234`

### Viewing Packages

Packages will appear after the first successful build. To view them:

**Option 1: From your profile/organization**
- Go to: `https://github.com/{OWNER}?tab=packages`
- This shows all packages across all your repositories

**Option 2: From the repository (after packages exist)**
- Go to your repository on GitHub
- Look for a "Packages" section in the right sidebar (below "About")
- Or navigate to: `https://github.com/{OWNER}/{REPO}/packages`

**Option 3: Direct package link (after first build)**
- Backend: `https://github.com/{OWNER}/{REPO}/pkgs/container/backend`
- Frontend: `https://github.com/{OWNER}/{REPO}/pkgs/container/frontend`

**Note:** Docker image names must be lowercase. The workflow automatically converts the repository name to lowercase (e.g., `Shatter-NC` becomes `shatter-nc` in image names).

### Usage

After images are pushed, you can pull them on your deployment server. First, authenticate with GitHub Packages:

```bash
# Create a Personal Access Token (PAT) with 'read:packages' permission
# Then login:
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

Then pull images:

```bash
# Pull latest images (note: repository name is lowercase)
docker pull ghcr.io/roblockwood/shatter-nc/backend:latest
docker pull ghcr.io/roblockwood/shatter-nc/frontend:latest
```

Or use specific commit tags:
```bash
# Pull by commit SHA
docker pull ghcr.io/roblockwood/shatter-nc/backend:abc1234
docker pull ghcr.io/roblockwood/shatter-nc/frontend:abc1234

# Pull by date + commit
docker pull ghcr.io/roblockwood/shatter-nc/backend:2025-12-15-abc1234
docker pull ghcr.io/roblockwood/shatter-nc/frontend:2025-12-15-abc1234
```

### Updating docker-compose files

To use pre-built images from GitHub Container Registry, use `docker-compose.prod.yml`:

```yaml
backend:
  image: ghcr.io/roblockwood/shatter-nc/backend:latest  # or specific tag

frontend:
  image: ghcr.io/roblockwood/shatter-nc/frontend:latest  # or specific tag
```

Or set environment variables in `.env`:

```bash
GITHUB_OWNER=roblockwood
GITHUB_REPO=shatter-nc
IMAGE_TAG=latest  # or v1.2.3, commit SHA, etc.
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

See [docs/INSTALLATION_GUIDE.md](../docs/INSTALLATION_GUIDE.md) for the full operator install flow (no git clone required).

### Package Visibility

By default, packages are private to the repository. To make them public:
1. Go to your repository → Packages
2. Click on the package
3. Go to Package settings → Change visibility → Make public

