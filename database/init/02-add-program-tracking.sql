-- Add program tracking and event logging tables to Shatter database
-- This script adds support for:
-- - NC program versioning and deployment tracking
-- - Machine status change history
-- - Alarm event logging
-- - Production run tracking

-- ==================== CORE TABLES ====================

-- Programs table: Global registry with version tracking
CREATE TABLE IF NOT EXISTS programs (
    id SERIAL PRIMARY KEY,

    -- Program identity (filename-based)
    original_filename VARCHAR(500) NOT NULL,
    content_hash VARCHAR(64) NOT NULL UNIQUE,

    -- Versioning
    posted_date TIMESTAMPTZ,                  -- From CAM header
    version_number INTEGER NOT NULL,

    -- Parsed metadata (JSONB for flexibility)
    program_metadata JSONB NOT NULL DEFAULT '{}',
    -- Structure: {
    --   "tools": [{"tool_number": 1, "diameter": 0.25, "corner_radius": 0, ...}],
    --   "wcs_offset": {"x": -21.99, "y": -2.85, "z": -15.89, "work_offset": 54, "tolerance": 2.0},
    --   "stock_size": {"x": 146.05, "y": 25.4, "z": 12.7}
    -- }

    -- File characteristics
    file_size_bytes INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    estimated_runtime_seconds FLOAT,

    -- Audit
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_deployed_at TIMESTAMPTZ,
    deployed_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    -- Constraints
    CONSTRAINT unique_content UNIQUE(content_hash),
    CONSTRAINT unique_version UNIQUE(original_filename, version_number),
    CONSTRAINT positive_version CHECK(version_number > 0)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_programs_filename ON programs(original_filename);
CREATE INDEX IF NOT EXISTS idx_programs_hash ON programs(content_hash);
CREATE INDEX IF NOT EXISTS idx_programs_posted_date ON programs(posted_date);
CREATE INDEX IF NOT EXISTS idx_programs_active ON programs(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_programs_metadata_gin ON programs USING gin(program_metadata);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE programs TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE programs_id_seq TO shatter_user;


-- Program deployments: Track when programs are uploaded to machines
CREATE TABLE IF NOT EXISTS program_deployments (
    id SERIAL PRIMARY KEY,

    -- References
    program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,

    -- Deployment details
    deployed_filename VARCHAR(500) NOT NULL,  -- "O2000.nc" format
    deployed_path VARCHAR(500) NOT NULL,      -- "/PROGRAM/O2000.nc"

    -- Timing
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_by VARCHAR(255),                 -- Future: user tracking

    -- Validation results (captured at deploy time)
    validation_results JSONB,
    validation_passed BOOLEAN DEFAULT TRUE,

    -- O-number reuse tracking
    is_current BOOLEAN DEFAULT TRUE,
    replaced_at TIMESTAMPTZ,
    replaced_by INTEGER REFERENCES program_deployments(id),

    CONSTRAINT unique_machine_filename UNIQUE(machine_id, deployed_filename, deployed_at)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_deployments_program ON program_deployments(program_id);
CREATE INDEX IF NOT EXISTS idx_deployments_machine ON program_deployments(machine_id);
CREATE INDEX IF NOT EXISTS idx_deployments_current ON program_deployments(machine_id, is_current)
    WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_deployments_deployed_at ON program_deployments(deployed_at DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE program_deployments TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE program_deployments_id_seq TO shatter_user;


-- ==================== EVENT TABLES (TimescaleDB Hypertables) ====================

-- Machine status events: Track status transitions
CREATE TABLE IF NOT EXISTS machine_status_events (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,

    status VARCHAR(50) NOT NULL,              -- 'running', 'stopped', 'error', 'alarm', 'idle'
    previous_status VARCHAR(50),

    program_name VARCHAR(500),
    o_number VARCHAR(50),

    metrics JSONB,                            -- {cycle_time_seconds, cutting_time_seconds, power_on_hours}

    PRIMARY KEY (time, machine_id)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('machine_status_events', 'time', if_not_exists => TRUE);

-- Retention policy: keep 1 year
SELECT add_retention_policy('machine_status_events', INTERVAL '1 year', if_not_exists => TRUE);

-- Compression policy: compress after 7 days
SELECT add_compression_policy('machine_status_events', INTERVAL '7 days', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_status_machine_time ON machine_status_events(machine_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_status_status ON machine_status_events(status);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE machine_status_events TO shatter_user;


-- Alarm events: Track alarm occurrences
CREATE TABLE IF NOT EXISTS alarm_events (
    time TIMESTAMPTZ NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    alarm_code VARCHAR(50) NOT NULL,

    alarm_message TEXT NOT NULL,
    alarm_type VARCHAR(50),
    severity VARCHAR(20),

    program_id INTEGER REFERENCES programs(id),
    deployment_id INTEGER REFERENCES program_deployments(id),

    cleared_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    cleared_by VARCHAR(255),
    resolution_notes TEXT,

    PRIMARY KEY (time, machine_id, alarm_code)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('alarm_events', 'time', if_not_exists => TRUE);

-- Retention policy: keep 2 years
SELECT add_retention_policy('alarm_events', INTERVAL '2 years', if_not_exists => TRUE);

-- Compression policy: compress after 30 days
SELECT add_compression_policy('alarm_events', INTERVAL '30 days', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_alarms_machine_time ON alarm_events(machine_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_alarms_code ON alarm_events(alarm_code);
CREATE INDEX IF NOT EXISTS idx_alarms_active ON alarm_events(cleared_at) WHERE cleared_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_alarms_program ON alarm_events(program_id) WHERE program_id IS NOT NULL;

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE alarm_events TO shatter_user;


-- Production runs: Track program execution
CREATE TABLE IF NOT EXISTS production_runs (
    id SERIAL PRIMARY KEY,

    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,

    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    program_id INTEGER REFERENCES programs(id),
    deployment_id INTEGER REFERENCES program_deployments(id),

    program_name VARCHAR(500),
    o_number VARCHAR(50),

    cycle_count INTEGER DEFAULT 0,
    parts_produced INTEGER DEFAULT 0,
    duration_seconds INTEGER,

    actual_cycle_time_seconds FLOAT,
    estimated_cycle_time_seconds FLOAT,
    efficiency_percent FLOAT,

    completion_status VARCHAR(50),            -- 'completed', 'aborted', 'alarm', 'interrupted'
    abort_reason VARCHAR(500),

    alarm_count INTEGER DEFAULT 0,
    total_downtime_seconds INTEGER DEFAULT 0,

    CONSTRAINT valid_time_range CHECK (ended_at IS NULL OR ended_at >= started_at)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('production_runs', 'started_at', if_not_exists => TRUE);

-- Retention policy: keep 5 years
SELECT add_retention_policy('production_runs', INTERVAL '5 years', if_not_exists => TRUE);

-- Compression policy: compress after 90 days
SELECT add_compression_policy('production_runs', INTERVAL '90 days', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_runs_machine_time ON production_runs(machine_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_program ON production_runs(program_id) WHERE program_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_runs_active ON production_runs(ended_at) WHERE ended_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_runs_status ON production_runs(completion_status);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE production_runs TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE production_runs_id_seq TO shatter_user;


-- ==================== CONFIRMATION ====================

DO $$
BEGIN
    RAISE NOTICE 'Program tracking tables created successfully';
    RAISE NOTICE '  - programs: Global program registry with version tracking';
    RAISE NOTICE '  - program_deployments: O-number deployment tracking';
    RAISE NOTICE '  - machine_status_events: Status change history (TimescaleDB)';
    RAISE NOTICE '  - alarm_events: Alarm event logging (TimescaleDB)';
    RAISE NOTICE '  - production_runs: Program execution tracking (TimescaleDB)';
    RAISE NOTICE 'All tables configured with retention and compression policies';
END $$;
