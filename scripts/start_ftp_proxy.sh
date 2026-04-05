#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${SHATTER_FTP_PROXY_ENABLED:=0}"
: "${SHATTER_FTP_PROXY_LISTEN_HOST:=0.0.0.0}"
: "${SHATTER_FTP_PROXY_LISTEN_PORT:=2121}"
: "${SHATTER_FTP_PROXY_TARGET_HOST:=}"
: "${SHATTER_FTP_PROXY_TARGET_PORT:=21}"
: "${SHATTER_FTP_PROXY_DATA_LISTEN_HOST:=0.0.0.0}"
: "${SHATTER_FTP_PROXY_DATA_TIMEOUT:=30}"
: "${SHATTER_FTP_PROXY_ADVERTISE_HOST:=}"

if [[ "$SHATTER_FTP_PROXY_ENABLED" != "1" ]]; then
  echo "FTP proxy disabled (SHATTER_FTP_PROXY_ENABLED != 1)"
  exit 0
fi

if [[ -z "$SHATTER_FTP_PROXY_TARGET_HOST" ]]; then
  echo "FTP proxy enabled but SHATTER_FTP_PROXY_TARGET_HOST is empty"
  exit 1
fi

LOG_DIR="$ROOT_DIR/.relay"
PID_FILE="$LOG_DIR/ftp-proxy.pid"
LOG_FILE="$LOG_DIR/ftp-proxy.log"
mkdir -p "$LOG_DIR"

if lsof -nP -iTCP:"$SHATTER_FTP_PROXY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "FTP proxy/listener already active on :$SHATTER_FTP_PROXY_LISTEN_PORT"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" >/dev/null 2>&1; then
    echo "FTP proxy process already running (pid $OLD_PID)"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if [[ -n "$SHATTER_FTP_PROXY_ADVERTISE_HOST" ]]; then
  nohup python3 "$ROOT_DIR/scripts/ftp_pasv_proxy.py" \
    --listen-host "$SHATTER_FTP_PROXY_LISTEN_HOST" \
    --listen-port "$SHATTER_FTP_PROXY_LISTEN_PORT" \
    --target-host "$SHATTER_FTP_PROXY_TARGET_HOST" \
    --target-port "$SHATTER_FTP_PROXY_TARGET_PORT" \
    --data-listen-host "$SHATTER_FTP_PROXY_DATA_LISTEN_HOST" \
    --data-timeout "$SHATTER_FTP_PROXY_DATA_TIMEOUT" \
    --advertise-host "$SHATTER_FTP_PROXY_ADVERTISE_HOST" \
    >> "$LOG_FILE" 2>&1 &
else
  nohup python3 "$ROOT_DIR/scripts/ftp_pasv_proxy.py" \
    --listen-host "$SHATTER_FTP_PROXY_LISTEN_HOST" \
    --listen-port "$SHATTER_FTP_PROXY_LISTEN_PORT" \
    --target-host "$SHATTER_FTP_PROXY_TARGET_HOST" \
    --target-port "$SHATTER_FTP_PROXY_TARGET_PORT" \
    --data-listen-host "$SHATTER_FTP_PROXY_DATA_LISTEN_HOST" \
    --data-timeout "$SHATTER_FTP_PROXY_DATA_TIMEOUT" \
    >> "$LOG_FILE" 2>&1 &
fi

PROXY_PID=$!
echo "$PROXY_PID" > "$PID_FILE"

for _ in {1..20}; do
  if lsof -nP -iTCP:"$SHATTER_FTP_PROXY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "FTP proxy started (pid $PROXY_PID): $SHATTER_FTP_PROXY_LISTEN_HOST:$SHATTER_FTP_PROXY_LISTEN_PORT -> $SHATTER_FTP_PROXY_TARGET_HOST:$SHATTER_FTP_PROXY_TARGET_PORT"
    exit 0
  fi
  sleep 0.2
done

echo "FTP proxy failed to start. Check $LOG_FILE"
exit 1
