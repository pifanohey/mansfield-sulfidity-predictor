#!/bin/bash
# ──────────────────────────────────────────────
# Sulfidity Predictor — one-command launcher
# ──────────────────────────────────────────────
#   Backend  → http://localhost:8005
#   Frontend → http://localhost:3005
# ──────────────────────────────────────────────

set -e

# Raise file-descriptor limit (prevents EMFILE errors in Next.js watcher)
ulimit -n 65536 2>/dev/null || ulimit -n 10240 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    echo "Done."
    exit 0
}
trap cleanup INT TERM

# ── Start backend ────────────────────────────
echo "Starting backend on http://localhost:8005 ..."
cd "$SCRIPT_DIR/backend"
python3 -m uvicorn app.main:app --reload --port 8005 &
BACKEND_PID=$!
sleep 2

# Quick health check
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "ERROR: Backend failed to start."
    exit 1
fi
echo "Backend is running (PID $BACKEND_PID)."

# ── Start frontend (foreground) ──────────────
echo ""
echo "Starting frontend on http://localhost:3005 ..."
echo "──────────────────────────────────────────────"
cd "$SCRIPT_DIR/frontend"
npm run dev
