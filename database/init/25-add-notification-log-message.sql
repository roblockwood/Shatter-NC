-- Add delivered message text to notification delivery log

ALTER TABLE notification_log
ADD COLUMN IF NOT EXISTS message TEXT;

DO $$
BEGIN
    RAISE NOTICE 'Added notification_log.message column';
END $$;
