@echo off
REM Train supervised + anomaly models into models\artifacts
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv — run setup.bat first.
  pause
  exit /b 1
)

if not exist "data\processed\arrays.npz" (
  echo Missing processed data — run setup.bat first.
  pause
  exit /b 1
)

echo Training models ...
".venv\Scripts\python.exe" scripts\train.py
if errorlevel 1 goto :fail

echo Running tests ...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :fail

echo.
echo Training complete. Start the API with start_api.bat
pause
exit /b 0

:fail
echo.
echo Training failed. See errors above.
pause
exit /b 1
