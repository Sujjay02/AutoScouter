@echo off
:: FRC AutoScouter — Windows development launcher
setlocal

set REPO_ROOT=%~dp0..

:: ── Backend ──────────────────────────────────────────────────────────────────
cd /d "%REPO_ROOT%\backend"

if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

echo Starting FastAPI backend on :8000...
start "AutoScouter Backend" .venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload

:: ── Frontend ─────────────────────────────────────────────────────────────────
cd /d "%REPO_ROOT%\frontend"

if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
)

echo Starting Vite frontend on :3000...
start "AutoScouter Frontend" npm run dev

echo.
echo  AutoScouter running!
echo    Frontend: http://localhost:3000
echo    API:      http://localhost:8000
echo    API docs: http://localhost:8000/docs
echo.
echo  Close the two terminal windows to stop.
