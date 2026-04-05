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

: "${SHATTER_SC2_RELAY_ENABLED:=0}"
: "${SHATTER_SC2_RELAY_LISTEN_HOST:=0.0.0.0}"
: "${SHATTER_SC2_RELAY_LISTEN_PORT:=8082}"
: "${SHATTER_SC2_RELAY_TARGET_HOST:=}"
: "${SHATTER_SC2_RELAY_TARGET_PORT:=80}"

if [[ "$SHATTER_SC2_RELAY_ENABLED" != "1" ]]; then
  echo "SC2 relay disabled (SHATTER_SC2_RELAY_ENABLED != 1)"
  exit 0
fi

if [[ -z "$SHATTER_SC2_RELAY_TARGET_HOST" ]]; then
  echo "SC2 relay enabled but SHATTER_SC2_RELAY_TARGET_HOST is empty"
  exit 1
fi

LOG_DIR="$ROOT_DIR/.relay"
PID_FILE="$LOG_DIR/sc2-relay.pid"
LOG_FILE="$LOG_DIR/sc2-relay.log"
mkdir -p "$LOG_DIR"

if lsof -nP -iTCP:"$SHATTER_SC2_RELAY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "SC2 relay/listener already active on :$SHATTER_SC2_RELAY_LISTEN_PORT"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" >/dev/null 2>&1; then
    echo "SC2 relay process already running (pid $OLD_PID)"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

nohup python3 "$ROOT_DIR/scripts/tcp_relay.py" \
  --listen-host "$SHATTER_SC2_RELAY_LISTEN_HOST" \
  --listen-port "$SHATTER_SC2_RELAY_LISTEN_PORT" \
  --target-host "$SHATTER_SC2_RELAY_TARGET_HOST" \
  --target-port "$SHATTER_SC2_RELAY_TARGET_PORT" \
  >> "$LOG_FILE" 2>&1 &

RELAY_PID=$!
echo "$RELAY_PID" > "$PID_FILE"

for _ in {1..20}; do
  if lsof -nP -iTCP:"$SHATTER_SC2_RELAY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "SC2 relay started (pid $RELAY_PID): $SHATTER_SC2_RELAY_LISTEN_HOST:$SHATTER_SC2_RELAY_LISTEN_PORT -> $SHATTER_SC2_RELAY_TARGET_HOST:$SHATTER_SC2_RELAY_TARGET_PORT"
    exit 0
  fi
  sleep 0.2
done

echo "SC2 relay failed to start. Check $LOG_FILE"
exit 1
