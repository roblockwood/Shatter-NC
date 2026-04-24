-- Add FTP folder sync tables for local-folder-to-machine upload workflows

CREATE TABLE IF NOT EXISTS ftp_sync_configs (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_folder VARCHAR(1024) NOT NULL,
    remote_folder VARCHAR(1024) NOT NULL DEFAULT '/',
    include_pattern VARCHAR(255) NOT NULL DEFAULT '*.NC',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    auto_validate BOOLEAN NOT NULL DEFAULT TRUE,
    auto_register BOOLEAN NOT NULL DEFAULT TRUE,
    debounce_seconds INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ftp_sync_configs_machine
    ON ftp_sync_configs(machine_id);
CREATE INDEX IF NOT EXISTS idx_ftp_sync_configs_enabled
    ON ftp_sync_configs(enabled);

CREATE TABLE IF NOT EXISTS ftp_sync_runs (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES ftp_sync_configs(id) ON DELETE CASCADE,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    trigger_source VARCHAR(50) NOT NULL DEFAULT 'manual',
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    total_files INTEGER NOT NULL DEFAULT 0,
    success_files INTEGER NOT NULL DEFAULT 0,
    failed_files INTEGER NOT NULL DEFAULT 0,
    conflict_files INTEGER NOT NULL DEFAULT 0,
    skipped_files INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ftp_sync_runs_machine_created
    ON ftp_sync_runs(machine_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ftp_sync_runs_config_created
    ON ftp_sync_runs(config_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ftp_sync_runs_status
    ON ftp_sync_runs(status);

CREATE TABLE IF NOT EXISTS ftp_sync_run_items (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES ftp_sync_runs(id) ON DELETE CASCADE,
    relative_path VARCHAR(1024) NOT NULL,
    local_path VARCHAR(2048) NOT NULL,
    remote_path VARCHAR(1024) NOT NULL,
    content_hash VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    error_message TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ftp_sync_run_items_run
    ON ftp_sync_run_items(run_id);
CREATE INDEX IF NOT EXISTS idx_ftp_sync_run_items_status
    ON ftp_sync_run_items(status);

CREATE TABLE IF NOT EXISTS ftp_sync_file_states (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES ftp_sync_configs(id) ON DELETE CASCADE,
    relative_path VARCHAR(1024) NOT NULL,
    last_uploaded_hash VARCHAR(64) NOT NULL,
    last_uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_uploaded_remote_path VARCHAR(1024) NOT NULL,
    CONSTRAINT uq_ftp_sync_file_state_config_path UNIQUE (config_id, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_ftp_sync_file_states_config
    ON ftp_sync_file_states(config_id);

GRANT ALL PRIVILEGES ON TABLE ftp_sync_configs TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE ftp_sync_runs TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE ftp_sync_run_items TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE ftp_sync_file_states TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE ftp_sync_configs_id_seq TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE ftp_sync_runs_id_seq TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE ftp_sync_run_items_id_seq TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE ftp_sync_file_states_id_seq TO shatter_user;

DO $$
BEGIN
    RAISE NOTICE 'FTP sync tables created';
END $$;
