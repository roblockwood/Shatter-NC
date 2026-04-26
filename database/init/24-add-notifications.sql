-- Add notification channels and rules for machine status alerts

CREATE TABLE IF NOT EXISTS notification_channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(20) NOT NULL DEFAULT 'email',
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notification_channels_enabled
    ON notification_channels(enabled);

CREATE TABLE IF NOT EXISTS notification_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    machine_id INTEGER REFERENCES machines(id) ON DELETE CASCADE,
    trigger_type VARCHAR(30) NOT NULL DEFAULT 'status_change',
    trigger_config JSONB NOT NULL DEFAULT '{}',
    channel_ids INTEGER[] NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notification_rules_machine
    ON notification_rules(machine_id);
CREATE INDEX IF NOT EXISTS idx_notification_rules_enabled
    ON notification_rules(enabled);

CREATE TABLE IF NOT EXISTS notification_log (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES notification_rules(id) ON DELETE SET NULL,
    channel_id INTEGER REFERENCES notification_channels(id) ON DELETE SET NULL,
    machine_id INTEGER REFERENCES machines(id) ON DELETE SET NULL,
    event_type VARCHAR(30) NOT NULL,
    event_data JSONB,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at
    ON notification_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_log_machine
    ON notification_log(machine_id, sent_at DESC);

GRANT ALL PRIVILEGES ON TABLE notification_channels TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE notification_rules TO shatter_user;
GRANT ALL PRIVILEGES ON TABLE notification_log TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE notification_channels_id_seq TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE notification_rules_id_seq TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE notification_log_id_seq TO shatter_user;

DO $$
BEGIN
    RAISE NOTICE 'Notification tables created';
END $$;
