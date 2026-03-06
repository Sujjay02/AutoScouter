#!/usr/bin/env bash
# Build frontend and serve everything from FastAPI
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Build frontend
cd "$REPO_ROOT/frontend"
[ ! -d "node_modules" ] && npm install
npm run build

# Run backend (serves built frontend at /)
cd "$REPO_ROOT/backend"
[ ! -d ".venv" ] && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

echo "Starting production server on :8000..."
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
