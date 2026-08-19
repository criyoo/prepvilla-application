#!/bin/sh
set -eu

if [ -n "${POSTGRES_HOST:-}" ]; then
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  tries=0
  until python -c "import socket; s=socket.create_connection(('${POSTGRES_HOST}', int('${POSTGRES_PORT:-5432}')), 3); s.close()" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "${tries}" -ge 30 ]; then
      echo "PostgreSQL did not become ready in time." >&2
      exit 1
    fi
    sleep 1
  done
fi

if [ "${MIGRATE_ON_STARTUP:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${SEED_DEMO_ACCOUNTS_ON_STARTUP:-${SEED_DEMO_ACCOUNTS:-0}}" = "1" ]; then
  python manage.py seed_demo_data
fi

exec python manage.py runserver 0.0.0.0:8000
