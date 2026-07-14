@echo off
REM NetGuard-AI Step 4: verify API tests, then print how to start the server
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

echo [1/2] Running API + unit tests ...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :fail

echo [2/2] Starting API on http://127.0.0.1:8000 ...
echo Open docs at http://127.0.0.1:8000/docs
echo Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
exit /b 0

:fail
echo.
echo Step 4 tests failed. See errors above.
pause
exit /b 1
