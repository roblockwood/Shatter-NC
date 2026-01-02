-- Add units column to machines table
-- Specifies whether the machine is configured in inches (in) or millimeters (mm)
-- This affects how tolerances and measurements are interpreted

ALTER TABLE machines 
ADD COLUMN IF NOT EXISTS units VARCHAR(2) DEFAULT 'in' CHECK (units IN ('in', 'mm'));

-- Add comment explaining the units field
COMMENT ON COLUMN machines.units IS 'Measurement units for the machine: "in" for inches, "mm" for millimeters';

-- Print confirmation
DO $$
BEGIN
    RAISE NOTICE 'Units column added to machines table';
END $$;

GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;

