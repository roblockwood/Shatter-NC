-- Add tolerance override flags to machines table
-- These flags control whether to use machine-defined tolerances or G-code defaults
-- When FALSE (default): Use G-code values (E parameter for WCS, exact match for tools)
-- When TRUE: Use machine database tolerance settings

ALTER TABLE machines 
ADD COLUMN IF NOT EXISTS use_machine_tool_tolerances BOOLEAN DEFAULT FALSE;

ALTER TABLE machines 
ADD COLUMN IF NOT EXISTS use_machine_wcs_tolerances BOOLEAN DEFAULT FALSE;

-- Add comments explaining the tolerance override flags
COMMENT ON COLUMN machines.use_machine_tool_tolerances IS 'When TRUE, use machine-defined tool tolerances. When FALSE (default), use G-code defaults: exact diameter match, length must be >= required';
COMMENT ON COLUMN machines.use_machine_wcs_tolerances IS 'When TRUE, use machine-defined WCS tolerances. When FALSE (default), use E parameter from G-code WCS validation macro if present';

-- Print confirmation
DO $$
BEGIN
    RAISE NOTICE 'Tolerance override flags added to machines table';
END $$;

GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;

