@echo off
REM NetGuard-AI Step 3: train models (assumes Step 2 data already processed)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [.venv missing] Run run_step2.bat first.
  pause
  exit /b 1
)

if not exist "data\processed\arrays.npz" (
  echo [processed data missing] Run run_step2.bat first.
  pause
  exit /b 1
)

echo [1/2] Training supervised + anomaly models ...
".venv\Scripts\python.exe" scripts\train.py
if errorlevel 1 goto :fail

echo [2/2] Running tests ...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :fail

echo.
echo Step 3 finished successfully.
echo Models are in models\artifacts\
pause
exit /b 0

:fail
echo.
echo Step 3 failed. See errors above.
pause
exit /b 1
