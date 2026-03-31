-- High-frequency compressor status samples (MQTT operational-data path; ingest interval from app env).
-- Separate from compressor_status_events (transition log on poll). Retention/compression superseded by 19-*.sql.

CREATE TABLE IF NOT EXISTS compressor_status_samples (
    time TIMESTAMPTZ NOT NULL,
    compressor_id INTEGER NOT NULL REFERENCES compressors(id) ON DELETE CASCADE,
    status VARCHAR(80) NOT NULL,
    metrics JSONB,
    PRIMARY KEY (time, compressor_id)
);

SELECT create_hypertable('compressor_status_samples', 'time', if_not_exists => TRUE);
SELECT add_retention_policy('compressor_status_samples', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE compressor_status_samples SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'compressor_id'
);
SELECT add_compression_policy('compressor_status_samples', INTERVAL '3 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_compressor_samples_comp_time ON compressor_status_samples(compressor_id, time DESC);

GRANT ALL PRIVILEGES ON TABLE compressor_status_samples TO shatter_user;
