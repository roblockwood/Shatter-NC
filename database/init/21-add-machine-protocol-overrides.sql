-- Add per-protocol machine endpoint overrides.
-- This keeps ip_address as the primary/display host while allowing Telnet/FTP/HTTP
-- to use different hosts or ports when needed (for example Docker Desktop relays).

ALTER TABLE machines ADD COLUMN IF NOT EXISTS telnet_host VARCHAR(255);
ALTER TABLE machines ADD COLUMN IF NOT EXISTS telnet_port INTEGER DEFAULT 10000;
ALTER TABLE machines ADD COLUMN IF NOT EXISTS ftp_host VARCHAR(255);
ALTER TABLE machines ADD COLUMN IF NOT EXISTS http_host VARCHAR(255);

UPDATE machines
SET telnet_port = 10000
WHERE telnet_port IS NULL;