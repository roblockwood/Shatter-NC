-- Kaeser SIGMA CONTROL 2 compressors via Brown-Industries kaeser-sc2-api sidecar (REST + MQTT).
-- SC2 web UI (Kaeser Connect) is reached by the sidecar; Shatter talks to sidecar + MQTT broker only.

CREATE TABLE IF NOT EXISTS compressors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45) NOT NULL,
    sidecar_rest_base_url VARCHAR(512) NOT NULL,
    mqtt_topic_root VARCHAR(255) NOT NULL,
    poll_interval_seconds INTEGER NOT NULL DEFAULT 5,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    tags JSONB,
    layout_config JSONB,
    kaeser_connect_base_url VARCHAR(512),
    kaeser_username VARCHAR(255),
    kaeser_password VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_compressors_enabled ON compressors(enabled);

GRANT ALL PRIVILEGES ON TABLE compressors TO shatter_user;
GRANT USAGE, SELECT ON SEQUENCE compressors_id_seq TO shatter_user;

-- Status transitions (TimescaleDB hypertable), analogous to machine_status_events
CREATE TABLE IF NOT EXISTS compressor_status_events (
    time TIMESTAMPTZ NOT NULL,
    compressor_id INTEGER NOT NULL REFERENCES compressors(id) ON DELETE CASCADE,
    status VARCHAR(80) NOT NULL,
    previous_status VARCHAR(80),
    metrics JSONB,
    PRIMARY KEY (time, compressor_id)
);

SELECT create_hypertable('compressor_status_events', 'time', if_not_exists => TRUE);
SELECT add_retention_policy('compressor_status_events', INTERVAL '1 year', if_not_exists => TRUE);

ALTER TABLE compressor_status_events SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'compressor_id'
);
SELECT add_compression_policy('compressor_status_events', INTERVAL '7 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_compressor_status_comp_time ON compressor_status_events(compressor_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_compressor_status_status ON compressor_status_events(status);

GRANT ALL PRIVILEGES ON TABLE compressor_status_events TO shatter_user;
