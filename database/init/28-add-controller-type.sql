-- Add controller_type and controller_config for multi-vendor CNC support.
-- Existing machines default to 'brother' (Brother Protocol Type 2 / Telnet).

ALTER TABLE machines
ADD COLUMN IF NOT EXISTS controller_type VARCHAR(32) NOT NULL DEFAULT 'brother';

ALTER TABLE machines
ADD COLUMN IF NOT EXISTS controller_config JSONB;

ALTER TABLE machines
DROP CONSTRAINT IF EXISTS machines_controller_type_check;

ALTER TABLE machines
ADD CONSTRAINT machines_controller_type_check
CHECK (controller_type IN ('brother', 'heidenhain'));

COMMENT ON COLUMN machines.controller_type IS 'CNC controller family: brother, heidenhain, ...';
COMMENT ON COLUMN machines.controller_config IS 'Controller-specific connection config (e.g. OPC UA port/credentials)';

DO $$
BEGIN
    RAISE NOTICE 'controller_type and controller_config columns ensured on machines table';
END $$;

GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;
