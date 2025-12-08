-- Add validation tolerance fields to machines table
-- These fields define per-machine validation tolerances for tool diameter, length, and WCS offsets

ALTER TABLE machines ADD COLUMN IF NOT EXISTS diameter_tolerance FLOAT DEFAULT 0.010;
ALTER TABLE machines ADD COLUMN IF NOT EXISTS length_tolerance_plus FLOAT DEFAULT 0.02;
ALTER TABLE machines ADD COLUMN IF NOT EXISTS length_tolerance_minus FLOAT DEFAULT 0.0;
ALTER TABLE machines ADD COLUMN IF NOT EXISTS tolerance_x FLOAT DEFAULT 0.0394;
ALTER TABLE machines ADD COLUMN IF NOT EXISTS tolerance_y FLOAT DEFAULT 0.0394;
ALTER TABLE machines ADD COLUMN IF NOT EXISTS tolerance_z FLOAT DEFAULT 0.0394;

-- Add comments explaining the tolerance fields
COMMENT ON COLUMN machines.diameter_tolerance IS 'Tool diameter tolerance (±) in inches';
COMMENT ON COLUMN machines.length_tolerance_plus IS 'Tool length tolerance positive direction (+) in inches';
COMMENT ON COLUMN machines.length_tolerance_minus IS 'Tool length tolerance negative direction (-) in inches';
COMMENT ON COLUMN machines.tolerance_x IS 'WCS X offset tolerance (±) in inches (±1mm = 0.0394")';
COMMENT ON COLUMN machines.tolerance_y IS 'WCS Y offset tolerance (±) in inches (±1mm = 0.0394")';
COMMENT ON COLUMN machines.tolerance_z IS 'WCS Z offset tolerance (±) in inches (±1mm = 0.0394")';

GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;
