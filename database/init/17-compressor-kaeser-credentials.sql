-- Copyright (C) 2024 Shatter-NC contributors
-- SPDX-License-Identifier: AGPL-3.0-or-later

-- Kaeser Connect credentials stored in Shatter DB; backend polls SIGMA CONTROL 2 directly (see integrations/kaeser_sc2/client.py).

ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_connect_base_url VARCHAR(512);
ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_username VARCHAR(255);
ALTER TABLE compressors ADD COLUMN IF NOT EXISTS kaeser_password VARCHAR(255);
