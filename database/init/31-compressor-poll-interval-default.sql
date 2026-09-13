-- Copyright (C) 2024 Shatter-NC contributors
-- SPDX-License-Identifier: AGPL-3.0-or-later

-- Default Kaeser compressor poll interval: 30 seconds (matches CNC tool poll cadence).
-- Existing compressor rows keep their configured interval; only new rows pick up the default.

ALTER TABLE compressors ALTER COLUMN poll_interval_seconds SET DEFAULT 30;
