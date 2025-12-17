-- Add layout_config column to machines table for storing custom pane layouts
-- This allows each machine to have its own customized detail pane layout

ALTER TABLE machines 
ADD COLUMN IF NOT EXISTS layout_config JSONB;

-- Create index for faster queries (though JSONB queries are already indexed)
-- This is optional but can help with queries filtering by layout_config
CREATE INDEX IF NOT EXISTS idx_machines_layout_config ON machines USING GIN (layout_config);

-- Print confirmation
DO $$
BEGIN
    RAISE NOTICE 'Layout config column added to machines table';
END $$;


