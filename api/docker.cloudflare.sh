#!/bin/sh
set -eu

TUNNEL_FILE="${CLOUDFLARE_TUNNEL_URL_FILE:-/data/cloudflared/tunnel-url}"
WEBHOOK_PATH="${FLUTTERWAVE_WEBHOOK_PATH:-/api/payments/webhook/flutterwave}"

attempt=0
max_attempts="${CLOUDFLARE_WAIT_ATTEMPTS:-60}"
while [ ! -s "$TUNNEL_FILE" ]; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Cloudflare tunnel URL was not available at $TUNNEL_FILE" >&2
    exit 1
  fi
  sleep 1
done

CLOUDFLARE_TUNNEL_URL="$(tr -d '\r\n' < "$TUNNEL_FILE")"
case "$CLOUDFLARE_TUNNEL_URL" in
  https://*.trycloudflare.com) ;;
  *) echo "Invalid Cloudflare tunnel URL: $CLOUDFLARE_TUNNEL_URL" >&2; exit 1 ;;
esac

export CLOUDFLARE_TUNNEL_URL
export FLUTTERWAVE_WEBHOOK_URL="${CLOUDFLARE_TUNNEL_URL%/}/${WEBHOOK_PATH#/}"
exec /app/docker-entrypoint.sh "$@"
