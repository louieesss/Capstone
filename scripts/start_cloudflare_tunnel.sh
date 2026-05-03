#!/usr/bin/env bash
set -euo pipefail

APP_PORT="${APP_PORT:-5000}"
LOCAL_URL="http://localhost:${APP_PORT}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. Install Cloudflare Tunnel first."
  exit 1
fi

echo "Starting Cloudflare quick tunnel for ${LOCAL_URL}"
echo "Keep this terminal open while you use the public URL."
echo

cloudflared tunnel --url "${LOCAL_URL}"
