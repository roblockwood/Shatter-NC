# Migration: Remove Redis

As of this release, Shatter no longer uses Redis. All previous Redis-backed behavior (per-machine locks, status/tool cache, API rate limiting) now uses in-process equivalents. This document tells existing users what to change in their deployment.

## What to change

### Compose (dev and prod)

- **Remove the `redis` service**  
  Delete the entire `redis` service block from your compose file(s):
  - `docker-compose.dev.yml`
  - `docker-compose.prod.yml`

- **Update the `backend` service**
  - Remove from `environment`: `REDIS_HOST`, and (in prod) `REDIS_PASSWORD`.
  - Remove `redis` from `depends_on`. Keep only `postgres` (and `condition: service_healthy` where present).
  - Under top-level `volumes`: remove the `redis_data` volume.

### Environment / .env

- Remove or stop setting `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD`. The application no longer reads them. Leaving them in `.env` is harmless but can be removed to avoid confusion.

No code or config changes are required on your side beyond compose and env; the new image/code already runs without Redis.

## Clearing the Redis volume (optional)

Redis only held ephemeral data (locks, status/tool cache, rate-limit counters). There is no data to migrate. You may remove the volume to free disk space.

1. **Stop the stack** so the Redis container is not running:
   - Dev: `docker compose -f docker-compose.dev.yml down`
   - Prod: `docker compose -f docker-compose.prod.yml down`

2. **Find the Redis volume name.** It is usually `<project>_redis_data` (project name is often the compose directory name or set by `-p` / `COMPOSE_PROJECT_NAME`):
   ```bash
   docker volume ls | grep redis
   ```

3. **Remove only the Redis volume** (replace with the name from step 2):
   ```bash
   docker volume rm <project>_redis_data
   ```
   Example: `docker volume rm shatter_redis_data`

**Do not** use `docker compose down -v` unless you intend to remove all named volumes (e.g. `postgres_data` would be removed and the database would be lost). Use `down` without `-v`, then remove only the Redis volume as above.

## Recommended upgrade order

1. Pull the latest images/code (no Redis dependency).
2. Stop the stack: `docker compose -f <compose-file> down`.
3. (Optional) Remove the Redis volume as above.
4. Edit your compose file and `.env` to remove the Redis service, backend Redis env and `depends_on`, and `redis_data` volume (and REDIS_* from env).
5. Start the stack: `docker compose -f <compose-file> up -d`.
6. Confirm the backend is healthy (e.g. `GET /health` returns 200). No Redis container should be running.

## Behavioral notes

- **Single backend:** Behavior is unchanged. Locks, cache, and rate limiting are in-process.
- **After a backend restart:** Status/tool cache and control-version cache are in memory and repopulate on the next poll; the first load after restart may be briefly empty or stale until the first poll completes.
- **Multiple backends:** If you run more than one backend replica, rate limiting and cache are per process (not shared). This is only relevant if you scale the backend horizontally.
