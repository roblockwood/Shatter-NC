-- Kaeser Connect credentials stored in Shatter; backend writes docker/generated/compressor-{id}.env for sidecar env_file.

ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_connect_base_url VARCHAR(512);
ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_username VARCHAR(255);
ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_password VARCHAR(255);
