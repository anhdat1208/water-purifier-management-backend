#!/bin/sh
set -e

if [ "${DATABASE_URL#sqlite}" = "$DATABASE_URL" ]; then
  echo "==> Running database migrations..."
  alembic upgrade head
fi

exec "$@"
