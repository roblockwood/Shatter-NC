# GitHub Actions Workflows

## Docker Build and Push

The `docker-build-push.yml` workflow automatically builds and pushes Docker images to Docker Hub when code is merged into the `main` branch.

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

### Required Secrets

Configure these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

- **`DOCKER_HUB_USERNAME`** - Your Docker Hub username (required)
- **`DOCKER_HUB_PASSWORD`** - Your Docker Hub access token or password (required)
- **`DOCKER_HUB_REPOSITORY`** - Repository name prefix (optional, defaults to `shatter-nc` if not set)

### Docker Hub Setup

1. Create a Docker Hub account if you don't have one
2. Create an access token:
   - Go to Docker Hub → Account Settings → Security
   - Click "New Access Token"
   - Give it a name (e.g., "GitHub Actions")
   - Copy the token (you'll only see it once)
3. Add the token as `DOCKER_HUB_PASSWORD` secret in GitHub

### Image Names

Images will be pushed as:
- `{DOCKER_HUB_USERNAME}/{DOCKER_HUB_REPOSITORY}-backend:{tag}`
- `{DOCKER_HUB_USERNAME}/{DOCKER_HUB_REPOSITORY}-frontend:{tag}`

For example, if `DOCKER_HUB_USERNAME=shatter-nc` and `DOCKER_HUB_REPOSITORY=shatter-nc`:
- `shatter-nc/shatter-nc-backend:latest`
- `shatter-nc/shatter-nc-backend:abc1234` (commit SHA)
- `shatter-nc/shatter-nc-backend:2025-12-15-abc1234` (date + commit)
- `shatter-nc/shatter-nc-frontend:latest`
- `shatter-nc/shatter-nc-frontend:abc1234`
- `shatter-nc/shatter-nc-frontend:2025-12-15-abc1234`

### Usage

After images are pushed, you can pull them on your deployment server:

```bash
# Pull latest images
docker pull shatter-nc/shatter-nc-backend:latest
docker pull shatter-nc/shatter-nc-frontend:latest
```

Or use specific commit tags:
```bash
# Pull by commit SHA
docker pull shatter-nc/shatter-nc-backend:abc1234
docker pull shatter-nc/shatter-nc-frontend:abc1234

# Pull by date + commit
docker pull shatter-nc/shatter-nc-backend:2025-12-15-abc1234
docker pull shatter-nc/shatter-nc-frontend:2025-12-15-abc1234
```

### Updating docker-compose.prod.yml

To use the images from Docker Hub instead of building locally, update your `docker-compose.prod.yml`:

```yaml
backend:
  image: shatter-nc/shatter-nc-backend:latest  # or specific tag
  # Remove the 'build:' section

frontend:
  image: shatter-nc/shatter-nc-frontend:latest  # or specific tag
  # Remove the 'build:' section
```

