-- Legacy migration retained as a safe no-op.
-- Compressors are now polled backend-direct, and the sidecar columns have been removed.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'compressors' AND column_name = 'modbus_port'
  ) THEN
    ALTER TABLE compressors DROP COLUMN modbus_port;
    ALTER TABLE compressors DROP COLUMN modbus_unit_id;
  END IF;
END $$;
