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
: "${SHATTER_TELNET_RELAY_LISTEN_PORT:=10000}"
: "${SHATTER_FTP_PROXY_ENABLED:=0}"
: "${SHATTER_FTP_PROXY_LISTEN_PORT:=2121}"
: "${SHATTER_SC2_RELAY_ENABLED:=0}"
: "${SHATTER_SC2_RELAY_LISTEN_PORT:=8082}"

status=0

if [[ "$SHATTER_TELNET_RELAY_ENABLED" == "1" ]]; then
  if lsof -nP -iTCP:"$SHATTER_TELNET_RELAY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "OK: Telnet relay listening on :$SHATTER_TELNET_RELAY_LISTEN_PORT"
  else
    echo "FAIL: Telnet relay not listening on :$SHATTER_TELNET_RELAY_LISTEN_PORT"
    status=1
  fi
else
  echo "SKIP: Telnet relay disabled"
fi

if [[ "$SHATTER_FTP_PROXY_ENABLED" == "1" ]]; then
  if lsof -nP -iTCP:"$SHATTER_FTP_PROXY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "OK: FTP proxy listening on :$SHATTER_FTP_PROXY_LISTEN_PORT"
  else
    echo "FAIL: FTP proxy not listening on :$SHATTER_FTP_PROXY_LISTEN_PORT"
    status=1
  fi
else
  echo "SKIP: FTP proxy disabled"
fi

if [[ "$SHATTER_SC2_RELAY_ENABLED" == "1" ]]; then
  if lsof -nP -iTCP:"$SHATTER_SC2_RELAY_LISTEN_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "OK: SC2 relay listening on :$SHATTER_SC2_RELAY_LISTEN_PORT"
  else
    echo "FAIL: SC2 relay not listening on :$SHATTER_SC2_RELAY_LISTEN_PORT"
    status=1
  fi
else
  echo "SKIP: SC2 relay disabled"
fi

exit $status
