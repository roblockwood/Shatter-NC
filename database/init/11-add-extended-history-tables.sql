-- Add extended history tables for long-term storage of machine data
-- These tables use a hybrid 'Log-on-Change + Heartbeat' approach

-- 1. Macro History Table
CREATE TABLE IF NOT EXISTS macro_history (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    change_type VARCHAR(20) NOT NULL, -- 'change' or 'heartbeat'
    PRIMARY KEY (time, machine_id)
);
SELECT create_hypertable('macro_history', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_macro_history_machine_time ON macro_history (machine_id, time DESC);

-- Enable compression for macro history
ALTER TABLE macro_history SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'machine_id'
);
SELECT add_compression_policy('macro_history', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('macro_history', INTERVAL '1 year', if_not_exists => TRUE);

-- 2. Tool Table History Table
CREATE TABLE IF NOT EXISTS tool_table_history (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    change_type VARCHAR(20) NOT NULL, -- 'change' or 'heartbeat'
    PRIMARY KEY (time, machine_id)
);
SELECT create_hypertable('tool_table_history', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_tool_table_history_machine_time ON tool_table_history (machine_id, time DESC);

-- Enable compression for tool table history
ALTER TABLE tool_table_history SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'machine_id'
);
SELECT add_compression_policy('tool_table_history', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('tool_table_history', INTERVAL '1 year', if_not_exists => TRUE);

-- 3. Panel History Table
CREATE TABLE IF NOT EXISTS panel_history (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    change_type VARCHAR(20) NOT NULL, -- 'change' or 'heartbeat'
    PRIMARY KEY (time, machine_id)
);
SELECT create_hypertable('panel_history', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_panel_history_machine_time ON panel_history (machine_id, time DESC);

-- Enable compression for panel history
ALTER TABLE panel_history SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'machine_id'
);
SELECT add_compression_policy('panel_history', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('panel_history', INTERVAL '1 year', if_not_exists => TRUE);

-- 4. Counter History Table
CREATE TABLE IF NOT EXISTS counter_history (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    change_type VARCHAR(20) NOT NULL, -- 'change' or 'heartbeat'
    PRIMARY KEY (time, machine_id)
);
SELECT create_hypertable('counter_history', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_counter_history_machine_time ON counter_history (machine_id, time DESC);

-- Enable compression for counter history
ALTER TABLE counter_history SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'machine_id'
);
SELECT add_compression_policy('counter_history', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('counter_history', INTERVAL '1 year', if_not_exists => TRUE);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE macro_history TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE tool_table_history TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE panel_history TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE counter_history TO shatter_user;

DO $$
BEGIN
    RAISE NOTICE 'Extended history tables created as TimescaleDB hypertables';
END $$;
