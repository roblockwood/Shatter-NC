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

: "${SHATTER_TELNET_RELAY_ENABLED:=0}"
: "${SHATTER_TELNET_RELAY_LISTEN_HOST:=0.0.0.0}"
: "${SHATTER_TELNET_RELAY_LISTEN_PORT:=10000}"
: "${SHATTER_TELNET_RELAY_TARGET_HOST:=}"
: "${SHATTER_TELNET_RELAY_TARGET_PORT:=10000}"

if [[ "$SHATTER_TELNET_RELAY_ENABLED" != "1" ]]; then
  echo "Telnet relay disabled (SHATTER_TELNET_RELAY_ENABLED != 1)"
  exit 0
fi

if [[ -z "$SHATTER_TELNET_RELAY_TARGET_HOST" ]]; then
  echo "Telnet relay enabled but SHATTER_TELNET_RELAY_TARGET_HOST is empty"
  exit 1
fi

LOG_DIR="$ROOT_DIR/.relay"
PID_FILE="$LOG_DIR/telnet-relay.pid"
LOG_FILE="$LOG_DIR/telnet-relay.log"
mkdir -p "$LOG_DIR"

# If another process is already listening on the relay port, keep it and continue.
if lsof -nP -iTCP:"$SHATTER_TELNET_RELAY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Telnet relay/listener already active on :$SHATTER_TELNET_RELAY_LISTEN_PORT"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" >/dev/null 2>&1; then
    echo "Telnet relay process already running (pid $OLD_PID)"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

nohup python3 "$ROOT_DIR/scripts/tcp_relay.py" \
  --listen-host "$SHATTER_TELNET_RELAY_LISTEN_HOST" \
  --listen-port "$SHATTER_TELNET_RELAY_LISTEN_PORT" \
  --target-host "$SHATTER_TELNET_RELAY_TARGET_HOST" \
  --target-port "$SHATTER_TELNET_RELAY_TARGET_PORT" \
  >> "$LOG_FILE" 2>&1 &

RELAY_PID=$!
echo "$RELAY_PID" > "$PID_FILE"

for _ in {1..20}; do
  if lsof -nP -iTCP:"$SHATTER_TELNET_RELAY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Telnet relay started (pid $RELAY_PID): $SHATTER_TELNET_RELAY_LISTEN_HOST:$SHATTER_TELNET_RELAY_LISTEN_PORT -> $SHATTER_TELNET_RELAY_TARGET_HOST:$SHATTER_TELNET_RELAY_TARGET_PORT"
    exit 0
  fi
  sleep 0.2
done

echo "Telnet relay failed to start. Check $LOG_FILE"
exit 1
