#!/bin/bash
# Entrypoint for the relay container.
# Starts all relays and keeps the container alive.
set -euo pipefail

exec /app/scripts/start_host_relays.sh &

# Keep container running - the background processes (nohup'd relays) will continue
# The container stays alive while this sleep runs (ignored on signals)
tail -f /dev/null
