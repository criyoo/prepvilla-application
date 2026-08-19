#!/bin/sh
set -eu

if [ "${MIGRATE_ON_STARTUP:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${COLLECTSTATIC_ON_STARTUP:-0}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
