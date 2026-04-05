#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.relay/ftp-proxy.pid"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" >/dev/null 2>&1; then
    kill "$PID" || true
    echo "Stopped FTP proxy pid $PID"
  fi
  rm -f "$PID_FILE"
fi

echo "FTP proxy stop complete"
