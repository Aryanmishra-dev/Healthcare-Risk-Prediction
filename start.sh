#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Healthcare Risk Prediction – local dev startup script
#  Usage:  ./start.sh
#  Stops:  Ctrl+C  (shuts down cleanly)
# ─────────────────────────────────────────────────────────────

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO_DIR/.venv-1"

# ── sanity checks ────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
  echo "❌  Virtual environment not found at .venv-1"
  echo "    Create it first:  conda create -p .venv-1 python=3.13"
  exit 1
fi

if [ ! -f "$VENV/bin/python" ]; then
  echo "❌  Python binary not found inside .venv-1"
  exit 1
fi

PYTHON="$VENV/bin/python"

# ── free port if already in use ─────────────────────────────
echo "⏳  Checking port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1

# ── start unified FastAPI + HTMX app (port 8000) ────────────
echo "🚀  Starting HealthPredict AI on http://localhost:8000"
echo "    (bound to 127.0.0.1 — not publicly accessible)"
"$PYTHON" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --reload-dir "$REPO_DIR/app" \
  --reload-dir "$REPO_DIR/fastapi_backend" &
APP_PID=$!

# ── wait for server to be ready ─────────────────────────────
echo ""
echo "⏳  Waiting for server to come up..."
for i in $(seq 1 15); do
  sleep 1
  if curl -sf http://localhost:8000/ -o /dev/null 2>/dev/null; then break; fi
done

echo ""
echo "────────────────────────────────────────────────"
echo "  ✅  UI + API     →  http://localhost:8000"
echo "  📖  API docs     →  http://localhost:8000/api/docs"
echo "────────────────────────────────────────────────"
echo "  Press Ctrl+C to stop the server"
echo ""

# ── trap Ctrl+C to shut down cleanly ────────────────────────
cleanup() {
  echo ""
  echo "🛑  Shutting down server..."
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  echo "👋  Done."
}
trap cleanup INT TERM

wait
