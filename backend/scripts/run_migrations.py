#!/usr/bin/env python3
"""Run pending database migrations on startup."""
import os
import sys
from pathlib import Path
import psycopg2
from sqlalchemy import create_engine, text

# Migration tracking table
MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def get_applied_migrations(engine):
    """Get list of already applied migrations."""
    with engine.connect() as conn:
        # Create migrations table if it doesn't exist
        conn.execute(text(MIGRATIONS_TABLE))
        conn.commit()

        result = conn.execute(text("SELECT filename FROM schema_migrations"))
        return {row[0] for row in result}

def get_pending_migrations(migrations_dir, applied):
    """Get list of SQL files that haven't been applied."""
    sql_files = sorted(Path(migrations_dir).glob("*.sql"))
    return [f for f in sql_files if f.name not in applied]

def apply_migration(db_config, migration_file):
    """Apply a single migration file using psql for full PostgreSQL support."""
    print(f"Applying migration: {migration_file.name}")

    import subprocess

    # Use psql to execute the migration file (handles all PostgreSQL syntax)
    cmd = [
        "psql",
        "-h", db_config['host'],
        "-p", db_config['port'],
        "-U", db_config['user'],
        "-d", db_config['database'],
        "-f", str(migration_file),
        "-v", "ON_ERROR_STOP=1"  # Stop on first error
    ]

    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']

    try:
        # Execute the migration
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout.strip())

        # Record that this migration was applied
        conn = psycopg2.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s)",
            (migration_file.name,)
        )
        conn.commit()
        cursor.close()
        conn.close()

        print(f"✓ Successfully applied: {migration_file.name}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to apply {migration_file.name}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        raise
    except Exception as e:
        print(f"✗ Failed to record migration {migration_file.name}: {e}")
        raise

def run_migrations():
    """Run all pending migrations."""
    # Get database configuration from environment
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'user': os.getenv('POSTGRES_USER', 'shatter_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'changeme'),
        'database': os.getenv('POSTGRES_DB', 'shatter')
    }

    # Build database URL for SQLAlchemy
    db_url = (
        f"postgresql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )

    # Get database connection
    engine = create_engine(db_url)

    # Determine migrations directory
    # Priority order:
    # 1. MIGRATIONS_DIR environment variable (explicit override)
    # 2. /app/migrations (migrations baked into the image - default for production)
    # 3. /docker-entrypoint-initdb.d (volume mount fallback)
    # 4. ../database/init (local development)
    migrations_dir = os.getenv("MIGRATIONS_DIR")
    if migrations_dir and Path(migrations_dir).exists():
        pass  # Use the environment variable
    elif Path("/app/migrations").exists():
        migrations_dir = "/app/migrations"
    elif Path("/docker-entrypoint-initdb.d").exists():
        migrations_dir = "/docker-entrypoint-initdb.d"
    else:
        migrations_dir = Path(__file__).parent.parent.parent / "database" / "init"

    print(f"Checking for pending migrations in: {migrations_dir}")

    # Get applied and pending migrations
    applied = get_applied_migrations(engine)
    pending = get_pending_migrations(migrations_dir, applied)

    if not pending:
        print("✓ All migrations up to date")
        return 0

    print(f"Found {len(pending)} pending migration(s)")

    # Apply each pending migration
    for migration_file in pending:
        try:
            apply_migration(db_config, migration_file)
        except Exception as e:
            print(f"Migration failed! Please fix the issue and restart.")
            return 1

    print(f"✓ Successfully applied {len(pending)} migration(s)")
    return 0

if __name__ == "__main__":
    sys.exit(run_migrations())
