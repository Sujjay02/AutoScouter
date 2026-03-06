#!/usr/bin/env bash
# Start backend and frontend in development mode
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Backend
cd "$REPO_ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

echo "Starting FastAPI backend on :8000..."
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Frontend
cd "$REPO_ROOT/frontend"
if [ ! -d "node_modules" ]; then
  npm install
fi

echo "Starting Vite frontend on :3000..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ AutoScouter running!"
echo "   Frontend: http://localhost:3000"
echo "   API:      http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
