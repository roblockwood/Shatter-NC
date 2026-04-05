#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/start_telnet_relay.sh
./scripts/start_ftp_proxy.sh
./scripts/start_sc2_relay.sh

echo "Host relay/proxy startup complete"
