#!/usr/bin/env bash
# End-to-end authentication smoke test against the docker compose stack:
# bootstrap -> login through the web proxy -> password-recovery email reaches Mailpit.
# Creates an organization: run it only on a disposable environment (CI or a fresh local stack).
# Usage: ERMS_ADMIN_PASSWORD=... bash scripts/smoke-auth.sh [WEB_URL] [MAILPIT_URL]
set -euo pipefail

WEB_URL="${1:-http://localhost:5173}"
MAILPIT_URL="${2:-http://localhost:8025}"
: "${ERMS_ADMIN_PASSWORD:?Set ERMS_ADMIN_PASSWORD}"
ADMIN_EMAIL="smoke-admin@example.com"

echo "ERMS auth smoke test"

docker compose exec -T -e ERMS_ADMIN_PASSWORD backend python -m app.cli bootstrap \
  --org-name "Organización de humo (CI)" --org-slug smoke-ci \
  --admin-email "$ADMIN_EMAIL" --admin-name "Administrador de humo"

login=$(curl -s -w '\n%{http_code}' -X POST "$WEB_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ERMS_ADMIN_PASSWORD\"}")
code=$(tail -n1 <<<"$login")
body=$(head -n -1 <<<"$login")
[[ "$code" == "200" ]] || { echo "  FAIL  login returned $code: $body"; exit 1; }
grep -q '"must_change_password":true' <<<"$body" || { echo "  FAIL  temporary password not flagged"; exit 1; }
echo "  OK    login through web proxy (temporary password flagged)"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$WEB_URL/api/v1/auth/password/forgot" \
  -H 'Content-Type: application/json' -d "{\"email\":\"$ADMIN_EMAIL\"}")
[[ "$code" == "202" ]] || { echo "  FAIL  forgot password returned $code"; exit 1; }

for _ in $(seq 1 10); do
  if curl -s "$MAILPIT_URL/api/v1/messages" | grep -q "$ADMIN_EMAIL"; then
    echo "  OK    password recovery email delivered to Mailpit"
    echo "All auth checks passed"
    exit 0
  fi
  sleep 1
done
echo "  FAIL  recovery email not found in Mailpit"
exit 1
