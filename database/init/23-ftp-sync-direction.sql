-- Add sync direction to ftp_sync_configs so jobs can run upload or download

ALTER TABLE ftp_sync_configs
    ADD COLUMN IF NOT EXISTS sync_direction VARCHAR(16) NOT NULL DEFAULT 'upload';

DO $$
BEGIN
    RAISE NOTICE 'FTP sync direction column added';
END $$;
