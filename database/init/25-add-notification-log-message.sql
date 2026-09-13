-- Copyright (C) 2024 Shatter-NC contributors
-- SPDX-License-Identifier: AGPL-3.0-or-later

-- Add delivered message text to notification delivery log

ALTER TABLE notification_log
ADD COLUMN IF NOT EXISTS message TEXT;

DO $$
BEGIN
    RAISE NOTICE 'Added notification_log.message column';
END $$;
