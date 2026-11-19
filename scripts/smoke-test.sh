#!/usr/bin/env bash
# End-to-end smoke test: web client -> API -> PostgreSQL.
# Requires the stack to be running (docker compose up, or backend + vite locally).
# Usage: bash scripts/smoke-test.sh [WEB_URL] [API_URL]
set -euo pipefail

WEB_URL="${1:-http://localhost:5173}"
API_URL="${2:-http://localhost:8000}"
failures=0

check() {
  local description="$1" expected="$2" url="$3"
  local code
  code=$(curl -s -o /tmp/erms-smoke-body -w '%{http_code}' --max-time 10 "$url" || echo "000")
  if [[ "$code" == "$expected" ]]; then
    echo "  OK    $description ($code)"
  else
    echo "  FAIL  $description: expected $expected, got $code"
    head -c 500 /tmp/erms-smoke-body 2>/dev/null; echo
    failures=$((failures + 1))
  fi
}

echo "ERMS smoke test"
check "API liveness"                    200 "$API_URL/api/v1/health/live"
check "API readiness (DB migrated)"     200 "$API_URL/api/v1/health/ready"
check "Swagger UI"                      200 "$API_URL/api/v1/docs"
check "OpenAPI schema"                  200 "$API_URL/api/v1/openapi.json"
check "Web client"                      200 "$WEB_URL/"
check "Web -> API proxy -> DB"          200 "$WEB_URL/api/v1/health/ready"

if [[ $failures -gt 0 ]]; then
  echo "$failures check(s) failed"
  exit 1
fi
echo "All checks passed"
