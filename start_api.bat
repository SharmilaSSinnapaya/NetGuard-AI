@echo off
REM Start FastAPI inference server (leave this window open)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv — run setup.bat first.
  pause
  exit /b 1
)

if not exist "models\artifacts\supervised_ids.joblib" (
  echo Missing trained models — run train_models.bat first.
  pause
  exit /b 1
)

echo Starting API on http://127.0.0.1:8000
echo Docs: http://127.0.0.1:8000/docs
echo Keep this window open, then run run_dashboard.bat in another terminal.
echo Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
exit /b %ERRORLEVEL%
