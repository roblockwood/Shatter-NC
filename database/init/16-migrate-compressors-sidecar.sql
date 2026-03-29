-- Migrate existing compressors table from Modbus columns to Kaeser sidecar (Brown-Industries kaeser-sc2-api).
-- Safe no-op when table already uses sidecar columns (fresh install from updated 15-add-compressors.sql).

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'compressors' AND column_name = 'modbus_port'
  ) THEN
    ALTER TABLE compressors ADD COLUMN IF NOT EXISTS sidecar_rest_base_url VARCHAR(512);
    ALTER TABLE compressors ADD COLUMN IF NOT EXISTS mqtt_topic_root VARCHAR(255);
    UPDATE compressors SET sidecar_rest_base_url = COALESCE(NULLIF(TRIM(sidecar_rest_base_url), ''), 'http://kaeser-sc2-api:3004')
      WHERE sidecar_rest_base_url IS NULL;
    UPDATE compressors SET mqtt_topic_root = COALESCE(NULLIF(TRIM(mqtt_topic_root), ''), 'kaeser-sc2')
      WHERE mqtt_topic_root IS NULL;
    ALTER TABLE compressors ALTER COLUMN sidecar_rest_base_url SET NOT NULL;
    ALTER TABLE compressors ALTER COLUMN mqtt_topic_root SET NOT NULL;
    ALTER TABLE compressors DROP COLUMN modbus_port;
    ALTER TABLE compressors DROP COLUMN modbus_unit_id;
  END IF;
END $$;
