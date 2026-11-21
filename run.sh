#!/usr/bin/env bash
# Starts the API (FastAPI) and the static frontend together. Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
# SIGNING_KEY (verify X-Signature-256) and REQUIRE_SIGNATURE=1 (reject unsigned posts) pass through from the environment.
export CORS_ORIGINS="http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}"

pids=()
cleanup() {
  trap - EXIT INT TERM
  for pid in "${pids[@]}"; do pkill -P "$pid" 2>/dev/null || true; kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run uvicorn app.main:app --port "$API_PORT" --reload & pids+=($!)
uv run python -m http.server "$WEB_PORT" --bind 127.0.0.1 --directory frontend >/dev/null 2>&1 & pids+=($!)

echo
echo "  API:      http://127.0.0.1:${API_PORT}/docs"
echo "  Frontend: http://localhost:${WEB_PORT}/?api=http://127.0.0.1:${API_PORT}"
echo
wait
