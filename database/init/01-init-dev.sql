-- Initialize Shatter database (development version without TimescaleDB)
-- This script runs automatically when the PostgreSQL container first starts

-- Create machines table
CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    model VARCHAR(100) DEFAULT 'Brother CNC',
    ip_address VARCHAR(45) NOT NULL,
    ftp_port INTEGER DEFAULT 21,
    http_port INTEGER DEFAULT 80,
    ftp_username VARCHAR(255) DEFAULT 'anonymous',
    ftp_password VARCHAR(255) DEFAULT 'anonymous',
    location VARCHAR(255),
    tags JSONB,
    poll_interval_seconds INTEGER DEFAULT 5,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    connection_status VARCHAR(20) DEFAULT 'unknown'
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_machines_enabled ON machines(enabled);
CREATE INDEX IF NOT EXISTS idx_machines_connection_status ON machines(connection_status);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE machines_id_seq TO shatter_user;
