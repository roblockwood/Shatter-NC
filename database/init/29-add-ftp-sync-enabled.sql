-- Copyright (C) 2024 Shatter-NC contributors
-- SPDX-License-Identifier: AGPL-3.0-or-later

-- Per-machine FTP sync master enable flag

ALTER TABLE machines
ADD COLUMN IF NOT EXISTS ftp_sync_enabled BOOLEAN DEFAULT FALSE;

UPDATE machines
SET ftp_sync_enabled = FALSE
WHERE ftp_sync_enabled IS NULL;

DO $$
BEGIN
    RAISE NOTICE 'ftp_sync_enabled column ensured on machines table';
END $$;

GRANT ALL PRIVILEGES ON TABLE machines TO shatter_user;
