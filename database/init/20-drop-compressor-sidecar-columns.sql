-- Drop legacy sidecar fields from compressors table (backend-direct Kaeser polling).
-- Safe to run multiple times / on older DBs.

ALTER TABLE compressors
  DROP COLUMN IF EXISTS sidecar_rest_base_url,
  DROP COLUMN IF EXISTS mqtt_topic_root;

