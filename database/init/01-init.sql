-- Initialize Shatter database with TimescaleDB extension
-- This script runs automatically when the PostgreSQL container first starts

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create machines table
CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    model VARCHAR(100) DEFAULT 'Brother CNC',
    ip_address VARCHAR(45) NOT NULL,
    telnet_host VARCHAR(255),
    telnet_port INTEGER DEFAULT 10000,
    ftp_host VARCHAR(255),
    ftp_port INTEGER DEFAULT 21,
    http_host VARCHAR(255),
    http_port INTEGER DEFAULT 80,
    ftp_username VARCHAR(255) DEFAULT 'anonymous',
    ftp_password VARCHAR(255) DEFAULT 'anonymous',
    path VARCHAR(255) DEFAULT '/program',
    tags JSONB,
    poll_interval_seconds INTEGER DEFAULT 5,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_machines_enabled ON machines(enabled);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE machines_id_seq TO shatter_user;

-- Print confirmation
DO $$
BEGIN
    RAISE NOTICE 'Shatter database initialized successfully';
    RAISE NOTICE 'TimescaleDB extension enabled';
    RAISE NOTICE 'Machines table created';
END $$;
