-- Fix foreign key constraint on program_deployments.replaced_by
-- This migration updates the constraint to allow cascading deletions
-- Required to fix machine deletion errors

-- Drop the old foreign key constraint
ALTER TABLE program_deployments
DROP CONSTRAINT IF EXISTS program_deployments_replaced_by_fkey;

-- Add the new constraint with ON DELETE SET NULL
ALTER TABLE program_deployments
ADD CONSTRAINT program_deployments_replaced_by_fkey
FOREIGN KEY (replaced_by) REFERENCES program_deployments(id) ON DELETE SET NULL;

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE program_deployments TO shatter_user;
