-- Add polling events table for tracking HTTP polling history
-- This enables historical polling data visualization

-- Create polling_events table as TimescaleDB hypertable
CREATE TABLE IF NOT EXISTS polling_events (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    response_time_ms INTEGER,
    error_message VARCHAR(500)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('polling_events', 'time', if_not_exists => TRUE);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_polling_events_machine_time
    ON polling_events (machine_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_polling_events_success
    ON polling_events (success);

-- Enable compression for polling events
ALTER TABLE polling_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'machine_id'
);
SELECT add_compression_policy('polling_events', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('polling_events', INTERVAL '1 year', if_not_exists => TRUE);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE polling_events TO shatter_user;

DO $$
BEGIN
    RAISE NOTICE 'Polling events table created as TimescaleDB hypertable';
END $$;
