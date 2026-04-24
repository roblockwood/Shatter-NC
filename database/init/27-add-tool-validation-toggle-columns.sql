-- Add per-machine tool validation toggles
-- Allows disabling diameter or length validation independently.

ALTER TABLE machines
ADD COLUMN IF NOT EXISTS validate_tool_diameter BOOLEAN DEFAULT TRUE;

ALTER TABLE machines
ADD COLUMN IF NOT EXISTS validate_tool_length BOOLEAN DEFAULT TRUE;

UPDATE machines
SET validate_tool_diameter = TRUE
WHERE validate_tool_diameter IS NULL;

UPDATE machines
SET validate_tool_length = TRUE
WHERE validate_tool_length IS NULL;

DO $$
BEGIN
    RAISE NOTICE 'Tool validation toggle columns ensured on machines table';
END $$;

GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;
