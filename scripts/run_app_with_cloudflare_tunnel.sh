#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PORT="${APP_PORT:-5000}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
LOCAL_URL="http://localhost:${APP_PORT}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. Install Cloudflare Tunnel first."
  exit 1
fi

if [ ! -x "${PYTHON_BIN}" ]; then
  PYTHON_BIN="python"
fi

cd "${ROOT_DIR}"

echo "Starting Pollination Monitoring System on ${LOCAL_URL}"
APP_PORT="${APP_PORT}" "${PYTHON_BIN}" app.py &
APP_PID="$!"

cleanup() {
  if kill -0 "${APP_PID}" >/dev/null 2>&1; then
    kill "${APP_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

sleep 5

echo
echo "Starting Cloudflare quick tunnel for ${LOCAL_URL}"
echo "Copy the generated https://*.trycloudflare.com URL."
echo

cloudflared tunnel --url "${LOCAL_URL}"
