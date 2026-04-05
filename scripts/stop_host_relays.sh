#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/stop_ftp_proxy.sh || true
./scripts/stop_telnet_relay.sh || true
./scripts/stop_sc2_relay.sh || true

echo "Host relay/proxy stop complete"
