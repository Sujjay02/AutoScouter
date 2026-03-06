@echo off
:: FRC AutoScouter — Windows production build + serve
setlocal

set REPO_ROOT=%~dp0..

:: ── Build frontend ────────────────────────────────────────────────────────────
cd /d "%REPO_ROOT%\frontend"

if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
)

echo Building frontend...
npm run build

:: ── Start backend (serves built frontend at /) ────────────────────────────────
cd /d "%REPO_ROOT%\backend"

if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

echo Starting production server on :8000...
.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000
