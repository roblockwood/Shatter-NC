-- Add Brother file exclusion and naming policy fields to ftp_sync_configs

ALTER TABLE ftp_sync_configs
    ADD COLUMN IF NOT EXISTS exclude_patterns VARCHAR(1024) NOT NULL DEFAULT '.*,~*,*.tmp,*.temp,*.bak,*.swp,*.DS_Store',
    ADD COLUMN IF NOT EXISTS control_type VARCHAR(8) NOT NULL DEFAULT 'C00',
    ADD COLUMN IF NOT EXISTS strict_brother_naming BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS require_onumber_filename BOOLEAN NOT NULL DEFAULT TRUE;

DO $$
BEGIN
    RAISE NOTICE 'FTP sync exclusion rule columns added';
END $$;
