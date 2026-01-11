-- Add tool_poll_interval_seconds column to machines table
-- This controls how frequently tool table and ATC magazine data is polled (slower than fast status polling)
-- Default: 30 seconds (separate from poll_interval_seconds which defaults to 5 seconds)

ALTER TABLE machines ADD COLUMN IF NOT EXISTS tool_poll_interval_seconds INTEGER DEFAULT 30;

-- Update existing machines to use default if NULL (shouldn't be needed due to DEFAULT, but being safe)
UPDATE machines SET tool_poll_interval_seconds = 30 WHERE tool_poll_interval_seconds IS NULL;

