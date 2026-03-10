#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Healthcare Risk Prediction – local dev startup script
#  Usage:  ./start.sh
#  Stops:  Ctrl+C  (shuts down both servers cleanly)
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

# ── free ports if already in use ────────────────────────────
echo "⏳  Checking ports 8000 and 8001..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 1

# ── start FastAPI (port 8000) ────────────────────────────────
echo "🚀  Starting FastAPI backend on http://localhost:8000"
"$PYTHON" -m uvicorn fastapi_backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir "$REPO_DIR/fastapi_backend" &
FASTAPI_PID=$!

# give it a moment before starting Django
sleep 2

# ── start Django (port 8001) ────────────────────────────────
echo "🌐  Starting Django UI       on http://localhost:8001"
"$PYTHON" "$REPO_DIR/django_ui/manage.py" runserver 0.0.0.0:8001 &
DJANGO_PID=$!

# ── wait for both to be ready ───────────────────────────────
echo ""
echo "⏳  Waiting for servers to come up..."
for i in $(seq 1 10); do
  sleep 1
  FA_OK=false
  DJ_OK=false
  curl -sf http://localhost:8000/ -o /dev/null 2>/dev/null && FA_OK=true
  curl -sf http://localhost:8001/ -o /dev/null 2>/dev/null && DJ_OK=true
  if $FA_OK && $DJ_OK; then break; fi
done

echo ""
echo "────────────────────────────────────────────────"
echo "  ✅  FastAPI API  →  http://localhost:8000"
echo "  ✅  Django UI    →  http://localhost:8001"
echo "  📖  API docs     →  http://localhost:8000/docs"
echo "────────────────────────────────────────────────"
echo "  Press Ctrl+C to stop both servers"
echo ""

# ── trap Ctrl+C to shut both down cleanly ───────────────────
cleanup() {
  echo ""
  echo "🛑  Shutting down servers..."
  kill "$FASTAPI_PID" "$DJANGO_PID" 2>/dev/null || true
  wait "$FASTAPI_PID" "$DJANGO_PID" 2>/dev/null || true
  echo "👋  Done."
}
trap cleanup INT TERM

wait
