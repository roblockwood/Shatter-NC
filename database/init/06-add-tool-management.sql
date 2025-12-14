-- Add tool management tables and indexes for Shatter database
-- This script adds support for:
-- - Tool instance tracking (physical tool lifecycle management)
-- - Performance indexes for tool analysis queries
-- - Optimized JSONB queries on program metadata

-- ==================== TOOL INSTANCE TRACKING ====================

-- Tool instances table: Track physical tool lifecycle
-- Initially unpopulated - infrastructure for future tool replacement tracking
CREATE TABLE IF NOT EXISTS tool_instances (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    tool_number INTEGER NOT NULL,

    -- Tool specifications
    diameter FLOAT NOT NULL,
    corner_radius FLOAT DEFAULT 0,
    description VARCHAR(500),
    length_total FLOAT,

    -- Lifecycle tracking
    installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at TIMESTAMPTZ,
    removal_reason VARCHAR(100),  -- 'normal_wear', 'breakage', 'upgrade', 'scheduled'

    -- Usage metrics (aggregated from production runs)
    total_runtime_seconds INTEGER DEFAULT 0,
    total_parts_produced INTEGER DEFAULT 0,
    total_cycles INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_removal_date CHECK (removed_at IS NULL OR removed_at >= installed_at)
);

-- Indexes for tool instance queries
CREATE INDEX IF NOT EXISTS idx_tool_instances_machine_tool
    ON tool_instances (machine_id, tool_number);
CREATE INDEX IF NOT EXISTS idx_tool_instances_active
    ON tool_instances (machine_id, tool_number, is_active)
    WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_tool_instances_installed
    ON tool_instances (installed_at);

-- Unique constraint: Only one active tool instance per machine/tool number
CREATE UNIQUE INDEX IF NOT EXISTS idx_tool_instances_unique_active
    ON tool_instances (machine_id, tool_number, is_active)
    WHERE is_active = TRUE;

-- ==================== PERFORMANCE INDEXES ====================

-- Critical GIN index for JSONB tool queries
-- Enables fast extraction of tools from program_metadata
CREATE INDEX IF NOT EXISTS idx_program_metadata_tools
    ON programs USING GIN (program_metadata jsonb_path_ops);

-- Optimize production run queries by program and date
-- Supports tool runtime aggregation queries
CREATE INDEX IF NOT EXISTS idx_production_runs_program_dates
    ON production_runs (program_id, started_at DESC);

-- Optimize alarm correlation with programs
-- Supports tool failure analysis
CREATE INDEX IF NOT EXISTS idx_alarm_events_program_time
    ON alarm_events (program_id, time DESC);

-- ==================== PERMISSIONS ====================

-- Grant permissions to shatter_user
GRANT ALL PRIVILEGES ON TABLE tool_instances TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE tool_instances_id_seq TO shatter_user;

-- ==================== COMPLETION NOTICE ====================

DO $$
BEGIN
    RAISE NOTICE 'Tool management tables and indexes created successfully';
    RAISE NOTICE 'tool_instances table: Ready for future tool replacement tracking';
    RAISE NOTICE 'Performance indexes: Optimized for JSONB tool queries';
END $$;
