#!/bin/sh
# Container entrypoint for the ERMS API.
# - RUN_MIGRATIONS=true applies Alembic migrations before starting (docker compose).
#   On Railway, migrations run as the pre-deploy command instead.
# - PORT is provided by Railway; defaults to 8000 locally.
# Extra arguments are passed to uvicorn (e.g. --reload in development).
set -eu

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  "$@"
