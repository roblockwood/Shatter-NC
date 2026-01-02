# Database Migration Strategy

## Problem

The recurring "online status modal won't load" issue was caused by missing database tables. Specifically, the `polling_events` table didn't exist, causing the backend API to throw 500 errors.

### Root Cause

Docker's `docker-entrypoint-initdb.d` only runs SQL scripts when the PostgreSQL container is **first created**. When you:
1. Add new migration files to [`database/init/`](../database/init/)
2. Restart containers with existing database volumes
3. The new migrations **don't run** automatically

This led to a mismatch between the application code (expecting `polling_events` table) and the database schema (missing that table).

## Solution Implemented

We've implemented an **automatic migration system** that runs on every backend container startup.

### How It Works

1. **Startup Scripts**
   - **Production**: [`backend/scripts/start.sh`](../backend/scripts/start.sh) - Runs migrations then starts the app
   - **Development**: [`backend/scripts/start-dev.sh`](../backend/scripts/start-dev.sh) - Runs migrations then starts the app with hot-reload
   - Both scripts:
     - Run before the FastAPI application starts
     - Wait for PostgreSQL to be ready
     - Execute the migration runner
     - Only start the app if migrations succeed

2. **Migration Runner** ([backend/scripts/run_migrations.py](../backend/scripts/run_migrations.py))
   - Tracks applied migrations in `schema_migrations` table
   - Scans [`database/init/`](../database/init/) for `.sql` files
   - Runs only pending (unapplied) migrations
   - Records successful migrations to prevent re-running

3. **Docker Integration**
   - Dockerfile copies migration scripts and makes them executable
   - docker-compose.dev.yml mounts migration files into the container
   - Backend command changed from direct `uvicorn` to startup script

### Migration Tracking

A new table tracks which migrations have been applied:

```sql
CREATE TABLE schema_migrations (
    filename VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

### Adding New Migrations

1. **Create SQL file** in [`database/init/`](../database/init/)
   ```bash
   # Use sequential numbering
   touch database/init/06-add-new-feature.sql
   ```

2. **Write your SQL migration**
   ```sql
   -- Add description at the top
   CREATE TABLE IF NOT EXISTS new_table (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255)
   );
   ```

3. **Restart backend container**
   ```bash
   docker compose -f docker-compose.dev.yml restart backend
   ```

4. **Check logs** to verify migration ran
   ```bash
   docker logs shatter-backend --tail 20
   ```

You should see:
```
✓ All migrations up to date
# OR
Applying migration: 06-add-new-feature.sql
✓ Successfully applied: 06-add-new-feature.sql
```

### Checking Migration Status

```bash
# View applied migrations
docker exec shatter-db psql -U shatter_user -d shatter -c "SELECT * FROM schema_migrations ORDER BY applied_at;"

# View pending migrations (if migration script shows them)
docker logs shatter-backend | grep "pending migration"
```

### Troubleshooting

**Migration fails with SQL syntax error:**
- Check your SQL file for syntax errors
- Test manually: `docker exec shatter-db psql -U shatter_user -d shatter -f /docker-entrypoint-initdb.d/YOUR_FILE.sql`
- PostgreSQL-specific syntax (DO blocks, functions) is fully supported

**Backend won't start after adding migration:**
1. Check backend logs: `docker logs shatter-backend`
2. Look for the migration error message
3. Fix the SQL file
4. Restart: `docker compose -f docker-compose.dev.yml restart backend`

**Need to re-run a migration:**
```bash
# Remove from tracking table
docker exec shatter-db psql -U shatter_user -d shatter -c "DELETE FROM schema_migrations WHERE filename = '06-my-migration.sql';"

# Restart backend to re-run
docker compose -f docker-compose.dev.yml restart backend
```

**Clean slate (DANGER - loses all data):**
```bash
# Stop containers
docker compose -f docker-compose.dev.yml down

# Remove database volume
docker volume rm shatter_postgres_data

# Start fresh (runs all migrations)
docker compose -f docker-compose.dev.yml up -d
```

## Files Modified

- [`backend/scripts/run_migrations.py`](../backend/scripts/run_migrations.py) - Migration runner script
- [`backend/scripts/start.sh`](../backend/scripts/start.sh) - Production startup script (runs migrations, starts app)
- [`backend/scripts/start-dev.sh`](../backend/scripts/start-dev.sh) - Development startup script (runs migrations, starts app with hot-reload)
- [`backend/Dockerfile`](../backend/Dockerfile) - Updated to use startup scripts (start-dev.sh for development, start.sh for production)
- [`docker-compose.dev.yml`](../docker-compose.dev.yml) - Mounts migration files, uses startup script

## Benefits

1. **No more manual intervention** - Migrations run automatically
2. **No more missing tables** - New migrations apply on container restart
3. **Tracked history** - Know exactly which migrations have run
4. **Idempotent** - Safe to restart containers, won't re-run migrations
5. **Developer friendly** - Just add SQL file and restart

## Future Improvements (Optional)

If the project grows, consider migrating to [Alembic](https://alembic.sqlalchemy.org/) for:
- Python-based migrations (type safety, IDE support)
- Automatic migration generation from model changes
- Up/down migrations (rollback support)
- Better team collaboration with version control

Current approach is simpler and works well for the project's current scale.
