-- Add control_version column to machines table
-- Allows explicit machine control selection instead of runtime inference.
-- Values:
--   NULL  -> auto-detect
--   C00   -> force C00 protocol behavior
--   D00   -> force D00 protocol behavior

ALTER TABLE machines
ADD COLUMN IF NOT EXISTS control_version VARCHAR(3);

-- Ensure only valid values are stored.
ALTER TABLE machines
DROP CONSTRAINT IF EXISTS machines_control_version_check;

ALTER TABLE machines
ADD CONSTRAINT machines_control_version_check
CHECK (control_version IS NULL OR control_version IN ('C00', 'D00'));

COMMENT ON COLUMN machines.control_version IS 'Control version override: C00, D00, or NULL for auto-detect';

DO $$
BEGIN
    RAISE NOTICE 'control_version column ensured on machines table';
END $$;

GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;
