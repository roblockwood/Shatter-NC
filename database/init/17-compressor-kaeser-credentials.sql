-- Kaeser Connect credentials stored in Shatter DB; backend polls SIGMA CONTROL 2 directly (see integrations/kaeser_sc2/client.py).

ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_connect_base_url VARCHAR(512);
ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_username VARCHAR(255);
ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_password VARCHAR(255);
