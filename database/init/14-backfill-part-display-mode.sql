-- Ensure machines.part_display_mode exists and is populated

ALTER TABLE machines
  ADD COLUMN IF NOT EXISTS part_display_mode VARCHAR(20);

ALTER TABLE machines
  ALTER COLUMN part_display_mode SET DEFAULT 'parts';

UPDATE machines
SET part_display_mode = 'parts'
WHERE part_display_mode IS NULL;

