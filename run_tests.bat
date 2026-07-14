@echo off
REM Run the test suite
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv — run setup.bat first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pytest -q
exit /b %ERRORLEVEL%
