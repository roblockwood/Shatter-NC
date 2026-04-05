-- Tiered compressor samples: 1-minute continuous aggregate for history; shorter raw retention;
-- compress raw chunks sooner. Align COMPRESSOR_STATUS_SAMPLES_RAW_DAYS in app settings with raw retention.

-- Replace retention: keep high-res raw for 14 days (was 30).
SELECT remove_retention_policy('compressor_status_samples', if_exists => TRUE);
SELECT add_retention_policy('compressor_status_samples', INTERVAL '14 days', if_not_exists => TRUE);

-- Compress raw hypertable chunks after 1 day on disk (was 3).
SELECT remove_compression_policy('compressor_status_samples', if_exists => TRUE);
SELECT add_compression_policy('compressor_status_samples', INTERVAL '1 day', if_not_exists => TRUE);

-- Downsampled history (last row per minute per compressor) for ranges older than raw retention.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.continuous_aggregates
    WHERE view_name = 'compressor_status_samples_1min'
  ) THEN
    EXECUTE $q$
      CREATE MATERIALIZED VIEW compressor_status_samples_1min
      WITH (timescaledb.continuous) AS
      SELECT
        time_bucket(INTERVAL '1 minute', time) AS bucket,
        compressor_id,
        last(status, time) AS status,
        last(metrics, time) AS metrics
      FROM compressor_status_samples
      GROUP BY 1, 2
      WITH NO DATA
    $q$;
  END IF;
END $$;

-- Include data not yet fully materialized so recent windows stay consistent with refresh lag.
ALTER MATERIALIZED VIEW compressor_status_samples_1min SET (timescaledb.materialized_only = false);

SELECT add_continuous_aggregate_policy(
  'compressor_status_samples_1min',
  start_offset => INTERVAL '3 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '10 minutes',
  if_not_exists => TRUE
);

-- Longer retention for rolled-up data (adjust as needed).
SELECT add_retention_policy('compressor_status_samples_1min', INTERVAL '400 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_compressor_samples_1min_comp_bucket
  ON compressor_status_samples_1min (compressor_id, bucket DESC);

GRANT SELECT ON compressor_status_samples_1min TO shatter_user;

-- Initial backfill (may take time on large DBs).
CALL refresh_continuous_aggregate('compressor_status_samples_1min', NULL, NULL);
