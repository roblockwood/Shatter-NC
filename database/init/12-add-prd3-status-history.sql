-- Add PRD3 status history table for status/runs derived from PRD3/PRDD3

CREATE TABLE IF NOT EXISTS prd3_status_history (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,

    -- Status information
    status VARCHAR(50) NOT NULL,
    status_code INTEGER NOT NULL,

    -- Program/error context
    program_no VARCHAR(50),
    error_no VARCHAR(50),
    folder_name VARCHAR(500),
    memory_operation_type INTEGER,

    -- Raw payload (decoded PRD3 row) for debugging/extensibility
    raw JSONB,

    PRIMARY KEY (time, machine_id)
);

-- Create hypertable on time
SELECT create_hypertable('prd3_status_history', 'time', if_not_exists => TRUE);

-- Helpful index for machine/time queries
CREATE INDEX IF NOT EXISTS idx_prd3_status_history_machine_time
    ON prd3_status_history (machine_id, time DESC);

-- Enable compression and retention similar to other history tables
ALTER TABLE prd3_status_history SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'machine_id'
);

SELECT add_compression_policy('prd3_status_history', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('prd3_status_history', INTERVAL '1 year', if_not_exists => TRUE);

-- Grant access to application user
GRANT ALL PRIVILEGES ON TABLE prd3_status_history TO shatter_user;

DO $$
BEGIN
    RAISE NOTICE 'PRD3 status history table created as TimescaleDB hypertable';
END $$;
