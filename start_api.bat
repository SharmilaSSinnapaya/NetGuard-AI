@echo off
REM Start NetGuard-AI FastAPI only (leave this window open)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [.venv missing] Run run_step2.bat first.
  pause
  exit /b 1
)

if not exist "models\artifacts\supervised_ids.joblib" (
  echo [models missing] Run run_step3.bat first.
  pause
  exit /b 1
)

echo Starting API on http://127.0.0.1:8000
echo Docs: http://127.0.0.1:8000/docs
echo Keep this window OPEN, then run run_step5.bat in another CMD.
echo Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
exit /b %ERRORLEVEL%
